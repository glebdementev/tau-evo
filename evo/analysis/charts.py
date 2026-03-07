"""Aggregate all charts from loop state — thin orchestration layer.

Re-exports individual chart functions for backward compatibility.
"""

from __future__ import annotations

from evo.models import FixResult, LoopState

from .eval_charts import chart_eval_pass_rate, chart_eval_rewards
from .test_charts import chart_test_comparison, chart_test_heatmap
from .theme import empty_figure
from .train_charts import (
    chart_comparison_bar,
    chart_comparison_bar_from_fixes,
    chart_cumulative_fix_rate,
    chart_failure_types_from_fixes,
    chart_fix_tiers,
    chart_reward_progression,
    chart_task_heatmap,
    chart_train_comparison,
)


def all_charts_from_state(state: LoopState) -> dict[str, dict]:
    """Return all chart figure dicts, using eval data when no fixes exist."""
    fixes = state.flat_fixes()
    charts: dict[str, dict] = {}

    if fixes:
        charts.update({
            "reward_progression": chart_reward_progression(fixes),
            "cumulative_fix_rate": chart_cumulative_fix_rate(fixes),
            "comparison_bar": chart_comparison_bar_from_fixes(fixes),
            "train_comparison": chart_train_comparison(fixes),
            "failure_types": chart_failure_types_from_fixes(fixes),
            "task_heatmap": chart_task_heatmap(fixes),
            "fix_tiers": chart_fix_tiers(fixes),
        })
    else:
        all_rewards: dict[str, float] = {}
        for h in state.history:
            all_rewards.update(h.eval_rewards)

        n = len(all_rewards)
        passed = sum(1 for r in all_rewards.values() if r >= 1.0)
        pass_rate = passed / n if n else None

        charts.update({
            "reward_progression": chart_eval_rewards(all_rewards),
            "cumulative_fix_rate": chart_eval_pass_rate(state.history),
            "comparison_bar": chart_comparison_bar(baseline_pass_rate=pass_rate),
            "train_comparison": empty_figure("Train: Pass Rate by Condition", "No fixes to compare."),
            "failure_types": empty_figure("Failure Types", "No failures to analyse."),
            "task_heatmap": empty_figure("Task Heatmap", "All tasks passed — no fix comparison."),
            "fix_tiers": empty_figure("Fix Tiers", "No fixes needed."),
        })

    charts["test_comparison"] = chart_test_comparison(state.test_results)
    charts["test_heatmap"] = chart_test_heatmap(state.test_results)

    return charts


def all_charts(fixes: list[FixResult]) -> dict[str, dict]:
    """Return all chart figure dicts keyed by chart ID (legacy, from fixes only)."""
    return {
        "reward_progression": chart_reward_progression(fixes),
        "cumulative_fix_rate": chart_cumulative_fix_rate(fixes),
        "comparison_bar": chart_comparison_bar_from_fixes(fixes),
        "failure_types": chart_failure_types_from_fixes(fixes),
        "task_heatmap": chart_task_heatmap(fixes),
        "fix_tiers": chart_fix_tiers(fixes),
    }
