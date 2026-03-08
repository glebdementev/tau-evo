"""Shared theme: Okabe-Ito palette, dark layout, and helper utilities."""

from __future__ import annotations

import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Okabe-Ito colorblind-friendly palette
# ---------------------------------------------------------------------------
_OI_BLUE = "#0072B2"
_OI_ORANGE = "#E69F00"
_OI_GREEN = "#009E73"
_OI_VERMILLION = "#D55E00"
_OI_SKY = "#56B4E9"
_OI_PURPLE = "#CC79A7"
_OI_YELLOW = "#F0E442"

COLORS = {
    "baseline": "#6B7B8D",       # neutral grey
    "patched": _OI_BLUE,
    "fixed": _OI_GREEN,
    "not_fixed": _OI_VERMILLION,
    "prompt_only": _OI_ORANGE,
    "guardrail": _OI_YELLOW,
    "airline": _OI_SKY,
    "retail": _OI_ORANGE,
    "telecom": _OI_GREEN,
    "TOOL_MISUSE": _OI_VERMILLION,
    "POLICY_VIOLATION": _OI_ORANGE,
    "REASONING_ERROR": _OI_BLUE,
}

# ---------------------------------------------------------------------------
# Dark layout for web dashboard
# ---------------------------------------------------------------------------
_FONT_FAMILY = "IBM Plex Sans, Arial, Helvetica, sans-serif"

DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(24,26,32,0.6)",
    font=dict(family=_FONT_FAMILY, color="#e5e7eb", size=13),
    margin=dict(l=64, r=24, t=56, b=52),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
        borderwidth=0,
    ),
    title=dict(
        font=dict(size=16, color="#f3f4f6"),
        x=0.01,
        xanchor="left",
        y=0.97,
        yanchor="top",
        pad=dict(b=8),
    ),
    hoverlabel=dict(font_size=12, font_family=_FONT_FAMILY),
)

_AXIS_COMMON = dict(
    showgrid=True,
    gridwidth=1,
    gridcolor="rgba(255,255,255,0.07)",
    showline=True,
    linewidth=1.2,
    linecolor="rgba(255,255,255,0.18)",
    zeroline=False,
    tickfont=dict(size=12),
    title_font=dict(size=13),
    title_standoff=10,
)

BAR_LINE = dict(color="rgba(255,255,255,0.15)", width=0.8)


def base_layout(**overrides) -> dict:
    """Merge DARK_LAYOUT + axis defaults + overrides."""
    layout = {**DARK_LAYOUT}
    xaxis = {**_AXIS_COMMON, **overrides.pop("xaxis", {})}
    yaxis = {**_AXIS_COMMON, **overrides.pop("yaxis", {})}
    layout["xaxis"] = xaxis
    layout["yaxis"] = yaxis
    layout.update(overrides)
    return layout


def empty_figure(title: str, message: str) -> dict:
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color="#6b7280"),
    )
    fig.update_layout(
        **DARK_LAYOUT,
        height=360,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig.to_dict()
