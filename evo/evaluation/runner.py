"""Run tau2-bench evaluations and extract failures."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Callable, Optional

from tau2.data_model.simulation import Results, RunConfig, SimulationRun
from tau2.run import run_domain

import evo.agents.evolvable  # noqa: F401  — registers EvolvableAgent
from evo.config import STUDENT_MODEL, RESULTS_DIR, NO_THINK_ARGS, DEFAULT_PARALLELISM

log = logging.getLogger(__name__)

LITELLM_PREFIX = "openrouter/"


def run_baseline(
    domain: str = "airline",
    num_tasks: int = 5,
    task_ids: Optional[list[str]] = None,
    seed: int = 42,
    prompt_instruction: Optional[str] = None,
    tool_schemas: Optional[dict] = None,
    system_prompt: Optional[str] = None,
    save_name: Optional[str] = None,
    on_task_complete: Optional[Callable[[str, int, Optional[float]], None]] = None,
    student_model: Optional[str] = None,
    parallelism: int = DEFAULT_PARALLELISM,
) -> Results:
    """Run the EvolvableAgent on tau2-bench tasks and return Results."""
    model = student_model or STUDENT_MODEL
    llm_args: dict = dict(NO_THINK_ARGS)
    if system_prompt is not None:
        llm_args["system_prompt"] = system_prompt
    elif prompt_instruction is not None:
        llm_args["prompt_instruction"] = prompt_instruction
    if tool_schemas is not None:
        llm_args["tool_schemas"] = tool_schemas

    config = RunConfig(
        domain=domain,
        agent="evolvable_agent",
        llm_agent=LITELLM_PREFIX + model,
        llm_args_agent=llm_args,
        user="user_simulator",
        llm_user=LITELLM_PREFIX + model,
        llm_args_user=dict(NO_THINK_ARGS),
        num_trials=1,
        task_ids=task_ids,
        num_tasks=num_tasks if task_ids is None else None,
        seed=seed,
        max_concurrency=parallelism,
    )
    results = run_domain(config, on_task_complete=on_task_complete)

    if save_name:
        results.save(RESULTS_DIR / f"{save_name}.json")
    return results


def extract_failures(results: Results) -> list[SimulationRun]:
    """Return simulations where the agent did not get a perfect score."""
    return [
        sim for sim in results.simulations
        if sim.reward_info is not None and sim.reward_info.reward < 1.0
    ]
