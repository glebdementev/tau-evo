#!/usr/bin/env python3
"""Translate plotly-emitted sweep_outcomes_print.svg files to Russian.

Reads each runs/*/sweep_outcomes_print.svg, applies a small label map to the
embedded <text> nodes, writes runs/*/sweep_outcomes_print_ru.svg + a rasterized
*.png alongside. Used to localize defense slide 13.

Usage:  python analysis/translate_sweep_svgs.py
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import cairosvg

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIRS = ["5", "10", "20", "glm47_5", "glm47_10", "qwen35-flash_10", "qwen35-flash_20"]

# Only translate label/legend/axis strings. Numeric tick labels stay untouched.
LABELS_RU = {
    "Sweep 1":             "Прогон 1",
    "Sweep 2":             "Прогон 2",
    "Sweep 3":             "Прогон 3",
    # Legend labels — kept short so they fit the fixed-width plotly legend box.
    "Unfixed":             "Не испр.",
    "Fixed (guardrail)":   "Испр. (guard)",
    "Fixed (instruction)": "Испр. (instr)",
    "Fixed (tools)":       "Испр. (tools)",
    "Fixed (code)":        "Испр. (code)",
    "Passed":              "Пройдено",
    "Tasks":               "Задачи",
    "Failures":            "Сбои",
    "Fixed Tasks":         "Исправлено",
}

# Match the inner content of a <text ...>VALUE</text> tag. Inner can have no
# nested tags in plotly output (label strings are plain text).
TEXT_RE = re.compile(r"(<text\b[^>]*>)([^<]+)(</text>)")


def translate_svg(src: Path, dst: Path) -> int:
    """Translate <text> contents in src SVG and write to dst. Returns replacement count."""
    content = src.read_text(encoding="utf-8")
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        before, inner, after = m.group(1), m.group(2), m.group(3)
        new = LABELS_RU.get(inner.strip())
        if new is None:
            return m.group(0)
        count += 1
        return f"{before}{new}{after}"

    new_content = TEXT_RE.sub(repl, content)
    dst.write_text(new_content, encoding="utf-8")
    return count


def rasterize(svg_path: Path, png_path: Path, width: int = 1800) -> None:
    """Rasterize SVG to PNG at given pixel width."""
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=width)


def main() -> None:
    total = 0
    for d in RUNS_DIRS:
        src = ROOT / "runs" / d / "sweep_outcomes_print.svg"
        if not src.exists():
            print(f"SKIP {src} (missing)")
            continue
        dst_svg = ROOT / "runs" / d / "sweep_outcomes_print_ru.svg"
        dst_png = ROOT / "runs" / d / "sweep_outcomes_print_ru.png"
        n = translate_svg(src, dst_svg)
        rasterize(dst_svg, dst_png)
        print(f"{d:18s}  replacements={n:>2}  -> {dst_svg.name} + {dst_png.name}")
        total += n
    print(f"\nTotal replacements: {total}")


if __name__ == "__main__":
    main()
