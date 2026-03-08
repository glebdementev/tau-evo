"""Aggregate all charts from loop state."""

from __future__ import annotations

from evo.models import LoopState

from .train_charts import (
    chart_error_categories,
    chart_fix_attempts,
    chart_sweep_heatmap,
    chart_sweep_outcomes,
    chart_test_heatmap,
    chart_test_outcomes,
)

# Chart IDs in display order — keep in sync with CHART_IDS in index.html.
CHART_IDS = [
    "sweep_outcomes", "fix_attempts", "sweep_heatmap", "error_categories",
    "test_outcomes", "test_heatmap",
]


def all_charts_from_state(state: LoopState) -> dict[str, dict]:
    """Return all chart figure dicts keyed by chart ID."""
    return {
        "sweep_outcomes": chart_sweep_outcomes(state.history),
        "fix_attempts": chart_fix_attempts(state.history),
        "sweep_heatmap": chart_sweep_heatmap(state.history),
        "error_categories": chart_error_categories(state.history),
        "test_outcomes": chart_test_outcomes(state.test_results),
        "test_heatmap": chart_test_heatmap(state.test_results),
    }
