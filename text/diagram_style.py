"""Shared style for thesis diagrams — Okabe-Ito palette, academic-clean look."""

from __future__ import annotations

import graphviz

# ---------------------------------------------------------------------------
# Okabe-Ito colorblind-friendly palette (matches evo/analysis/theme.py)
# ---------------------------------------------------------------------------
BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
VERMILLION = "#D55E00"
SKY = "#56B4E9"
PURPLE = "#CC79A7"
YELLOW = "#F0E442"
GREY = "#6B7B8D"

# Semantic aliases
C = {
    "baseline": GREY,
    "evolved": BLUE,
    "frontier": PURPLE,
    "fixed": GREEN,
    "not_fixed": VERMILLION,
    "prompt_only": ORANGE,
    "guardrail": YELLOW,
    "tool_misuse": VERMILLION,
    "policy_violation": ORANGE,
    "reasoning_error": BLUE,
    "communication_error": GREEN,
    # Diagram roles
    "process": "#E8F4FD",       # light blue fill
    "decision": "#FFF3CD",      # light amber fill
    "terminal": "#E8E8E8",      # light grey fill
    "success": "#D4EDDA",       # light green fill
    "failure": "#F8D7DA",       # light red fill
    "data": "#E2E0F5",          # light purple fill
    "highlight": SKY,
    "border": "#2C3E50",
    "border_light": "#5D6D7E",
    "arrow": "#34495E",
    "bg": "white",
    "text": "#1A1A2E",
}

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
FONT = "Liberation Serif"
FONT_BOLD = "Liberation Serif"
FONT_MONO = "Liberation Mono"
FONT_SIZE = "11"
FONT_SIZE_SMALL = "9"
FONT_SIZE_TITLE = "14"

# ---------------------------------------------------------------------------
# Output config
# ---------------------------------------------------------------------------
OUTPUT_DIR = "figures"
FORMAT = "png"
DPI = "300"

# ---------------------------------------------------------------------------
# Graph factory helpers
# ---------------------------------------------------------------------------

def new_graph(name: str, *, directed: bool = True, rankdir: str = "TB",
              engine: str = "dot", **extra) -> graphviz.Digraph | graphviz.Graph:
    """Create a new graph with standard thesis styling."""
    cls = graphviz.Digraph if directed else graphviz.Graph
    g = cls(name, format=FORMAT, engine=engine)
    g.attr(
        rankdir=rankdir,
        bgcolor="white",
        fontname=FONT,
        fontsize=FONT_SIZE,
        pad="0.4",
        dpi=DPI,
        margin="0",
        **extra,
    )
    g.attr("node",
        fontname=FONT,
        fontsize=FONT_SIZE,
        style="filled",
        color=C["border"],
        penwidth="1.2",
    )
    g.attr("edge",
        fontname=FONT,
        fontsize=FONT_SIZE_SMALL,
        color=C["arrow"],
        arrowsize="0.7",
        penwidth="1.0",
    )
    return g


def process_node(g: graphviz.Digraph, name: str, label: str, **kw):
    """Rounded rectangle — a process step."""
    g.node(name, label=label, shape="box", style="filled,rounded",
           fillcolor=C["process"], **kw)


def decision_node(g: graphviz.Digraph, name: str, label: str, **kw):
    """Diamond — a decision point."""
    g.node(name, label=label, shape="diamond", style="filled",
           fillcolor=C["decision"], fontsize=FONT_SIZE_SMALL,
           width="1.8", height="1.0", **kw)


def terminal_node(g: graphviz.Digraph, name: str, label: str, **kw):
    """Stadium/rounded — start/end."""
    g.node(name, label=label, shape="oval", style="filled",
           fillcolor=C["terminal"], **kw)


def data_node(g: graphviz.Digraph, name: str, label: str, **kw):
    """Parallelogram-ish — data/artifact."""
    g.node(name, label=label, shape="note", style="filled",
           fillcolor=C["data"], **kw)


def highlight_node(g: graphviz.Digraph, name: str, label: str, color: str = "", **kw):
    """Accented box for emphasis."""
    fill = color or C["highlight"]
    g.node(name, label=label, shape="box", style="filled,rounded,bold",
           fillcolor=fill, color=C["border"], **kw)


def cluster(g: graphviz.Digraph, name: str, label: str, **kw) -> graphviz.Digraph:
    """Create a named subgraph cluster with a label."""
    sub = graphviz.Digraph(f"cluster_{name}")
    sub.attr(label=label, style="dashed", color=C["border_light"],
             fontname=FONT_BOLD, fontsize=FONT_SIZE, labeljust="l",
             bgcolor="#FAFAFA", penwidth="1.0", **kw)
    return sub


def render(g: graphviz.Digraph | graphviz.Graph, filename: str | None = None):
    """Render to OUTPUT_DIR, return the output path."""
    fname = filename or g.name
    path = g.render(directory=OUTPUT_DIR, filename=fname, cleanup=True)
    print(f"  -> {path}")
    return path
