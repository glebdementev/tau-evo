"""Shared data models for the evolution loop."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Patch:
    """A single find-and-replace patch to the agent's prompt or tool schema."""
    old_text: str
    new_text: str
    tool_name: Optional[str] = None  # None → prompt patch; str → tool schema patch

    @property
    def is_prompt(self) -> bool:
        return self.tool_name is None

    @property
    def is_tool(self) -> bool:
        return self.tool_name is not None


@dataclass
class FixResult:
    """Outcome of a teacher session fixing one task."""
    task_id: str
    baseline_reward: float
    patched_reward: float
    diagnosis: str
    patches: list[Patch]
    retries: int
    fixed: bool

    @property
    def delta(self) -> float:
        return self.patched_reward - self.baseline_reward


@dataclass
class IterationResult:
    """Outcome of one outer iteration (evaluate all → fix failures in parallel)."""
    iteration: int
    num_evaluated: int
    num_failures: int
    fixes: list[FixResult]
    num_fixed: int

    @property
    def all_fixes(self) -> list[FixResult]:
        return self.fixes


@dataclass
class LoopState:
    """Full state of the evolution loop, serialisable to JSON."""
    prompt_instruction: Optional[str] = None
    tool_schemas: Optional[dict] = None
    history: list[IterationResult] = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: Path) -> LoopState:
        raw = json.loads(path.read_text())
        history = []
        for h in raw.get("history", []):
            fixes = [
                FixResult(
                    patches=[Patch(**p) for p in f.get("patches", [])],
                    task_id=f["task_id"],
                    baseline_reward=f["baseline_reward"],
                    patched_reward=f["patched_reward"],
                    diagnosis=f.get("diagnosis", ""),
                    retries=f.get("retries", 0),
                    fixed=f["fixed"],
                )
                for f in h.get("fixes", [])
            ]
            history.append(IterationResult(
                iteration=h["iteration"],
                num_evaluated=h["num_evaluated"],
                num_failures=h["num_failures"],
                fixes=fixes,
                num_fixed=h["num_fixed"],
            ))
        return cls(
            prompt_instruction=raw.get("prompt_instruction"),
            tool_schemas=raw.get("tool_schemas"),
            history=history,
        )

    def flat_fixes(self) -> list[FixResult]:
        """All FixResults across all iterations, in order."""
        return [fix for r in self.history for fix in r.fixes]
