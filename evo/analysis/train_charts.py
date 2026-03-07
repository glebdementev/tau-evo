"""Charts derived from fix results (train split)."""

from __future__ import annotations

from typing import Optional

import plotly.graph_objects as go

from evo.models import FixResult

from .theme import BAR_LINE, COLORS, DARK_LAYOUT, FAILURE_TYPES, HEATMAP_SCALE, base_layout, empty_figure


# ---------------------------------------------------------------------------
# Reward progression per iteration
# ---------------------------------------------------------------------------

def chart_reward_progression(fixes: list[FixResult]) -> dict:
    """Grouped bar: baseline vs patched reward for each fix attempt."""
    if not fixes:
        return empty_figure("Reward Progression", "No data yet.")

    labels = [f"Task {f.task_id}" for f in fixes]
    baselines = [f.baseline_reward for f in fixes]
    patched = [f.patched_reward for f in fixes]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Baseline", x=labels, y=baselines,
        marker=dict(color=COLORS["baseline"], line=BAR_LINE),
        width=0.35,
    ))
    fig.add_trace(go.Bar(
        name="Patched", x=labels, y=patched,
        marker=dict(color=COLORS["patched"], line=BAR_LINE),
        width=0.35,
    ))
    fig.update_layout(**base_layout(
        yaxis=dict(title="Reward", range=[0, 1.08], dtick=0.2),
        barmode="group",
        height=360,
        bargap=0.2,
        bargroupgap=0.06,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    ))
    return fig.to_dict()


# ---------------------------------------------------------------------------
# Cumulative fix rate
# ---------------------------------------------------------------------------

def chart_cumulative_fix_rate(fixes: list[FixResult]) -> dict:
    """Line chart showing running fix rate as fixes progress."""
    if not fixes:
        return empty_figure("Cumulative Fix Rate", "No data yet.")

    xs, ys = [], []
    fixed_count = 0
    for i, f in enumerate(fixes, 1):
        if f.fixed:
            fixed_count += 1
        xs.append(i)
        ys.append(fixed_count / i * 100)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        line=dict(color=COLORS["fixed"], width=2.5),
        marker=dict(size=7, color=COLORS["fixed"], line=dict(color="white", width=1)),
        fill="tozeroy",
        fillcolor="rgba(0,158,115,0.08)",
        name="Fix Rate",
    ))
    fig.update_layout(**base_layout(
        xaxis=dict(title="Fix Attempt", dtick=1),
        yaxis=dict(title="Cumulative Fix Rate (%)", range=[0, 105], dtick=20),
        height=360,
        showlegend=False,
    ))
    return fig.to_dict()


# ---------------------------------------------------------------------------
# Baseline vs Evolved vs Frontier
# ---------------------------------------------------------------------------

def chart_comparison_bar(
    baseline_pass_rate: Optional[float] = None,
    evolved_pass_rate: Optional[float] = None,
    frontier_pass_rate: Optional[float] = None,
    domain: str = "airline",
) -> dict:
    """Three bars: baseline, evolved, frontier for one domain."""
    conditions, values, colors = [], [], []

    for label, val, color in [
        ("Baseline", baseline_pass_rate, COLORS["baseline"]),
        ("Evolved", evolved_pass_rate, COLORS["patched"]),
        ("Frontier", frontier_pass_rate, COLORS["frontier"]),
    ]:
        if val is not None:
            conditions.append(label)
            values.append(val)
            colors.append(color)

    if not conditions:
        return empty_figure("Baseline vs Evolved vs Frontier", "No data yet.")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=conditions, y=values,
        marker=dict(color=colors, line=BAR_LINE),
        text=[f"{v:.0%}" for v in values],
        textposition="outside",
        textfont=dict(size=13, color="#e5e7eb"),
        width=0.5,
    ))
    fig.update_layout(**base_layout(
        yaxis=dict(title="Pass Rate", range=[0, 1.15], dtick=0.2,
                   tickformat=".0%"),
        height=360,
        showlegend=False,
        bargap=0.3,
    ))
    return fig.to_dict()


def chart_comparison_bar_from_fixes(fixes: list[FixResult]) -> dict:
    """Derive baseline/evolved pass rates from fix results."""
    if not fixes:
        return empty_figure("Baseline vs Evolved", "No data yet.")

    n = len(fixes)
    baseline_pass = sum(1 for f in fixes if f.baseline_reward >= 1.0) / n
    evolved_pass = sum(
        1 for f in fixes
        if (f.patched_reward >= 1.0 if f.fixed else f.baseline_reward >= 1.0)
    ) / n

    return chart_comparison_bar(
        baseline_pass_rate=baseline_pass,
        evolved_pass_rate=evolved_pass,
    )


def chart_train_comparison(fixes: list[FixResult]) -> dict:
    """Three bars: Baseline / Prompt-Only / Evolved on train split."""
    if not fixes:
        return empty_figure("Train: Pass Rate by Condition", "No data yet.")

    n = len(fixes)
    baseline_pass = sum(1 for f in fixes if f.baseline_reward >= 1.0) / n
    prompt_only_pass = sum(
        1 for f in fixes
        if (f.patched_reward >= 1.0 if f.fix_tier == "prompt" else f.baseline_reward >= 1.0)
    ) / n
    evolved_pass = sum(
        1 for f in fixes
        if (f.patched_reward >= 1.0 if f.fixed else f.baseline_reward >= 1.0)
    ) / n

    conditions = ["Baseline", "Prompt-Only", "Evolved"]
    values = [baseline_pass, prompt_only_pass, evolved_pass]
    bar_colors = [COLORS["baseline"], COLORS["prompt_only"], COLORS["patched"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=conditions, y=values,
        marker=dict(color=bar_colors, line=BAR_LINE),
        text=[f"{v:.0%}" for v in values],
        textposition="outside",
        textfont=dict(size=13, color="#e5e7eb"),
        width=0.5,
    ))
    fig.update_layout(**base_layout(
        yaxis=dict(title="Pass Rate", range=[0, 1.15], dtick=0.2,
                   tickformat=".0%"),
        height=360,
        showlegend=False,
        bargap=0.3,
    ))
    return fig.to_dict()


# ---------------------------------------------------------------------------
# Failure type distribution
# ---------------------------------------------------------------------------

def chart_failure_types(
    before_counts: Optional[dict[str, int]] = None,
    after_counts: Optional[dict[str, int]] = None,
) -> dict:
    """Grouped bar: failure types before vs after."""
    if not before_counts and not after_counts:
        return empty_figure("Failure Types", "No failure type data yet.")

    before_counts = before_counts or {ft: 0 for ft in FAILURE_TYPES}
    after_counts = after_counts or {ft: 0 for ft in FAILURE_TYPES}

    short_labels = [ft.replace("_", " ").title() for ft in FAILURE_TYPES]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Before",
        x=short_labels,
        y=[before_counts.get(ft, 0) for ft in FAILURE_TYPES],
        marker=dict(color="rgba(107,123,141,0.7)", line=BAR_LINE),
        width=0.35,
    ))
    fig.add_trace(go.Bar(
        name="After",
        x=short_labels,
        y=[after_counts.get(ft, 0) for ft in FAILURE_TYPES],
        marker=dict(
            color=[COLORS[ft] for ft in FAILURE_TYPES],
            line=BAR_LINE,
        ),
        width=0.35,
    ))
    fig.update_layout(**base_layout(
        barmode="group",
        yaxis=dict(title="Count", dtick=1),
        xaxis=dict(tickangle=-20),
        height=360,
        bargap=0.25,
        bargroupgap=0.06,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    ))
    return fig.to_dict()


def chart_failure_types_from_fixes(fixes: list[FixResult]) -> dict:
    """Derive failure type counts from diagnoses in fix results."""
    before: dict[str, int] = {ft: 0 for ft in FAILURE_TYPES}
    after: dict[str, int] = {ft: 0 for ft in FAILURE_TYPES}

    for f in fixes:
        diag_upper = (f.diagnosis or "").upper()

        matched = False
        for ft in FAILURE_TYPES:
            if ft in diag_upper:
                before[ft] += 1
                if not f.fixed:
                    after[ft] += 1
                matched = True
                break
        if not matched and f.baseline_reward < 1.0:
            before["REASONING_ERROR"] += 1
            if not f.fixed:
                after["REASONING_ERROR"] += 1

    return chart_failure_types(before, after)


# ---------------------------------------------------------------------------
# Per-task pass/fail heatmap
# ---------------------------------------------------------------------------

def chart_task_heatmap(fixes: list[FixResult]) -> dict:
    """Heatmap: rows=tasks, columns=[baseline, patched], green/red."""
    if not fixes:
        return empty_figure("Task Pass/Fail", "No data yet.")

    tasks = [f"Task {f.task_id}" for f in fixes]
    baseline_pass = [1 if f.baseline_reward >= 1.0 else 0 for f in fixes]
    patched_pass = [1 if f.patched_reward >= 1.0 else 0 for f in fixes]

    z = list(zip(baseline_pass, patched_pass))
    text = [["Pass" if v == 1 else "Fail" for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=["Baseline", "Patched"],
        y=tasks,
        colorscale=HEATMAP_SCALE,
        showscale=False,
        zmin=0, zmax=1,
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=11, color="white"),
        hovertemplate="Task: %{y}<br>Stage: %{x}<br>%{text}<extra></extra>",
        xgap=3, ygap=3,
    ))
    fig.update_layout(**base_layout(
        yaxis=dict(autorange="reversed", showgrid=False, showline=False),
        xaxis=dict(showgrid=False, showline=False, side="top"),
        height=max(260, len(fixes) * 36 + 80),
    ))
    return fig.to_dict()


# ---------------------------------------------------------------------------
# Fix tier breakdown (prompt vs guardrail vs unfixed)
# ---------------------------------------------------------------------------

def chart_fix_tiers(fixes: list[FixResult]) -> dict:
    """Donut chart showing how fixes break down by escalation tier."""
    if not fixes:
        return empty_figure("Fix Tiers", "No data yet.")

    prompt_fixes = sum(1 for f in fixes if f.fix_tier == "prompt")
    code_fixes = sum(1 for f in fixes if f.fix_tier == "code")
    unfixed = sum(1 for f in fixes if not f.fixed)

    labels, values, colors = [], [], []
    for label, count, color in [
        ("Prompt / Schema", prompt_fixes, COLORS["prompt_only"]),
        ("Guardrail (code)", code_fixes, COLORS["guardrail"]),
        ("Unfixed", unfixed, COLORS["not_fixed"]),
    ]:
        if count > 0:
            labels.append(label)
            values.append(count)
            colors.append(color)

    if not values:
        return empty_figure("Fix Tiers", "No data yet.")

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        marker=dict(colors=colors, line=dict(color="rgba(24,26,32,1)", width=2.5)),
        textinfo="label+value+percent",
        texttemplate="%{label}<br>%{value} (%{percent})",
        textfont=dict(size=12),
        hole=0.45,
        pull=[0.02] * len(values),
        insidetextorientation="horizontal",
    ))
    layout = {**DARK_LAYOUT}
    layout["margin"] = dict(l=24, r=24, t=56, b=24)
    fig.update_layout(
        **layout,
        height=360,
        showlegend=False,
    )
    return fig.to_dict()
