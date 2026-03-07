"""Generate thesis charts from evolution loop state and results files.

All chart functions return Plotly figure dicts (JSON-serialisable).
Used by:
  - Web dashboard (live updates via /api/charts)
  - CLI static export (--demo or --export)

Charts:
  1. Reward progression per iteration (baseline vs patched)
  2. Cumulative fix rate over iterations
  3. Baseline vs Evolved vs Frontier (grouped bar per domain)
  4. Failure type distribution before/after
  5. Per-task pass/fail heatmap
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import plotly.graph_objects as go

from evo.config import RESULTS_DIR
from evo.models import FixResult, IterationResult, LoopState

FIGURES_DIR = RESULTS_DIR / "figures"
FAILURE_TYPES = ["TOOL_MISUSE", "POLICY_VIOLATION", "REASONING_ERROR", "COMMUNICATION_ERROR"]

# Consistent dark theme matching the web UI
DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(31,41,55,0.5)",
    font=dict(color="#d1d5db", size=12),
    margin=dict(l=50, r=30, t=45, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)

COLORS = {
    "baseline": "#6b7280",
    "patched": "#3b82f6",
    "fixed": "#22c55e",
    "not_fixed": "#ef4444",
    "frontier": "#a78bfa",
    "airline": "#60a5fa",
    "retail": "#f97316",
    "telecom": "#34d399",
    "TOOL_MISUSE": "#ef4444",
    "POLICY_VIOLATION": "#f59e0b",
    "REASONING_ERROR": "#3b82f6",
    "COMMUNICATION_ERROR": "#22c55e",
}


# ---------------------------------------------------------------------------
# Chart 1: Reward progression per iteration
# ---------------------------------------------------------------------------

def chart_reward_progression(fixes: list[FixResult]) -> dict:
    """Grouped bar: baseline vs patched reward for each fix attempt."""
    if not fixes:
        return _empty_figure("Reward Progression", "No data yet.")

    labels = [f"Task {f.task_id}" for f in fixes]
    baselines = [f.baseline_reward for f in fixes]
    patched = [f.patched_reward for f in fixes]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Baseline", x=labels, y=baselines,
        marker_color=COLORS["baseline"], width=0.35,
    ))
    fig.add_trace(go.Bar(
        name="Patched", x=labels, y=patched,
        marker_color=COLORS["patched"], width=0.35,
    ))
    fig.update_layout(
        **DARK_LAYOUT,
        title="Reward: Baseline vs Patched",
        yaxis=dict(title="Reward", range=[0, 1.05]),
        barmode="group",
        height=350,
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# Chart 2: Cumulative fix rate
# ---------------------------------------------------------------------------

def chart_cumulative_fix_rate(fixes: list[FixResult]) -> dict:
    """Line chart showing running fix rate as fixes progress."""
    if not fixes:
        return _empty_figure("Cumulative Fix Rate", "No data yet.")

    xs = []
    ys = []
    fixed_count = 0
    for i, f in enumerate(fixes, 1):
        if f.fixed:
            fixed_count += 1
        xs.append(i)
        ys.append(fixed_count / i * 100)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        line=dict(color=COLORS["fixed"], width=2),
        marker=dict(size=8),
        fill="tozeroy",
        fillcolor="rgba(34,197,94,0.1)",
    ))
    fig.update_layout(
        **DARK_LAYOUT,
        title="Cumulative Fix Rate",
        xaxis=dict(title="Fix #", dtick=1),
        yaxis=dict(title="Fix Rate (%)", range=[0, 105]),
        height=350,
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# Chart 3: Baseline vs Evolved vs Frontier
# ---------------------------------------------------------------------------

def chart_comparison_bar(
    baseline_pass_rate: Optional[float] = None,
    evolved_pass_rate: Optional[float] = None,
    frontier_pass_rate: Optional[float] = None,
    domain: str = "airline",
) -> dict:
    """Three bars: baseline, evolved, frontier for one domain."""
    conditions = []
    values = []
    colors = []

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
        return _empty_figure("Baseline vs Evolved vs Frontier", "No data yet.")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=conditions, y=values,
        marker_color=colors,
        text=[f"{v:.0%}" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        **DARK_LAYOUT,
        title=f"Pass Rate Comparison — {domain.capitalize()}",
        yaxis=dict(title="Pass Rate", range=[0, 1.15]),
        height=350,
        showlegend=False,
    )
    return fig.to_dict()


def chart_comparison_bar_from_fixes(fixes: list[FixResult]) -> dict:
    """Derive baseline/evolved pass rates from fix results."""
    if not fixes:
        return _empty_figure("Baseline vs Evolved", "No data yet.")

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


# ---------------------------------------------------------------------------
# Chart 4: Failure type distribution
# ---------------------------------------------------------------------------

def chart_failure_types(
    before_counts: Optional[dict[str, int]] = None,
    after_counts: Optional[dict[str, int]] = None,
) -> dict:
    """Stacked bar: failure types before vs after."""
    if not before_counts and not after_counts:
        return _empty_figure("Failure Types", "No failure type data yet.")

    before_counts = before_counts or {ft: 0 for ft in FAILURE_TYPES}
    after_counts = after_counts or {ft: 0 for ft in FAILURE_TYPES}

    fig = go.Figure()
    for ft in FAILURE_TYPES:
        fig.add_trace(go.Bar(
            name=ft.replace("_", " ").title(),
            x=["Before", "After"],
            y=[before_counts.get(ft, 0), after_counts.get(ft, 0)],
            marker_color=COLORS[ft],
        ))
    fig.update_layout(
        **DARK_LAYOUT,
        title="Failure Types: Before vs After",
        barmode="stack",
        yaxis=dict(title="Count"),
        height=350,
    )
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
# Chart 5: Per-task pass/fail heatmap
# ---------------------------------------------------------------------------

def chart_task_heatmap(fixes: list[FixResult]) -> dict:
    """Heatmap: rows=tasks, columns=[baseline, patched], green/red."""
    if not fixes:
        return _empty_figure("Task Pass/Fail", "No data yet.")

    tasks = [f"Task {f.task_id}" for f in fixes]
    baseline_pass = [1 if f.baseline_reward >= 1.0 else 0 for f in fixes]
    patched_pass = [1 if f.patched_reward >= 1.0 else 0 for f in fixes]

    z = [baseline_pass, patched_pass]

    fig = go.Figure(go.Heatmap(
        z=list(zip(*z)),  # transpose: rows=tasks, cols=[baseline, patched]
        x=["Baseline", "Patched"],
        y=tasks,
        colorscale=[[0, COLORS["not_fixed"]], [1, COLORS["fixed"]]],
        showscale=False,
        zmin=0, zmax=1,
        hovertemplate="Task: %{y}<br>Stage: %{x}<br>Pass: %{z}<extra></extra>",
    ))
    fig.update_layout(
        **DARK_LAYOUT,
        title="Per-Task Pass/Fail",
        yaxis=dict(autorange="reversed"),
        height=max(250, len(fixes) * 35 + 80),
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# Aggregate: all charts from fix results
# ---------------------------------------------------------------------------

def chart_eval_rewards(eval_rewards: dict[str, float]) -> dict:
    """Bar chart of per-task rewards from evaluation (used when no fixes needed)."""
    if not eval_rewards:
        return _empty_figure("Evaluation Results", "No data yet.")

    tasks = [f"Task {tid}" for tid in sorted(eval_rewards.keys())]
    rewards = [eval_rewards[tid] for tid in sorted(eval_rewards.keys())]
    colors = [COLORS["fixed"] if r >= 1.0 else COLORS["not_fixed"] for r in rewards]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=tasks, y=rewards,
        marker_color=colors,
        text=[f"{r:.2f}" for r in rewards],
        textposition="outside",
    ))
    fig.update_layout(
        **DARK_LAYOUT,
        title="Evaluation Rewards",
        yaxis=dict(title="Reward", range=[0, 1.15]),
        height=350,
        showlegend=False,
    )
    return fig.to_dict()


def chart_eval_pass_rate(history: list[IterationResult]) -> dict:
    """Pass rate across iterations (works even with 0 failures)."""
    if not history:
        return _empty_figure("Pass Rate", "No data yet.")

    iters = []
    rates = []
    for h in history:
        if h.eval_rewards:
            n = len(h.eval_rewards)
            passed = sum(1 for r in h.eval_rewards.values() if r >= 1.0)
            iters.append(f"Iter {h.iteration}")
            rates.append(passed / n * 100 if n else 0)

    if not iters:
        return _empty_figure("Pass Rate", "No evaluation data.")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=iters, y=rates,
        marker_color=COLORS["fixed"],
        text=[f"{r:.0f}%" for r in rates],
        textposition="outside",
    ))
    fig.update_layout(
        **DARK_LAYOUT,
        title="Pass Rate per Iteration",
        yaxis=dict(title="Pass Rate (%)", range=[0, 115]),
        height=350,
        showlegend=False,
    )
    return fig.to_dict()


def all_charts_from_state(state: LoopState) -> dict[str, dict]:
    """Return all chart figure dicts, using eval data when no fixes exist."""
    fixes = state.flat_fixes()

    if fixes:
        return {
            "reward_progression": chart_reward_progression(fixes),
            "cumulative_fix_rate": chart_cumulative_fix_rate(fixes),
            "comparison_bar": chart_comparison_bar_from_fixes(fixes),
            "failure_types": chart_failure_types_from_fixes(fixes),
            "task_heatmap": chart_task_heatmap(fixes),
        }

    # No fixes — show eval-based charts
    all_rewards: dict[str, float] = {}
    for h in state.history:
        all_rewards.update(h.eval_rewards)

    n = len(all_rewards)
    passed = sum(1 for r in all_rewards.values() if r >= 1.0)
    pass_rate = passed / n if n else None

    return {
        "reward_progression": chart_eval_rewards(all_rewards),
        "cumulative_fix_rate": chart_eval_pass_rate(state.history),
        "comparison_bar": chart_comparison_bar(baseline_pass_rate=pass_rate),
        "failure_types": _empty_figure("Failure Types", "No failures to analyse."),
        "task_heatmap": _empty_figure("Task Heatmap", "All tasks passed — no fix comparison."),
    }


def all_charts(fixes: list[FixResult]) -> dict[str, dict]:
    """Return all chart figure dicts keyed by chart ID (legacy, from fixes only)."""
    return {
        "reward_progression": chart_reward_progression(fixes),
        "cumulative_fix_rate": chart_cumulative_fix_rate(fixes),
        "comparison_bar": chart_comparison_bar_from_fixes(fixes),
        "failure_types": chart_failure_types_from_fixes(fixes),
        "task_heatmap": chart_task_heatmap(fixes),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_figure(title: str, message: str) -> dict:
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color="#6b7280"),
    )
    fig.update_layout(
        **DARK_LAYOUT,
        title=title,
        height=350,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# CLI: static export
# ---------------------------------------------------------------------------

def _export_charts(charts: dict[str, dict], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, fig_dict in charts.items():
        fig = go.Figure(fig_dict)
        path = out / f"{name}.png"
        fig.write_image(path, width=900, height=400, scale=2)
        print(f"  Saved {path}")


def _demo_fixes() -> list[FixResult]:
    """Synthetic fix results for preview."""
    import random
    random.seed(42)
    fixes = []
    for i in range(8):
        baseline_r = random.uniform(0.0, 0.6)
        fixed = random.random() < 0.6
        patched_r = 1.0 if fixed else random.uniform(0.0, baseline_r + 0.1)
        ft = random.choice(FAILURE_TYPES)
        fixes.append(FixResult(
            task_id=str(i),
            baseline_reward=round(baseline_r, 2),
            patched_reward=round(patched_r, 2),
            fixed=fixed,
            diagnosis=f"{ft}: the agent failed to ...",
            patches=[],
            retries=random.randint(0, 2),
        ))
    return fixes


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate thesis evaluation charts")
    parser.add_argument("--demo", action="store_true", help="Use synthetic demo data")
    parser.add_argument("--export", action="store_true", help="Export PNGs (requires kaleido)")
    parser.add_argument("--json", action="store_true", help="Print Plotly JSON to stdout")
    args = parser.parse_args()

    if args.demo:
        print("Using synthetic demo data.")
        fixes = _demo_fixes()
        charts = all_charts(fixes)
    else:
        state_path = Path("patches/loop_state.json")
        if not state_path.exists():
            state_path = RESULTS_DIR.parent / "patches" / "loop_state.json"
        if state_path.exists():
            state = LoopState.load(state_path)
            charts = all_charts_from_state(state)
        else:
            print("No loop_state.json found. Use --demo for preview.")
            return

    if args.json:
        print(json.dumps(charts, indent=2))
    elif args.export:
        _export_charts(charts, FIGURES_DIR)
    else:
        # Default: save as interactive HTML
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        for name, fig_dict in charts.items():
            fig = go.Figure(fig_dict)
            path = FIGURES_DIR / f"{name}.html"
            fig.write_html(path, include_plotlyjs="cdn")
            print(f"  Saved {path}")
    print("Done.")


if __name__ == "__main__":
    main()
