"""Parallel evolution loop: evaluate -> fix failures concurrently -> merge -> repeat."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from typing import Callable, Optional

from tau2.agent.llm_agent import AGENT_INSTRUCTION, SYSTEM_PROMPT
from tau2.registry import registry as tau2_registry

from evo.config import (
    PATCHES_DIR, DEFAULT_DOMAIN, DEFAULT_NUM_TASKS,
    DEFAULT_MAX_ITERATIONS, DEFAULT_MAX_RETRIES, DEFAULT_SEED,
)
from evo.evaluation.runner import run_baseline, extract_failures
from evo.models import Patch, FixResult, IterationResult, LoopState
from evo.reflection.teacher import TeacherSession, apply_patches

log = logging.getLogger(__name__)


def _fix_single_failure(
    sim,
    task,
    domain: str,
    seed: int,
    base_instruction: str,
    base_tool_schemas: dict[str, dict],
    domain_policy: str,
    tools: list,
    max_retries: int,
    on_status: Callable[[str], None],
) -> FixResult:
    """Run teacher loop on one failure. Returns FixResult."""
    task_id = sim.task_id
    baseline_reward = sim.reward_info.reward

    agent_system_prompt = SYSTEM_PROMPT.format(
        domain_policy=domain_policy,
        agent_instruction=base_instruction,
    )

    session = TeacherSession(
        system_prompt=agent_system_prompt,
        tools=tools,
        messages=sim.messages,
        task=task,
        reward_info=sim.reward_info,
    )

    # Work on a local copy — don't mutate the shared base.
    local_instruction = base_instruction
    local_tool_schemas = deepcopy(base_tool_schemas)

    all_patches: list[Patch] = []
    all_diagnoses: list[str] = []
    fixed = False
    patched_reward = baseline_reward

    for attempt in range(1 + max_retries):
        label = f"attempt {attempt + 1}/{1 + max_retries}"
        on_status(f"[{task_id}] Teacher {label}...")

        patches, diagnosis = session.reflect()
        all_diagnoses.append(diagnosis)

        if diagnosis:
            on_status(f"[{task_id}] Diagnosis: {diagnosis[:200]}")

        if not patches:
            on_status(f"[{task_id}] Teacher returned no patches.")
            break

        on_status(f"[{task_id}] Got {len(patches)} patch(es).")
        all_patches.extend(patches)

        local_instruction, local_tool_schemas = apply_patches(
            local_instruction, local_tool_schemas, patches,
        )

        on_status(f"[{task_id}] Validating...")
        val_results = run_baseline(
            domain=domain,
            task_ids=[task_id],
            seed=seed,
            prompt_instruction=local_instruction,
            tool_schemas=local_tool_schemas,
            save_name=f"fix_{task_id}_a{attempt}",
        )

        val_sim = val_results.simulations[0]
        patched_reward = val_sim.reward_info.reward
        fixed = patched_reward > baseline_reward

        on_status(
            f"[{task_id}] {baseline_reward:.2f} -> {patched_reward:.2f} "
            f"({'FIXED' if fixed else 'NOT FIXED'})"
        )

        if fixed:
            break

        if attempt < max_retries:
            session.report_failure(
                baseline_reward=baseline_reward,
                patched_reward=patched_reward,
                new_sim=val_sim,
            )

    return FixResult(
        task_id=task_id,
        baseline_reward=baseline_reward,
        patched_reward=patched_reward,
        diagnosis="\n---\n".join(d for d in all_diagnoses if d),
        patches=all_patches if fixed else [],
        retries=attempt,
        fixed=fixed,
    )


def run_loop(
    domain: str = DEFAULT_DOMAIN,
    num_tasks: int = DEFAULT_NUM_TASKS,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    seed: int = DEFAULT_SEED,
    task_ids: Optional[list[str]] = None,
    max_workers: int = 4,
    on_status: Optional[Callable[[str], None]] = None,
) -> LoopState:
    """Run the parallel evolution loop."""
    state = LoopState()

    def status(msg: str):
        if on_status:
            on_status(msg)

    # Pre-load domain tools and policy once.
    env = tau2_registry.get_env_constructor(domain)()
    tools = env.get_tools()
    domain_policy = env.domain_policy if hasattr(env, "domain_policy") else ""

    current_instruction = AGENT_INSTRUCTION
    current_tool_schemas: dict[str, dict] = {
        t.name: deepcopy(t.openai_schema) for t in tools
    }

    for iteration in range(1, max_iterations + 1):
        status(f"\n{'='*60}")
        status(f"ITERATION {iteration}/{max_iterations}")
        status(f"{'='*60}")

        # -- 1. Evaluate all tasks ------------------------------------------
        label = f"tasks {task_ids}" if task_ids else f"{num_tasks} tasks"
        status(f"Evaluating {domain} ({label})...")
        results = run_baseline(
            domain=domain,
            num_tasks=num_tasks,
            task_ids=task_ids,
            seed=seed,
            prompt_instruction=current_instruction if state.history else None,
            tool_schemas=current_tool_schemas if state.history else None,
            save_name=f"eval_iter{iteration}",
        )

        failures = extract_failures(results)
        status(f"Evaluation done. {len(failures)}/{len(results.simulations)} tasks failed.")

        if not failures:
            status("All tasks pass!")
            break

        # -- 2. Fix each failure in parallel --------------------------------
        status(f"Spawning {len(failures)} parallel teacher(s)...")

        fix_results: list[FixResult] = []
        workers = min(max_workers, len(failures))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for sim in failures:
                task = next((t for t in results.tasks if t.id == sim.task_id), None)
                future = pool.submit(
                    _fix_single_failure,
                    sim=sim,
                    task=task,
                    domain=domain,
                    seed=seed,
                    base_instruction=current_instruction,
                    base_tool_schemas=current_tool_schemas,
                    domain_policy=domain_policy,
                    tools=tools,
                    max_retries=max_retries,
                    on_status=status,
                )
                futures[future] = sim.task_id

            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    result = future.result()
                    fix_results.append(result)
                except Exception as e:
                    status(f"[{task_id}] ERROR: {e}")
                    log.exception(f"Teacher failed for {task_id}")

        # -- 3. Merge winning patches (sequential apply) --------------------
        winners = [f for f in fix_results if f.fixed]
        status(f"\n{len(winners)}/{len(fix_results)} failures fixed. Merging patches...")

        for fix in winners:
            current_instruction, current_tool_schemas = apply_patches(
                current_instruction, current_tool_schemas, fix.patches,
            )

        state.prompt_instruction = current_instruction
        state.tool_schemas = current_tool_schemas
        state.history.append(IterationResult(
            iteration=iteration,
            num_evaluated=len(results.simulations),
            num_failures=len(failures),
            fixes=fix_results,
            num_fixed=len(winners),
        ))

    # -- Save final state ---------------------------------------------------
    state.save(PATCHES_DIR / "loop_state.json")
    total_fixed = sum(r.num_fixed for r in state.history)
    total_failures = sum(r.num_failures for r in state.history)
    status(f"\nLoop complete. {total_fixed}/{total_failures} total fixes across {len(state.history)} iteration(s).")
    return state
