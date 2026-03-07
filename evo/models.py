"""Shared data models for the evolution loop."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Patch:
    """A single find-and-replace patch to the agent's prompt, tool schema, or tool preprocessor."""
    old_text: str
    new_text: str
    tool_name: Optional[str] = None  # None → prompt patch; str → tool schema or code patch
    is_code: bool = False  # True → tool preprocessor patch (vs schema patch)

    @property
    def is_prompt(self) -> bool:
        return self.tool_name is None and not self.is_code

    @property
    def is_tool(self) -> bool:
        return self.tool_name is not None and not self.is_code

    @property
    def is_tool_code(self) -> bool:
        return self.tool_name is not None and self.is_code


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
    eval_rewards: dict[str, float] = field(default_factory=dict)  # task_id → reward



@dataclass
class RunMeta:
    """Lightweight metadata for a run, used in the history sidebar."""
    run_id: str
    domain: str
    started_at: str  # ISO format
    status: str = "running"  # running | finished | error
    num_tasks: int = 0
    total_fixes: int = 0
    total_failures: int = 0

    @property
    def fix_rate(self) -> int:
        if self.total_failures == 0:
            return 0
        return int(self.total_fixes / self.total_failures * 100)

    @staticmethod
    def make_id(domain: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{domain}_{ts}"


@dataclass
class LoopState:
    """Full state of the evolution loop, serialisable to JSON."""
    system_prompt: Optional[str] = None
    prompt_instruction: Optional[str] = None  # legacy, kept for old state files
    tool_schemas: Optional[dict] = None
    tool_code: Optional[dict[str, str]] = None  # tool_name → preprocessor source
    history: list[IterationResult] = field(default_factory=list)
    meta: Optional[RunMeta] = None
    session_ids: list[str] = field(default_factory=list)
    dropped_task_ids: list[str] = field(default_factory=list)

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
                eval_rewards=h.get("eval_rewards", {}),
            ))
        meta_raw = raw.get("meta")
        meta = RunMeta(**meta_raw) if meta_raw else None
        return cls(
            system_prompt=raw.get("system_prompt"),
            prompt_instruction=raw.get("prompt_instruction"),
            tool_schemas=raw.get("tool_schemas"),
            tool_code=raw.get("tool_code"),
            history=history,
            meta=meta,
            session_ids=raw.get("session_ids", []),
            dropped_task_ids=raw.get("dropped_task_ids", []),
        )

    @property
    def total_fixed(self) -> int:
        return sum(r.num_fixed for r in self.history)

    @property
    def total_failures(self) -> int:
        return sum(r.num_failures for r in self.history)

    def flat_fixes(self) -> list[FixResult]:
        """All FixResults across all iterations, in order."""
        return [fix for r in self.history for fix in r.fixes]
