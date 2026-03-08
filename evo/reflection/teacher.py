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
from copy import deepcopy
from datetime import datetime
from typing import Callable, Optional

log = logging.getLogger(__name__)

from openai import OpenAI

from evo.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, TEACHER_MODEL
from evo.models import Patch
from evo.session_log import (
    now_iso, save_session,
    ErrorRecord, ResponseMeta, SessionData, SessionMessage, SessionSummary,
    ToolCallFunction, ToolCallInfo, UsageInfo,
)

from evo.reflection.formatting import (
    SCHEMA_INDENT, format_messages, format_preprocessors, format_reward, format_tools,
)
from evo.reflection.patches import apply_one_patch, apply_patches
from evo.reflection.preprocessor import DEFAULT_PREPROCESSOR, format_tool_info
from evo.reflection.prompts import ESCALATION_PROMPT, REFLECTION_PROMPT, RETRY_PROMPT
from evo.reflection.tools import (
    TEACHING_TOOLS, TEACHER_TOOLS, TOOL_MODELS,
    PatchPrompt, PatchTool, PatchToolCode, ReadToolCode,
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
        tool_code: Optional[dict[str, str]] = None,
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
        self._current_tool_code: dict[str, str] = dict(tool_code) if tool_code else {}
        # Save base state so we can revert after failed validations.
        self._base_prompt = system_prompt
        self._base_tool_schemas = deepcopy(tool_schemas)
        self._base_tool_code: dict[str, str] = dict(tool_code) if tool_code else {}
        self._tools_by_name: dict[str, object] = {
            (t.name if hasattr(t, "name") else ""): t for t in tools
        }
        self._errors: list[ErrorRecord] = []
        self._active_tools = TEACHING_TOOLS  # Start with teaching-only tools
        self.escalated = False

        task_requirements = ""
        if hasattr(task, "evaluation_criteria") and task.evaluation_criteria:
            task_requirements = task.evaluation_criteria.model_dump_json(indent=2)
        if hasattr(task, "user_scenario"):
            task_requirements = f"User scenario: {task.user_scenario}\n\n{task_requirements}"

        initial_prompt = REFLECTION_PROMPT.format(
            system_prompt=system_prompt,
            tool_definitions=format_tools(tools),
            conversation_trace=format_messages(messages),
            task_requirements=task_requirements,
            reward_breakdown=format_reward(reward_info),
        )
        self._history.append({"role": "user", "content": initial_prompt})
        self._log_message(SessionMessage(role="user", content=initial_prompt))

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
                    tools=self._active_tools,
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
        model_cls = TOOL_MODELS.get(tc.function.name)
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

        # -- read_tool_code: read-only, returns tool info + current preprocessor --
        if isinstance(parsed, ReadToolCode):
            return self._handle_read_tool_code(parsed)

        # -- patch_tool_code: edit a tool's input preprocessor --
        if isinstance(parsed, PatchToolCode):
            return self._handle_patch_tool_code(parsed, all_patches)

        # -- patch_prompt / patch_tool: existing behaviour --
        if isinstance(parsed, PatchPrompt):
            patch = Patch(old_text=parsed.old_text, new_text=parsed.new_text)
        elif isinstance(parsed, PatchTool):
            patch = Patch(old_text=parsed.old_text, new_text=parsed.new_text,
                          tool_name=parsed.tool_name)
        else:
            return "Error: unhandled tool type."

        self._current_prompt, self._current_tool_schemas, self._current_tool_code, ok, result = apply_one_patch(
            self._current_prompt, self._current_tool_schemas, patch, self._current_tool_code,
        )
        if ok:
            all_patches.append(patch)
        else:
            self._log_error(result, context="patch_apply")
        return result

    def _validate_tool_name(self, tool_name: str) -> str | None:
        """Return an error string if tool_name is unknown, else None."""
        if tool_name not in self._tools_by_name:
            available = list(self._tools_by_name.keys())
            return f"Error: unknown tool '{tool_name}'. Available tools: {available}"
        return None

    def _handle_read_tool_code(self, parsed: ReadToolCode) -> str:
        """Return tool info and current preprocessor (no source code)."""
        if err := self._validate_tool_name(parsed.tool_name):
            return err

        info = format_tool_info(self._tools_by_name[parsed.tool_name])
        preprocessor = self._current_tool_code.get(parsed.tool_name, DEFAULT_PREPROCESSOR)
        return f"{info}\n\n--- Current Preprocessor ---\n{preprocessor}"

    def _handle_patch_tool_code(self, parsed: PatchToolCode, all_patches: list[Patch]) -> str:
        """Edit a tool's preprocessor source, validate it compiles."""
        if err := self._validate_tool_name(parsed.tool_name):
            return err

        patch = Patch(
            old_text=parsed.old_text, new_text=parsed.new_text,
            tool_name=parsed.tool_name, is_code=True,
        )
        self._current_prompt, self._current_tool_schemas, self._current_tool_code, ok, result = apply_one_patch(
            self._current_prompt, self._current_tool_schemas, patch, self._current_tool_code,
        )
        if ok:
            all_patches.append(patch)
            result += f"\n\nCurrent source:\n{self._current_tool_code[parsed.tool_name]}"
        else:
            self._log_error(result, context="patch_tool_code")
        return result

    def revert_patches(self) -> None:
        """Revert prompt, tool schemas, and tool code to their base (pre-patch) state."""
        self._current_prompt = self._base_prompt
        self._current_tool_schemas = deepcopy(self._base_tool_schemas)
        self._current_tool_code = dict(self._base_tool_code)

    def report_failure(
        self,
        baseline_reward: float,
        patched_reward: float,
        new_sim,
    ) -> None:
        """Feed a failed validation back into the conversation.

        Reverts all patches so the teacher must apply fixes from scratch.
        The teacher still sees the original failure and the failed validation
        trace in its conversation history.
        """
        self.revert_patches()
        self.status = "retrying"
        current_tools_str = json.dumps(
            list(self._current_tool_schemas.values()), indent=SCHEMA_INDENT,
        )
        preprocessors_str = format_preprocessors(self._current_tool_code)
        retry_content = RETRY_PROMPT.format(
            baseline_reward=baseline_reward,
            patched_reward=patched_reward,
            new_trace=format_messages(new_sim.messages),
            new_reward=format_reward(new_sim.reward_info),
            current_prompt=self._current_prompt,
            current_tools=current_tools_str,
            current_preprocessors=preprocessors_str,
        )
        self._history.append({"role": "user", "content": retry_content})
        self._log_message(SessionMessage(role="user", content=retry_content))

    def escalate(
        self,
        baseline_reward: float,
        patched_reward: float,
        new_sim,
    ) -> None:
        """Unlock tool code patches after prompt-only fixes failed.

        Reverts all patches and switches active tools from TEACHING_TOOLS to
        TEACHER_TOOLS (full set), so the teacher starts fresh with the
        additional tool code capability.
        """
        self.revert_patches()
        self.escalated = True
        self.status = "escalated"
        self._active_tools = TEACHER_TOOLS

        current_tools_str = json.dumps(
            list(self._current_tool_schemas.values()), indent=SCHEMA_INDENT,
        )
        preprocessors_str = format_preprocessors(self._current_tool_code)
        escalation_content = ESCALATION_PROMPT.format(
            baseline_reward=baseline_reward,
            patched_reward=patched_reward,
            new_trace=format_messages(new_sim.messages),
            new_reward=format_reward(new_sim.reward_info),
            current_prompt=self._current_prompt,
            current_tools=current_tools_str,
            current_preprocessors=preprocessors_str,
        )
        self._history.append({"role": "user", "content": escalation_content})
        self._log_message(SessionMessage(role="user", content=escalation_content))
