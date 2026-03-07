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
    DEFAULT_PARALLELISM,
)
from evo.evaluation.runner import run_baseline, extract_failures
from evo.models import Patch, FixResult, IterationResult, LoopState
from evo.reflection.teacher import TeacherSession, apply_patches
from evo.session_log import save_student_sessions

log = logging.getLogger(__name__)


def _fix_single_failure(
    sim,
    task,
    domain: str,
    seed: int,
    base_system_prompt: str,
    base_tool_schemas: dict[str, dict],
    tools: list,
    max_retries: int,
    on_status: Callable[[str], None],
    on_fix_attempt: Optional[Callable[[str, int, list[Patch], str, str], None]] = None,
    on_teacher_message: Optional[Callable] = None,
    on_session: Optional[Callable] = None,
    student_model: Optional[str] = None,
    parallelism: int = DEFAULT_PARALLELISM,
) -> FixResult:
    """Run teacher loop on one failure. Returns FixResult."""
    task_id = sim.task_id
    baseline_reward = sim.reward_info.reward

    session = TeacherSession(
        system_prompt=base_system_prompt,
        tools=tools,
        messages=sim.messages,
        task=task,
        reward_info=sim.reward_info,
        tool_schemas=deepcopy(base_tool_schemas),
        task_id=task_id,
        on_message=on_teacher_message,
    )

    all_patches: list[Patch] = []
    all_diagnoses: list[str] = []
    fixed = False
    patched_reward = baseline_reward
    attempt = 0

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

        if on_fix_attempt:
            on_fix_attempt(task_id, attempt, list(all_patches), diagnosis, "reflecting")

        # Use the session's live-patched state for validation.
        on_status(f"[{task_id}] Validating...")
        val_results = run_baseline(
            domain=domain,
            task_ids=[task_id],
            seed=seed,
            system_prompt=session.current_prompt,
            tool_schemas=session.current_tool_schemas,
            save_name=f"fix_{task_id}_a{attempt}",
            student_model=student_model,
            parallelism=parallelism,
        )

        # Log validation student session.
        save_student_sessions(
            val_results,
            context=f"fix_{task_id}_a{attempt}",
            model=student_model or "",
            on_session=on_session,
        )

        val_sim = val_results.simulations[0]
        patched_reward = val_sim.reward_info.reward
        fixed = patched_reward > baseline_reward

        on_status(
            f"[{task_id}] {baseline_reward:.2f} -> {patched_reward:.2f} "
            f"({'FIXED' if fixed else 'NOT FIXED'})"
        )

        if on_fix_attempt:
            on_fix_attempt(task_id, attempt, list(all_patches), diagnosis,
                           "fixed" if fixed else "validating")

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
    parallelism: int = DEFAULT_PARALLELISM,
    student_model: Optional[str] = None,
    on_status: Optional[Callable[[str], None]] = None,
    on_iteration: Optional[Callable[[LoopState], None]] = None,
    on_fix_attempt: Optional[Callable[[str, int, list[Patch], str, str], None]] = None,
    on_teacher_message: Optional[Callable] = None,
    on_session: Optional[Callable] = None,
) -> LoopState:
    """Run the parallel evolution loop."""
    state = LoopState()

    def status(msg: str):
        if on_status:
            on_status(msg)

    # Pre-load domain tools and policy once.
    env = tau2_registry.get_env_constructor(domain)()
    tools = env.get_tools()
    domain_policy = env.get_policy()

    current_system_prompt = SYSTEM_PROMPT.format(
        domain_policy=domain_policy,
        agent_instruction=AGENT_INSTRUCTION,
    )
    current_tool_schemas: dict[str, dict] = {
        t.name: deepcopy(t.openai_schema) for t in tools
    }
    log.debug("System prompt: %d chars, policy: %d chars", len(current_system_prompt), len(domain_policy))

    for iteration in range(1, max_iterations + 1):
        status(f"\n{'='*60}")
        status(f"ITERATION {iteration}/{max_iterations}")
        status(f"{'='*60}")

        # -- 1. Evaluate all tasks ------------------------------------------
        label = f"tasks {task_ids}" if task_ids else f"{num_tasks} tasks"
        status(f"Evaluating {domain} ({label})...")

        def _on_task(task_id, trial, reward):
            if reward is not None:
                marker = "PASS" if reward >= 1.0 else "FAIL"
                status(f"  Task {task_id} done — reward {reward:.2f} [{marker}]")
            else:
                status(f"  Task {task_id} done — no reward")

        results = run_baseline(
            domain=domain,
            num_tasks=num_tasks,
            task_ids=task_ids,
            seed=seed,
            system_prompt=current_system_prompt,
            tool_schemas=current_tool_schemas,
            save_name=f"eval_iter{iteration}",
            on_task_complete=_on_task if on_status else None,
            student_model=student_model,
            parallelism=parallelism,
        )

        # Log student sessions.
        save_student_sessions(
            results,
            context=f"eval_iter{iteration}",
            model=student_model or "",
            on_session=on_session,
        )

        failures = extract_failures(results)
        eval_rewards = {
            sim.task_id: sim.reward_info.reward
            for sim in results.simulations
            if sim.reward_info is not None
        }
        status(f"Evaluation done. {len(failures)}/{len(results.simulations)} tasks failed.")

        if not failures:
            status("All tasks pass!")
            state.history.append(IterationResult(
                iteration=iteration,
                num_evaluated=len(results.simulations),
                num_failures=0,
                fixes=[],
                num_fixed=0,
                eval_rewards=eval_rewards,
            ))
            if on_iteration:
                on_iteration(state)
            break

        # -- 2. Fix each failure in parallel --------------------------------
        status(f"Spawning {len(failures)} parallel teacher(s)...")

        fix_results: list[FixResult] = []
        workers = min(parallelism, len(failures))

        task_by_id = {t.id: t for t in results.tasks}

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for sim in failures:
                future = pool.submit(
                    _fix_single_failure,
                    sim=sim,
                    task=task_by_id.get(sim.task_id),
                    domain=domain,
                    seed=seed,
                    base_system_prompt=current_system_prompt,
                    base_tool_schemas=current_tool_schemas,
                    tools=tools,
                    max_retries=max_retries,
                    on_status=status,
                    on_fix_attempt=on_fix_attempt,
                    on_teacher_message=on_teacher_message,
                    on_session=on_session,
                    student_model=student_model,
                    parallelism=parallelism,
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
                    # Don't silently drop — record as an unfixed result.
                    fix_results.append(FixResult(
                        task_id=task_id,
                        baseline_reward=eval_rewards.get(task_id, 0.0),
                        patched_reward=eval_rewards.get(task_id, 0.0),
                        diagnosis=f"Teacher crashed: {e}",
                        patches=[],
                        retries=0,
                        fixed=False,
                    ))

        # -- 3. Merge winning patches (sequential apply) --------------------
        winners = [f for f in fix_results if f.fixed]
        status(f"\n{len(winners)}/{len(fix_results)} failures fixed. Merging patches...")

        for fix in winners:
            current_system_prompt, current_tool_schemas = apply_patches(
                current_system_prompt, current_tool_schemas, fix.patches,
            )

        state.system_prompt = current_system_prompt
        state.tool_schemas = current_tool_schemas
        state.history.append(IterationResult(
            iteration=iteration,
            num_evaluated=len(results.simulations),
            num_failures=len(failures),
            fixes=fix_results,
            num_fixed=len(winners),
            eval_rewards=eval_rewards,
        ))

        if on_iteration:
            on_iteration(state)

    # -- Save final state ---------------------------------------------------
    state.save(PATCHES_DIR / "loop_state.json")
    status(f"\nLoop complete. {state.total_fixed}/{state.total_failures} total fixes across {len(state.history)} iteration(s).")
    return state
