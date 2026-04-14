#!/usr/bin/env python3
"""Generate phased rollout roadmap diagram for defense slide 18.

Produces: slides/fig_roadmap.png

Data sourced from thesis Section 3.5 "Recommendations for target ai".

Usage:  cd slides && python gen_roadmap.py
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
from pathlib import Path

# ── HSE GSB palette ──────────────────────────────────────────────────
NAVY       = "#0F2D69"
BLUE_MED   = "#234B9B"
BLUE_LIGHT = "#D6EAF8"
RED        = "#E61E3C"
GRAY_MID   = "#7F7F7F"
GRAY_LIGHT = "#E0E0E0"
WHITE      = "#FFFFFF"
GREEN      = "#2E7D32"
GREEN_LIGHT = "#C8E6C9"
AMBER      = "#F57F17"
AMBER_LIGHT = "#FFF9C4"
TEAL       = "#00897B"
TEAL_LIGHT = "#B2DFDB"
BG         = "#FFFFFF"

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


def fig_roadmap():
    """Three-phase rollout roadmap — clean blocks, no durations."""
    fig, ax = plt.subplots(figsize=(10.0, 4.6))
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(0.0, 5.8)
    ax.axis("off")

    # Title
    ax.text(5.0, 5.55, "DPV Framework: Phased Integration Roadmap for target ai",
            ha="center", va="center", fontsize=14, fontweight="bold", color=NAVY)

    # ── Phase definitions ─────────────────────────────────────────
    phases = [
        {
            "num": "1",
            "title": "Validation",
            "subtitle": "Internal benchmarks",
            "color": BLUE_MED,
            "bg": BLUE_LIGHT,
            "x": 0.2,
            "w": 3.0,
            "human_role": "Full review of\nall patches",
            "success": "Pass rate improvement\non held-out tasks",
            "details": [
                "Run on tau2-bench airline domain",
                "Compare baseline vs evolved",
                "Validate patch quality manually",
                "Screen student model compatibility",
            ],
        },
        {
            "num": "2",
            "title": "Shadow Mode",
            "subtitle": "Production traces",
            "color": AMBER,
            "bg": AMBER_LIGHT,
            "x": 3.6,
            "w": 3.0,
            "human_role": "Review & selective\napproval",
            "success": ">80% precision on\napproved patches",
            "details": [
                "Analyze real customer failures",
                "Propose patches (not deployed)",
                "Human approves/rejects each",
                "Build regression test suite",
            ],
        },
        {
            "num": "3",
            "title": "Automated",
            "subtitle": "Closed-loop operation",
            "color": GREEN,
            "bg": GREEN_LIGHT,
            "x": 7.0,
            "w": 3.0,
            "human_role": "Exception\nhandling only",
            "success": "Net-positive pass rate\n(rolling 30-day window)",
            "details": [
                "Auto-deploy passing patches",
                "Regression guard: rollback if",
                "  pass rate drops >2pp",
                "Patch consolidation every 3-5 sweeps",
            ],
        },
    ]

    # ── Draw phases ───────────────────────────────────────────────
    phase_y = 3.65
    phase_h = 1.5

    for p in phases:
        x, w = p["x"], p["w"]
        color, bg = p["color"], p["bg"]

        # Phase box
        rect = mpatches.FancyBboxPatch(
            (x, phase_y - phase_h / 2), w, phase_h,
            boxstyle="round,pad=0.08",
            facecolor=bg, edgecolor=color, linewidth=2.0
        )
        ax.add_patch(rect)

        # Phase number badge
        badge = mpatches.FancyBboxPatch(
            (x + 0.08, phase_y + phase_h / 2 - 0.35), 0.30, 0.30,
            boxstyle="round,pad=0.04",
            facecolor=color, edgecolor=color
        )
        ax.add_patch(badge)
        ax.text(x + 0.23, phase_y + phase_h / 2 - 0.20, p["num"],
                ha="center", va="center", fontsize=11, fontweight="bold", color=WHITE)

        # Title + subtitle
        ax.text(x + 0.48, phase_y + phase_h / 2 - 0.14, p["title"],
                ha="left", va="center", fontsize=11, fontweight="bold", color=color)
        ax.text(x + 0.48, phase_y + phase_h / 2 - 0.38, p["subtitle"],
                ha="left", va="center", fontsize=8, color=GRAY_MID)

        # Details (bullet points)
        for j, detail in enumerate(p["details"]):
            bullet = "\u2022 " if not detail.startswith(" ") else "  "
            ax.text(x + 0.15, phase_y - 0.05 - j * 0.22, bullet + detail.strip(),
                    ha="left", va="center", fontsize=7.5, color="#333333")

    # ── Arrows between phases ─────────────────────────────────────
    arrow_props = dict(arrowstyle="-|>", color=NAVY, lw=2.0, mutation_scale=15)
    for i in range(len(phases) - 1):
        x_from = phases[i]["x"] + phases[i]["w"] + 0.03
        x_to = phases[i + 1]["x"] - 0.03
        ax.annotate("", xy=(x_to, phase_y), xytext=(x_from, phase_y),
                     arrowprops=arrow_props)

    # ── Bottom info row: Human Role + Success Criterion ───────────
    row_y_human = 1.25
    row_y_success = 0.55

    # Row labels
    ax.text(-0.3, row_y_human, "Human\nrole:", ha="right", va="center",
            fontsize=8, fontweight="bold", color=NAVY)
    ax.text(-0.3, row_y_success, "Success\ncriterion:", ha="right", va="center",
            fontsize=8, fontweight="bold", color=NAVY)

    for p in phases:
        cx = p["x"] + p["w"] / 2

        # Human role
        ax.text(cx, row_y_human, p["human_role"],
                ha="center", va="center", fontsize=8, color=p["color"],
                bbox=dict(boxstyle="round,pad=0.2", facecolor=p["bg"],
                          edgecolor=p["color"], linewidth=0.8))

        # Success criterion
        ax.text(cx, row_y_success, p["success"],
                ha="center", va="center", fontsize=7.5, color="#333333",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#F5F5F5",
                          edgecolor=GRAY_LIGHT, linewidth=0.8))

    # ── Automation gradient arrow at very bottom ──────────────────
    grad_y = 0.12
    ax.annotate("", xy=(9.8, grad_y), xytext=(0.4, grad_y),
                arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.5,
                                mutation_scale=12))
    ax.text(0.4, grad_y - 0.10, "More human oversight", ha="left", va="top",
            fontsize=7, color=GRAY_MID, fontstyle="italic")
    ax.text(9.8, grad_y - 0.10, "More automation", ha="right", va="top",
            fontsize=7, color=GRAY_MID, fontstyle="italic")

    plt.subplots_adjust(left=0.05, right=0.98, top=0.95, bottom=0.02)
    out = OUT_DIR / "fig_roadmap.png"
    fig.savefig(str(out), dpi=200, bbox_inches="tight", pad_inches=0.15)
    print(f"Saved -> {out}")
    plt.close(fig)


if __name__ == "__main__":
    fig_roadmap()
    print("Done!")
