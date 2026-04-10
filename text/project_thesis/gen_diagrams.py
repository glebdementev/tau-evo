#!/usr/bin/env python3
"""Generate the project_thesis-specific diagrams.

These three figures are referenced from project_thesis/ chapters but were
never produced by the original ../gen_diagrams.py (which targets the
research_thesis):

  - fig_ds_01_five_forces.png   (ch1_3_diagnostic_study.md)
  - fig_ds_02_value_chain.png   (ch1_3_diagnostic_study.md)
  - fig_edp_cycle.png           (ch2_1_methodology_choice.md)

Output goes to ../figures/ so they sit alongside the existing figure pool
that pandoc resolves via `resource-path: [., ..]` from defaults.yaml.

Usage:
    cd text/project_thesis && uv run python gen_diagrams.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# The shared diagram_style helpers live in the sister research_thesis dir.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "research_thesis"))

import diagram_style  # noqa: E402
from diagram_style import (  # noqa: E402
    BLUE,
    C,
    FONT,
    FONT_BOLD,
    FONT_SIZE,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GREEN,
    GREY,
    ORANGE,
    PURPLE,
    SKY,
    VERMILLION,
    cluster,
    new_graph,
    process_node,
    render,
)

# Write into the shared figure pool used by both thesis variants.
diagram_style.OUTPUT_DIR = str(HERE.parent / "figures")


# ---------------------------------------------------------------------------
# Local style helpers
# ---------------------------------------------------------------------------

# Intensity colors for force / activity highlighting. Light fills with strong
# borders, matching the existing diagram style (see fig_06_patch_surfaces).
HIGH_FILL = "#F8D7DA"     # light red
HIGH_BORDER = VERMILLION
MED_FILL = "#FCE5C8"      # light orange
MED_BORDER = ORANGE
LOW_FILL = "#D5F5E3"      # light green
LOW_BORDER = GREEN
NEUTRAL_FILL = "#E8F4FD"  # light blue (matches process_node)
NEUTRAL_BORDER = BLUE


def force_node(g, name, label, *, intensity, **kw):
    """Outer / center node in the Five Forces diagram."""
    fills = {"high": HIGH_FILL, "moderate": MED_FILL, "low": LOW_FILL}
    borders = {"high": HIGH_BORDER, "moderate": MED_BORDER, "low": LOW_BORDER}
    attrs = dict(
        shape="box",
        style="filled,rounded,bold",
        fillcolor=fills[intensity],
        color=borders[intensity],
        penwidth="1.8",
        fontname=FONT_BOLD,
        fontsize=FONT_SIZE,
    )
    attrs.update(kw)
    g.node(name, label=label, **attrs)


def vc_activity_node(g, name, label, *, highlighted=False, **kw):
    """Primary value-chain activity node."""
    fill = "#FFE8D6" if highlighted else NEUTRAL_FILL
    border = VERMILLION if highlighted else NEUTRAL_BORDER
    pen = "2.2" if highlighted else "1.2"
    attrs = dict(
        shape="box",
        style="filled,rounded" + (",bold" if highlighted else ""),
        fillcolor=fill,
        color=border,
        penwidth=pen,
        fontname=FONT_BOLD if highlighted else FONT,
        fontsize=FONT_SIZE_SMALL,
        width="1.7",
        height="1.0",
    )
    attrs.update(kw)
    g.node(name, label=label, **attrs)


def vc_support_node(g, name, label, **kw):
    """Support activity (sits above the primary chain)."""
    attrs = dict(
        shape="box",
        style="filled,rounded",
        fillcolor="#E2E0F5",
        color=C["border_light"],
        fontname=FONT,
        fontsize=FONT_SIZE_SMALL,
        width="3.6",
        height="0.7",
    )
    attrs.update(kw)
    g.node(name, label=label, **attrs)


# ---------------------------------------------------------------------------
# Figure 1.3.1 — Porter's Five Forces (ds_01)
# ---------------------------------------------------------------------------

def fig_ds_01_five_forces():
    """Porter's Five Forces applied to the CX automation market.

    Layout uses neato with explicit pinned positions for the canonical
    cross/star arrangement: rivalry at center, four outer forces N/S/E/W.
    """
    g = new_graph("fig_ds_01_five_forces", rankdir="TB", engine="neato")
    g.attr(
        overlap="false",
        splines="true",
        pad="0.5",
    )

    # Pinned positions (inches). Center of the cross is (0,0).
    # Outer nodes pushed out to leave room for arrow labels.
    # x ranges roughly [-3.6, 3.6], y roughly [-2.4, 2.4].
    nodes = [
        ("entrants",   "Threat of\nNew Entrants",
         "moderate",  ( 0.0,  2.4)),
        ("substitutes", "Threat of\nSubstitutes",
         "moderate",  ( 0.0, -2.4)),
        ("suppliers",  "Bargaining Power\nof Suppliers\n(LLM providers)",
         "high",      (-3.6,  0.0)),
        ("buyers",     "Bargaining Power\nof Buyers\n(enterprise clients)",
         "high",      ( 3.6,  0.0)),
    ]

    for nid, label, intensity, (x, y) in nodes:
        force_node(
            g, nid, label,
            intensity=intensity,
            pos=f"{x},{y}!",
            width="2.3",
            height="1.0",
        )

    # Center: industry rivalry (high)
    force_node(
        g, "rivalry",
        "Industry\nRivalry",
        intensity="high",
        pos="0,0!",
        width="2.0",
        height="1.2",
        fontsize=FONT_SIZE_TITLE,
    )

    # All outer forces press inward against the center.
    arrow_kwargs = dict(
        color=C["border"],
        penwidth="1.6",
        arrowsize="0.9",
        fontsize=FONT_SIZE_SMALL,
        fontname=FONT,
    )
    g.edge("entrants",   "rivalry",
           label=" moderate ", fontcolor=ORANGE, **arrow_kwargs)
    g.edge("substitutes", "rivalry",
           label=" moderate ", fontcolor=ORANGE, **arrow_kwargs)
    g.edge("suppliers",  "rivalry",
           label=" HIGH ", fontcolor=VERMILLION, **arrow_kwargs)
    g.edge("buyers",     "rivalry",
           label=" HIGH ", fontcolor=VERMILLION, **arrow_kwargs)

    # Legend in the bottom-right corner.
    legend = cluster(g, "legend", "  Pressure Intensity  ")
    legend.attr(rank="sink")
    legend.node(
        "leg_high", label="HIGH (red)",
        shape="box", style="filled,rounded,bold",
        fillcolor=HIGH_FILL, color=HIGH_BORDER, penwidth="1.8",
        fontname=FONT_BOLD, fontsize=FONT_SIZE_SMALL,
        pos="3.6,-2.4!", width="1.6", height="0.45",
    )
    legend.node(
        "leg_med", label="MODERATE (orange)",
        shape="box", style="filled,rounded,bold",
        fillcolor=MED_FILL, color=MED_BORDER, penwidth="1.8",
        fontname=FONT_BOLD, fontsize=FONT_SIZE_SMALL,
        pos="3.6,-2.95!", width="1.6", height="0.45",
    )
    g.subgraph(legend)

    render(g)


# ---------------------------------------------------------------------------
# Figure 1.3.2 — target ai's Value Chain (ds_02)
# ---------------------------------------------------------------------------

def fig_ds_02_value_chain():
    """target ai's value chain. Activities 2 and 5 share a labor pool and
    are highlighted as the binding constraint."""
    g = new_graph("fig_ds_02_value_chain", rankdir="TB")
    g.attr(
        nodesep="0.25",
        ranksep="0.6",
    )

    # Support activities row (top)
    support = cluster(g, "support", "  Support Activities  ")
    support.attr(bgcolor="#F5F5FB")
    vc_support_node(
        support, "support_eval",
        "Evaluation infrastructure\n(τ²-bench, regression suites)",
    )
    vc_support_node(
        support, "support_routing",
        "API routing & model management\n(litellm / OpenRouter)",
    )
    g.subgraph(support)

    # Primary activities row (bottom) — six boxes left to right.
    primary = cluster(g, "primary", "  Primary Activities  ")
    primary.attr(bgcolor="#FAFAFA")
    activities = [
        ("a1", "1. Model\nselection",                False),
        ("a2", "2. Requirements\ntranslation &\nagent configuration",  True),
        ("a3", "3. Deployment\n(integration,\nrouting)",  False),
        ("a4", "4. Monitoring\n(logs, dashboards,\nalerts)",  False),
        ("a5", "5. Maintenance\n(diagnose, patch,\nregression test)",  True),
        ("a6", "6. Client\nreporting",  False),
    ]
    with primary.subgraph() as row:
        row.attr(rank="same")
        for nid, label, highlighted in activities:
            vc_activity_node(row, nid, label, highlighted=highlighted)
    # Sequential flow arrows
    for (left, _, _), (right, _, _) in zip(activities, activities[1:]):
        primary.edge(
            left, right,
            color=C["arrow"],
            penwidth="1.4",
            arrowsize="0.8",
        )
    g.subgraph(primary)

    # Pull both support boxes down to feed into the primary chain.
    # Use invisible edges to enforce vertical layering without clutter.
    for sup in ("support_eval", "support_routing"):
        for prim in ("a3", "a4"):
            g.edge(sup, prim, style="invis")

    # Footnote-style annotation BELOW the primary chain. Drawing this as a
    # plaintext node tied to a2 and a5 with invisible edges keeps it placed
    # under the chain without competing with the support cluster above.
    g.node(
        "footnote",
        label=(
            "Activities 2 and 5 share a single 25-person\n"
            "systems-analyst pool — the binding constraint\n"
            "on profitable scaling."
        ),
        shape="note",
        style="filled",
        fillcolor="#FFF9E6",
        color=VERMILLION,
        fontname=FONT_BOLD,
        fontsize=FONT_SIZE_SMALL,
        fontcolor=VERMILLION,
        width="3.4",
    )
    # Anchor the footnote below activities 2 and 5 with invisible spacers,
    # then connect with thin dotted leaders.
    g.edge("a2", "footnote", style="invis", weight="2")
    g.edge("a5", "footnote", style="invis", weight="2")
    g.edge(
        "a2", "footnote",
        style="dotted",
        color=VERMILLION,
        arrowhead="none",
        constraint="false",
        penwidth="1.2",
    )
    g.edge(
        "a5", "footnote",
        style="dotted",
        color=VERMILLION,
        arrowhead="none",
        constraint="false",
        penwidth="1.2",
    )

    render(g)


# ---------------------------------------------------------------------------
# Figure 2.1.3 — Engineering Design Process cycle (edp)
# ---------------------------------------------------------------------------

def fig_edp_cycle():
    """The seven EDP phases applied to this project. Solid arrows show the
    primary forward flow; dashed arrows show iteration paths from Test (6)
    back to Specify Requirements (3), Choose Solution (4), and Prototype (5)."""
    # LR layout with very tight ranksep so the seven phases pack horizontally
    # without huge gaps. Iteration arcs route under the chain via south ports.
    g = new_graph("fig_edp_cycle", rankdir="LR")
    g.attr(
        nodesep="0.15",
        ranksep="0.12",
        splines="spline",
    )

    # Each phase: id, headline, project artifact (rendered as a smaller
    # second line inside the same node so the layout stays compact in LR mode).
    # Headlines wrap to two lines and annotations are kept terse so seven
    # boxes fit horizontally inside the column width without ballooning.
    phases = [
        ("p1", "1. Define\nthe Problem",     "Impl. tax\nat target ai"),
        ("p2", "2. Background\nResearch",    "Lit. review\n& DS (Ch. 1)"),
        ("p3", "3. Specify\nRequirements",   "Five constraints\nfrom §1.3"),
        ("p4", "4. Choose\nSolution",        "DPV framework\n(vs. RL/FT/KD)"),
        ("p5", "5. Develop &\nPrototype",    "Evolution loop\non τ²-bench"),
        ("p6", "6. Test\nSolution",          "5 / 10 / 20-task\nexperiments"),
        ("p7", "7. Communicate\nResults",    "This thesis\n& recs"),
    ]

    # Two-line labels via HTML-like tables: bold headline, smaller annotation.
    def _esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    for nid, headline, annot in phases:
        annot_html = _esc(annot).replace("\n", "<BR/>")
        headline_html = _esc(headline).replace("\n", "<BR/>")
        label = (
            "<<TABLE BORDER=\"0\" CELLBORDER=\"0\" CELLSPACING=\"1\">"
            f"<TR><TD><FONT POINT-SIZE=\"11\"><B>{headline_html}</B></FONT></TD></TR>"
            f"<TR><TD><FONT POINT-SIZE=\"9\" COLOR=\"#6B7B8D\">{annot_html}</FONT></TD></TR>"
            "</TABLE>>"
        )
        g.node(
            nid,
            label=label,
            shape="box",
            style="filled,rounded,bold",
            fillcolor=NEUTRAL_FILL,
            color=NEUTRAL_BORDER,
            penwidth="1.6",
            margin="0.10,0.06",
        )

    # Forward (solid) flow.
    for (left, *_), (right, *_) in zip(phases, phases[1:]):
        g.edge(
            left, right,
            color=C["arrow"],
            penwidth="1.6",
            arrowsize="0.8",
        )

    # Iteration loops from Test (p6) back to earlier phases.
    # In LR mode, route via south ports so the curves arc cleanly *under*
    # the main chain rather than overlapping the forward arrows.
    iter_kwargs = dict(
        style="dashed",
        color=VERMILLION,
        penwidth="1.4",
        arrowsize="0.7",
        fontcolor=VERMILLION,
        fontname=FONT,
        fontsize=FONT_SIZE_SMALL,
        constraint="false",
        tailport="s",
        headport="s",
    )
    # Iteration arrow labels are intentionally absent: with seven boxes
    # crammed into a column-width LR layout, label glyphs steal precious
    # horizontal space. The dashed arrows are documented in the caption.
    g.edge("p6", "p5", **iter_kwargs)
    g.edge("p6", "p4", **iter_kwargs)
    g.edge("p6", "p3", **iter_kwargs)

    render(g)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_FIGURES = [
    fig_ds_01_five_forces,
    fig_ds_02_value_chain,
    fig_edp_cycle,
]


if __name__ == "__main__":
    targets = sys.argv[1:]
    name_map = {f.__name__: f for f in ALL_FIGURES}

    if targets:
        for t in targets:
            if t in name_map:
                print(f"Generating {t}...")
                name_map[t]()
            else:
                print(f"Unknown figure: {t}")
                print(f"Available: {', '.join(name_map)}")
                sys.exit(1)
    else:
        print(f"Generating {len(ALL_FIGURES)} project_thesis figures...")
        for fn in ALL_FIGURES:
            print(f"  {fn.__name__}...")
            fn()
        print("Done.")
