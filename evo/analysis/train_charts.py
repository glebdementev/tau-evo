"""Per-sweep charts for the evolution loop."""

from __future__ import annotations

from collections import defaultdict
from typing import Optional, Union

import plotly.graph_objects as go

from evo.models import SweepResult, TestResults, FIX_TIER_PROMPT, FIX_TIER_TOOLS, FIX_TIER_CODE, is_task_passed, is_task_error

from .theme import BAR_LINE, COLORS, base_layout, empty_figure

_MISSING = object()  # sentinel: task not evaluated in this sweep


def _pass_fraction_text(reward_val) -> str:
    """Return a text label like '2/3' or 'Pass' for a reward value."""
    if isinstance(reward_val, list):
        valid = [r for r in reward_val if r is not None]
        if not valid:
            return "Error"
        passes = sum(1 for r in valid if r >= 1.0)
        return f"{passes}/{len(reward_val)}"
    if reward_val is None:
        return "Error"
    return "Pass" if reward_val >= 1.0 else "Fail"

# Error categories matched against diagnosis text.
ERROR_CATEGORIES = ["TOOL_MISUSE", "POLICY_VIOLATION", "REASONING_ERROR"]


def _categorise_diagnosis(diagnosis: str) -> str:
    """Map a diagnosis string to an error category."""
    upper = (diagnosis or "").upper()
    for cat in ERROR_CATEGORIES:
        if cat in upper:
            return cat
    return "REASONING_ERROR"


# ---------------------------------------------------------------------------
# 1. Sweep outcomes — stacked bar
# ---------------------------------------------------------------------------

def chart_sweep_outcomes(history: list[SweepResult]) -> dict:
    """Stacked bar per sweep: passes / fixed-instruction / fixed-tools / fixed-guardrail / unfixed / errors."""
    if not history:
        return empty_figure("Sweep Outcomes", "No data yet.")

    sweeps: list[str] = []
    passes: list[int] = []
    fixed_instruction: list[int] = []
    fixed_tools: list[int] = []
    fixed_guardrail: list[int] = []
    unfixed: list[int] = []
    errors: list[int] = []

    for h in history:
        sweeps.append(f"Sweep {h.sweep}")
        # Count from sweep_rewards using unanimous voting
        n_tasks = len(h.sweep_rewards) if h.sweep_rewards else h.num_evaluated
        n_pass_count = sum(1 for r in h.sweep_rewards.values() if is_task_passed(r)) if h.sweep_rewards else (h.num_evaluated - h.num_failures)
        n_error_count = sum(1 for r in h.sweep_rewards.values() if is_task_error(r)) if h.sweep_rewards else h.num_errors
        n_instr = sum(1 for f in h.fixes if f.fixed and f.fix_tier == FIX_TIER_PROMPT)
        n_tools = sum(1 for f in h.fixes if f.fixed and f.fix_tier == FIX_TIER_TOOLS)
        n_guard = sum(1 for f in h.fixes if f.fixed and f.fix_tier == FIX_TIER_CODE)
        n_unfixed = max(0, n_tasks - n_pass_count - n_error_count - n_instr - n_tools - n_guard)

        passes.append(max(0, n_pass_count))
        fixed_instruction.append(n_instr)
        fixed_tools.append(n_tools)
        fixed_guardrail.append(n_guard)
        unfixed.append(n_unfixed)
        errors.append(n_error_count)

    fig = go.Figure()
    for name, vals, color in [
        ("Passed", passes, COLORS["fixed"]),
        ("Fixed (instruction)", fixed_instruction, COLORS["prompt_only"]),
        ("Fixed (tools)", fixed_tools, COLORS["tools"]),
        ("Fixed (guardrail)", fixed_guardrail, COLORS["guardrail"]),
        ("Unfixed", unfixed, COLORS["not_fixed"]),
        ("Error", errors, COLORS["error"]),
    ]:
        if not any(v > 0 for v in vals):
            continue
        fig.add_trace(go.Bar(
            name=name, x=sweeps, y=vals,
            marker=dict(color=color, line=BAR_LINE),
            text=vals,
            textposition="inside",
            textfont=dict(size=11, color="white"),
            insidetextanchor="middle",
        ))

    totals = [p + fi + ft + fg + u + e for p, fi, ft, fg, u, e in zip(passes, fixed_instruction, fixed_tools, fixed_guardrail, unfixed, errors)]
    fig.update_layout(**base_layout(
        barmode="stack",
        yaxis=dict(title="Tasks", dtick=max(1, max(totals) // 5) if totals else 1),
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    ))
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 2. Fix attempts — grouped bar showing which attempt fixed each task
# ---------------------------------------------------------------------------

def chart_fix_attempts(history: list[SweepResult]) -> dict:
    """Grouped bar per sweep: for fixed tasks, which attempt succeeded.

    Prompt fixes (attempts 1-2) and guardrail fixes (3+) get different colors.
    """
    if not history:
        return empty_figure("Fix Attempts", "No data yet.")

    # Collect all attempt numbers that appear across all sweeps
    all_attempts: set[int] = set()
    for h in history:
        for f in h.fixes:
            if f.fixed:
                all_attempts.add(f.retries)

    if not all_attempts:
        return empty_figure("Fix Attempts", "No tasks were fixed.")

    sweeps = [f"Sweep {h.sweep}" for h in history]
    sorted_attempts = sorted(all_attempts)

    fig = go.Figure()
    for attempt in sorted_attempts:
        counts = []
        tier_counts: dict[str, int] = {}
        for h in history:
            n = 0
            for f in h.fixes:
                if f.fixed and f.retries == attempt:
                    n += 1
                    tier_counts[f.fix_tier] = tier_counts.get(f.fix_tier, 0) + 1
            counts.append(n)
        dominant_tier = max(tier_counts, key=tier_counts.get) if tier_counts else FIX_TIER_PROMPT
        tier_colors = {FIX_TIER_PROMPT: COLORS["prompt_only"], FIX_TIER_TOOLS: COLORS["tools"], FIX_TIER_CODE: COLORS["guardrail"]}
        tier_labels = {FIX_TIER_PROMPT: "instruction", FIX_TIER_TOOLS: "tools", FIX_TIER_CODE: "guardrail"}
        color = tier_colors.get(dominant_tier, COLORS["prompt_only"])
        tier_label = tier_labels.get(dominant_tier, "instruction")
        display_attempt = attempt + 1  # 0-indexed → 1-indexed

        fig.add_trace(go.Bar(
            name=f"Attempt {display_attempt} ({tier_label})",
            x=sweeps, y=counts,
            marker=dict(color=color, line=BAR_LINE),
            text=counts,
            textposition="outside",
            textfont=dict(size=11, color="#e5e7eb"),
        ))

    fig.update_layout(**base_layout(
        barmode="group",
        yaxis=dict(title="Fixed Tasks", dtick=1),
        height=360,
        bargap=0.2,
        bargroupgap=0.06,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    ))
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 3. Sweep × task heatmap
# ---------------------------------------------------------------------------


def chart_sweep_heatmap(history: list[SweepResult]) -> dict:
    """Heatmap: rows=sweeps, columns=individual attempts grouped by task.

    Each task expands into N columns (one per trial). Cells are simply
    Pass (green) or Fail (red) with no text — just colored rectangles.
    """
    if not history:
        return empty_figure("Sweep × Task", "No data yet.")

    # Collect all task IDs and determine max attempts per task
    all_tasks: set[str] = set()
    for h in history:
        all_tasks.update(h.sweep_rewards.keys())
    task_ids = sorted(all_tasks, key=lambda t: (len(t), t))

    # Find the max number of attempts across all tasks/sweeps
    max_attempts = 1
    for h in history:
        for rewards in h.sweep_rewards.values():
            if isinstance(rewards, list):
                max_attempts = max(max_attempts, len(rewards))

    # Build expanded columns: each task gets max_attempts sub-columns
    # x-labels: use task name for the middle attempt, empty for others
    x_labels: list[str] = []
    x_positions: list[float] = []  # numeric positions with gaps between groups
    task_tick_positions: list[float] = []
    task_tick_labels: list[str] = []

    pos = 0.0
    for i, tid in enumerate(task_ids):
        group_start = pos
        for a in range(max_attempts):
            x_labels.append(f"Task {tid} #{a+1}")
            x_positions.append(pos)
            pos += 1.0
        group_center = group_start + (max_attempts - 1) / 2.0
        task_tick_positions.append(group_center)
        task_tick_labels.append(f"Task {tid}")
        pos += 0.5  # gap between task groups

    sweep_labels = [f"Sweep {h.sweep}" for h in history]

    # Simple 2-value colorscale: fail=red, pass=green
    _ATTEMPT_FAIL = 0
    _ATTEMPT_PASS = 1
    _ATTEMPT_ERROR = -1
    attempt_colorscale = [
        [0.0, COLORS["error"]],      # -1 = error
        [0.25, COLORS["not_fixed"]], # 0 = fail
        [0.5, COLORS["not_fixed"]],
        [0.75, COLORS["fixed"]],     # 1 = pass
        [1.0, COLORS["fixed"]],
    ]

    z: list[list[float]] = []
    hover: list[list[str]] = []

    for h in history:
        row_z: list[float] = []
        row_hover: list[str] = []
        for tid in task_ids:
            rewards = h.sweep_rewards.get(tid, _MISSING)
            for a in range(max_attempts):
                if rewards is _MISSING:
                    row_z.append(float("nan"))
                    row_hover.append("N/A")
                elif isinstance(rewards, list):
                    if a < len(rewards):
                        r = rewards[a]
                        if r is None:
                            row_z.append(_ATTEMPT_ERROR)
                            row_hover.append(f"Task {tid} attempt {a+1}: Error")
                        elif r >= 1.0:
                            row_z.append(_ATTEMPT_PASS)
                            row_hover.append(f"Task {tid} attempt {a+1}: Pass")
                        else:
                            row_z.append(_ATTEMPT_FAIL)
                            row_hover.append(f"Task {tid} attempt {a+1}: Fail")
                    else:
                        row_z.append(float("nan"))
                        row_hover.append("N/A")
                else:
                    # Single reward value — show only in first column
                    if a == 0:
                        if rewards is None:
                            row_z.append(_ATTEMPT_ERROR)
                            row_hover.append(f"Task {tid}: Error")
                        elif rewards >= 1.0:
                            row_z.append(_ATTEMPT_PASS)
                            row_hover.append(f"Task {tid}: Pass")
                        else:
                            row_z.append(_ATTEMPT_FAIL)
                            row_hover.append(f"Task {tid}: Fail")
                    else:
                        row_z.append(float("nan"))
                        row_hover.append("N/A")
        z.append(row_z)
        hover.append(row_hover)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=x_positions,
        y=sweep_labels,
        colorscale=attempt_colorscale,
        showscale=False,
        zmin=-1, zmax=1,
        hovertext=hover,
        hovertemplate="%{hovertext}<extra></extra>",
        xgap=1, ygap=3,
    ))

    n_sweeps = len(history)
    fig.update_layout(**base_layout(
        yaxis=dict(autorange="reversed", showgrid=False, showline=False),
        xaxis=dict(
            showgrid=False, showline=False, side="top", tickangle=-45,
            tickmode="array",
            tickvals=task_tick_positions,
            ticktext=task_tick_labels,
        ),
        height=max(260, n_sweeps * 40 + 100),
    ))

    # Add vertical separators between task groups
    for i in range(1, len(task_ids)):
        # Boundary is halfway through the gap between groups
        boundary = x_positions[i * max_attempts] - 0.25
        fig.add_shape(
            type="line",
            x0=boundary, x1=boundary,
            y0=-0.5, y1=n_sweeps - 0.5,
            xref="x", yref="y",
            line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"),
        )

    return fig.to_dict()


# ---------------------------------------------------------------------------
# 4. Error categories — stacked bar per sweep
# ---------------------------------------------------------------------------

def chart_error_categories(history: list[SweepResult]) -> dict:
    """Stacked bar per sweep: error counts by category."""
    if not history:
        return empty_figure("Error Categories", "No data yet.")

    sweeps: list[str] = []
    counts_by_cat: dict[str, list[int]] = {cat: [] for cat in ERROR_CATEGORIES}

    for h in history:
        if not h.fixes:
            continue
        sweeps.append(f"Sweep {h.sweep}")
        cat_counts: dict[str, int] = defaultdict(int)
        for f in h.fixes:
            cat = _categorise_diagnosis(f.diagnosis)
            cat_counts[cat] += 1
        for cat in ERROR_CATEGORIES:
            counts_by_cat[cat].append(cat_counts.get(cat, 0))

    if not sweeps:
        return empty_figure("Error Categories", "No failures to categorise.")

    cat_labels = {
        "TOOL_MISUSE": "Tool Misuse",
        "POLICY_VIOLATION": "Policy Violation",
        "REASONING_ERROR": "Reasoning Error",
    }

    fig = go.Figure()
    for cat in ERROR_CATEGORIES:
        vals = counts_by_cat[cat]
        fig.add_trace(go.Bar(
            name=cat_labels[cat], x=sweeps, y=vals,
            marker=dict(color=COLORS[cat], line=BAR_LINE),
            text=vals,
            textposition="inside",
            textfont=dict(size=11, color="white"),
            insidetextanchor="middle",
        ))

    fig.update_layout(**base_layout(
        barmode="stack",
        yaxis=dict(title="Failures", dtick=1),
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    ))
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 5. Test outcomes — stacked bar (pass / fail per condition)
# ---------------------------------------------------------------------------

_TEST_CONDITIONS = [
    ("Baseline", "baseline_rewards", COLORS["baseline"]),
    ("Prompt-Only", "prompt_only_rewards", COLORS["prompt_only"]),
    ("Evolved", "evolved_rewards", COLORS["patched"]),
]


def chart_test_outcomes(tr: TestResults | None) -> dict:
    """Stacked bar: passed vs failed vs errors for each test condition."""
    if tr is None:
        return empty_figure("Test Outcomes", "No test evaluation yet.")

    conditions: list[str] = []
    passed: list[int] = []
    failed: list[int] = []
    errors: list[int] = []

    for label, attr, _ in _TEST_CONDITIONS:
        rewards = getattr(tr, attr)
        if not rewards:
            continue
        n_pass = sum(1 for r in rewards.values() if is_task_passed(r))
        n_error = sum(1 for r in rewards.values() if is_task_error(r))
        n_fail = len(rewards) - n_pass - n_error
        conditions.append(label)
        passed.append(n_pass)
        failed.append(n_fail)
        errors.append(n_error)

    if not conditions:
        return empty_figure("Test Outcomes", "No test data.")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Passed", x=conditions, y=passed,
        marker=dict(color=COLORS["fixed"], line=BAR_LINE),
        text=passed,
        textposition="inside",
        textfont=dict(size=11, color="white"),
        insidetextanchor="middle",
    ))
    fig.add_trace(go.Bar(
        name="Failed", x=conditions, y=failed,
        marker=dict(color=COLORS["not_fixed"], line=BAR_LINE),
        text=failed,
        textposition="inside",
        textfont=dict(size=11, color="white"),
        insidetextanchor="middle",
    ))
    if any(e > 0 for e in errors):
        fig.add_trace(go.Bar(
            name="Error", x=conditions, y=errors,
            marker=dict(color=COLORS["error"], line=BAR_LINE),
            text=errors,
            textposition="inside",
            textfont=dict(size=11, color="white"),
            insidetextanchor="middle",
        ))

    total = max(p + f + e for p, f, e in zip(passed, failed, errors)) if passed else 1
    fig.update_layout(**base_layout(
        barmode="stack",
        yaxis=dict(title="Tasks", dtick=max(1, total // 5)),
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    ))
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 6. Test heatmap — rows=conditions, columns=task IDs, pass/fail
# ---------------------------------------------------------------------------

_TEST_HEATMAP_SCALE = [
    [0.0, COLORS["error"]],      # -1 = error (purple)
    [0.25, COLORS["not_fixed"]], # 0 = fail (red)
    [0.5, COLORS["not_fixed"]],  # boundary
    [0.75, COLORS["fixed"]],     # 1 = pass (green)
    [1.0, COLORS["fixed"]],      # pass
]

_TEST_STATUS_PASS = 1
_TEST_STATUS_FAIL = 0
_TEST_STATUS_ERROR = -1


def chart_test_heatmap(tr: TestResults | None) -> dict:
    """Heatmap: rows=conditions (baseline/prompt-only/evolved), columns=tasks."""
    if tr is None:
        return empty_figure("Test Heatmap", "No test evaluation yet.")

    # Collect all task IDs across conditions
    all_tasks: set[str] = set()
    rows_data: list[tuple[str, dict[str, float]]] = []
    for label, attr, _ in _TEST_CONDITIONS:
        rewards: dict[str, float] = getattr(tr, attr)
        if rewards:
            all_tasks.update(rewards.keys())
            rows_data.append((label, rewards))

    if not all_tasks:
        return empty_figure("Test Heatmap", "No test data.")

    task_ids = sorted(all_tasks, key=lambda t: (len(t), t))
    row_labels: list[str] = []
    z: list[list[float]] = []
    text: list[list[str]] = []

    for label, rewards in rows_data:
        row_labels.append(label)
        row_z: list[float] = []
        row_text: list[str] = []
        for tid in task_ids:
            r = rewards.get(tid, _MISSING)
            if r is _MISSING:
                row_z.append(float("nan"))
                row_text.append("N/A")
            elif is_task_error(r):
                row_z.append(_TEST_STATUS_ERROR)
                row_text.append("Error")
            elif is_task_passed(r):
                frac = _pass_fraction_text(r)
                row_z.append(_TEST_STATUS_PASS)
                row_text.append(f"Pass ({frac})" if isinstance(r, list) and len(r) > 1 else "Pass")
            else:
                frac = _pass_fraction_text(r)
                row_z.append(_TEST_STATUS_FAIL)
                row_text.append(f"Fail ({frac})" if isinstance(r, list) and len(r) > 1 else "Fail")
        z.append(row_z)
        text.append(row_text)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=[f"Task {tid}" for tid in task_ids],
        y=row_labels,
        colorscale=_TEST_HEATMAP_SCALE,
        showscale=False,
        zmin=-1, zmax=1,
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=10, color="white"),
        hovertemplate="Condition: %{y}<br>Task: %{x}<br>%{text}<extra></extra>",
        xgap=3, ygap=3,
    ))

    fig.update_layout(**base_layout(
        yaxis=dict(autorange="reversed", showgrid=False, showline=False),
        xaxis=dict(showgrid=False, showline=False, side="top", tickangle=-45),
        height=max(200, len(rows_data) * 40 + 100),
    ))
    return fig.to_dict()
