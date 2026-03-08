"""Patch application logic for prompt, tool schemas, and tool preprocessors."""

from __future__ import annotations

import json
import logging
from typing import Optional

from evo.models import Patch
from evo.reflection.formatting import SCHEMA_INDENT
from evo.reflection.preprocessor import compile_preprocessor, DEFAULT_PREPROCESSOR

log = logging.getLogger(__name__)


def serialize_schema(schema: dict) -> str:
    """Serialize a tool schema dict to JSON with consistent formatting."""
    return json.dumps(schema, indent=SCHEMA_INDENT)


def text_replace(text: str, old: str, new: str, label: str) -> tuple[str, bool, str]:
    """Find-and-replace on a string.  Returns (result, ok, message).

    Shared logic for both prompt and tool-schema patches.
    If old is empty, appends new to the end.
    """
    if old == "":
        result = text + "\n" + new
        return result, True, f"OK: appended to {label}."
    if old not in text:
        return text, False, (
            f"FAILED: old_text not found in {label}. "
            f"Make sure you copy the exact text (including whitespace and newlines). "
            f"First 120 chars of old_text you sent: {old[:120]!r}"
        )
    result = text.replace(old, new, 1)
    return result, True, f"OK: applied in {label}."


def apply_one_patch(
    prompt: str,
    tool_schemas: dict[str, dict],
    patch: Patch,
    tool_code: Optional[dict[str, str]] = None,
) -> tuple[str, dict[str, dict], dict[str, str] | None, bool, str]:
    """Apply a single patch. Returns (prompt, tool_schemas, tool_code, ok, message)."""
    if patch.is_prompt:
        prompt, ok, msg = text_replace(prompt, patch.old_text, patch.new_text, "prompt")
        return prompt, tool_schemas, tool_code, ok, msg

    if patch.is_tool_code:
        # Tool preprocessor patch.
        if tool_code is None:
            tool_code = {}
        current_source = tool_code.get(patch.tool_name, DEFAULT_PREPROCESSOR)
        new_source, ok, msg = text_replace(
            current_source, patch.old_text, patch.new_text,
            f"tool '{patch.tool_name}' preprocessor",
        )
        if not ok:
            return prompt, tool_schemas, tool_code, False, msg
        try:
            compile_preprocessor(new_source, patch.tool_name)
        except ValueError as e:
            return prompt, tool_schemas, tool_code, False, f"FAILED: {e}"
        tool_code[patch.tool_name] = new_source
        return prompt, tool_schemas, tool_code, True, msg

    # Tool schema patch.
    if patch.tool_name not in tool_schemas:
        return prompt, tool_schemas, tool_code, False, (
            f"FAILED: unknown tool '{patch.tool_name}'. "
            f"Available tools: {list(tool_schemas.keys())}"
        )
    schema_str = serialize_schema(tool_schemas[patch.tool_name])
    schema_str, ok, msg = text_replace(schema_str, patch.old_text, patch.new_text, f"tool '{patch.tool_name}' schema")
    if not ok:
        return prompt, tool_schemas, tool_code, False, msg
    # Validate that the patched string is still valid JSON.
    try:
        tool_schemas[patch.tool_name] = json.loads(schema_str)
    except json.JSONDecodeError as e:
        return prompt, tool_schemas, tool_code, False, (
            f"FAILED: replacement produced invalid JSON in tool '{patch.tool_name}': {e}"
        )
    return prompt, tool_schemas, tool_code, True, msg


def apply_patches(
    current_prompt: str,
    current_tool_schemas: dict[str, dict],
    patches: list[Patch],
    current_tool_code: Optional[dict[str, str]] = None,
) -> tuple[str, dict[str, dict], dict[str, str]]:
    """Apply old_text -> new_text replacements to prompt, tool schemas, and tool code."""
    if current_tool_code is None:
        current_tool_code = {}
    for i, patch in enumerate(patches):
        current_prompt, current_tool_schemas, current_tool_code, ok, msg = apply_one_patch(
            current_prompt, current_tool_schemas, patch, current_tool_code,
        )
        if not ok:
            log.warning("Patch %d skipped: %s", i, msg)
    return current_prompt, current_tool_schemas, current_tool_code
