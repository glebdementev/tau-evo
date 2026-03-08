"""Top-level merge entry point: partition → detect → resolve → apply."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Optional

from evo.config import TEACHER_MODEL
from evo.merge.partition import partition_and_detect
from evo.merge.resolver import resolve_conflicts
from evo.merge.types import MergeResult
from evo.models import FixResult
from evo.reflection.patches import apply_patches

log = logging.getLogger(__name__)


def merge_fixes(
    fixes: list[FixResult],
    prompt: str,
    tool_schemas: dict[str, dict],
    tool_code: Optional[dict[str, str]] = None,
    model: str = TEACHER_MODEL,
) -> tuple[str, dict[str, dict], dict[str, str], MergeResult]:
    """Merge patches from multiple teacher fixes into a single state.

    1. Partition patches by target (prompt / tool / code).
    2. Detect conflicts (overlapping regions within the same target).
    3. Auto-merge clean patches.
    4. Send conflict groups to LLM merger.
    5. Apply everything to produce the final state.

    Returns:
        (merged_prompt, merged_schemas, merged_code, merge_result)
    """
    if tool_code is None:
        tool_code = {}

    winners = [f for f in fixes if f.fixed]
    if not winners:
        return prompt, tool_schemas, tool_code, MergeResult([], [])

    # Partition and detect conflicts.
    clean, conflicts = partition_and_detect(
        winners, prompt, deepcopy(tool_schemas), dict(tool_code),
    )

    n_clean = len(clean)
    n_conflicts = len(conflicts)
    n_conflict_patches = sum(len(g.regions) for g in conflicts)

    log.info(
        "Merge: %d clean patches, %d conflict groups (%d patches)",
        n_clean, n_conflicts, n_conflict_patches,
    )

    # Resolve conflicts via LLM.
    resolved: list = []
    if conflicts:
        log.info("Resolving %d conflict groups via LLM merger...", n_conflicts)
        resolved = resolve_conflicts(conflicts, model=model)
        log.info("Resolved %d/%d conflict groups", len(resolved), n_conflicts)

    result = MergeResult(
        merged_patches=clean,
        conflict_groups=conflicts,
        resolved_patches=resolved,
    )

    # Apply all patches to produce the final state.
    all_patches = result.all_patches
    merged_prompt, merged_schemas, merged_code = apply_patches(
        prompt, deepcopy(tool_schemas), all_patches, dict(tool_code),
    )

    return merged_prompt, merged_schemas, merged_code, result
