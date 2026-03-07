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
    fix_tier: str = "none"  # "prompt" | "code" | "none"

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
class TestResults:
    """Results of evaluating the evolved system on held-out test tasks."""
    baseline_rewards: dict[str, float] = field(default_factory=dict)
    evolved_rewards: dict[str, float] = field(default_factory=dict)
    prompt_only_rewards: dict[str, float] = field(default_factory=dict)
    frontier_rewards: dict[str, float] = field(default_factory=dict)

    def _pass_rate(self, rewards: dict[str, float]) -> float:
        if not rewards:
            return 0.0
        return sum(1 for r in rewards.values() if r >= 1.0) / len(rewards)

    @property
    def baseline_pass_rate(self) -> float:
        return self._pass_rate(self.baseline_rewards)

    @property
    def evolved_pass_rate(self) -> float:
        return self._pass_rate(self.evolved_rewards)

    @property
    def prompt_only_pass_rate(self) -> float:
        return self._pass_rate(self.prompt_only_rewards)

    @property
    def frontier_pass_rate(self) -> float:
        return self._pass_rate(self.frontier_rewards)

    @property
    def gap_closure(self) -> Optional[float]:
        """(evolved - baseline) / (frontier - baseline). None if denominator is 0."""
        gap = self.frontier_pass_rate - self.baseline_pass_rate
        if gap <= 0:
            return None
        return (self.evolved_pass_rate - self.baseline_pass_rate) / gap

    @property
    def prompt_only_gap_closure(self) -> Optional[float]:
        gap = self.frontier_pass_rate - self.baseline_pass_rate
        if gap <= 0:
            return None
        return (self.prompt_only_pass_rate - self.baseline_pass_rate) / gap


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
    train_task_ids: list[str] = field(default_factory=list)
    test_task_ids: list[str] = field(default_factory=list)
    test_results: Optional[TestResults] = None

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
                    fix_tier=f.get("fix_tier", "none"),
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
        test_raw = raw.get("test_results")
        test_results = TestResults(**test_raw) if test_raw else None
        return cls(
            system_prompt=raw.get("system_prompt"),
            prompt_instruction=raw.get("prompt_instruction"),
            tool_schemas=raw.get("tool_schemas"),
            tool_code=raw.get("tool_code"),
            history=history,
            meta=meta,
            session_ids=raw.get("session_ids", []),
            dropped_task_ids=raw.get("dropped_task_ids", []),
            train_task_ids=raw.get("train_task_ids", []),
            test_task_ids=raw.get("test_task_ids", []),
            test_results=test_results,
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
