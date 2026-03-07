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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import plotly.graph_objects as go
import plotly.io as pio

from evo.config import RESULTS_DIR

FIGURES_DIR = RESULTS_DIR / "figures"
DOMAINS = ["airline", "retail", "telecom"]
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

def chart_reward_progression(history: list[dict]) -> dict:
    """Grouped bar: baseline vs patched reward for each iteration."""
    if not history:
        return _empty_figure("Reward Progression", "No data yet.")

    labels = [f"Iter {h['iteration']}<br>Task {h['task_id']}" for h in history]
    baselines = [h["baseline_reward"] for h in history]
    patched = [h["patched_reward"] for h in history]

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

def chart_cumulative_fix_rate(history: list[dict]) -> dict:
    """Line chart showing running fix rate as iterations progress."""
    if not history:
        return _empty_figure("Cumulative Fix Rate", "No data yet.")

    xs = []
    ys = []
    fixed_count = 0
    for i, h in enumerate(history, 1):
        if h["fixed"]:
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
        xaxis=dict(title="Iteration", dtick=1),
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


def chart_comparison_bar_from_history(history: list[dict]) -> dict:
    """Derive baseline/evolved pass rates from loop history."""
    if not history:
        return _empty_figure("Baseline vs Evolved", "No data yet.")

    n = len(history)
    baseline_pass = sum(1 for h in history if h["baseline_reward"] >= 1.0) / n
    evolved_pass = sum(1 for h in history
                       if (h["patched_reward"] >= 1.0 if h["fixed"]
                           else h["baseline_reward"] >= 1.0)) / n

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


def chart_failure_types_from_history(history: list[dict]) -> dict:
    """Derive failure type counts from diagnoses in history.

    Scans each diagnosis string for failure type keywords.
    """
    before: dict[str, int] = {ft: 0 for ft in FAILURE_TYPES}
    after: dict[str, int] = {ft: 0 for ft in FAILURE_TYPES}

    for h in history:
        diag = h.get("diagnosis") or ""
        # Diagnosis may be a dict (structured) or a string.
        if isinstance(diag, dict):
            diag_str = diag.get("failure_type", "")
        else:
            diag_str = str(diag)
        diag_upper = diag_str.upper()

        matched = False
        for ft in FAILURE_TYPES:
            if ft in diag_upper:
                before[ft] += 1
                if not h["fixed"]:
                    after[ft] += 1
                matched = True
                break
        if not matched and h.get("baseline_reward", 1.0) < 1.0:
            before["REASONING_ERROR"] += 1
            if not h["fixed"]:
                after["REASONING_ERROR"] += 1

    return chart_failure_types(before, after)


# ---------------------------------------------------------------------------
# Chart 5: Per-task pass/fail heatmap
# ---------------------------------------------------------------------------

def chart_task_heatmap(history: list[dict]) -> dict:
    """Heatmap: rows=tasks, columns=[baseline, patched], green/red."""
    if not history:
        return _empty_figure("Task Pass/Fail", "No data yet.")

    tasks = [f"Task {h['task_id']}" for h in history]
    baseline_pass = [1 if h["baseline_reward"] >= 1.0 else 0 for h in history]
    patched_pass = [1 if h["patched_reward"] >= 1.0 else 0 for h in history]

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
        height=max(250, len(history) * 35 + 80),
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# Aggregate: all charts from loop history
# ---------------------------------------------------------------------------

def all_charts_from_history(history: list[dict]) -> dict[str, dict]:
    """Return all chart figure dicts keyed by chart ID."""
    return {
        "reward_progression": chart_reward_progression(history),
        "cumulative_fix_rate": chart_cumulative_fix_rate(history),
        "comparison_bar": chart_comparison_bar_from_history(history),
        "failure_types": chart_failure_types_from_history(history),
        "task_heatmap": chart_task_heatmap(history),
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


def _flatten_history(raw_history: list[dict]) -> list[dict]:
    """Flatten nested IterationResult/FixResult dicts into per-fix dicts."""
    rows = []
    for h in raw_history:
        if "fixes" in h:
            for fix in h["fixes"]:
                rows.append({
                    "iteration": h["iteration"],
                    "task_id": fix["task_id"],
                    "baseline_reward": fix["baseline_reward"],
                    "patched_reward": fix["patched_reward"],
                    "fixed": fix["fixed"],
                    "diagnosis": fix.get("diagnosis", ""),
                    "retries": fix.get("retries", 0),
                })
        else:
            rows.append(h)
    return rows


def _demo_history() -> list[dict]:
    """Synthetic history for preview."""
    import random
    random.seed(42)
    history = []
    for i in range(8):
        baseline_r = random.uniform(0.0, 0.6)
        fixed = random.random() < 0.6
        patched_r = 1.0 if fixed else random.uniform(0.0, baseline_r + 0.1)
        ft = random.choice(FAILURE_TYPES)
        history.append({
            "iteration": i + 1,
            "task_id": str(i),
            "baseline_reward": round(baseline_r, 2),
            "patched_reward": round(patched_r, 2),
            "fixed": fixed,
            "diagnosis": f"{ft}: the agent failed to ...",
            "patches": [],
            "retries": random.randint(0, 2),
        })
    return history


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate thesis evaluation charts")
    parser.add_argument("--demo", action="store_true", help="Use synthetic demo data")
    parser.add_argument("--export", action="store_true", help="Export PNGs (requires kaleido)")
    parser.add_argument("--json", action="store_true", help="Print Plotly JSON to stdout")
    args = parser.parse_args()

    if args.demo:
        print("Using synthetic demo data.")
        history = _demo_history()
    else:
        state_path = Path("patches/loop_state.json")
        if not state_path.exists():
            state_path = RESULTS_DIR.parent / "patches" / "loop_state.json"
        if state_path.exists():
            raw = json.loads(state_path.read_text())
            history = _flatten_history(raw.get("history", []))
        else:
            print("No loop_state.json found. Use --demo for preview.")
            return

    charts = all_charts_from_history(history)

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
