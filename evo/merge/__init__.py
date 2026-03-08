"""Patch merging: single LLM session applies, resolves, deduplicates, and compacts."""

from evo.merge.merge import merge_fixes
from evo.merge.types import MergeResult

__all__ = ["merge_fixes", "MergeResult"]
