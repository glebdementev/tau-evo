"""LLM-based conflict resolution for overlapping patches."""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Optional

from openai import OpenAI

from evo.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, TEACHER_MODEL
from evo.merge.types import ConflictGroup
from evo.models import Patch

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


MERGE_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_resolution",
        "description": "Submit the merged replacement text that incorporates fixes from all conflicting patches.",
        "parameters": {
            "type": "object",
            "properties": {
                "old_text": {
                    "type": "string",
                    "description": "The original text region to replace (must be a substring of the base text that covers all conflicting patches).",
                },
                "new_text": {
                    "type": "string",
                    "description": "The merged replacement text that incorporates all fixes.",
                },
            },
            "required": ["old_text", "new_text"],
        },
    },
}


def _build_merge_prompt(group: ConflictGroup) -> str:
    """Build a prompt asking the LLM to merge conflicting patches."""
    # Show the conflicting region with some context.
    min_start = min(r.start for r in group.regions)
    max_end = max(r.end for r in group.regions)
    ctx = 200
    view_start = max(0, min_start - ctx)
    view_end = min(len(group.base_text), max_end + ctx)
    base_view = group.base_text[view_start:view_end]

    patches_desc = []
    for i, region in enumerate(group.regions, 1):
        patches_desc.append(
            f"### Patch {i} (task: {region.fix.task_id})\n"
            f"Diagnosis: {region.fix.diagnosis[:500]}\n"
            f"old_text: {region.patch.old_text!r}\n"
            f"new_text: {region.patch.new_text!r}"
        )

    target_desc = group.target
    if target_desc == "prompt":
        target_desc = "the agent's system prompt"
    elif target_desc.startswith("tool:"):
        target_desc = f"tool schema for '{target_desc.split(':', 1)[1]}'"
    elif target_desc.startswith("code:"):
        target_desc = f"preprocessor code for '{target_desc.split(':', 1)[1]}'"

    return (
        f"You are merging conflicting patches to {target_desc}.\n\n"
        f"Multiple teachers independently proposed patches to fix different tasks, "
        f"but their patches touch overlapping regions of the same text.\n\n"
        f"## Base text (relevant section)\n```\n{base_view}\n```\n\n"
        f"## Conflicting patches\n\n" + "\n\n".join(patches_desc) + "\n\n"
        f"Your job: produce a SINGLE replacement that incorporates the intent of ALL patches. "
        f"The old_text must be an exact substring of the base text. "
        f"The new_text should combine all fixes without breaking any of them.\n\n"
        f"Use the submit_resolution tool to submit your merged patch."
    )


def resolve_conflict(
    group: ConflictGroup,
    model: str = TEACHER_MODEL,
    retries: int = 3,
) -> Patch | None:
    """Ask the LLM to merge one conflict group into a single patch.

    Returns a Patch if successful, None if the LLM fails.
    """
    client = _get_client()
    prompt = _build_merge_prompt(group)

    messages = [{"role": "user", "content": prompt}]

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=[MERGE_TOOL],
                temperature=0.2,
            )
            msg = response.choices[0].message

            if not msg.tool_calls:
                log.warning("Merger gave no tool call for %s (attempt %d)", group.target, attempt + 1)
                # Append response and ask again.
                messages.append({"role": "assistant", "content": msg.content or ""})
                messages.append({"role": "user", "content": "Please use the submit_resolution tool to submit your merged patch."})
                continue

            tc = msg.tool_calls[0]
            if tc.function.name != "submit_resolution":
                log.warning("Merger called wrong tool: %s", tc.function.name)
                continue

            args = json.loads(tc.function.arguments)
            old_text = args["old_text"]
            new_text = args["new_text"]

            # Validate old_text exists in base.
            if old_text not in group.base_text:
                log.warning("Merger old_text not found in base for %s (attempt %d)", group.target, attempt + 1)
                messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                ]})
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": (
                    f"FAILED: old_text not found in base text. "
                    f"Make sure you copy the exact text including whitespace. "
                    f"First 120 chars of your old_text: {old_text[:120]!r}"
                )})
                continue

            # Build the patch with correct target info.
            tool_name = None
            is_code = False
            if group.target.startswith("tool:"):
                tool_name = group.target.split(":", 1)[1]
            elif group.target.startswith("code:"):
                tool_name = group.target.split(":", 1)[1]
                is_code = True

            return Patch(
                old_text=old_text,
                new_text=new_text,
                tool_name=tool_name,
                is_code=is_code,
            )

        except Exception as e:
            log.warning("Merger API error (attempt %d/%d): %s", attempt + 1, retries, e)
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))

    log.error("Merger failed for conflict group on %s after %d attempts", group.target, retries)
    return None


def resolve_conflicts(
    groups: list[ConflictGroup],
    model: str = TEACHER_MODEL,
) -> list[Patch]:
    """Resolve all conflict groups, returning merged patches.

    Groups that fail resolution are skipped (logged as warnings).
    """
    resolved = []
    for group in groups:
        patch = resolve_conflict(group, model=model)
        if patch is not None:
            resolved.append(patch)
        else:
            task_ids = group.task_ids
            log.warning("Dropping conflict group for %s (tasks: %s) — merger failed", group.target, task_ids)
    return resolved
