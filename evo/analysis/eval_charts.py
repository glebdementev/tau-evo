"""Charts for per-iteration evaluation data (before fixes exist)."""

from __future__ import annotations

import plotly.graph_objects as go

from evo.models import IterationResult

from .theme import BAR_LINE, COLORS, base_layout, empty_figure


def chart_eval_rewards(eval_rewards: dict[str, float]) -> dict:
    """Bar chart of per-task rewards from evaluation."""
    if not eval_rewards:
        return empty_figure("Evaluation Results", "No data yet.")

    tasks = [f"Task {tid}" for tid in sorted(eval_rewards.keys())]
    rewards = [eval_rewards[tid] for tid in sorted(eval_rewards.keys())]
    colors = [COLORS["fixed"] if r >= 1.0 else COLORS["not_fixed"] for r in rewards]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=tasks, y=rewards,
        marker=dict(color=colors, line=BAR_LINE),
        text=[f"{r:.2f}" for r in rewards],
        textposition="outside",
        textfont=dict(size=11, color="#e5e7eb"),
    ))
    fig.update_layout(**base_layout(
        yaxis=dict(title="Reward", range=[0, 1.15], dtick=0.2),
        height=360,
        showlegend=False,
    ))
    return fig.to_dict()


def chart_eval_pass_rate(history: list[IterationResult]) -> dict:
    """Pass rate across iterations."""
    if not history:
        return empty_figure("Pass Rate", "No data yet.")

    iters, rates = [], []
    for h in history:
        if h.eval_rewards:
            n = len(h.eval_rewards)
            passed = sum(1 for r in h.eval_rewards.values() if r >= 1.0)
            iters.append(f"Iter {h.iteration}")
            rates.append(passed / n * 100 if n else 0)

    if not iters:
        return empty_figure("Pass Rate", "No evaluation data.")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=iters, y=rates,
        marker=dict(color=COLORS["fixed"], line=BAR_LINE),
        text=[f"{r:.0f}%" for r in rates],
        textposition="outside",
        textfont=dict(size=12, color="#e5e7eb"),
    ))
    fig.update_layout(**base_layout(
        yaxis=dict(title="Pass Rate (%)", range=[0, 110], dtick=20),
        height=360,
        showlegend=False,
    ))
    return fig.to_dict()
