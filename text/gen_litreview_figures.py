#!/usr/bin/env python3
"""Generate literature review figures for Chapter 2.

Usage:  cd text && uv run python gen_litreview_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from diagram_style import *

# ---------------------------------------------------------------------------
# Shared matplotlib style (matches diagram_style palette)
# ---------------------------------------------------------------------------

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "mathtext.fontset": "custom",
    "mathtext.rm": "Liberation Serif",
    "mathtext.it": "Liberation Serif:italic",
    "mathtext.bf": "Liberation Serif:bold",
})

_OI = {
    "blue": BLUE, "orange": ORANGE, "green": GREEN,
    "vermillion": VERMILLION, "sky": SKY, "purple": PURPLE,
    "yellow": YELLOW, "grey": GREY,
}


def _save(fig, name: str):
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    out = f"{OUTPUT_DIR}/{name}.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


# ===================================================================
# Figure 2.1 — Argument structure of the literature review
# ===================================================================

def fig_lr_01_argument_flow():
    """Six-step logical chain as a vertical flowchart."""
    g = new_graph("fig_lr_01_argument_flow", rankdir="TB")
    g.attr(label="Figure 2.1: Argument Structure of the Literature Review",
           labelloc="b", fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD,
           nodesep="0.35", ranksep="0.5")

    steps = [
        ("s1", "Tool-using LLM agents\nare unreliable at\nenterprise scale", "2.1"),
        ("s2", "Static prompting helps\nbut hits a ceiling", "2.2"),
        ("s3", "Fine-tuning works but is\nimpractical for rapid\ndomain adaptation", "2.3"),
        ("s4", "Automated prompt optimization\nis effective but untested on\ntool-calling benchmarks", "2.4"),
        ("s5", "Teacher-student distillation\nis mature at weights, growing\nat the output/prompt level", "2.5"),
        ("s6", "Nobody has combined\nteacher-driven prompt evolution\nwith agentic benchmarks", "2.6"),
    ]

    fills = [
        "#F8D7DA",  # red-ish — problem
        "#FCF3CF",  # amber — limitation
        "#FCF3CF",  # amber — limitation
        "#D6EAF8",  # blue — opportunity
        "#D6EAF8",  # blue — opportunity
        "#D5F5E3",  # green — gap / contribution
    ]

    section_color = GREY

    for i, ((nid, label, sec), fill) in enumerate(zip(steps, fills)):
        g.node(nid, label=label, shape="box", style="filled,rounded",
               fillcolor=fill, width="3.2", height="0.9",
               fontname=FONT, fontsize="10")
        # Section reference on the right
        ref_id = f"{nid}_ref"
        g.node(ref_id, label=f"\u00a7{sec}", shape="plaintext",
               fontsize="9", fontcolor=section_color, fontname=FONT)
        g.edge(nid, ref_id, style="invis")
        with g.subgraph() as s:
            s.attr(rank="same")
            s.node(nid)
            s.node(ref_id)

    # Chain edges
    for i in range(len(steps) - 1):
        style = "bold" if i < len(steps) - 2 else "bold"
        g.edge(steps[i][0], steps[i + 1][0], penwidth="1.4")

    # Arrow to gap
    g.node("gap", label="Research Gap\n(this thesis)",
           shape="box", style="filled,rounded,bold",
           fillcolor="#D5F5E3", color=GREEN, penwidth="2.0",
           fontname=FONT_BOLD, fontsize="11", width="2.4")
    g.edge("s6", "gap", penwidth="1.8", color=GREEN,
           style="bold", arrowsize="1.0")

    render(g)


# ===================================================================
# Figure 2.2 — Benchmark performance gap (human vs best model)
# ===================================================================

def fig_lr_02_benchmark_gap():
    """Grouped horizontal bar: human score vs best model score."""
    fig, ax = plt.subplots(figsize=(7.5, 3.8))

    benchmarks = [
        "GAIA",
        "SWE-bench",
        "ToolBench (OSS)",
        "API-Bank",
        r"$\tau$-bench (retail, pass$^8$)",
        "AgentBench (avg)",
    ]
    human_scores = [92, None, None, None, None, None]
    model_scores = [15, 1.96, 0, 56, 25, 34]
    # Labels for the model used
    model_labels = [
        "GPT-4 + plugins",
        "Best model (2024)",
        "OSS instruction-tuned",
        "GPT-4",
        "GPT-4o",
        "GPT-4 (best)",
    ]

    y = np.arange(len(benchmarks))
    bar_h = 0.32

    # Model scores
    bars_model = ax.barh(y + bar_h / 2, model_scores, bar_h,
                         color=_OI["blue"], edgecolor="white",
                         linewidth=0.6, label="Best model", zorder=3)

    # Human scores (only where available)
    human_y = [i for i, h in enumerate(human_scores) if h is not None]
    human_v = [h for h in human_scores if h is not None]
    bars_human = ax.barh(
        [y[i] - bar_h / 2 for i in human_y], human_v, bar_h,
        color=_OI["grey"], edgecolor="white", linewidth=0.6,
        label="Human", zorder=3,
    )

    # Value labels
    for i, (val, mlabel) in enumerate(zip(model_scores, model_labels)):
        x_pos = max(val + 1.2, 4)
        ax.text(x_pos, y[i] + bar_h / 2, f"{val}%  ({mlabel})",
                va="center", fontsize=8, color=_OI["blue"])

    for i in human_y:
        ax.text(human_scores[i] + 1.2, y[i] - bar_h / 2,
                f"{human_scores[i]}%",
                va="center", fontsize=8, color=_OI["grey"])

    # GAIA gap annotation
    ax.annotate("", xy=(15, y[0]), xytext=(92, y[0]),
                arrowprops=dict(arrowstyle="<->", color=_OI["vermillion"],
                                lw=1.5))
    ax.text(53.5, y[0] + 0.35, "77-point gap", ha="center",
            fontsize=8, color=_OI["vermillion"], fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(benchmarks, fontsize=9)
    ax.set_xlabel("Score (%)", fontsize=10)
    ax.set_xlim(0, 108)
    ax.invert_yaxis()
    ax.legend(loc="lower right", fontsize=9, framealpha=0.9)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, alpha=0.2)

    fig.suptitle("Figure 2.2: Agent Benchmark Performance Gap",
                 fontsize=12, fontweight="bold", y=1.01)

    _save(fig, "fig_lr_02_benchmark_gap")


# ===================================================================
# Figure 2.3 — Prompt sensitivity range (Sclar et al.)
# ===================================================================

def fig_lr_03_prompt_sensitivity():
    """Lollipop/range chart showing accuracy spread from formatting changes."""
    fig, ax = plt.subplots(figsize=(6.5, 3.2))

    # Data from Sclar et al. (2023) — approximate ranges per model
    models = [
        "LLaMA-2-13B",
        "Mistral-7B",
        "LLaMA-2-7B",
        "GPT-3.5",
    ]
    # (min_accuracy, max_accuracy) from meaning-preserving format changes
    ranges = [
        (11, 87),   # 76-point spread
        (18, 82),
        (8, 68),
        (42, 89),
    ]

    y = np.arange(len(models))

    for i, (lo, hi) in enumerate(ranges):
        # Range line
        ax.hlines(y[i], lo, hi, color=_OI["grey"], linewidth=2.5, zorder=2)
        # Endpoints
        ax.plot(lo, y[i], "o", color=_OI["vermillion"], markersize=8, zorder=3)
        ax.plot(hi, y[i], "o", color=_OI["green"], markersize=8, zorder=3)
        # Spread label
        spread = hi - lo
        ax.text(hi + 2, y[i], f"{spread}pp", va="center",
                fontsize=9, fontweight="bold",
                color=_OI["vermillion"] if spread > 50 else _OI["grey"])

    # Highlight the 76-point spread
    ax.annotate("76-point spread from\nformatting changes alone",
                xy=(87, 0), xytext=(72, 1.8),
                fontsize=8, color=_OI["vermillion"],
                fontweight="bold", ha="center",
                arrowprops=dict(arrowstyle="->", color=_OI["vermillion"],
                                lw=1.2))

    ax.set_yticks(y)
    ax.set_yticklabels(models, fontsize=9)
    ax.set_xlabel("Accuracy (%)", fontsize=10)
    ax.set_xlim(0, 100)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, alpha=0.2)
    ax.invert_yaxis()

    # Legend
    ax.plot([], [], "o", color=_OI["vermillion"], markersize=7, label="Worst format")
    ax.plot([], [], "o", color=_OI["green"], markersize=7, label="Best format")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)

    fig.suptitle("Figure 2.3: Prompt Format Sensitivity (Sclar et al., 2023)",
                 fontsize=11, fontweight="bold", y=1.02)

    _save(fig, "fig_lr_03_prompt_sensitivity")


# ===================================================================
# Figure 2.4 — Fine-tuning approaches comparison table
# ===================================================================

def fig_lr_04_finetuning_comparison():
    """Styled table comparing fine-tuning methods."""
    fig, ax = plt.subplots(figsize=(8.5, 3.0))
    ax.axis("off")

    columns = ["Method", "Params\nUpdated", "Data\nRequired", "Alignment\nTax", "Forgetting\nRisk", "Reversible"]
    rows = [
        ["RLHF",   "All",    "Human labels\n+ RL pipeline", "Yes",  "High",   "No"],
        ["CAI",    "All",    "Constitutional\nprinciples + RL", "Partial", "High", "No"],
        ["DPO",    "All",    "Preference\npairs",  "Yes",  "High",   "No"],
        ["LoRA",   "0.01%",  "Task-specific\nexamples", "Reduced", "Moderate", "Partially"],
        ["LIMA",   "All",    "1K curated\nexamples", "Minimal", "High", "No"],
        ["This work", "None", "Benchmark\nfeedback", "None", "None", "Yes"],
    ]

    # Colors for the last row
    cell_colors = []
    for i, row in enumerate(rows):
        if i == len(rows) - 1:  # "This work"
            cell_colors.append(["#D5F5E3"] * len(columns))
        else:
            cell_colors.append(["#F8F9FA"] * len(columns))

    header_color = "#2C3E50"

    table = ax.table(
        cellText=rows,
        colLabels=columns,
        cellLoc="center",
        loc="center",
        cellColours=cell_colors,
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.7)

    # Style header
    for j in range(len(columns)):
        cell = table[0, j]
        cell.set_facecolor(header_color)
        cell.set_text_props(color="white", fontweight="bold", fontsize=9)
        cell.set_edgecolor("white")
        cell.set_linewidth(1.5)

    # Style all cells
    for i in range(1, len(rows) + 1):
        for j in range(len(columns)):
            cell = table[i, j]
            cell.set_edgecolor("#DDDDDD")
            cell.set_linewidth(0.8)
            # Bold "This work" row
            if i == len(rows):
                cell.set_text_props(fontweight="bold")

    fig.suptitle("Figure 2.4: Fine-Tuning Approaches for Agent Improvement",
                 fontsize=11, fontweight="bold", y=0.98)

    _save(fig, "fig_lr_04_finetuning_comparison")


# ===================================================================
# Figure 2.5 — Optimization methods x evaluation domain coverage
# ===================================================================

def fig_lr_05_optimization_coverage():
    """Binary heatmap: which methods have been tested on which domains."""
    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    methods = [
        "DSPy",
        "TextGrad",
        "OPRO",
        "EvoPrompt",
        "PromptBreeder",
        "ProTeGi",
        "Reflexion",
        "ADAS",
        "Trace",
        "AgentOptimizer",
        "AvaTaR",
        "GEPA",
        "SCOPE",
        "LEAP",
    ]

    domains = [
        "QA /\nReasoning",
        "Math",
        "Coding",
        "Classifi-\ncation",
        "Interactive\nEnv",
        "Tool-Calling\nBenchmark",
    ]

    # 1 = tested, 0 = not tested
    # Last column (tool-calling benchmark) is all zeros — that's the point
    data = np.array([
        [1, 1, 0, 0, 0, 0],  # DSPy
        [1, 0, 1, 0, 0, 0],  # TextGrad
        [1, 1, 0, 0, 0, 0],  # OPRO
        [1, 0, 0, 1, 0, 0],  # EvoPrompt
        [1, 0, 0, 1, 0, 0],  # PromptBreeder
        [0, 0, 0, 1, 0, 0],  # ProTeGi
        [1, 0, 1, 0, 1, 0],  # Reflexion
        [1, 0, 0, 0, 1, 0],  # ADAS
        [1, 0, 0, 0, 0, 0],  # Trace
        [0, 0, 0, 0, 1, 0],  # AgentOptimizer
        [1, 0, 0, 0, 0, 0],  # AvaTaR
        [1, 1, 0, 0, 0, 0],  # GEPA
        [0, 0, 0, 0, 1, 0],  # SCOPE
        [0, 0, 0, 0, 1, 0],  # LEAP
    ])

    # Custom colormap: light grey for 0, blue for 1
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(["#F0F0F0", _OI["sky"]])

    ax.imshow(data, cmap=cmap, aspect="auto", vmin=0, vmax=1)

    # Cell labels
    for i in range(len(methods)):
        for j in range(len(domains)):
            if data[i, j] == 1:
                ax.text(j, i, "Y", ha="center", va="center",
                        fontsize=13, fontweight="bold", color=_OI["blue"])
            # Empty column highlight
            if j == len(domains) - 1 and data[i, j] == 0:
                ax.text(j, i, "--", ha="center", va="center",
                        fontsize=11, color="#CCCCCC")

    ax.set_xticks(range(len(domains)))
    ax.set_xticklabels(domains, fontsize=9, ha="center")
    ax.set_yticks(range(len(methods)))
    ax.set_yticklabels(methods, fontsize=9)

    ax.tick_params(axis="x", top=True, bottom=False, labeltop=True, labelbottom=False)

    # Highlight the empty column
    rect = mpatches.FancyBboxPatch(
        (len(domains) - 1.5, -0.5), 1, len(methods),
        boxstyle="round,pad=0.02",
        linewidth=2.5, edgecolor=_OI["vermillion"],
        facecolor="none", zorder=5,
    )
    ax.add_patch(rect)

    ax.annotate("No existing work\nvalidated here",
                xy=(len(domains) - 1, len(methods) - 1),
                xytext=(len(domains) - 2.3, len(methods) + 0.8),
                fontsize=9, fontweight="bold", color=_OI["vermillion"],
                ha="center",
                arrowprops=dict(arrowstyle="->", color=_OI["vermillion"],
                                lw=1.3))

    # Grid
    for i in range(len(methods) + 1):
        ax.axhline(i - 0.5, color="white", linewidth=1.5)
    for j in range(len(domains) + 1):
        ax.axvline(j - 0.5, color="white", linewidth=1.5)

    ax.set_xlim(-0.5, len(domains) - 0.5)
    ax.set_ylim(len(methods) - 0.5, -0.5)

    fig.suptitle("Figure 2.5: Prompt Optimization Methods and Evaluation Domain Coverage",
                 fontsize=11, fontweight="bold", y=0.98)

    _save(fig, "fig_lr_05_optimization_coverage")


# ===================================================================
# Figure 2.6 — Research gap positioning matrix
# ===================================================================

def fig_lr_06_gap_matrix():
    """Table showing closest works vs required properties."""
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    ax.axis("off")

    columns = [
        "Work",
        "Prompt-Level\n(no weights)",
        "Teacher-\nStudent",
        "Iterative\nEvolution",
        "Tool-Calling\nBenchmark",
        "Multi-Turn\nPolicy Tasks",
    ]

    # (work, [properties]) — checkmarks and X marks
    works = [
        ("GEPA (2025)",       ["Y", "Y*",    "Y", "N", "N"]),
        ("SCOPE (2025)",      ["Y", "N", "Y", "N", "N"]),
        ("LEAP (2024)",       ["N", "Y", "Y", "N", "N"]),
        ("Reflexion (2023)",  ["Y", "N", "N", "N", "N"]),
        ("ADAS (2024)",       ["Y", "N", "Y", "N", "N"]),
        ("This work",        ["Y", "Y", "Y", "Y", "Y"]),
    ]

    rows = [[w[0]] + w[1] for w in works]

    cell_colors = []
    for i, row in enumerate(rows):
        colors = []
        colors.append("#F8F9FA")  # work name column
        for val in row[1:]:
            if "Y" in val:
                colors.append("#D5F5E3")
            else:
                colors.append("#FADBD8")
        if i == len(rows) - 1:
            colors = ["#D5F5E3"] * len(columns)
        cell_colors.append(colors)

    header_color = "#2C3E50"

    table = ax.table(
        cellText=rows,
        colLabels=columns,
        cellLoc="center",
        loc="center",
        cellColours=cell_colors,
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.65)

    # Style header
    for j in range(len(columns)):
        cell = table[0, j]
        cell.set_facecolor(header_color)
        cell.set_text_props(color="white", fontweight="bold", fontsize=9)
        cell.set_edgecolor("white")
        cell.set_linewidth(1.5)

    # Style cells
    for i in range(1, len(rows) + 1):
        for j in range(len(columns)):
            cell = table[i, j]
            cell.set_edgecolor("#DDDDDD")
            cell.set_linewidth(0.8)
            txt = cell.get_text().get_text()
            if "N" in txt:
                cell.get_text().set_color(_OI["vermillion"])
                cell.get_text().set_fontweight("bold")
            elif "Y" in txt:
                cell.get_text().set_color(_OI["green"])
                cell.get_text().set_fontweight("bold")
            if i == len(rows):
                cell.set_text_props(fontweight="bold")

    fig.suptitle("Figure 2.6: Research Gap \u2014 Positioning of Related Work",
                 fontsize=11, fontweight="bold", y=0.99)

    # Footnote
    fig.text(0.12, 0.02, "* GEPA uses a stronger model implicitly but does not frame it as teacher-student.",
             fontsize=7.5, color=_OI["grey"], fontstyle="italic")

    _save(fig, "fig_lr_06_gap_matrix")


# ===================================================================
# Figure 2.7 — Chronological timeline of key papers by area
# ===================================================================

def fig_lr_07_timeline():
    """Timeline of key papers color-coded by research area."""
    fig, ax = plt.subplots(figsize=(10, 4.5))

    area_colors = {
        "Benchmarking":     _OI["vermillion"],
        "Prompting":        _OI["orange"],
        "Fine-tuning":      _OI["purple"],
        "Prompt Opt.":      _OI["blue"],
        "Distillation":     _OI["green"],
    }

    # (year, vertical_offset, label, area)
    # Offsets: +1/+2/+3 = above, -1/-2/-3 = below; spread to avoid overlap
    papers = [
        (2015.0,  1, "Hinton\n(KD)", "Distillation"),
        (2019.0,  2, "DistilBERT", "Distillation"),
        (2020.5, -1, "GPT-3", "Prompting"),
        (2022.0,  1, "CoT", "Prompting"),
        (2022.2, -1.5, "InstructGPT\n(RLHF)", "Fine-tuning"),
        (2022.5,  2.5, "LoRA", "Fine-tuning"),
        (2022.7, -2.8, "APE", "Prompt Opt."),
        (2023.0,  1, "ReAct", "Prompting"),
        (2023.1, -1, "Alpaca", "Distillation"),
        (2023.25, 2.5, "DPO", "Fine-tuning"),
        (2023.35, -2.5, "Reflexion", "Prompt Opt."),
        (2023.55,  1.5, "DSPy", "Prompt Opt."),
        (2023.7, -1, "AgentBench", "Benchmarking"),
        (2023.85, 2.5, "ToolBench", "Benchmarking"),
        (2023.95, -2.5, "GAIA", "Benchmarking"),
        (2023.5,  3, "LIMA", "Fine-tuning"),
        (2024.15, -1, r"$\tau$-bench", "Benchmarking"),
        (2024.3,  2, "SWE-bench", "Benchmarking"),
        (2024.45, -2.5, "TextGrad", "Prompt Opt."),
        (2024.6,  1, "ADAS", "Prompt Opt."),
        (2024.75, -1.5, "LEAP", "Distillation"),
        (2025.0,  2.5, r"$\tau^2$-bench", "Benchmarking"),
        (2025.15, -2, "GEPA", "Prompt Opt."),
        (2025.3,  1, "SCOPE", "Prompt Opt."),
    ]

    # Baseline timeline
    ax.axhline(0, color="#DDDDDD", linewidth=1.5, zorder=1)

    # Year markers
    for yr in range(2015, 2026):
        ax.axvline(yr, color="#F0F0F0", linewidth=0.8, zorder=0)
        ax.text(yr, -3.7, str(yr), ha="center", fontsize=8, color=_OI["grey"])

    # Plot papers
    for year, offset, label, area in papers:
        color = area_colors[area]
        # Stem
        ax.plot([year, year], [0, offset], color=color, linewidth=1.0,
                zorder=2, alpha=0.6)
        # Dot
        ax.plot(year, offset, "o", color=color, markersize=6, zorder=4)
        # Label
        va = "bottom" if offset > 0 else "top"
        y_off = 0.2 if offset > 0 else -0.2
        ax.text(year, offset + y_off, label, ha="center", va=va,
                fontsize=7, color=color, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                          edgecolor=color, alpha=0.85, linewidth=0.6))

    # Legend
    handles = [mpatches.Patch(color=c, label=a) for a, c in area_colors.items()]
    ax.legend(handles=handles, loc="upper left", fontsize=8,
              framealpha=0.9, ncol=5, bbox_to_anchor=(0, 1.12))

    ax.set_xlim(2014.3, 2025.8)
    ax.set_ylim(-4.0, 4.2)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)

    fig.suptitle("Figure 2.7: Chronological Development of Key Work by Research Area",
                 fontsize=11, fontweight="bold", y=1.02)

    _save(fig, "fig_lr_07_timeline")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_FIGURES = [
    fig_lr_01_argument_flow,
    fig_lr_02_benchmark_gap,
    fig_lr_03_prompt_sensitivity,
    fig_lr_04_finetuning_comparison,
    fig_lr_05_optimization_coverage,
    fig_lr_06_gap_matrix,
    fig_lr_07_timeline,
]


if __name__ == "__main__":
    import sys

    targets = sys.argv[1:] if len(sys.argv) > 1 else []

    if targets:
        name_map = {f.__name__: f for f in ALL_FIGURES}
        for t in targets:
            if t in name_map:
                print(f"Generating {t}...")
                name_map[t]()
            else:
                print(f"Unknown figure: {t}")
                print(f"Available: {', '.join(name_map)}")
    else:
        print(f"Generating {len(ALL_FIGURES)} literature review figures...")
        for fn in ALL_FIGURES:
            print(f"  {fn.__name__}...")
            fn()
        print("Done!")
