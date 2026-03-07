"""Run tau2-bench evaluations and extract failures."""

from __future__ import annotations

from copy import deepcopy
from typing import Optional

from tau2.data_model.simulation import Results, RunConfig, SimulationRun
from tau2.run import run_domain

import evo.agents.evolvable  # noqa: F401  — registers EvolvableAgent
from evo.config import STUDENT_MODEL, USER_SIM_MODEL, RESULTS_DIR, NO_THINK_ARGS

LITELLM_PREFIX = "openrouter/"


def run_baseline(
    domain: str = "airline",
    num_tasks: int = 5,
    task_ids: Optional[list[str]] = None,
    seed: int = 42,
    prompt_instruction: Optional[str] = None,
    tool_schemas: Optional[dict] = None,
    save_name: Optional[str] = None,
) -> Results:
    """Run the EvolvableAgent on tau2-bench tasks and return Results."""
    llm_args: dict = deepcopy(NO_THINK_ARGS)
    if prompt_instruction is not None:
        llm_args["prompt_instruction"] = prompt_instruction
    if tool_schemas is not None:
        llm_args["tool_schemas"] = tool_schemas

    config = RunConfig(
        domain=domain,
        agent="evolvable_agent",
        llm_agent=LITELLM_PREFIX + STUDENT_MODEL,
        llm_args_agent=llm_args,
        user="user_simulator",
        llm_user=LITELLM_PREFIX + USER_SIM_MODEL,
        llm_args_user=deepcopy(NO_THINK_ARGS),
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
