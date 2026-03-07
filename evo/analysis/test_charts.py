"""Charts for test-split evaluation results."""

from __future__ import annotations

from typing import Optional

import plotly.graph_objects as go

from evo.models import TestResults

from .theme import BAR_LINE, COLORS, HEATMAP_SCALE, base_layout, empty_figure


def chart_test_comparison(test_results: Optional[TestResults]) -> dict:
    """Four grouped bars: Baseline / Prompt-Only / Evolved / Frontier on test split."""
    if test_results is None:
        return empty_figure("Test Results", "No test evaluation yet.")

    conditions = ["Baseline", "Prompt-Only", "Evolved", "Frontier"]
    values = [
        test_results.baseline_pass_rate,
        test_results.prompt_only_pass_rate,
        test_results.evolved_pass_rate,
        test_results.frontier_pass_rate,
    ]
    bar_colors = [
        COLORS["baseline"], COLORS["prompt_only"],
        COLORS["patched"], COLORS["frontier"],
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=conditions, y=values,
        marker=dict(color=bar_colors, line=BAR_LINE),
        text=[f"{v:.0%}" for v in values],
        textposition="outside",
        textfont=dict(size=13, color="#e5e7eb"),
        width=0.55,
    ))

    gc = test_results.gap_closure
    gc_text = f"Gap closure: {gc:.0%}" if gc is not None else "Gap closure: N/A"
    fig.add_annotation(
        text=gc_text, xref="paper", yref="paper",
        x=0.98, y=0.92, showarrow=False,
        font=dict(size=12, color=COLORS["fixed"]),
        xanchor="right",
        bgcolor="rgba(0,0,0,0.3)",
        borderpad=4,
    )

    fig.update_layout(**base_layout(
        yaxis=dict(title="Pass Rate", range=[0, 1.15], dtick=0.2,
                   tickformat=".0%"),
        height=360,
        showlegend=False,
        bargap=0.25,
    ))
    return fig.to_dict()


def chart_test_heatmap(test_results: Optional[TestResults]) -> dict:
    """Heatmap: rows=test tasks, columns=[Baseline, Prompt-Only, Evolved, Frontier]."""
    if test_results is None:
        return empty_figure("Test Task Heatmap", "No test evaluation yet.")

    task_ids = sorted(test_results.baseline_rewards.keys())
    if not task_ids:
        return empty_figure("Test Task Heatmap", "No test tasks.")

    conditions = ["Baseline", "Prompt-Only", "Evolved", "Frontier"]
    reward_dicts = [
        test_results.baseline_rewards,
        test_results.prompt_only_rewards,
        test_results.evolved_rewards,
        test_results.frontier_rewards,
    ]

    z = []
    text = []
    for tid in task_ids:
        row = [1 if rd.get(tid, 0) >= 1.0 else 0 for rd in reward_dicts]
        z.append(row)
        text.append(["Pass" if v == 1 else "Fail" for v in row])

    labels = [f"Task {tid}" for tid in task_ids]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=conditions,
        y=labels,
        colorscale=HEATMAP_SCALE,
        showscale=False,
        zmin=0, zmax=1,
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=11, color="white"),
        hovertemplate="Task: %{y}<br>Condition: %{x}<br>%{text}<extra></extra>",
        xgap=3, ygap=3,
    ))
    fig.update_layout(**base_layout(
        yaxis=dict(autorange="reversed", showgrid=False, showline=False),
        xaxis=dict(showgrid=False, showline=False, side="top"),
        height=max(260, len(task_ids) * 32 + 80),
    ))
    return fig.to_dict()
