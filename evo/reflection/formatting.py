"""Formatting helpers for teacher session messages and tool schemas."""

from __future__ import annotations

import json

# Consistent serialization indent for tool schemas — must match what the teacher sees.
SCHEMA_INDENT = 2


def format_messages(messages: list) -> str:
    """Format a list of tau2 message objects into a readable trace.

    Tracks the last tool call name so tool-result messages can show
    which tool produced the result (tau2 doesn't always set msg.name).
    """
    lines = []
    # Map tool_call_id → tool name so we can label tool results properly.
    tc_names: dict[str, str] = {}
    for msg in messages:
        role = msg.role if hasattr(msg, "role") else "unknown"
        content = getattr(msg, "content", None) or ""
        tool_calls = getattr(msg, "tool_calls", None)

        if role == "system":
            continue

        if tool_calls:
            # Show assistant text content if present alongside tool calls.
            if content:
                lines.append(f"[assistant] {content}")
            for tc in tool_calls:
                tc_id = getattr(tc, "id", None) or ""
                tc_names[tc_id] = tc.name
                lines.append(f"[assistant -> tool_call] {tc.name}({json.dumps(tc.arguments)})")
        elif role == "tool":
            # Resolve tool name: explicit name > tracked by call id > fallback.
            tool_name = getattr(msg, "name", None)
            if not tool_name:
                # ToolMessage uses `id` field, not `tool_call_id`.
                tc_id = getattr(msg, "tool_call_id", None) or getattr(msg, "id", None) or ""
                tool_name = tc_names.get(tc_id, "tool")
            lines.append(f"[tool_result: {tool_name}] {content}")
        else:
            lines.append(f"[{role}] {content}")
    return "\n".join(lines)


def format_tools(tools: list) -> str:
    """Format tool openai_schemas as readable JSON.

    Uses the same indent as _serialize_schema so the teacher sees
    exactly the same text it needs to match for patch_tool calls.
    """
    schemas = [t.openai_schema if hasattr(t, "openai_schema") else t for t in tools]
    return json.dumps(schemas, indent=SCHEMA_INDENT)


def format_preprocessors(tool_code: dict[str, str]) -> str:
    """Format current preprocessor sources for the teacher."""
    if not tool_code:
        return "(no custom preprocessors — all tools use default pass-through)"
    parts = []
    for name, source in sorted(tool_code.items()):
        parts.append(f"### {name}\n```python\n{source}```")
    return "\n\n".join(parts)


def format_reward(reward_info) -> str:
    """Format reward info into a readable string."""
    if reward_info is None:
        return "No reward info available."
    return reward_info.model_dump_json(indent=2)
