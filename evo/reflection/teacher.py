"""Teacher: sends a failed trace to the teacher model and gets back patches via tool-calling.

The TeacherSession maintains a conversation with the teacher model so that
when a patch fails validation, we can feed the result back and let the teacher
refine its approach — within the same context window.
"""

from __future__ import annotations

import json
from typing import Optional

from openai import OpenAI
from openai.lib._tools import pydantic_function_tool
from pydantic import BaseModel, Field

from evo.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, TEACHER_MODEL
from evo.models import Patch


_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    return _client


# ── Tool definitions for the teacher ─────────────────────────────────────

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


# ── Prompts ──────────────────────────────────────────────────────────────

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
   - `patch_prompt`: to edit the agent's system prompt (find-and-replace). Use old_text='' to append new text.
   - `patch_tool`: to edit a tool's schema JSON (find-and-replace).

   You may call these tools multiple times. Make your patches surgical and specific.

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


# ── Formatting helpers ───────────────────────────────────────────────────

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


def _parse_tool_calls(tool_calls) -> list[Patch]:
    """Extract patch operations from OpenAI tool_calls using Pydantic validation."""
    if not tool_calls:
        return []

    patches = []
    for tc in tool_calls:
        model_cls = _TOOL_MODELS.get(tc.function.name)
        if model_cls is None:
            continue

        parsed = model_cls.model_validate_json(tc.function.arguments)

        if isinstance(parsed, PatchPrompt):
            patches.append(Patch(old_text=parsed.old_text, new_text=parsed.new_text))
        elif isinstance(parsed, PatchTool):
            patches.append(Patch(
                old_text=parsed.old_text,
                new_text=parsed.new_text,
                tool_name=parsed.tool_name,
            ))
    return patches


# ── TeacherSession ───────────────────────────────────────────────────────

class TeacherSession:
    """Stateful conversation with the teacher model.

    Maintains message history so failed patch attempts can be fed back,
    letting the teacher refine without repeating the same mistakes.
    """

    def __init__(
        self,
        system_prompt: str,
        tools: list,
        messages: list,
        task,
        reward_info,
        model: str = TEACHER_MODEL,
    ):
        self.model = model
        self._history: list[dict] = []

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

    def reflect(self) -> tuple[list[Patch], str]:
        """Call the teacher and return (patches, diagnosis)."""
        client = _get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=self._history,
            tools=TEACHER_TOOLS,
            temperature=0.3,
        )

        msg = response.choices[0].message
        patches = _parse_tool_calls(msg.tool_calls)
        diagnosis = msg.content or ""

        # Append the assistant message to history for continuity.
        assistant_msg: dict = {"role": "assistant"}
        if msg.content:
            assistant_msg["content"] = msg.content
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        self._history.append(assistant_msg)

        # Append synthetic tool results so the conversation stays valid.
        if msg.tool_calls:
            for tc in msg.tool_calls:
                self._history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": "Patch applied.",
                })

        return patches, diagnosis

    def report_failure(
        self,
        baseline_reward: float,
        patched_reward: float,
        new_sim,
    ) -> None:
        """Feed a failed validation back into the conversation."""
        retry_msg = RETRY_PROMPT.format(
            baseline_reward=baseline_reward,
            patched_reward=patched_reward,
            new_trace=_format_messages(new_sim.messages),
            new_reward=_format_reward(new_sim.reward_info),
        )
        self._history.append({"role": "user", "content": retry_msg})


# ── Patch application ────────────────────────────────────────────────────

def apply_patches(
    current_prompt: str,
    current_tool_schemas: dict[str, dict],
    patches: list[Patch],
) -> tuple[str, dict[str, dict]]:
    """Apply old_text -> new_text replacements to prompt and tool schemas."""
    for patch in patches:
        if patch.is_prompt:
            if patch.old_text == "":
                current_prompt += "\n" + patch.new_text
            else:
                current_prompt = current_prompt.replace(patch.old_text, patch.new_text, 1)
        elif patch.tool_name in current_tool_schemas:
            schema_str = json.dumps(current_tool_schemas[patch.tool_name])
            schema_str = schema_str.replace(patch.old_text, patch.new_text, 1)
            current_tool_schemas[patch.tool_name] = json.loads(schema_str)
    return current_prompt, current_tool_schemas
