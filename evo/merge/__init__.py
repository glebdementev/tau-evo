"""Patch merging: programmatic where possible, LLM for conflicts."""

from evo.merge.merge import merge_fixes
from evo.merge.types import ConflictGroup, MergeResult

__all__ = ["merge_fixes", "ConflictGroup", "MergeResult"]
