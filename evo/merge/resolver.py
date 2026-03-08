"""LLM merger: applies, resolves, deduplicates, and compacts patches in one session.

Works like a teacher — loops calling patch_prompt / patch_tool until satisfied.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Callable, Optional

from openai import OpenAI, RateLimitError

from evo.config import (
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, TEACHER_MODEL,
    API_RETRIES, API_BACKOFF, API_RATE_LIMIT_RETRIES, API_RATE_LIMIT_BACKOFF,
    rate_limit_delay,
)
from evo.models import FixResult, Patch
from evo.reflection.formatting import SCHEMA_INDENT, format_preprocessors
from evo.reflection.patches import apply_one_patch, serialize_schema
from evo.reflection.preprocessor import DEFAULT_PREPROCESSOR
from evo.reflection.tools import PatchPrompt, PatchTool, PatchToolCode, TOOL_MODELS
from evo.session_log import (
    SessionData, SessionMessage, ToolCallFunction, ToolCallInfo,
    ResponseMeta, UsageInfo, now_iso, save_session,
)

log = logging.getLogger(__name__)

_client: Optional[OpenAI] = None
_client_lock = threading.Lock()


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    return _client


# Tools available to the merger (same as teacher, minus read_tool_code).
MERGER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "patch_prompt",
            "description": "Find-and-replace in the agent's system prompt. Use old_text='' to append.",
            "parameters": {
                "type": "object",
                "properties": {
                    "old_text": {"type": "string", "description": "Exact text to find ('' to append)."},
                    "new_text": {"type": "string", "description": "Replacement text."},
                },
                "required": ["old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "patch_tool",
            "description": "Find-and-replace in a tool's JSON schema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["tool_name", "old_text", "new_text"],
            },
        },
    },
]


MERGER_PROMPT = """\
You are an expert editor merging and consolidating patches into a customer service agent's system prompt.

Multiple teacher sessions independently fixed different task failures by proposing patches. \
Your job is to apply ALL of them into a single clean, consolidated prompt.

## Current System Prompt (before any patches from this round)

{current_prompt}

## Current Tool Schemas

{current_tools}

{current_preprocessors_section}

## Proposed Patches

The following patches were verified to fix their target tasks. Apply them all, \
then consolidate the result.

{patches_section}

## Instructions

1. **Apply** all proposed patches using patch_prompt / patch_tool. If two patches \
touch the same region, combine their intent into one replacement.
2. **Deduplicate**: if the prompt already contains a rule that a patch wants to add \
(or multiple patches add the same rule), consolidate into one clear statement.
3. **Compact**: tighten verbose additions. If a rule can be said in one sentence \
instead of a paragraph, do it.
4. **Preserve**: do NOT remove any rule with unique semantic purpose. Every proposed \
fix addresses a real failure — keep the intent of each one.
5. **Position**: place critical rules near the start or end of their section, not \
buried in the middle.

Call patch_prompt and patch_tool as many times as needed. You will get feedback \
after each call. Stop calling tools when you are satisfied with the result.
"""


def _format_proposed_patches(winners: list[FixResult]) -> str:
    """Format all proposed patches grouped by source task."""
    parts = []
    for fix in winners:
        lines = [f"### Task {fix.task_id}"]
        if fix.diagnosis:
            diag = fix.diagnosis[:600]
            lines.append(f"Diagnosis: {diag}")
        for i, p in enumerate(fix.patches, 1):
            if p.is_prompt:
                lines.append(f"  {i}. [instruction] patch_prompt:")
            elif p.is_tool_code:
                lines.append(f"  {i}. [guardrail] patch_tool_code({p.tool_name}):")
            else:
                lines.append(f"  {i}. [tool] patch_tool({p.tool_name}):")
            old_preview = p.old_text[:200] if p.old_text else "(append)"
            new_preview = p.new_text[:400]
            lines.append(f"     old: {old_preview!r}")
            lines.append(f"     new: {new_preview!r}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


class MergerSession:
    """Stateful conversation with the merger LLM.

    Works like TeacherSession: loops calling tools until done, logs as a session.
    """

    def __init__(
        self,
        system_prompt: str,
        tool_schemas: dict[str, dict],
        tool_code: Optional[dict[str, str]] = None,
        model: str = TEACHER_MODEL,
        on_message: Optional[Callable] = None,
        on_session: Optional[Callable] = None,
    ):
        self.session_id = f"merger_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.model = model
        self.status = "active"
        self.started_at = now_iso()
        self._on_message = on_message
        self._on_session = on_session

        self._history: list[dict] = []
        self._messages: list[SessionMessage] = []
        self._current_prompt = system_prompt
        self._current_tool_schemas = deepcopy(tool_schemas)
        self._current_tool_code: dict[str, str] = dict(tool_code) if tool_code else {}
        self._patches_applied: list[Patch] = []

    @property
    def current_prompt(self) -> str:
        return self._current_prompt

    @property
    def current_tool_schemas(self) -> dict[str, dict]:
        return self._current_tool_schemas

    @property
    def current_tool_code(self) -> dict[str, str]:
        return self._current_tool_code

    def _log_message(self, msg: SessionMessage) -> None:
        if not msg.ts:
            msg.ts = now_iso()
        self._messages.append(msg)
        self._save_log()
        if self._on_message:
            try:
                self._on_message(self, msg)
            except Exception:
                pass

    def _save_log(self) -> None:
        save_session(SessionData(
            session_id=self.session_id,
            session_type="merger",
            model=self.model,
            started_at=self.started_at,
            status=self.status,
            messages=self._messages,
        ))

    def merge(
        self,
        winners: list[FixResult],
        max_rounds: int = 15,
    ) -> list[Patch]:
        """Run the merger loop. Returns list of patches applied."""
        # Build initial prompt
        tools_str = json.dumps(
            list(self._current_tool_schemas.values()), indent=SCHEMA_INDENT,
        )
        preprocessors_str = format_preprocessors(self._current_tool_code)
        prep_section = ""
        if any(v != DEFAULT_PREPROCESSOR for v in self._current_tool_code.values()):
            prep_section = f"## Current Tool Preprocessors\n\n{preprocessors_str}"

        patches_section = _format_proposed_patches(winners)

        initial = MERGER_PROMPT.format(
            current_prompt=self._current_prompt,
            current_tools=tools_str,
            current_preprocessors_section=prep_section,
            patches_section=patches_section,
        )

        self._history.append({"role": "user", "content": initial})
        self._log_message(SessionMessage(role="user", content=initial))

        # Tool-calling loop (like teacher.reflect)
        client = _get_client()
        for round_idx in range(max_rounds):
            msg, response = self._call_llm(client)
            if msg is None:
                log.warning("[merger] LLM unreachable at round %d", round_idx)
                break

            # Log assistant response
            tc_info = None
            tc_api = None
            if msg.tool_calls:
                tc_info = [
                    ToolCallInfo(
                        id=tc.id,
                        function=ToolCallFunction(
                            name=tc.function.name,
                            arguments=tc.function.arguments,
                        ),
                    )
                    for tc in msg.tool_calls
                ]
                tc_api = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ]

            resp_meta = None
            if response and hasattr(response, "usage") and response.usage:
                resp_meta = ResponseMeta(
                    response_model=getattr(response, "model", None),
                    usage=UsageInfo(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    ),
                )

            api_msg: dict = {"role": "assistant"}
            if msg.content:
                api_msg["content"] = msg.content
            if tc_api:
                api_msg["tool_calls"] = tc_api
            self._history.append(api_msg)

            self._log_message(SessionMessage(
                role="assistant", content=msg.content or "",
                tool_calls=tc_info, meta=resp_meta,
            ))

            if not msg.tool_calls:
                break  # Merger is done

            # Apply each tool call with feedback
            for tc in msg.tool_calls:
                result_text = self._apply_tool_call(tc)
                self._history.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})
                self._log_message(SessionMessage(role="tool", tool_call_id=tc.id, content=result_text))

        self.status = "done"
        self._save_log()

        # Notify session callback
        if self._on_session:
            try:
                data = SessionData(
                    session_id=self.session_id,
                    session_type="merger",
                    model=self.model,
                    started_at=self.started_at,
                    status=self.status,
                    messages=self._messages,
                )
                self._on_session(self.session_id, data)
            except Exception:
                pass

        return list(self._patches_applied)

    def _call_llm(self, client: OpenAI):
        """Single LLM call with retry. 429s get extra retries with exponential backoff."""
        max_retries = API_RATE_LIMIT_RETRIES
        rate_limit_hits = 0
        attempt = 0
        while attempt < max_retries:
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=self._history,
                    tools=MERGER_TOOLS,
                    temperature=0.2,
                    timeout=60,
                )
                return response.choices[0].message, response
            except RateLimitError as e:
                rate_limit_hits += 1
                delay = rate_limit_delay(e, rate_limit_hits, API_RATE_LIMIT_BACKOFF)
                log.warning(
                    "[merger] 429 (attempt %d, rate-limit hit #%d), retrying in %.1fs: %s",
                    attempt + 1, rate_limit_hits, delay, e,
                )
                time.sleep(delay)
                attempt += 1
            except Exception as e:
                attempt += 1
                log.warning("[merger] API error (attempt %d/%d): %s", attempt, max_retries, e)
                if attempt >= API_RETRIES:
                    break
                time.sleep(API_BACKOFF * attempt)
        return None, None

    def _apply_tool_call(self, tc) -> str:
        """Apply a single tool call, mutate internal state, return feedback."""
        model_cls = TOOL_MODELS.get(tc.function.name)
        if model_cls is None:
            return f"Error: unknown tool '{tc.function.name}'."

        try:
            parsed = model_cls.model_validate_json(tc.function.arguments)
        except Exception as e:
            return f"Error: invalid arguments — {e}"

        if isinstance(parsed, PatchPrompt):
            patch = Patch(old_text=parsed.old_text, new_text=parsed.new_text)
        elif isinstance(parsed, PatchTool):
            patch = Patch(old_text=parsed.old_text, new_text=parsed.new_text,
                          tool_name=parsed.tool_name)
        elif isinstance(parsed, PatchToolCode):
            patch = Patch(old_text=parsed.old_text, new_text=parsed.new_text,
                          tool_name=parsed.tool_name, is_code=True)
        else:
            return f"Error: unsupported tool '{tc.function.name}'."

        self._current_prompt, self._current_tool_schemas, self._current_tool_code, ok, result = apply_one_patch(
            self._current_prompt, self._current_tool_schemas, patch, self._current_tool_code,
        )
        if ok:
            self._patches_applied.append(patch)
        return result
