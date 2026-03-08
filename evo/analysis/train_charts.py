"""Per-sweep charts for the evolution loop."""

from __future__ import annotations

from collections import defaultdict

import plotly.graph_objects as go

from evo.models import SweepResult, TestResults, FIX_TIER_PROMPT, FIX_TIER_CODE

from .theme import BAR_LINE, COLORS, base_layout, empty_figure

_MISSING = object()  # sentinel: task not evaluated in this sweep

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
    """Stacked bar per sweep: passes / fixed-prompt / fixed-guardrail / unfixed / errors."""
    if not history:
        return empty_figure("Sweep Outcomes", "No data yet.")

    sweeps: list[str] = []
    passes: list[int] = []
    fixed_prompt: list[int] = []
    fixed_guardrail: list[int] = []
    unfixed: list[int] = []
    errors: list[int] = []

    for h in history:
        sweeps.append(f"Sweep {h.sweep}")
        n_errors = h.num_errors
        n_pass = h.num_evaluated - h.num_failures - n_errors
        n_prompt = sum(1 for f in h.fixes if f.fixed and f.fix_tier == FIX_TIER_PROMPT)
        n_guard = sum(1 for f in h.fixes if f.fixed and f.fix_tier == FIX_TIER_CODE)
        n_unfixed = max(0, h.num_failures - n_prompt - n_guard)

        passes.append(max(0, n_pass))
        fixed_prompt.append(n_prompt)
        fixed_guardrail.append(n_guard)
        unfixed.append(n_unfixed)
        errors.append(n_errors)

    fig = go.Figure()
    for name, vals, color in [
        ("Passed", passes, COLORS["fixed"]),
        ("Fixed (prompt)", fixed_prompt, COLORS["prompt_only"]),
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

    totals = [p + fp + fg + u + e for p, fp, fg, u, e in zip(passes, fixed_prompt, fixed_guardrail, unfixed, errors)]
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
        for h in history:
            counts.append(sum(1 for f in h.fixes if f.fixed and f.retries == attempt))

        # Attempts 0-1 (displayed as 1-2) are prompt phase, 2+ (displayed as 3+) are guardrail
        is_guardrail = attempt >= 2
        color = COLORS["guardrail"] if is_guardrail else COLORS["prompt_only"]
        tier_label = "guardrail" if is_guardrail else "prompt"
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

# Status codes for heatmap colorscale
_STATUS_ERROR = 0
_STATUS_UNFIXED = 1
_STATUS_FIXED_GUARDRAIL = 2
_STATUS_FIXED_PROMPT = 3
_STATUS_PASS = 4

_HEATMAP_COLORSCALE = [
    [0.0, COLORS["error"]],          # 0 = error (purple)
    [0.25, COLORS["not_fixed"]],     # 1 = unfixed (red)
    [0.50, COLORS["guardrail"]],     # 2 = fixed guardrail (yellow)
    [0.75, COLORS["prompt_only"]],   # 3 = fixed prompt (orange)
    [1.0, COLORS["fixed"]],          # 4 = pass (green)
]

_STATUS_LABELS = {
    _STATUS_PASS: "Pass",
    _STATUS_FIXED_PROMPT: "Fixed (prompt)",
    _STATUS_FIXED_GUARDRAIL: "Fixed (guardrail)",
    _STATUS_UNFIXED: "Unfixed",
    _STATUS_ERROR: "Error",
}


def chart_sweep_heatmap(history: list[SweepResult]) -> dict:
    """Heatmap: rows=sweeps, columns=task IDs, colored by outcome status."""
    if not history:
        return empty_figure("Sweep × Task", "No data yet.")

    # Collect all task IDs across all sweeps
    all_tasks: set[str] = set()
    for h in history:
        all_tasks.update(h.sweep_rewards.keys())
    task_ids = sorted(all_tasks, key=lambda t: (len(t), t))

    sweep_labels = [f"Sweep {h.sweep}" for h in history]
    z: list[list[float]] = []
    text: list[list[str]] = []

    for h in history:
        fix_map = {f.task_id: f for f in h.fixes}
        row_z: list[float] = []
        row_text: list[str] = []
        for tid in task_ids:
            reward = h.sweep_rewards.get(tid, _MISSING)
            if reward is _MISSING:
                # Task not evaluated this sweep
                row_z.append(float("nan"))
                row_text.append("N/A")
            elif reward is None:
                # Task errored out
                row_z.append(_STATUS_ERROR)
                row_text.append("Error")
            elif reward >= 1.0:
                row_z.append(_STATUS_PASS)
                row_text.append("Pass")
            elif tid in fix_map and fix_map[tid].fixed:
                f = fix_map[tid]
                if f.fix_tier == FIX_TIER_PROMPT:
                    row_z.append(_STATUS_FIXED_PROMPT)
                    row_text.append("Fixed (prompt)")
                else:
                    row_z.append(_STATUS_FIXED_GUARDRAIL)
                    row_text.append("Fixed (guardrail)")
            else:
                row_z.append(_STATUS_UNFIXED)
                row_text.append("Unfixed")
        z.append(row_z)
        text.append(row_text)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=[f"Task {tid}" for tid in task_ids],
        y=sweep_labels,
        colorscale=_HEATMAP_COLORSCALE,
        showscale=False,
        zmin=0, zmax=4,
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=10, color="white"),
        hovertemplate="Sweep: %{y}<br>Task: %{x}<br>%{text}<extra></extra>",
        xgap=3, ygap=3,
    ))

    n_tasks = len(task_ids)
    n_sweeps = len(history)
    fig.update_layout(**base_layout(
        yaxis=dict(autorange="reversed", showgrid=False, showline=False),
        xaxis=dict(showgrid=False, showline=False, side="top", tickangle=-45),
        height=max(260, n_sweeps * 40 + 100),
    ))
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
        n_pass = sum(1 for r in rewards.values() if r is not None and r >= 1.0)
        n_error = sum(1 for r in rewards.values() if r is None)
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
            elif r is None:
                row_z.append(_TEST_STATUS_ERROR)
                row_text.append("Error")
            elif r >= 1.0:
                row_z.append(_TEST_STATUS_PASS)
                row_text.append("Pass")
            else:
                row_z.append(_TEST_STATUS_FAIL)
                row_text.append("Fail")
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
