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
    DEFAULT_PARALLELISM, TEACHER_MODEL,
)
from evo.evaluation.runner import run_baseline, extract_failures
from evo.models import Patch, FixResult, IterationResult, LoopState, TestResults
from evo.reflection.teacher import TeacherSession, apply_patches
from evo.session_log import save_student_sessions, _calc_duration

log = logging.getLogger(__name__)


def _validate_patches(
    session: TeacherSession,
    task_id: str,
    domain: str,
    seed: int,
    attempt: int,
    student_model: Optional[str],
    parallelism: int,
    on_status: Callable[[str], None],
    on_session: Optional[Callable],
):
    """Run the student with the session's current patched state. Returns (val_sim, reward)."""
    on_status(f"[{task_id}] Validating...")
    val_results = run_baseline(
        domain=domain,
        task_ids=[task_id],
        seed=seed,
        system_prompt=session.current_prompt,
        tool_schemas=session.current_tool_schemas,
        tool_code=session.current_tool_code or None,
        save_name=f"fix_{task_id}_a{attempt}",
        student_model=student_model,
        parallelism=parallelism,
    )
    save_student_sessions(
        val_results,
        context=f"fix_{task_id}_a{attempt}",
        model=student_model or "",
        on_session=on_session,
    )
    val_sim = val_results.simulations[0]
    return val_sim, val_sim.reward_info.reward


def _fix_single_failure(
    sim,
    task,
    domain: str,
    seed: int,
    base_system_prompt: str,
    base_tool_schemas: dict[str, dict],
    base_tool_code: dict[str, str],
    tools: list,
    max_retries: int,
    on_status: Callable[[str], None],
    on_fix_attempt: Optional[Callable[[str, int, list[Patch], str, str], None]] = None,
    on_teacher_message: Optional[Callable] = None,
    on_session: Optional[Callable] = None,
    student_model: Optional[str] = None,
    parallelism: int = DEFAULT_PARALLELISM,
) -> FixResult:
    """Run teacher loop on one failure with two-phase escalation.

    Phase 1 (teaching): teacher can only use patch_prompt + patch_tool.
    Phase 2 (guardrails): if Phase 1 fails, unlock patch_tool_code and retry.

    The fix_tier field records which phase produced the fix:
    - "prompt": fixed by prompt/schema patches alone
    - "code": required tool code (preprocessor) patches
    - "none": not fixed
    """
    task_id = sim.task_id
    baseline_reward = sim.reward_info.reward

    session = TeacherSession(
        system_prompt=base_system_prompt,
        tools=tools,
        messages=sim.messages,
        task=task,
        reward_info=sim.reward_info,
        tool_schemas=deepcopy(base_tool_schemas),
        tool_code=deepcopy(base_tool_code),
        task_id=task_id,
        on_message=on_teacher_message,
    )

    all_patches: list[Patch] = []
    all_diagnoses: list[str] = []
    fixed = False
    fix_tier = "none"
    patched_reward = baseline_reward
    val_sim = None  # last validation sim, needed for escalation/retry
    attempt = 0

    # -- Phase 1: Teaching (prompt + schema only) --
    # Use ceil(total_attempts / 2) for Phase 1, rest for Phase 2.
    total_attempts = 1 + max_retries
    phase1_attempts = max(1, (total_attempts + 1) // 2)
    phase2_attempts = total_attempts - phase1_attempts

    for attempt in range(phase1_attempts):
        label = f"attempt {attempt + 1}/{total_attempts} [teaching]"
        on_status(f"[{task_id}] Teacher {label}...")

        patches, diagnosis = session.reflect()
        all_diagnoses.append(diagnosis)

        if diagnosis:
            on_status(f"[{task_id}] Diagnosis: {diagnosis[:200]}")

        if not patches:
            on_status(f"[{task_id}] Teacher returned no patches.")
            break

        on_status(f"[{task_id}] Got {len(patches)} patch(es) [teaching].")
        all_patches.extend(patches)

        if on_fix_attempt:
            on_fix_attempt(task_id, attempt, list(all_patches), diagnosis, "reflecting")

        val_sim, patched_reward = _validate_patches(
            session, task_id, domain, seed, attempt,
            student_model, parallelism, on_status, on_session,
        )
        fixed = patched_reward > baseline_reward

        on_status(
            f"[{task_id}] {baseline_reward:.2f} -> {patched_reward:.2f} "
            f"({'FIXED [teaching]' if fixed else 'NOT FIXED'})"
        )

        if on_fix_attempt:
            on_fix_attempt(task_id, attempt, list(all_patches), diagnosis,
                           "fixed" if fixed else "validating")

        if fixed:
            fix_tier = "prompt"
            break

        if attempt < phase1_attempts - 1:
            session.report_failure(
                baseline_reward=baseline_reward,
                patched_reward=patched_reward,
                new_sim=val_sim,
            )

    # -- Phase 2: Guardrails (unlock tool code) --
    if not fixed and phase2_attempts > 0 and val_sim is not None:
        on_status(f"[{task_id}] Escalating: unlocking tool code patches...")
        session.escalate(
            baseline_reward=baseline_reward,
            patched_reward=patched_reward,
            new_sim=val_sim,
        )

        for phase2_idx in range(phase2_attempts):
            attempt = phase1_attempts + phase2_idx
            label = f"attempt {attempt + 1}/{total_attempts} [guardrails]"
            on_status(f"[{task_id}] Teacher {label}...")

            patches, diagnosis = session.reflect()
            all_diagnoses.append(diagnosis)

            if diagnosis:
                on_status(f"[{task_id}] Diagnosis: {diagnosis[:200]}")

            if not patches:
                on_status(f"[{task_id}] Teacher returned no patches.")
                break

            on_status(f"[{task_id}] Got {len(patches)} patch(es) [guardrails].")
            all_patches.extend(patches)

            if on_fix_attempt:
                on_fix_attempt(task_id, attempt, list(all_patches), diagnosis, "reflecting")

            val_sim, patched_reward = _validate_patches(
                session, task_id, domain, seed, attempt,
                student_model, parallelism, on_status, on_session,
            )
            fixed = patched_reward > baseline_reward

            on_status(
                f"[{task_id}] {baseline_reward:.2f} -> {patched_reward:.2f} "
                f"({'FIXED [guardrails]' if fixed else 'NOT FIXED'})"
            )

            if on_fix_attempt:
                on_fix_attempt(task_id, attempt, list(all_patches), diagnosis,
                               "fixed" if fixed else "validating")

            if fixed:
                fix_tier = "code"
                break

            if phase2_idx < phase2_attempts - 1:
                session.report_failure(
                    baseline_reward=baseline_reward,
                    patched_reward=patched_reward,
                    new_sim=val_sim,
                )

    session_data = session._as_session_data()
    teacher_msgs = len(session_data.messages)
    teacher_tool_calls = sum(
        1 for m in session_data.messages if m.tool_calls
    )
    teacher_duration_s = _calc_duration(session_data) or 0.0

    return FixResult(
        task_id=task_id,
        baseline_reward=baseline_reward,
        patched_reward=patched_reward,
        diagnosis="\n---\n".join(d for d in all_diagnoses if d),
        patches=all_patches if fixed else [],
        retries=attempt,
        fixed=fixed,
        fix_tier=fix_tier,
        teacher_msgs=teacher_msgs,
        teacher_tool_calls=teacher_tool_calls,
        teacher_duration_s=round(teacher_duration_s, 1),
    )


def _run_test_evaluation(
    domain: str,
    test_ids: list[str],
    seed: int,
    evolved_prompt: Optional[str],
    evolved_schemas: Optional[dict],
    evolved_code: Optional[dict[str, str]],
    student_model: Optional[str],
    parallelism: int,
    on_status: Callable[[str], None],
    on_session: Optional[Callable] = None,
) -> TestResults:
    """Run all four conditions on the held-out test split."""
    on_status("\n" + "=" * 60)
    on_status("TEST EVALUATION (held-out test split)")
    on_status("=" * 60)

    def _rewards(results) -> dict[str, float]:
        return {
            s.task_id: s.reward_info.reward
            for s in results.simulations
            if s.reward_info is not None
        }

    # a) Baseline: default prompt, no patches
    on_status(f"[test] Running baseline ({len(test_ids)} tasks)...")
    baseline = run_baseline(
        domain=domain, task_ids=test_ids, seed=seed,
        save_name="test_baseline", student_model=student_model,
        parallelism=parallelism,
    )
    baseline_rewards = _rewards(baseline)
    bp = sum(1 for r in baseline_rewards.values() if r >= 1.0)
    on_status(f"[test] Baseline: {bp}/{len(baseline_rewards)} passed")

    # b) Evolved: full evolved system
    on_status(f"[test] Running evolved ({len(test_ids)} tasks)...")
    evolved = run_baseline(
        domain=domain, task_ids=test_ids, seed=seed,
        system_prompt=evolved_prompt, tool_schemas=evolved_schemas,
        tool_code=evolved_code, save_name="test_evolved",
        student_model=student_model, parallelism=parallelism,
    )
    evolved_rewards = _rewards(evolved)
    ep = sum(1 for r in evolved_rewards.values() if r >= 1.0)
    on_status(f"[test] Evolved: {ep}/{len(evolved_rewards)} passed")

    # c) Prompt-only: evolved prompt + schemas, NO code patches
    on_status(f"[test] Running prompt-only ({len(test_ids)} tasks)...")
    prompt_only = run_baseline(
        domain=domain, task_ids=test_ids, seed=seed,
        system_prompt=evolved_prompt, tool_schemas=evolved_schemas,
        tool_code=None, save_name="test_prompt_only",
        student_model=student_model, parallelism=parallelism,
    )
    prompt_only_rewards = _rewards(prompt_only)
    pp = sum(1 for r in prompt_only_rewards.values() if r >= 1.0)
    on_status(f"[test] Prompt-only: {pp}/{len(prompt_only_rewards)} passed")

    # d) Frontier: teacher model as student, default prompt
    on_status(f"[test] Running frontier / {TEACHER_MODEL} ({len(test_ids)} tasks)...")
    frontier = run_baseline(
        domain=domain, task_ids=test_ids, seed=seed,
        save_name="test_frontier", student_model=TEACHER_MODEL,
        parallelism=parallelism,
    )
    frontier_rewards = _rewards(frontier)
    fp = sum(1 for r in frontier_rewards.values() if r >= 1.0)
    on_status(f"[test] Frontier: {fp}/{len(frontier_rewards)} passed")

    tr = TestResults(
        baseline_rewards=baseline_rewards,
        evolved_rewards=evolved_rewards,
        prompt_only_rewards=prompt_only_rewards,
        frontier_rewards=frontier_rewards,
    )
    on_status(
        f"[test] Gap closure: {tr.gap_closure:.1%}"
        if tr.gap_closure is not None else "[test] Gap closure: N/A (no gap)"
    )
    return tr


def run_loop(
    domain: str = DEFAULT_DOMAIN,
    num_tasks: int = DEFAULT_NUM_TASKS,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    seed: int = DEFAULT_SEED,
    task_ids: Optional[list[str]] = None,
    parallelism: int = DEFAULT_PARALLELISM,
    student_model: Optional[str] = None,
    use_split: bool = True,
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

    # Load train/test splits if enabled.
    train_ids: Optional[list[str]] = None
    test_ids: list[str] = []
    if use_split and task_ids is None:
        from tau2.run import load_task_splits
        splits = load_task_splits(domain)
        if splits:
            train_ids = splits["train"]
            test_ids = splits["test"]
            task_ids = train_ids[:num_tasks] if num_tasks < len(train_ids) else train_ids
            status(f"Using canonical split: {len(train_ids)} train, {len(test_ids)} test")
            status(f"Evolving on {len(task_ids)} train task(s)")
        else:
            status(f"No canonical splits for {domain}, using all tasks")
    elif task_ids is not None:
        train_ids = task_ids

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
    current_tool_code: dict[str, str] = {}
    log.debug("System prompt: %d chars, policy: %d chars", len(current_system_prompt), len(domain_policy))

    dropped_task_ids: set[str] = set()

    for iteration in range(1, max_iterations + 1):
        status(f"\n{'='*60}")
        status(f"ITERATION {iteration}/{max_iterations}")
        status(f"{'='*60}")

        # -- 1. Evaluate all tasks (excluding permanently dropped) ----------
        eval_task_ids = task_ids
        if eval_task_ids is not None and dropped_task_ids:
            eval_task_ids = [t for t in eval_task_ids if t not in dropped_task_ids]
        if dropped_task_ids:
            status(f"Skipping {len(dropped_task_ids)} permanently dropped task(s): {sorted(dropped_task_ids)}")

        label = f"tasks {eval_task_ids}" if eval_task_ids else f"{num_tasks} tasks"
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
            task_ids=eval_task_ids,
            seed=seed,
            system_prompt=current_system_prompt,
            tool_schemas=current_tool_schemas,
            tool_code=current_tool_code or None,
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

        # After first eval, lock in task IDs so we can exclude dropped ones.
        if task_ids is None:
            task_ids = [sim.task_id for sim in results.simulations]
            status(f"Locked task set: {task_ids}")

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
                    base_tool_code=current_tool_code,
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

        # -- 3. Drop all failed tasks (fixed or not), merge winning patches --
        winners = [f for f in fix_results if f.fixed]
        for f in fix_results:
            dropped_task_ids.add(f.task_id)
            label = "fixed, validated during fix phase" if f.fixed else "teacher could not fix"
            status(f"[{f.task_id}] Dropped ({label}).")
        status(f"\n{len(winners)}/{len(fix_results)} failures fixed. Merging patches...")

        for fix in winners:
            current_system_prompt, current_tool_schemas, current_tool_code = apply_patches(
                current_system_prompt, current_tool_schemas, fix.patches, current_tool_code,
            )

        state.system_prompt = current_system_prompt
        state.tool_schemas = current_tool_schemas
        state.tool_code = current_tool_code or None
        state.dropped_task_ids = sorted(dropped_task_ids)
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

    # -- Store split info ----------------------------------------------------
    state.train_task_ids = train_ids or task_ids or []
    state.test_task_ids = test_ids

    # -- Phase 2: Test evaluation on held-out split -------------------------
    if test_ids:
        state.test_results = _run_test_evaluation(
            domain=domain,
            test_ids=test_ids,
            seed=seed,
            evolved_prompt=state.system_prompt,
            evolved_schemas=state.tool_schemas,
            evolved_code=state.tool_code,
            student_model=student_model,
            parallelism=parallelism,
            on_status=status,
            on_session=on_session,
        )
        if on_iteration:
            on_iteration(state)

    # -- Save final state ---------------------------------------------------
    state.save(PATCHES_DIR / "loop_state.json")
    status(f"\nLoop complete. {state.total_fixed}/{state.total_failures} total fixes across {len(state.history)} iteration(s).")
    return state
