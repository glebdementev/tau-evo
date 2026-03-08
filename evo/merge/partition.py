"""Partition patches by target and detect conflicts via region overlap."""

from __future__ import annotations

from collections import defaultdict

from evo.merge.types import ConflictGroup, Region
from evo.models import FixResult, Patch
from evo.reflection.patches import serialize_schema
from evo.reflection.preprocessor import DEFAULT_PREPROCESSOR


def _target_key(patch: Patch) -> str:
    """Return a string key identifying which text blob this patch targets."""
    if patch.is_prompt:
        return "prompt"
    if patch.is_tool_code:
        return f"code:{patch.tool_name}"
    return f"tool:{patch.tool_name}"


def _get_base_text(
    target: str,
    prompt: str,
    tool_schemas: dict[str, dict],
    tool_code: dict[str, str],
) -> str:
    """Return the base text for a given target key."""
    if target == "prompt":
        return prompt
    kind, name = target.split(":", 1)
    if kind == "tool":
        return serialize_schema(tool_schemas[name])
    return tool_code.get(name, DEFAULT_PREPROCESSOR)


def _locate(base_text: str, patch: Patch) -> tuple[int, int] | None:
    """Find the (start, end) span of patch.old_text in base_text.

    Returns None for appends (old_text == "") — these never conflict.
    """
    if patch.old_text == "":
        return None
    idx = base_text.find(patch.old_text)
    if idx == -1:
        return None
    return (idx, idx + len(patch.old_text))


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def partition_and_detect(
    fixes: list[FixResult],
    prompt: str,
    tool_schemas: dict[str, dict],
    tool_code: dict[str, str],
) -> tuple[list[Patch], list[ConflictGroup]]:
    """Partition patches, auto-merge non-conflicting ones, return conflict groups.

    Returns:
        clean: patches that can be applied without conflicts (ordered back-to-front
               within each target so offsets stay valid).
        conflicts: groups of overlapping patches that need LLM resolution.
    """
    # Group (Region | Patch) by target.
    located: dict[str, list[Region]] = defaultdict(list)
    appends: dict[str, list[Patch]] = defaultdict(list)

    for fix in fixes:
        for patch in fix.patches:
            target = _target_key(patch)
            base = _get_base_text(target, prompt, tool_schemas, tool_code)
            span = _locate(base, patch)
            if span is None:
                # Append or unfindable — appends never conflict.
                if patch.old_text == "":
                    appends[target].append(patch)
                # If old_text wasn't found, skip silently (will fail at apply time).
                continue
            located[target].append(Region(
                patch=patch, start=span[0], end=span[1], fix=fix,
            ))

    clean: list[Patch] = []
    conflicts: list[ConflictGroup] = []

    for target, regions in located.items():
        base = _get_base_text(target, prompt, tool_schemas, tool_code)
        target_clean, target_conflicts = _split_conflicts(regions, target, base)
        clean.extend(target_clean)
        conflicts.extend(target_conflicts)

    # Appends are always clean.
    for _target, patches in appends.items():
        clean.extend(patches)

    return clean, conflicts


def _split_conflicts(
    regions: list[Region],
    target: str,
    base_text: str,
) -> tuple[list[Patch], list[ConflictGroup]]:
    """Within one target, find overlapping clusters and separate clean patches.

    Uses a sweep-line approach: sort by start, greedily extend the current
    cluster as long as regions overlap.
    """
    if not regions:
        return [], []

    regions.sort(key=lambda r: r.start)

    clusters: list[list[Region]] = []
    current_cluster = [regions[0]]
    cluster_end = regions[0].end

    for region in regions[1:]:
        if region.start < cluster_end:
            # Overlaps with current cluster.
            current_cluster.append(region)
            cluster_end = max(cluster_end, region.end)
        else:
            clusters.append(current_cluster)
            current_cluster = [region]
            cluster_end = region.end
    clusters.append(current_cluster)

    clean: list[Patch] = []
    conflict_groups: list[ConflictGroup] = []

    for cluster in clusters:
        if len(cluster) == 1:
            clean.append(cluster[0].patch)
        else:
            conflict_groups.append(ConflictGroup(
                target=target,
                regions=cluster,
                base_text=base_text,
            ))

    # Sort clean patches back-to-front so applying them preserves offsets.
    clean.sort(key=lambda p: -(base_text.find(p.old_text) if p.old_text else 0))

    return clean, conflict_groups
