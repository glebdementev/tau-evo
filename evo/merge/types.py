"""Data types for the merge pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

from evo.models import FixResult, Patch


@dataclass
class Region:
    """A located patch: the patch plus its character span in the base text."""
    patch: Patch
    start: int
    end: int
    fix: FixResult  # which teacher fix this came from


@dataclass
class ConflictGroup:
    """A set of patches that touch overlapping regions in the same target."""
    target: str  # "prompt" | "tool:<name>" | "code:<name>"
    regions: list[Region]
    base_text: str  # the relevant base text (full prompt, or serialized schema/code)

    @property
    def task_ids(self) -> list[str]:
        return list({r.fix.task_id for r in self.regions})

    @property
    def diagnoses(self) -> list[str]:
        return [r.fix.diagnosis for r in self.regions if r.fix.diagnosis]


@dataclass
class MergeResult:
    """Output of the merge pipeline."""
    merged_patches: list[Patch]              # patches that merged cleanly
    conflict_groups: list[ConflictGroup]      # groups that need LLM resolution
    resolved_patches: list[Patch] = field(default_factory=list)  # LLM-resolved patches

    @property
    def all_patches(self) -> list[Patch]:
        return self.merged_patches + self.resolved_patches
