#!/usr/bin/env python3
"""Generate economic analysis visualizations for defense slide 17.

Produces two PNG figures in HSE GSB style:
  1. slides/fig_economic_cost_comparison.png  — per-fix and per-deployment cost bars
  2. slides/fig_economic_roi.png             — ROI across deployment scenarios

Data sourced from thesis Section 3.5 "Economic Effectiveness".

Usage:  cd slides && python gen_economic_analysis.py
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path

# ── HSE GSB palette ──────────────────────────────────────────────────
NAVY      = "#0F2D69"
BLUE_MED  = "#234B9B"
RED       = "#E61E3C"
GRAY_MID  = "#7F7F7F"
GRAY_LIGHT = "#D0D0D0"
WHITE     = "#FFFFFF"
BG        = "#FFFFFF"
GREEN     = "#2E7D32"
AMBER     = "#F57F17"

_preferred = ["HSE Sans", "Arial"]
_available = {f.name for f in fm.fontManager.ttflist}
FONT = next((f for f in _preferred if f in _available), "sans-serif")

plt.rcParams.update({
    "font.family": FONT,
    "axes.facecolor": BG,
    "figure.facecolor": BG,
    "savefig.facecolor": BG,
})

OUT_DIR = Path(__file__).resolve().parent


# =====================================================================
# Figure 1: Per-fix cost comparison  (log-scale bar chart)
# =====================================================================

def fig_cost_per_fix():
    """Side-by-side comparison: manual vs automated per-fix cost."""
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6), gridspec_kw={"width_ratios": [1.1, 1]})

    # ── LEFT: Per-fix cost ────────────────────────────────────────
    ax = axes[0]
    labels = ["Manual\n(human analyst)", "DPV Framework\n(automated)"]
    # Manual: $22–$86 per fix (thesis 3.5); DPV: ~$0.05 per fix
    manual_lo, manual_hi = 22, 86
    auto_val = 0.05

    x = np.array([0, 1])
    bar_w = 0.45

    # Manual — show range as a bar from lo to hi
    ax.bar(x[0], manual_hi, bar_w, color=RED, alpha=0.85, zorder=3)
    ax.bar(x[0], manual_lo, bar_w, color=RED, alpha=0.55, zorder=3)
    # DPV — single value
    ax.bar(x[1], auto_val, bar_w, color=GREEN, alpha=0.85, zorder=3)

    ax.set_yscale("log")
    ax.set_ylim(0.01, 200)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, color="black")
    ax.set_ylabel("Cost per fix (USD, log scale)", fontsize=9, color=NAVY)
    ax.set_title("Per-fix cost comparison", fontsize=11, color=NAVY,
                 fontweight="bold", loc="left", pad=8)

    # Annotations
    ax.annotate(f"${manual_lo}–${manual_hi}",
                xy=(0, manual_hi), xytext=(0.35, manual_hi * 1.3),
                fontsize=9, color=RED, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=RED, lw=0.8))
    ax.annotate(f"${auto_val:.2f}",
                xy=(1, auto_val), xytext=(1.35, auto_val * 4),
                fontsize=9, color=GREEN, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=GREEN, lw=0.8))

    # Multiplier callout
    ax.text(0.5, 3.0, "440–1,720x\ncheaper", ha="center", va="center",
            fontsize=10, fontweight="bold", color=NAVY,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#E8EAF6",
                      edgecolor=NAVY, linewidth=1.2))

    # Style
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color(GRAY_MID)
    ax.spines["bottom"].set_color(GRAY_MID)
    ax.tick_params(colors=GRAY_MID)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"${v:g}" if v >= 1 else f"${v:.2f}"))

    # ── RIGHT: Annual per-deployment cost ─────────────────────────
    ax = axes[1]
    scenarios = ["Conservative\n(0.5 FTE)", "Mid-range\n(1.5 FTE)", "High-complexity\n(3.0 FTE)"]
    manual_costs = [15_000, 67_500, 180_000]
    auto_cost = 3_102  # from thesis Table (auto-cost-summary)

    x = np.arange(len(scenarios))
    bar_w = 0.30

    bars_m = ax.bar(x - bar_w / 2, manual_costs, bar_w, color=RED, alpha=0.85,
                    label="Manual", zorder=3)
    bars_a = ax.bar(x + bar_w / 2, [auto_cost] * 3, bar_w, color=GREEN, alpha=0.85,
                    label="DPV Framework", zorder=3)

    ax.set_yscale("log")
    ax.set_ylim(1_000, 400_000)
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=8, color="black")
    ax.set_ylabel("Annual cost per deployment (USD, log)", fontsize=9, color=NAVY)
    ax.set_title("Annual per-deployment cost", fontsize=11, color=NAVY,
                 fontweight="bold", loc="left", pad=8)

    # Value labels
    for bar, val in zip(bars_m, manual_costs):
        ax.text(bar.get_x() + bar.get_width() / 2, val * 1.15,
                f"${val:,.0f}", ha="center", va="bottom",
                fontsize=7, color=RED, fontweight="bold")
    for bar in bars_a:
        ax.text(bar.get_x() + bar.get_width() / 2, auto_cost * 1.15,
                f"${auto_cost:,.0f}", ha="center", va="bottom",
                fontsize=7, color=GREEN, fontweight="bold")

    ax.legend(fontsize=8, frameon=False, loc="upper left")

    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color(GRAY_MID)
    ax.spines["bottom"].set_color(GRAY_MID)
    ax.tick_params(colors=GRAY_MID)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"${v/1000:.0f}K"))

    plt.tight_layout(w_pad=2.0)
    out = OUT_DIR / "fig_economic_cost_comparison.png"
    fig.savefig(str(out), dpi=200, bbox_inches="tight")
    print(f"Saved -> {out}")
    plt.close(fig)


# =====================================================================
# Figure 2: ROI across deployment scenarios
# =====================================================================

def fig_roi_scenarios():
    """Grouped bar chart showing manual vs automated cost + net saving."""
    fig, ax = plt.subplots(figsize=(7.0, 3.6))

    scenarios = ["Small\n(3 deployments)", "Medium\n(10 deployments)", "Large\n(30 deployments)"]
    manual  = [202_500, 675_000, 2_025_000]
    auto    = [19_306,  41_020,  103_060]
    savings = [m - a for m, a in zip(manual, auto)]
    roi_pct = [1_732, 6_240, 19_119]

    x = np.arange(len(scenarios))
    bar_w = 0.28

    bars_m = ax.bar(x - bar_w / 2, manual, bar_w, color=RED, alpha=0.85,
                    label="Manual maintenance", zorder=3)
    bars_a = ax.bar(x + bar_w / 2, auto, bar_w, color=GREEN, alpha=0.85,
                    label="DPV Framework", zorder=3)

    ax.set_yscale("log")
    ax.set_ylim(5_000, 5_000_000)
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=9, color="black")
    ax.set_ylabel("Annual cost (USD, log scale)", fontsize=10, color=NAVY)
    ax.set_title("First-year cost and ROI by deployment scale", fontsize=11, color=NAVY,
                 fontweight="bold", loc="left", pad=8)

    # Value labels + ROI annotations
    for i, (bar_m, bar_a) in enumerate(zip(bars_m, bars_a)):
        # Manual
        ax.text(bar_m.get_x() + bar_m.get_width() / 2, manual[i] * 1.20,
                f"${manual[i] / 1000:.0f}K", ha="center", va="bottom",
                fontsize=8, color=RED, fontweight="bold")
        # Auto
        ax.text(bar_a.get_x() + bar_a.get_width() / 2, auto[i] * 1.20,
                f"${auto[i] / 1000:.0f}K", ha="center", va="bottom",
                fontsize=8, color=GREEN, fontweight="bold")

    # ROI callout boxes
    for i in range(len(scenarios)):
        mid_x = x[i]
        # Position above the manual bar
        callout_y = manual[i] * 2.5
        ax.text(mid_x, callout_y,
                f"ROI: {roi_pct[i]:,}%\nSaving: ${savings[i] / 1000:.0f}K",
                ha="center", va="center", fontsize=8, fontweight="bold", color=NAVY,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#E8EAF6",
                          edgecolor=NAVY, linewidth=1.0, alpha=0.9))

    ax.legend(fontsize=9, frameon=False, loc="upper left")

    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color(GRAY_MID)
    ax.spines["bottom"].set_color(GRAY_MID)
    ax.tick_params(colors=GRAY_MID)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"${v / 1000:.0f}K" if v < 1_000_000 else f"${v / 1_000_000:.1f}M"))

    # Break-even note
    ax.text(0.98, 0.02,
            "Break-even: ~2 months (mid-range scenario)",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color=NAVY, fontstyle="italic",
            bbox=dict(boxstyle="round,pad=0.2", facecolor=WHITE,
                      edgecolor=GRAY_LIGHT))

    plt.tight_layout()
    out = OUT_DIR / "fig_economic_roi.png"
    fig.savefig(str(out), dpi=200, bbox_inches="tight")
    print(f"Saved -> {out}")
    plt.close(fig)


# =====================================================================
# Main
# =====================================================================

if __name__ == "__main__":
    fig_cost_per_fix()
    fig_roi_scenarios()
    print("Done!")
