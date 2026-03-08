"""Shared data models for the evolution loop."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

# ── Constants for stringly-typed fields ────────────────────────────────────
# Fix tiers — which phase produced the fix.
FIX_TIER_PROMPT = "prompt"       # instruction-only patches (system prompt)
FIX_TIER_TOOLS = "tools"        # tool schema patches (possibly + prompt)
FIX_TIER_CODE = "code"          # tool preprocessor patches (guardrails)
FIX_TIER_NONE = "none"

# Run status values.
RUN_RUNNING = "running"
RUN_FINISHED = "finished"
RUN_STOPPED = "stopped"
RUN_ERROR = "error"

# Phase names (also in parallel_loop.py as PHASE_* constants).
PHASE_SWEEP = "sweep"
PHASE_FIX = "fix"
PHASE_MERGE = "merge"
PHASE_TEST = "test"

# Phase status values.
PHASE_RUNNING = "running"
PHASE_DONE = "done"
PHASE_SKIPPED = "skipped"
PHASE_WAITING = "waiting"


def task_passed(rewards: list[Optional[float]], threshold: float = 1.0) -> bool:
    """Task passes only if ALL valid trials pass."""
    valid = [r for r in rewards if r is not None]
    if not valid:
        return False
    return all(r >= threshold for r in valid)


def is_task_passed(reward_val) -> bool:
    """Check if a reward value (list or scalar) indicates a pass."""
    if isinstance(reward_val, list):
        return task_passed(reward_val)
    if reward_val is None:
        return False
    return reward_val >= 1.0


def is_task_error(reward_val) -> bool:
    """Check if a reward value indicates an error (all None)."""
    if isinstance(reward_val, list):
        return all(r is None for r in reward_val)
    return reward_val is None


def _coerce_rewards(raw: dict) -> dict[str, list[Optional[float]]]:
    """Normalise rewards from either old (single-float) or new (list) format."""
    out: dict[str, list[Optional[float]]] = {}
    for k, v in raw.items():
        if isinstance(v, list):
            out[k] = v
        else:
            out[k] = [v]
    return out


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
    fix_tier: str = FIX_TIER_NONE
    teacher_msgs: int = 0
    teacher_tool_calls: int = 0
    teacher_duration_s: float = 0.0
    error_count: int = 0

    @property
    def delta(self) -> float:
        return self.patched_reward - self.baseline_reward


@dataclass
class SweepResult:
    """Outcome of one sweep (run all train tasks → fix failures → merge)."""
    sweep: int
    num_evaluated: int
    num_failures: int
    fixes: list[FixResult]
    num_fixed: int
    sweep_rewards: dict[str, list[Optional[float]]] = field(default_factory=dict)  # task_id → [reward per trial]
    num_errors: int = 0


@dataclass
class TestResults:
    """Results of evaluating the evolved system on held-out test tasks."""
    baseline_rewards: dict[str, Union[list[Optional[float]], Optional[float]]] = field(default_factory=dict)
    evolved_rewards: dict[str, Union[list[Optional[float]], Optional[float]]] = field(default_factory=dict)
    prompt_only_rewards: dict[str, Union[list[Optional[float]], Optional[float]]] = field(default_factory=dict)

    def _pass_rate(self, rewards: dict) -> float:
        if not rewards:
            return 0.0
        return sum(1 for v in rewards.values() if is_task_passed(v)) / len(rewards)

    @property
    def baseline_pass_rate(self) -> float:
        return self._pass_rate(self.baseline_rewards)

    @property
    def evolved_pass_rate(self) -> float:
        return self._pass_rate(self.evolved_rewards)

    @property
    def prompt_only_pass_rate(self) -> float:
        return self._pass_rate(self.prompt_only_rewards)


@dataclass
class RunMeta:
    """Lightweight metadata for a run, used in the history sidebar."""
    run_id: str
    domain: str
    started_at: str  # ISO format
    status: str = RUN_RUNNING
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
    tool_schemas: Optional[dict] = None
    tool_code: Optional[dict[str, str]] = None  # tool_name → preprocessor source
    history: list[SweepResult] = field(default_factory=list)
    meta: Optional[RunMeta] = None
    session_ids: list[str] = field(default_factory=list)
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
                    fix_tier=f.get("fix_tier", FIX_TIER_NONE),
                    teacher_msgs=f.get("teacher_msgs", 0),
                    teacher_tool_calls=f.get("teacher_tool_calls", 0),
                    teacher_duration_s=f.get("teacher_duration_s", 0.0),
                    error_count=f.get("error_count", 0),
                )
                for f in h.get("fixes", [])
            ]
            raw_rewards = h.get("sweep_rewards", h.get("eval_rewards", {}))
            history.append(SweepResult(
                sweep=h.get("sweep", h.get("iteration", 0)),
                num_evaluated=h["num_evaluated"],
                num_failures=h["num_failures"],
                fixes=fixes,
                num_fixed=h["num_fixed"],
                sweep_rewards=_coerce_rewards(raw_rewards),
                num_errors=h.get("num_errors", 0),
            ))
        meta_raw = raw.get("meta")
        meta = RunMeta(**meta_raw) if meta_raw else None
        test_raw = raw.get("test_results")
        if test_raw:
            # Only pass known fields; coerce rewards to lists.
            known = {}
            for k in ("baseline_rewards", "evolved_rewards", "prompt_only_rewards"):
                if k in test_raw:
                    known[k] = _coerce_rewards(test_raw[k])
            test_results = TestResults(**known)
        else:
            test_results = None
        return cls(
            system_prompt=raw.get("system_prompt"),
            tool_schemas=raw.get("tool_schemas"),
            tool_code=raw.get("tool_code"),
            history=history,
            meta=meta,
            session_ids=raw.get("session_ids", []),
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
        """All FixResults across all sweeps, in order."""
        return [fix for r in self.history for fix in r.fixes]
