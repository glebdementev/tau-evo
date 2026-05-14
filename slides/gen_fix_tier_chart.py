#!/usr/bin/env python3
"""Generate a raster (PNG) fix-tier stacked horizontal bar chart in HSE GSB style.

Usage:  cd slides && python gen_fix_tier_chart.py [--lang en|ru]
Output: slides/fix_tier_breakdown[_ru].png
"""
from __future__ import annotations
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from pathlib import Path

# ── HSE GSB palette ──────────────────────────────────────────────────
NAVY     = "#0F2D69"
BLUE_MED = "#234B9B"
RED      = "#E61E3C"
GRAY_MID = "#7F7F7F"
WHITE    = "#FFFFFF"
BG       = "#FFFFFF"

_preferred = ["HSE Sans", "Arial"]
_available = {f.name for f in fm.fontManager.ttflist}
FONT = next((f for f in _preferred if f in _available), "sans-serif")

plt.rcParams.update({
    "font.family": FONT,
    "axes.facecolor": BG,
    "figure.facecolor": BG,
    "savefig.facecolor": BG,
})

LABELS = {
    "en": {
        "instruction": "Instruction (70–92%)",
        "tool_schema": "Tool schema",
        "guardrail":   "Guardrail",
        "xlabel":      "Number of fixes",
        "title":       "Fix tier breakdown (all experiments)",
    },
    "ru": {
        "instruction": "Инструкция (70–92%)",
        "tool_schema": "Схема инструментов",
        "guardrail":   "Guardrail",
        "xlabel":      "Количество исправлений",
        "title":       "Распределение исправлений по уровням (все эксперименты)",
    },
}


def main(lang: str = "en") -> None:
    L = LABELS[lang]

    labels = [
        "Q30B 5t", "Q30B 10t", "Q30B 20t",
        "Q3.5F 10t", "Q3.5F 20t",
        "GLM 5t", "GLM 10t",
    ]
    instruction = [5, 5, 7, 4, 11, 3, 3]
    tool_schema = [0, 0, 2, 0,  0, 0, 0]
    guardrail   = [2, 2, 1, 1,  1, 1, 1]

    totals = [i + t + g for i, t, g in zip(instruction, tool_schema, guardrail)]

    labels = labels[::-1]
    instruction = instruction[::-1]
    tool_schema = tool_schema[::-1]
    guardrail = guardrail[::-1]
    totals = totals[::-1]

    y = np.arange(len(labels))
    bar_h = 0.55

    fig, ax = plt.subplots(figsize=(4.8, 3.2))

    bars_instr = ax.barh(y, instruction, bar_h, label=L["instruction"], color=NAVY)
    bars_tools = ax.barh(y, tool_schema, bar_h, left=instruction, label=L["tool_schema"], color=BLUE_MED)
    left_guard = [i + t for i, t in zip(instruction, tool_schema)]
    bars_guard = ax.barh(y, guardrail, bar_h, left=left_guard, label=L["guardrail"], color=RED)

    for bar, val in zip(bars_instr, instruction):
        if val >= 2:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                    str(val), ha="center", va="center", color=WHITE, fontsize=8, fontweight="bold")
    for bar, val in zip(bars_tools, tool_schema):
        if val >= 1:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                    str(val), ha="center", va="center", color=WHITE, fontsize=8, fontweight="bold")
    for bar, val in zip(bars_guard, guardrail):
        if val >= 1:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                    str(val), ha="center", va="center", color=WHITE, fontsize=8, fontweight="bold")

    for i, total in enumerate(totals):
        ax.text(total + 0.25, i, f"= {total}", ha="left", va="center",
                color=GRAY_MID, fontsize=8)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel(L["xlabel"], fontsize=10, color=NAVY)
    ax.set_title(L["title"], fontsize=11, color=NAVY,
                 fontweight="bold", loc="left", pad=8)
    ax.set_xlim(0, max(totals) + 2)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRAY_MID)
    ax.spines["bottom"].set_color(GRAY_MID)
    ax.tick_params(axis="x", colors=GRAY_MID, labelsize=8)
    ax.tick_params(axis="y", colors="black", labelsize=9, length=0)

    ax.legend(loc="lower right", fontsize=8, frameon=False)

    plt.tight_layout()
    suffix = "" if lang == "en" else f"_{lang}"
    out = Path(__file__).resolve().parent / f"fix_tier_breakdown{suffix}.png"
    fig.savefig(str(out), dpi=200, bbox_inches="tight")
    print(f"Saved → {out}")
    plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--lang", choices=["en", "ru"], default="en")
    main(p.parse_args().lang)
