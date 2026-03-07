"""Run tau2-bench evaluations and extract failures."""

from __future__ import annotations

from typing import Optional

from tau2.data_model.simulation import Results, RunConfig, SimulationRun
from tau2.run import run_domain

import tau_evo.agents.evolvable  # noqa: F401  — registers EvolvableAgent
from tau_evo.config import STUDENT_MODEL, USER_SIM_MODEL, RESULTS_DIR, NO_THINK_ARGS


def run_baseline(
    domain: str = "airline",
    num_tasks: int = 5,
    task_ids: Optional[list[str]] = None,
    seed: int = 42,
    prompt_patch: Optional[str] = None,
    tool_patches: Optional[dict] = None,
    save_name: Optional[str] = None,
) -> Results:
    """Run the EvolvableAgent on tau2-bench tasks and return Results."""
    llm_args: dict = {**NO_THINK_ARGS}
    if prompt_patch is not None:
        llm_args["prompt_patch"] = prompt_patch
    if tool_patches is not None:
        llm_args["tool_patches"] = tool_patches

    config = RunConfig(
        domain=domain,
        agent="evolvable_agent",
        llm_agent=STUDENT_MODEL,
        llm_args_agent=llm_args,
        user="user_simulator",
        llm_user=USER_SIM_MODEL,
        llm_args_user=NO_THINK_ARGS,
        num_trials=1,
        task_ids=task_ids,
        num_tasks=num_tasks if task_ids is None else None,
        seed=seed,
    )
    results = run_domain(config)

    if save_name:
        results.save(RESULTS_DIR / f"{save_name}.json")
    return results


def extract_failures(results: Results) -> list[SimulationRun]:
    """Return simulations where the agent did not get a perfect score."""
    return [
        sim for sim in results.simulations
        if sim.reward_info is not None and sim.reward_info.reward < 1.0
    ]
