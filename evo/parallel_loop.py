"""Parallel evolution loop: sweep -> fix failures concurrently -> merge -> repeat."""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from typing import Callable, Optional

from tau2.agent.llm_agent import AGENT_INSTRUCTION, SYSTEM_PROMPT
from tau2.registry import registry as tau2_registry

from evo.config import (
    PATCHES_DIR, DEFAULT_DOMAIN, DEFAULT_NUM_TASKS,
    DEFAULT_MAX_SWEEPS, DEFAULT_MAX_RETRIES, DEFAULT_SEED,
    DEFAULT_PARALLELISM, DEFAULT_NUM_TRIALS,
    MAX_ERRORS_PER_TASK, VERIFY_RETRIES, VERIFY_BACKOFF,
)
from evo.evaluation.runner import run_tasks, extract_failures
from evo.models import (
    Patch, FixResult, SweepResult, LoopState, TestResults,
    FIX_TIER_PROMPT, FIX_TIER_TOOLS, FIX_TIER_CODE, FIX_TIER_NONE,
    PHASE_SWEEP, PHASE_FIX, PHASE_MERGE, PHASE_TEST,
    PHASE_RUNNING, PHASE_DONE, PHASE_SKIPPED,
    RUN_RUNNING, RUN_FINISHED, RUN_STOPPED, RUN_ERROR,
    task_passed,
)
from evo.merge import merge_fixes
from evo.reflection.teacher import TeacherSession, apply_patches
from evo.session_log import save_student_sessions, _calc_duration

log = logging.getLogger(__name__)


def _extract_rewards(simulations) -> tuple[dict[str, list[float | None]], int]:
    """Extract task_id → [rewards] from simulations (one per trial). Returns (rewards, num_errors)."""
    rewards: dict[str, list[float | None]] = {}
    num_errors = 0
    for s in simulations:
        if s.task_id not in rewards:
            rewards[s.task_id] = []
        if s.reward_info is not None:
            rewards[s.task_id].append(s.reward_info.reward)
        else:
            rewards[s.task_id].append(None)
            num_errors += 1
    return rewards, num_errors


def _verify_patches(
    session: TeacherSession,
    task_id: str,
    domain: str,
    seed: int,
    attempt: int,
    num_trials: int,
    student_model: Optional[str],
    parallelism: int,
    on_status: Callable[[str], None],
    on_session: Optional[Callable],
):
    """Re-run the student on one task (num_trials times) to verify the teacher's patches helped.

    Returns (sim, passed, error_occurred).
    """
    on_status(f"[{task_id}] Verifying ({num_trials} trials)...")
    for retry in range(VERIFY_RETRIES):
        try:
            results = run_tasks(
                domain=domain,
                task_ids=[task_id],
                seed=seed,
                num_trials=num_trials,
                system_prompt=session.current_prompt,
                tool_schemas=session.current_tool_schemas,
                tool_code=session.current_tool_code or None,
                save_name=f"verify_{task_id}_a{attempt}",
                student_model=student_model,
                parallelism=parallelism,
            )
            save_student_sessions(
                results,
                context=f"verify_{task_id}_a{attempt}",
                model=student_model or "",
                on_session=on_session,
            )
            rewards, _ = _extract_rewards(results.simulations)
            passed = task_passed(rewards.get(task_id, []))
            # Pick the worst sim as representative
            valid = [s for s in results.simulations if s.reward_info is not None]
            sim = min(valid, key=lambda s: s.reward_info.reward) if valid else results.simulations[0]
            return sim, passed, False
        except Exception as e:
            log.warning("[%s] Verify error (retry %d/%d): %s", task_id, retry + 1, VERIFY_RETRIES, e)
            on_status(f"[{task_id}] Verify error (retry {retry + 1}/{VERIFY_RETRIES}): {e}")
            if retry < VERIFY_RETRIES - 1:
                time.sleep(VERIFY_BACKOFF * (retry + 1))
    return None, False, True


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
    num_trials: int,
    on_status: Callable[[str], None],
    on_fix_attempt: Optional[Callable[[str, int, list[Patch], str, str], None]] = None,
    on_teacher_message: Optional[Callable] = None,
    on_session: Optional[Callable] = None,
    student_model: Optional[str] = None,
    parallelism: int = DEFAULT_PARALLELISM,
    stop_event: Optional[threading.Event] = None,
) -> FixResult:
    """Run teacher loop on one failure with two-phase escalation.

    Phase 1 (teaching): teacher can only use patch_prompt + patch_tool.
    Phase 2 (guardrails): if Phase 1 fails, unlock patch_tool_code and retry.
    """
    def _stopped() -> bool:
        return stop_event is not None and stop_event.is_set()

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
    fix_tier = FIX_TIER_NONE
    verify_sim = None
    attempt = 0
    error_count = 0

    total_attempts = 1 + max_retries
    phase1_attempts = max(1, (total_attempts + 1) // 2)
    phase2_attempts = total_attempts - phase1_attempts

    def _run_fix_phase(
        num_attempts: int,
        attempt_offset: int,
        phase_label: str,
        tier: str,
    ) -> bool:
        """Run one fix phase (teaching or guardrails). Returns True if fixed."""
        nonlocal attempt, error_count, fixed, fix_tier, verify_sim

        for phase_idx in range(num_attempts):
            if _stopped():
                on_status(f"[{task_id}] Stop requested, aborting fix.")
                break
            if error_count >= MAX_ERRORS_PER_TASK:
                on_status(f"[{task_id}] Too many errors ({error_count}), marking as errored.")
                break

            attempt = attempt_offset + phase_idx
            label = f"attempt {attempt + 1}/{total_attempts} [{phase_label}]"
            on_status(f"[{task_id}] Fixing {label}...")

            try:
                patches, diagnosis = session.reflect()
            except Exception as e:
                error_count += 1
                log.warning("[%s] Teacher reflect error (%d/%d): %s", task_id, error_count, MAX_ERRORS_PER_TASK, e)
                on_status(f"[{task_id}] Teacher error ({error_count}/{MAX_ERRORS_PER_TASK}): {e}")
                continue

            all_diagnoses.append(diagnosis)
            if diagnosis:
                on_status(f"[{task_id}] Diagnosis: {diagnosis[:200]}")
            if not patches:
                on_status(f"[{task_id}] Teacher returned no patches.")
                break

            on_status(f"[{task_id}] Got {len(patches)} patch(es) [{phase_label}].")
            all_patches.extend(patches)

            if on_fix_attempt:
                on_fix_attempt(task_id, attempt, list(all_patches), diagnosis, "reflecting")

            verify_sim_r, verify_passed, verify_error = _verify_patches(
                session, task_id, domain, seed, attempt, num_trials,
                student_model, parallelism, on_status, on_session,
            )
            if verify_error:
                error_count += 1
                on_status(f"[{task_id}] Verify failed ({error_count}/{MAX_ERRORS_PER_TASK})")
                continue

            verify_sim = verify_sim_r
            fixed = verify_passed

            on_status(
                f"[{task_id}] Verified {num_trials} trials: "
                f"{'FIXED [' + phase_label + ']' if fixed else 'NOT FIXED'}"
            )
            if on_fix_attempt:
                on_fix_attempt(task_id, attempt, list(all_patches), diagnosis,
                               "fixed" if fixed else "verifying")
            if fixed:
                # Determine tier from actual patch types, not just phase.
                if tier == FIX_TIER_CODE:
                    fix_tier = FIX_TIER_CODE
                elif any(p.is_tool for p in all_patches):
                    fix_tier = FIX_TIER_TOOLS
                else:
                    fix_tier = FIX_TIER_PROMPT
                return True

            if phase_idx < num_attempts - 1:
                session.report_failure(
                    baseline_reward=baseline_reward,
                    patched_reward=0.0,
                    new_sim=verify_sim,
                )
                all_patches.clear()
        return False

    # -- Phase 1: Teaching (prompt + schema only) --
    _run_fix_phase(phase1_attempts, 0, "teaching", FIX_TIER_PROMPT)

    # -- Phase 2: Guardrails (unlock tool code) --
    if not fixed and phase2_attempts > 0 and verify_sim is not None and error_count < MAX_ERRORS_PER_TASK:
        on_status(f"[{task_id}] Escalating: unlocking tool code patches...")
        session.escalate(
            baseline_reward=baseline_reward,
            patched_reward=0.0,
            new_sim=verify_sim,
        )
        all_patches.clear()
        _run_fix_phase(phase2_attempts, phase1_attempts, "guardrails", FIX_TIER_CODE)

    session_data = session._as_session_data()
    teacher_msgs = len(session_data.messages)
    teacher_tool_calls = sum(1 for m in session_data.messages if m.tool_calls)
    teacher_duration_s = _calc_duration(session_data) or 0.0

    return FixResult(
        task_id=task_id,
        baseline_reward=baseline_reward,
        patched_reward=1.0 if fixed else baseline_reward,
        diagnosis="\n---\n".join(d for d in all_diagnoses if d),
        patches=all_patches if fixed else [],
        retries=attempt,
        fixed=fixed,
        fix_tier=fix_tier,
        teacher_msgs=teacher_msgs,
        teacher_tool_calls=teacher_tool_calls,
        teacher_duration_s=round(teacher_duration_s, 1),
        error_count=error_count,
    )


def _run_condition_with_retry(
    label: str,
    on_status: Callable[[str], None],
    retries: int = VERIFY_RETRIES,
    **run_kwargs,
) -> dict[str, list[float | None]]:
    """Run a single test condition with retry. Returns task_id -> [rewards]."""
    for retry in range(retries):
        try:
            results = run_tasks(**run_kwargs)
            rewards, _ = _extract_rewards(results.simulations)
            return rewards
        except Exception as e:
            log.warning("[test/%s] Error (retry %d/%d): %s", label, retry + 1, retries, e)
            on_status(f"[test] {label} error (retry {retry + 1}/{retries}): {e}")
            if retry < retries - 1:
                time.sleep(VERIFY_BACKOFF * (retry + 1))
    on_status(f"[test] {label} failed after {retries} retries, returning empty results.")
    return {}


def _run_test_evaluation(
    domain: str,
    test_ids: list[str],
    seed: int,
    evolved_prompt: Optional[str],
    evolved_schemas: Optional[dict],
    evolved_code: Optional[dict[str, str]],
    student_model: Optional[str],
    parallelism: int,
    num_trials: int,
    on_status: Callable[[str], None],
    on_session: Optional[Callable] = None,
) -> TestResults:
    """Run baseline and only the relevant evolved conditions on the held-out test split."""
    on_status("\n" + "=" * 60)
    on_status("TEST EVALUATION (held-out test split)")
    on_status("=" * 60)

    has_prompt_patches = evolved_prompt is not None or evolved_schemas is not None
    has_code_patches = bool(evolved_code)

    common = dict(
        domain=domain, task_ids=test_ids, seed=seed,
        num_trials=num_trials,
        student_model=student_model, parallelism=parallelism,
    )
    conditions: dict[str, dict] = {
        "baseline": dict(**common, save_name="test_baseline"),
    }
    if has_prompt_patches:
        conditions["prompt_only"] = dict(
            **common, save_name="test_prompt_only",
            system_prompt=evolved_prompt, tool_schemas=evolved_schemas,
        )
    if has_code_patches:
        conditions["evolved"] = dict(
            **common, save_name="test_evolved",
            system_prompt=evolved_prompt, tool_schemas=evolved_schemas,
            tool_code=evolved_code,
        )

    on_status(f"[test] Running {len(conditions)} conditions in parallel ({len(test_ids)} tasks × {num_trials} trials each)...")
    results: dict[str, dict[str, list[float | None]]] = {}
    with ThreadPoolExecutor(max_workers=len(conditions)) as pool:
        futures = {
            pool.submit(_run_condition_with_retry, label, on_status, **kwargs): label
            for label, kwargs in conditions.items()
        }
        for future in as_completed(futures):
            label = futures[future]
            rewards = future.result()
            results[label] = rewards
            passed = sum(1 for r in rewards.values() if task_passed(r))
            on_status(f"[test] {label}: {passed}/{len(rewards)} passed (majority of {num_trials} trials)")

    return TestResults(
        baseline_rewards=results["baseline"],
        evolved_rewards=results.get("evolved", {}),
        prompt_only_rewards=results.get("prompt_only", {}),
    )


def run_loop(
    domain: str = DEFAULT_DOMAIN,
    num_tasks: int = DEFAULT_NUM_TASKS,
    max_sweeps: int = DEFAULT_MAX_SWEEPS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    seed: int = DEFAULT_SEED,
    num_trials: int = DEFAULT_NUM_TRIALS,
    task_ids: Optional[list[str]] = None,
    parallelism: int = DEFAULT_PARALLELISM,
    student_model: Optional[str] = None,
    use_split: bool = True,
    on_status: Optional[Callable[[str], None]] = None,
    on_iteration: Optional[Callable[[LoopState], None]] = None,
    on_phase: Optional[Callable[[int, str, str], None]] = None,
    on_fix_attempt: Optional[Callable[[str, int, list[Patch], str, str], None]] = None,
    on_teacher_message: Optional[Callable] = None,
    on_session: Optional[Callable] = None,
    stop_event: Optional[threading.Event] = None,
    resume_state: Optional[LoopState] = None,
) -> LoopState:
    """Run the parallel evolution loop.

    Each sweep: SWEEP (run all tasks) -> FIX (teachers in parallel) -> MERGE.
    All tasks are re-evaluated every sweep to catch regressions from merging.

    on_phase(sweep_num, phase_name, status) is called at phase transitions.
    Use PHASE_* and PHASE_RUNNING/PHASE_DONE/PHASE_SKIPPED constants.
    """
    state = LoopState()

    def status(msg: str):
        if on_status:
            on_status(msg)

    def phase(sweep_num: int, phase_name: str, phase_status: str):
        if on_phase:
            on_phase(sweep_num, phase_name, phase_status)

    def _stopped() -> bool:
        return stop_event is not None and stop_event.is_set()

    # Load train/test splits if enabled (skip when resuming — state has them).
    train_ids: Optional[list[str]] = None
    test_ids: list[str] = []
    if resume_state is None:
        if use_split and task_ids is None:
            from tau2.run import load_task_splits
            splits = load_task_splits(domain)
            if splits:
                train_ids = splits["train"]
                test_ids = splits["test"]
                task_ids = train_ids[:num_tasks] if num_tasks < len(train_ids) else train_ids
                # Cap test split so it never exceeds the number of train tasks used.
                if len(test_ids) > len(task_ids):
                    test_ids = test_ids[:len(task_ids)]
                status(f"Using canonical split: {len(task_ids)} train, {len(test_ids)} test")
                status(f"Evolving on {len(task_ids)} train task(s)")
            else:
                status(f"No canonical splits for {domain}, using all tasks")
        elif task_ids is not None:
            train_ids = task_ids

    # Pre-load domain tools and policy once.
    env = tau2_registry.get_env_constructor(domain)()
    tools = env.get_tools()
    domain_policy = env.get_policy()

    base_system_prompt = SYSTEM_PROMPT.format(
        domain_policy=domain_policy,
        agent_instruction=AGENT_INSTRUCTION,
    )
    current_system_prompt = base_system_prompt
    current_tool_schemas: dict[str, dict] = {
        t.name: deepcopy(t.openai_schema) for t in tools
    }
    current_tool_code: dict[str, str] = {}
    log.debug("System prompt: %d chars, policy: %d chars", len(current_system_prompt), len(domain_policy))

    # -- Resume from previous state if provided --------------------------------
    start_sweep = 1
    if resume_state is not None:
        start_sweep = len(resume_state.history) + 1
        state.history = list(resume_state.history)
        if resume_state.system_prompt:
            current_system_prompt = resume_state.system_prompt
        if resume_state.tool_schemas:
            current_tool_schemas = deepcopy(resume_state.tool_schemas)
        if resume_state.tool_code:
            current_tool_code = deepcopy(resume_state.tool_code)
        if resume_state.train_task_ids:
            task_ids = resume_state.train_task_ids
            train_ids = resume_state.train_task_ids
        if resume_state.test_task_ids:
            test_ids = resume_state.test_task_ids
        status(f"Resuming from sweep {start_sweep} ({len(state.history)} completed)")
        del resume_state

    stopped = False
    end_sweep = start_sweep + max_sweeps - 1
    sweep = start_sweep - 1  # default if loop body never runs

    for sweep in range(start_sweep, end_sweep + 1):
        if _stopped():
            status("\nStop requested. Finishing current work...")
            stopped = True
            break

        status(f"Sweep {sweep}/{end_sweep}")

        # ── PHASE 1: SWEEP ────────────────────────────────────────────────
        phase(sweep, PHASE_SWEEP, PHASE_RUNNING)
        label = f"tasks {task_ids}" if task_ids else f"{num_tasks} tasks"
        status(f"Sweeping {domain} ({label})...")

        def _on_task(task_id, trial, reward):
            if reward is not None:
                marker = "PASS" if reward >= 1.0 else "FAIL"
                status(f"  Task {task_id} t{trial} — reward {reward:.2f} [{marker}]")
            else:
                status(f"  Task {task_id} t{trial} — no reward")

        results = run_tasks(
            domain=domain,
            num_tasks=num_tasks,
            task_ids=task_ids,
            seed=seed,
            num_trials=num_trials,
            system_prompt=current_system_prompt,
            tool_schemas=current_tool_schemas,
            tool_code=current_tool_code or None,
            save_name=f"sweep_{sweep}",
            on_task_complete=_on_task if on_status else None,
            student_model=student_model,
            parallelism=parallelism,
        )

        save_student_sessions(
            results,
            context=f"sweep_{sweep}",
            model=student_model or "",
            on_session=on_session,
        )

        # After first sweep, lock in task IDs.
        if task_ids is None:
            task_ids = [sim.task_id for sim in results.simulations]
            status(f"Locked task set: {task_ids}")

        failures = extract_failures(results)
        sweep_rewards, num_errors = _extract_rewards(results.simulations)
        n_tasks = len(sweep_rewards)
        n_passed = sum(1 for r in sweep_rewards.values() if task_passed(r))
        if num_errors:
            status(f"  {num_errors} trial(s) errored out (no reward).")
        status(f"Sweep done. {n_passed}/{n_tasks} tasks pass (majority of {num_trials}), {len(failures)} to fix.")
        phase(sweep, PHASE_SWEEP, PHASE_DONE)

        # No failures → record and stop.
        if not failures:
            status("All tasks pass!")
            phase(sweep, PHASE_FIX, PHASE_SKIPPED)
            phase(sweep, PHASE_MERGE, PHASE_SKIPPED)
            state.history.append(SweepResult(
                sweep=sweep,
                num_evaluated=len(sweep_rewards),
                num_failures=0,
                fixes=[],
                num_fixed=0,
                sweep_rewards=sweep_rewards,
                num_errors=num_errors,
            ))
            if on_iteration:
                on_iteration(state)
            break

        # Last sweep is evaluation-only: no fix/merge, go straight to test.
        is_last_sweep = sweep == end_sweep

        # Check for stop after sweep but before expensive fix phase.
        if _stopped() or is_last_sweep:
            if _stopped():
                status("\nStop requested after sweep. Saving state...")
                stopped = True
            else:
                status("Final sweep complete (evaluation only, no fix/merge).")
            phase(sweep, PHASE_FIX, PHASE_SKIPPED)
            phase(sweep, PHASE_MERGE, PHASE_SKIPPED)
            state.history.append(SweepResult(
                sweep=sweep,
                num_evaluated=len(sweep_rewards),
                num_failures=len(failures),
                fixes=[],
                num_fixed=0,
                sweep_rewards=sweep_rewards,
                num_errors=num_errors,
            ))
            if on_iteration:
                on_iteration(state)
            break

        # ── PHASE 2: FIX ──────────────────────────────────────────────────
        phase(sweep, PHASE_FIX, PHASE_RUNNING)
        status(f"Fixing {len(failures)} failure(s) in parallel...")

        fix_results: list[FixResult] = []
        # Cap concurrent teachers so total verify sessions ≤ parallelism.
        # Each teacher's verify runs num_trials concurrent sessions.
        max_teachers = max(1, parallelism // max(num_trials, 1))
        workers = min(max_teachers, len(failures))
        status(f"  (up to {workers} teachers × {num_trials} verify trials = {workers * num_trials} concurrent sessions, cap {parallelism})")
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
                    num_trials=num_trials,
                    on_status=status,
                    on_fix_attempt=on_fix_attempt,
                    on_teacher_message=on_teacher_message,
                    on_session=on_session,
                    student_model=student_model,
                    parallelism=num_trials,
                    stop_event=stop_event,
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
                    fix_results.append(FixResult(
                        task_id=task_id,
                        baseline_reward=sweep_rewards.get(task_id, 0.0),
                        patched_reward=sweep_rewards.get(task_id, 0.0),
                        diagnosis=f"Teacher crashed: {e}",
                        patches=[],
                        retries=0,
                        fixed=False,
                        error_count=1,
                    ))

        winners = [f for f in fix_results if f.fixed]
        status(f"\n{len(winners)}/{len(fix_results)} failures fixed.")
        phase(sweep, PHASE_FIX, PHASE_DONE)

        # ── PHASE 3: MERGE ────────────────────────────────────────────────
        phase(sweep, PHASE_MERGE, PHASE_RUNNING)
        status("Merging patches...")

        current_system_prompt, current_tool_schemas, current_tool_code, merge_result = merge_fixes(
            fix_results, current_system_prompt, current_tool_schemas, current_tool_code,
            on_session=on_session,
            on_message=on_teacher_message,
        )
        n_applied = len(merge_result.merged_patches)
        status(f"  Merger applied {n_applied} patches.")

        phase(sweep, PHASE_MERGE, PHASE_DONE)

        state.system_prompt = current_system_prompt
        state.tool_schemas = current_tool_schemas
        state.tool_code = current_tool_code or None
        state.history.append(SweepResult(
            sweep=sweep,
            num_evaluated=len(sweep_rewards),
            num_failures=len(failures),
            fixes=fix_results,
            num_fixed=len(winners),
            sweep_rewards=sweep_rewards,
            num_errors=num_errors,
        ))

        if on_iteration:
            on_iteration(state)

        # Check for stop after merge completes.
        if _stopped():
            status("\nStop requested. Saving state after merge...")
            stopped = True
            break

    # -- Mark remaining sweeps as skipped ------------------------------------
    # When we break early (all pass, stop, or last-sweep eval-only), sweeps
    # after the last one entered were never reached.  Emit skipped so the
    # timeline UI shows them correctly.
    for remaining in range(sweep + 1, end_sweep + 1):
        phase(remaining, PHASE_SWEEP, PHASE_SKIPPED)
        if remaining < end_sweep:
            phase(remaining, PHASE_FIX, PHASE_SKIPPED)
            phase(remaining, PHASE_MERGE, PHASE_SKIPPED)

    # -- Store split info ----------------------------------------------------
    state.train_task_ids = train_ids or task_ids or []
    state.test_task_ids = test_ids

    # -- Test evaluation on held-out split -----------------------------------
    if test_ids and not stopped:
        phase(0, PHASE_TEST, PHASE_RUNNING)
        state.test_results = _run_test_evaluation(
            domain=domain,
            test_ids=test_ids,
            seed=seed,
            evolved_prompt=state.system_prompt,
            evolved_schemas=state.tool_schemas,
            evolved_code=state.tool_code,
            student_model=student_model,
            parallelism=parallelism,
            num_trials=num_trials,
            on_status=status,
            on_session=on_session,
        )
        phase(0, PHASE_TEST, PHASE_DONE)
        if on_iteration:
            on_iteration(state)
    elif test_ids and stopped:
        phase(0, PHASE_TEST, PHASE_SKIPPED)

    # -- Save final state ---------------------------------------------------
    state.save(PATCHES_DIR / "loop_state.json")
    if stopped:
        status(f"\nLoop stopped. {state.total_fixed}/{state.total_failures} total fixes across {len(state.history)} sweep(s).")
    else:
        status(f"\nLoop complete. {state.total_fixed}/{state.total_failures} total fixes across {len(state.history)} sweep(s).")
    return state
