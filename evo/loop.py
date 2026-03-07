"""Core evolution loop: run -> find failures -> reflect -> patch -> validate."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

from tau2.registry import registry as tau2_registry

from evo.config import PATCHES_DIR, DEFAULT_DOMAIN, DEFAULT_NUM_TASKS, DEFAULT_MAX_ITERATIONS, DEFAULT_SEED
from evo.evaluation.runner import run_baseline, extract_failures
from evo.reflection.teacher import reflect, merge_patches


@dataclass
class IterationResult:
    iteration: int
    task_id: str
    baseline_reward: float
    diagnosis: dict
    delta_prompt_patch: Optional[str]
    delta_tool_patches: Optional[dict]
    patched_reward: float
    fixed: bool


@dataclass
class LoopState:
    prompt_patch: Optional[str] = None
    tool_patches: Optional[dict] = None
    history: list[IterationResult] = field(default_factory=list)

    def save(self, path: Path) -> None:
        data = {
            "prompt_patch": self.prompt_patch,
            "tool_patches": self.tool_patches,
            "history": [asdict(r) for r in self.history],
        }
        path.write_text(json.dumps(data, indent=2))


def run_loop(
    domain: str = DEFAULT_DOMAIN,
    num_tasks: int = DEFAULT_NUM_TASKS,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    seed: int = DEFAULT_SEED,
    task_ids: Optional[list[str]] = None,
    on_status: Optional[Callable[[str], None]] = None,
) -> LoopState:
    """Run the full evolution loop.

    If task_ids is given, skip the broad baseline and run only those tasks.
    Otherwise: run baseline, find failures, then iterate.
    """
    state = LoopState()

    def status(msg: str):
        if on_status:
            on_status(msg)

    # ── Step 1: Baseline run ─────────────────────────────────────────────
    label = f"tasks {task_ids}" if task_ids else f"{num_tasks} tasks"
    status(f"Running baseline on {domain} ({label})...")
    results = run_baseline(
        domain=domain,
        num_tasks=num_tasks,
        task_ids=task_ids,
        seed=seed,
        save_name="baseline",
    )

    failures = extract_failures(results)
    status(f"Baseline done. {len(failures)}/{len(results.simulations)} tasks failed.")

    if not failures:
        status("No failures found — nothing to fix!")
        return state

    # Pre-load domain tools once (they don't change between iterations).
    env = tau2_registry.get_env_constructor(domain)()
    tools = env.get_tools()

    # ── Step 2-N: Iterate over failures ──────────────────────────────────
    for i, sim in enumerate(failures[:max_iterations]):
        iteration = i + 1
        task_id = sim.task_id
        baseline_reward = sim.reward_info.reward
        status(f"\n--- Iteration {iteration}: fixing task {task_id} (reward={baseline_reward:.2f}) ---")

        task = next((t for t in results.tasks if t.id == task_id), None)

        # ── Reflect ──────────────────────────────────────────────────────
        status("Sending failure to teacher for reflection...")

        agent_system_prompt = ""
        for msg in sim.messages:
            if hasattr(msg, "role") and msg.role == "system":
                agent_system_prompt = msg.content
                break

        patch = reflect(
            system_prompt=agent_system_prompt,
            tools=tools,
            messages=sim.messages,
            task=task,
            reward_info=sim.reward_info,
        )

        status(f"Diagnosis: {patch['diagnosis']['failure_type']} — {patch['diagnosis']['explanation']}")

        # ── Merge patches ────────────────────────────────────────────────
        state.prompt_patch, state.tool_patches = merge_patches(
            state.prompt_patch, state.tool_patches, patch,
        )

        if patch.get("prompt_patch"):
            status(f"Prompt patch: {patch['prompt_patch'][:200]}")
        if patch.get("tool_patches"):
            status(f"Tool patches: {list(patch['tool_patches'].keys())}")

        # ── Validate ─────────────────────────────────────────────────────
        status(f"Re-running task {task_id} with patches...")
        val_results = run_baseline(
            domain=domain,
            task_ids=[task_id],
            seed=seed,
            prompt_patch=state.prompt_patch,
            tool_patches=state.tool_patches,
            save_name=f"patched_iter{iteration}",
        )

        patched_reward = val_results.simulations[0].reward_info.reward
        fixed = patched_reward > baseline_reward

        state.history.append(IterationResult(
            iteration=iteration,
            task_id=task_id,
            baseline_reward=baseline_reward,
            diagnosis=patch["diagnosis"],
            delta_prompt_patch=patch.get("prompt_patch"),
            delta_tool_patches=patch.get("tool_patches"),
            patched_reward=patched_reward,
            fixed=fixed,
        ))

        status(
            f"Result: reward {baseline_reward:.2f} -> {patched_reward:.2f} "
            f"({'FIXED' if fixed else 'NOT FIXED'})"
        )

    # ── Save final state ─────────────────────────────────────────────────
    state.save(PATCHES_DIR / "loop_state.json")
    status(f"\nLoop complete. {sum(1 for r in state.history if r.fixed)}/{len(state.history)} tasks fixed.")
    return state
