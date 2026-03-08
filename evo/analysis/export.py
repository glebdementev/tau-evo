"""CLI: static chart export (PNG/HTML/JSON)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import plotly.graph_objects as go

from evo.config import RESULTS_DIR
from evo.models import FixResult, LoopState, SweepResult, FIX_TIER_PROMPT, FIX_TIER_CODE, FIX_TIER_NONE

from .charts import all_charts_from_state
from .train_charts import ERROR_CATEGORIES

FIGURES_DIR = RESULTS_DIR / "figures"

# Academic (print) layout overrides for PNG/SVG export
_PRINT_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(family="Arial, Helvetica, sans-serif", color="black", size=14),
    title=dict(font=dict(size=18, color="black"), x=0.5, xanchor="center"),
    margin=dict(l=80, r=40, t=80, b=70),
)

_PRINT_AXIS = dict(
    gridcolor="rgba(0,0,0,0.08)",
    linecolor="black",
    linewidth=1.5,
    zerolinecolor="rgba(0,0,0,0.12)",
    tickfont=dict(size=12, color="black"),
    title_font=dict(size=14, color="black"),
)


def _export_charts(charts: dict[str, dict], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, fig_dict in charts.items():
        fig = go.Figure(fig_dict)
        fig.update_layout(**_PRINT_LAYOUT)
        fig.update_xaxes(**_PRINT_AXIS)
        fig.update_yaxes(**_PRINT_AXIS)
        fig.update_layout(
            legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="black",
                        borderwidth=1, font=dict(color="black", size=12)),
        )
        for trace in fig.data:
            if hasattr(trace, "textfont") and trace.textfont:
                trace.textfont.color = "black"

        path = out / f"{name}.png"
        fig.write_image(path, width=900, height=500, scale=2)
        print(f"  Saved {path}")


def _demo_state() -> LoopState:
    """Synthetic loop state for preview (binary 0/1 rewards)."""
    import random
    random.seed(42)
    num_tasks = 10
    # All tasks start as failures (baseline=0); some get fixed
    fixes = []
    sweep_rewards: dict[str, float] = {}
    for i in range(num_tasks):
        passed_baseline = random.random() < 0.3
        sweep_rewards[str(i)] = 1.0 if passed_baseline else 0.0
        if not passed_baseline:
            fixed = random.random() < 0.6
            ft = random.choice(ERROR_CATEGORIES)
            tier = random.choice([FIX_TIER_PROMPT, FIX_TIER_CODE]) if fixed else FIX_TIER_NONE
            fixes.append(FixResult(
                task_id=str(i),
                baseline_reward=0.0,
                patched_reward=1.0 if fixed else 0.0,
                fixed=fixed,
                diagnosis=f"{ft}: the agent failed to ...",
                patches=[],
                retries=random.randint(0, 2),
                fix_tier=tier,
            ))

    num_failures = sum(1 for r in sweep_rewards.values() if r < 1.0)
    num_fixed = sum(1 for f in fixes if f.fixed)
    history = [SweepResult(
        sweep=1,
        num_evaluated=num_tasks,
        num_failures=num_failures,
        fixes=fixes,
        num_fixed=num_fixed,
        sweep_rewards=sweep_rewards,
    )]
    return LoopState(history=history)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate thesis evaluation charts")
    parser.add_argument("--demo", action="store_true", help="Use synthetic demo data")
    parser.add_argument("--export", action="store_true", help="Export PNGs (requires kaleido)")
    parser.add_argument("--json", action="store_true", help="Print Plotly JSON to stdout")
    args = parser.parse_args()

    if args.demo:
        print("Using synthetic demo data.")
        state = _demo_state()
        charts = all_charts_from_state(state)
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
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        for name, fig_dict in charts.items():
            fig = go.Figure(fig_dict)
            path = FIGURES_DIR / f"{name}.html"
            fig.write_html(path, include_plotlyjs="cdn")
            print(f"  Saved {path}")
    print("Done.")


if __name__ == "__main__":
    main()
