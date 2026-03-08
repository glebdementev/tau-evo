"""Top-level merge entry point: one LLM session applies, resolves, and compacts all patches."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Callable, Optional

from evo.config import TEACHER_MODEL
from evo.merge.resolver import MergerSession
from evo.merge.types import MergeResult
from evo.models import FixResult

log = logging.getLogger(__name__)


def merge_fixes(
    fixes: list[FixResult],
    prompt: str,
    tool_schemas: dict[str, dict],
    tool_code: Optional[dict[str, str]] = None,
    model: str = TEACHER_MODEL,
    on_session: Optional[Callable] = None,
    on_message: Optional[Callable] = None,
) -> tuple[str, dict[str, dict], dict[str, str], MergeResult]:
    """Merge patches from multiple teacher fixes via a single LLM merger session.

    The merger receives the full prompt + all proposed diffs, applies them via
    patch_prompt / patch_tool tool calls, resolves conflicts, deduplicates, and
    compacts — all in one session (like a teacher).

    Returns:
        (merged_prompt, merged_schemas, merged_code, merge_result)
    """
    if tool_code is None:
        tool_code = {}

    winners = [f for f in fixes if f.fixed]
    if not winners:
        return prompt, tool_schemas, tool_code, MergeResult([], [])

    session = MergerSession(
        system_prompt=prompt,
        tool_schemas=deepcopy(tool_schemas),
        tool_code=dict(tool_code),
        model=model,
        on_message=on_message,
        on_session=on_session,
    )

    applied = session.merge(winners)

    log.info("Merger applied %d patches from %d fixes", len(applied), len(winners))

    result = MergeResult(
        merged_patches=applied,
        conflict_groups=[],
    )

    return session.current_prompt, session.current_tool_schemas, session.current_tool_code, result
