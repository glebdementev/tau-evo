"""Teacher: sends a failed trace to the teacher model and gets back patches via tool-calling.

The TeacherSession maintains a conversation with the teacher model so that
when a patch fails validation, we can feed the result back and let the teacher
refine its approach — within the same context window.

Every message is logged with timestamps in full OpenAI format to JSON files.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Callable, Optional

log = logging.getLogger(__name__)

from openai import OpenAI
from openai.lib._tools import pydantic_function_tool
from pydantic import BaseModel, Field

from evo.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, TEACHER_MODEL
from evo.models import Patch
from evo.session_log import (
    now_iso, save_session,
    ErrorRecord, ResponseMeta, SessionData, SessionMessage, SessionSummary,
    ToolCallFunction, ToolCallInfo, UsageInfo,
)


_client: Optional[OpenAI] = None
_client_lock = threading.Lock()


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    return _client


# -- Tool definitions for the teacher -----------------------------------------

class PatchPrompt(BaseModel):
    """Replace text in the agent's system prompt. Use old_text='' and new_text='...' to insert new text at the end."""

    old_text: str = Field(
        description="Exact text to find in the current prompt. Empty string to append.",
    )
    new_text: str = Field(
        description="Replacement text. Empty string to delete the old_text.",
    )


class PatchTool(BaseModel):
    """Replace text in a tool's schema (description or parameter description)."""

    tool_name: str = Field(description="Name of the tool to patch.")
    old_text: str = Field(description="Exact text to find in the tool's schema JSON.")
    new_text: str = Field(description="Replacement text.")


TEACHER_TOOLS = [
    pydantic_function_tool(PatchPrompt, name="patch_prompt"),
    pydantic_function_tool(PatchTool, name="patch_tool"),
]

_TOOL_MODELS = {
    "patch_prompt": PatchPrompt,
    "patch_tool": PatchTool,
}


# -- Prompts -------------------------------------------------------------------

REFLECTION_PROMPT = """\
You are an expert at diagnosing failures in LLM-based customer service agents.

Below you will find:
1. The agent's current system prompt (with any previously applied patches already baked in).
2. The current tool schemas (with any previously applied patches already baked in).
3. A failed conversation trace between the agent and a user (simulated).
4. The task requirements that the agent was supposed to fulfil.
5. The reward breakdown showing exactly what went wrong.

Your job is to:
1. **Diagnose** the root cause of the failure in your message text. Classify it as one of:
   - TOOL_MISUSE: wrong tool, wrong parameters, missing tool call
   - POLICY_VIOLATION: skipped a validation step, broke a constraint
   - REASONING_ERROR: incorrect assumption, incomplete plan
   - COMMUNICATION_ERROR: confusing message, failed to guide user

2. **Fix** the issue by calling the provided tools:
   - `patch_prompt`: to edit the agent's system prompt (find-and-replace). Use old_text='' to append new text at the end.
   - `patch_tool`: to edit a tool's schema JSON (find-and-replace).

   You may call these tools multiple times across multiple rounds. After each round of tool calls, \
you will receive a result indicating whether each patch was applied successfully or failed (with the reason). \
If a patch fails, adjust your old_text to match the exact text in the prompt and try again. \
Take your time — think deeply about ALL the ways the agent could fail on this type of task, \
and address each one. Only stop calling tools when you are fully satisfied that your patches \
comprehensively fix the issue. Do not rush; thoroughness is more important than brevity.

---

## Agent System Prompt

{system_prompt}

## Tool Definitions

{tool_definitions}

## Failed Conversation Trace

{conversation_trace}

## Task Requirements

{task_requirements}

## Reward Breakdown

{reward_breakdown}
"""

RETRY_PROMPT = """\
Your previous patches did NOT fix the issue. The agent was re-run on the same task.

- Baseline reward: {baseline_reward:.2f}
- Reward after your patches: {patched_reward:.2f}

Here is the new conversation trace after applying your patches:

{new_trace}

And the new reward breakdown:

{new_reward}

Please analyse what went wrong with your previous patches and try again. \
Use the patch tools to make further edits to the prompt or tool schemas. \
Remember: the patches you made earlier are already applied — build on top of them or undo them if they were counterproductive.
"""


# -- Formatting helpers --------------------------------------------------------

def _format_messages(messages: list) -> str:
    """Format a list of tau2 message objects into a readable trace."""
    lines = []
    for msg in messages:
        role = msg.role if hasattr(msg, "role") else "unknown"
        content = getattr(msg, "content", None) or ""
        tool_calls = getattr(msg, "tool_calls", None)

        if role == "system":
            continue

        if tool_calls:
            for tc in tool_calls:
                lines.append(f"[assistant -> tool_call] {tc.name}({json.dumps(tc.arguments)})")
        elif role == "tool":
            tool_name = getattr(msg, "name", "tool")
            lines.append(f"[tool_result: {tool_name}] {content[:500]}")
        else:
            lines.append(f"[{role}] {content}")
    return "\n".join(lines)


def _format_tools(tools: list) -> str:
    """Format tool openai_schemas as readable JSON."""
    schemas = [t.openai_schema if hasattr(t, "openai_schema") else t for t in tools]
    return json.dumps(schemas, indent=2)


def _format_reward(reward_info) -> str:
    """Format reward info into a readable string."""
    if reward_info is None:
        return "No reward info available."
    return reward_info.model_dump_json(indent=2)


# -- TeacherSession -----------------------------------------------------------

class TeacherSession:
    """Stateful conversation with the teacher model.

    Maintains message history so failed patch attempts can be fed back,
    letting the teacher refine without repeating the same mistakes.

    Every message is logged with timestamps in full OpenAI format to JSON.
    """

    def __init__(
        self,
        system_prompt: str,
        tools: list,
        messages: list,
        task,
        reward_info,
        tool_schemas: dict[str, dict],
        model: str = TEACHER_MODEL,
        task_id: str = "",
        on_message: Optional[Callable[["TeacherSession", SessionMessage], None]] = None,
    ):
        self.session_id = f"{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.task_id = task_id
        self.model = model
        self.status = "active"
        self.started_at = now_iso()
        self._on_message = on_message

        self._history: list[dict] = []
        self._messages: list[SessionMessage] = []
        self._current_prompt = system_prompt
        self._current_tool_schemas = tool_schemas
        self._errors: list[ErrorRecord] = []

        task_requirements = ""
        if hasattr(task, "evaluation_criteria") and task.evaluation_criteria:
            task_requirements = task.evaluation_criteria.model_dump_json(indent=2)
        if hasattr(task, "user_scenario"):
            task_requirements = f"User scenario: {task.user_scenario}\n\n{task_requirements}"

        initial_prompt = REFLECTION_PROMPT.format(
            system_prompt=system_prompt,
            tool_definitions=_format_tools(tools),
            conversation_trace=_format_messages(messages),
            task_requirements=task_requirements,
            reward_breakdown=_format_reward(reward_info),
        )
        self._history.append({"role": "user", "content": initial_prompt})
        self._log_message(SessionMessage(role="user", content=initial_prompt))

    @property
    def current_prompt(self) -> str:
        return self._current_prompt

    @property
    def current_tool_schemas(self) -> dict[str, dict]:
        return self._current_tool_schemas

    def _log_message(self, msg: SessionMessage) -> None:
        """Append a timestamped message to the log, save to disk, notify callback."""
        if not msg.ts:
            msg.ts = now_iso()
        self._messages.append(msg)
        self._save_log()
        if self._on_message:
            try:
                self._on_message(self, msg)
            except Exception:
                pass

    def _log_error(self, error: str, context: str = "") -> None:
        """Log an error event as a system message."""
        ts = now_iso()
        self._errors.append(ErrorRecord(ts=ts, error=error, context=context))
        self._log_message(SessionMessage(
            ts=ts, role="system", content=f"[ERROR] {error}",
            error=error, context=context,
        ))

    def _save_log(self) -> None:
        save_session(self._as_session_data())

    def _as_session_data(self) -> SessionData:
        return SessionData(
            session_id=self.session_id,
            session_type="teacher",
            task_id=self.task_id,
            model=self.model,
            started_at=self.started_at,
            status=self.status,
            messages=self._messages,
            errors=self._errors,
        )

    def get_log_snapshot(self) -> SessionSummary:
        return SessionSummary.from_data(self._as_session_data())

    def _call_teacher(self, retries: int = 3, backoff: float = 2.0):
        """Single LLM call with retry. Returns (message, response) or (None, None)."""
        client = _get_client()
        for attempt in range(retries):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=self._history,
                    tools=TEACHER_TOOLS,
                    temperature=0.3,
                )
                msg = response.choices[0].message
                if log.isEnabledFor(logging.DEBUG):
                    log.debug(
                        "Teacher response: content=%s, tool_calls=%d",
                        repr((msg.content or "")[:200]),
                        len(msg.tool_calls or []),
                    )
                return msg, response
            except Exception as e:
                raw = ""
                if hasattr(e, "response"):
                    try:
                        raw = e.response.text[:500]
                    except Exception:
                        pass
                log.warning(
                    "Teacher API error (attempt %d/%d): %s%s",
                    attempt + 1, retries, e,
                    f"\nRaw response: {raw}" if raw else "",
                )
                self._log_error(
                    str(e),
                    context=f"API call attempt {attempt + 1}/{retries}",
                )
                if attempt < retries - 1:
                    time.sleep(backoff * (attempt + 1))
        return None, None

    def reflect(self, max_rounds: int = 10) -> tuple[list[Patch], str]:
        """Call the teacher in a loop until it stops calling tools.

        Each tool call is applied immediately to the internal prompt/schema
        state, and real success/failure feedback is returned to the teacher.
        """
        all_patches: list[Patch] = []
        diagnosis_parts: list[str] = []

        for round_idx in range(max_rounds):
            msg, response = self._call_teacher()
            if msg is None:
                log.warning("Teacher unreachable at round %d, stopping early.", round_idx)
                break

            if msg.content:
                diagnosis_parts.append(msg.content)

            # Build typed tool call list (shared between API dict and log).
            tc_info: list[ToolCallInfo] | None = None
            tc_api: list[dict] | None = None
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

            # Build response metadata for the log.
            resp_meta: ResponseMeta | None = None
            if response:
                usage = None
                if hasattr(response, "usage") and response.usage:
                    usage = UsageInfo(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    )
                resp_meta = ResponseMeta(
                    response_model=getattr(response, "model", None),
                    usage=usage,
                )

            # API history (plain dict, no metadata).
            api_msg: dict = {"role": "assistant"}
            if msg.content:
                api_msg["content"] = msg.content
            if tc_api:
                api_msg["tool_calls"] = tc_api
            self._history.append(api_msg)

            # Typed log message (with metadata).
            self._log_message(SessionMessage(
                role="assistant",
                content=msg.content or "",
                tool_calls=tc_info,
                meta=resp_meta,
            ))

            if not msg.tool_calls:
                break

            # Apply each tool call and give real feedback.
            for tc in msg.tool_calls:
                result_text = self._apply_tool_call(tc, all_patches)
                self._history.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})
                self._log_message(SessionMessage(role="tool", tool_call_id=tc.id, content=result_text))

        self.status = "done"
        self._save_log()
        if self._on_message:
            try:
                self._on_message(self, SessionMessage(ts=now_iso(), role="system", content="[SESSION_DONE]"))
            except Exception:
                pass

        diagnosis = "\n\n".join(diagnosis_parts)
        return all_patches, diagnosis

    def _apply_tool_call(self, tc, all_patches: list[Patch]) -> str:
        """Apply a single tool call, mutate internal state, return feedback."""
        model_cls = _TOOL_MODELS.get(tc.function.name)
        if model_cls is None:
            error = f"Error: unknown tool '{tc.function.name}'."
            self._log_error(error, context="tool_call")
            return error

        try:
            parsed = model_cls.model_validate_json(tc.function.arguments)
        except Exception as e:
            error = f"Error: invalid arguments — {e}"
            self._log_error(error, context="tool_call_parse")
            return error

        if isinstance(parsed, PatchPrompt):
            patch = Patch(old_text=parsed.old_text, new_text=parsed.new_text)
        elif isinstance(parsed, PatchTool):
            patch = Patch(old_text=parsed.old_text, new_text=parsed.new_text,
                          tool_name=parsed.tool_name)
        else:
            return "Error: unhandled tool type."

        self._current_prompt, self._current_tool_schemas, ok, result = _apply_one_patch(
            self._current_prompt, self._current_tool_schemas, patch,
        )
        if ok:
            all_patches.append(patch)
        else:
            self._log_error(result, context="patch_apply")
        return result

    def report_failure(
        self,
        baseline_reward: float,
        patched_reward: float,
        new_sim,
    ) -> None:
        """Feed a failed validation back into the conversation."""
        self.status = "retrying"
        retry_content = RETRY_PROMPT.format(
            baseline_reward=baseline_reward,
            patched_reward=patched_reward,
            new_trace=_format_messages(new_sim.messages),
            new_reward=_format_reward(new_sim.reward_info),
        )
        self._history.append({"role": "user", "content": retry_content})
        self._log_message(SessionMessage(role="user", content=retry_content))


# -- Patch application --------------------------------------------------------

def _apply_one_patch(
    prompt: str,
    tool_schemas: dict[str, dict],
    patch: Patch,
) -> tuple[str, dict[str, dict], bool, str]:
    """Apply a single patch. Returns (prompt, tool_schemas, ok, message)."""
    if patch.is_prompt:
        if patch.old_text == "":
            return prompt + "\n" + patch.new_text, tool_schemas, True, "OK: text appended to end of prompt."
        if patch.old_text in prompt:
            return prompt.replace(patch.old_text, patch.new_text, 1), tool_schemas, True, "OK: replacement applied."
        return prompt, tool_schemas, False, (
            f"FAILED: old_text not found in the current prompt. "
            f"Make sure you copy the exact text (including whitespace). "
            f"First 120 chars of old_text: {patch.old_text[:120]!r}"
        )

    # Tool schema patch.
    if patch.tool_name not in tool_schemas:
        return prompt, tool_schemas, False, (
            f"FAILED: unknown tool '{patch.tool_name}'. "
            f"Available tools: {list(tool_schemas.keys())}"
        )
    schema_str = json.dumps(tool_schemas[patch.tool_name])
    if patch.old_text not in schema_str:
        return prompt, tool_schemas, False, (
            f"FAILED: old_text not found in tool '{patch.tool_name}' schema. "
            f"Make sure you copy the exact text."
        )
    schema_str = schema_str.replace(patch.old_text, patch.new_text, 1)
    tool_schemas[patch.tool_name] = json.loads(schema_str)
    return prompt, tool_schemas, True, "OK: tool schema updated."


def apply_patches(
    current_prompt: str,
    current_tool_schemas: dict[str, dict],
    patches: list[Patch],
) -> tuple[str, dict[str, dict]]:
    """Apply old_text -> new_text replacements to prompt and tool schemas."""
    for i, patch in enumerate(patches):
        current_prompt, current_tool_schemas, ok, msg = _apply_one_patch(
            current_prompt, current_tool_schemas, patch,
        )
        if not ok:
            log.warning("Patch %d skipped: %s", i, msg)
    return current_prompt, current_tool_schemas
