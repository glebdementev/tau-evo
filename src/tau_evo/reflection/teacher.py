"""Teacher: sends a failed trace to the teacher model and gets back a patch."""

from __future__ import annotations

import json
import re
from typing import Optional

from openai import OpenAI

from tau_evo.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, TEACHER_MODEL


_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    return _client


REFLECTION_PROMPT = """\
You are an expert at diagnosing failures in LLM-based customer service agents.

Below you will find:
1. The agent's system prompt (which includes the domain policy).
2. The tool definitions available to the agent.
3. A failed conversation trace between the agent and a user (simulated).
4. The task requirements that the agent was supposed to fulfil.
5. The reward breakdown showing exactly what went wrong.

Your job is to:
1. **Diagnose** the root cause of the failure. Classify it as one of:
   - TOOL_MISUSE: wrong tool, wrong parameters, missing tool call
   - POLICY_VIOLATION: skipped a validation step, broke a constraint
   - REASONING_ERROR: incorrect assumption, incomplete plan
   - COMMUNICATION_ERROR: confusing message, failed to guide user

2. **Propose a patch** to prevent this failure. You can propose one or both of:

   a) A **prompt patch**: one or more concise rules to add to the agent's instructions.
      These should be specific and actionable, not vague.

   b) A **tool patch**: modified descriptions or parameter descriptions for specific tools.
      Only propose this if the tool definition itself was misleading or ambiguous.

Respond in this exact JSON format (no markdown, no extra text):
{{
  "diagnosis": {{
    "failure_type": "TOOL_MISUSE | POLICY_VIOLATION | REASONING_ERROR | COMMUNICATION_ERROR",
    "explanation": "Brief explanation of what went wrong and why."
  }},
  "prompt_patch": "Rule text to append to agent instructions, or null if not needed.",
  "tool_patches": {{
    "tool_name": {{
      "description": "New tool description, or omit if unchanged.",
      "params": {{
        "param_name": "New parameter description."
      }}
    }}
  }}
}}

If no tool patch is needed, set "tool_patches" to {{}}.

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


def _extract_json(raw: str) -> dict:
    """Extract JSON from an LLM response, handling markdown fences."""
    match = re.search(r"```(?:json)?\s*\n(.*?)```", raw, re.DOTALL)
    text = match.group(1) if match else raw
    return json.loads(text.strip())


def reflect(
    system_prompt: str,
    tools: list,
    messages: list,
    task,
    reward_info,
    model: str = TEACHER_MODEL,
) -> dict:
    """Send a failed trace to the teacher and parse the returned patch.

    Returns a dict with keys: diagnosis, prompt_patch, tool_patches.
    """
    task_requirements = ""
    if hasattr(task, "evaluation_criteria") and task.evaluation_criteria:
        task_requirements = task.evaluation_criteria.model_dump_json(indent=2)
    if hasattr(task, "user_scenario"):
        task_requirements = f"User scenario: {task.user_scenario}\n\n{task_requirements}"

    prompt = REFLECTION_PROMPT.format(
        system_prompt=system_prompt,
        tool_definitions=_format_tools(tools),
        conversation_trace=_format_messages(messages),
        task_requirements=task_requirements,
        reward_breakdown=_format_reward(reward_info),
    )

    client = _get_client()
    # Strip litellm's "openrouter/" prefix — the OpenAI client talks directly to OpenRouter.
    bare_model = model.removeprefix("openrouter/")
    response = client.chat.completions.create(
        model=bare_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()
    return _extract_json(raw)


def merge_patches(
    existing_prompt_patch: Optional[str],
    existing_tool_patches: Optional[dict],
    new_patch: dict,
) -> tuple[Optional[str], Optional[dict]]:
    """Merge a new patch from the teacher into existing patches."""
    prompt_patch = existing_prompt_patch
    if new_patch.get("prompt_patch"):
        if prompt_patch:
            prompt_patch += "\n" + new_patch["prompt_patch"]
        else:
            prompt_patch = new_patch["prompt_patch"]

    tool_patches = dict(existing_tool_patches) if existing_tool_patches else {}
    for tool_name, patch in (new_patch.get("tool_patches") or {}).items():
        if tool_name in tool_patches:
            existing = tool_patches[tool_name]
            if "description" in patch:
                existing["description"] = patch["description"]
            if "params" in patch:
                existing.setdefault("params", {}).update(patch["params"])
        else:
            tool_patches[tool_name] = patch

    return prompt_patch, tool_patches or None
