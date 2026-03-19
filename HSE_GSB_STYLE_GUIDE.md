# HSE Graduate School of Business (ВШБ) — Presentation Style Guide

This document describes the visual standards for creating presentations in the HSE GSB brand. Use it alongside `hse_gsb_style.js` (the PptxGenJS helper module) to produce on-brand slides programmatically.

---

## Slide Dimensions

The template uses a **non-standard** slide size: **13.33" × 7.50"** (12192000 × 6858000 EMU). This is wider than the typical 16:9 (10" × 5.625"). Always set the custom layout before adding slides.

---

## Font

Every text element uses **HSE Sans** — a custom sans-serif typeface from the HSE brand book. Download from: https://www.hse.ru/info/brandbook/#font

Fallback (when HSE Sans is unavailable): **Arial**.

### Type Scale

| Role                        | Size (pt) | Color       | Notes                                     |
|-----------------------------|-----------|-------------|-------------------------------------------|
| Cover title                 | 43        | `#0F2D69`   | Navy, regular weight                      |
| Content slide heading       | 24        | `#0F2D69`   | Navy, regular weight, max 2-3 lines       |
| Subtitle / chart title      | 16        | `#0F2D69`   | Navy or black                             |
| Body text                   | 13        | black       | Standard paragraph text                   |
| Header meta (pres/section)  | 10        | black       | In the top header bar                     |
| Header info (dept/city)     | 12        | black       | Cover slide only                          |
| Footnote / annotation       | 10        | black       | Bottom of slide                           |
| Slide number                | 20        | `#0F2D69`   | Top-right corner                          |
| Callout / emphasis text     | 32        | `#0F2D69`   | Large quote-style text                    |
| Big stat number             | 96        | `#C00000`   | e.g. "152 МЛН"                            |

### Rules

- Never reduce body text below 13pt to fit content; instead, reduce word count.
- Headings should convey the main idea and fit in 2-3 lines.
- All text uses HSE Sans — no mixing of fonts.

---

## Color Palette

### Primary Colors (Основные цвета)

| Name        | Hex       | RGB             | Usage                                    |
|-------------|-----------|-----------------|------------------------------------------|
| Navy        | `0F2D69`  | 15, 45, 105     | Headings, titles, separator lines, slide numbers |
| Red         | `E61E3C`  | 230, 30, 60     | Accent rectangles on title slide         |
| Dark Red    | `C00000`  | 192, 0, 0       | Big stat numbers                         |
| Pink Light  | `F5C3C3`  | 245, 195, 195   | Table header row background              |
| Rose        | `CD5A5A`  | 205, 90, 90     | Chart series, secondary accent           |

### Secondary Colors (Дополнительные цвета)

| Name        | Hex       | RGB             | Usage                                    |
|-------------|-----------|-----------------|------------------------------------------|
| Blue Medium | `234B9B`  | 35, 75, 155     | Charts, supplementary graphics           |
| Gray Mid    | `7F7F7F`  | 127, 127, 127   | Charts, annotations                      |
| Gray Light  | `A6A6A6`  | 166, 166, 166   | Charts                                   |
| Gray Silver | `BFBFBF`  | 191, 191, 191   | Table borders, chart gridlines           |

### Chart Color Order

When building charts (bar, pie, doughnut), use this series order:
1. Navy (`0F2D69`)
2. Red (`E61E3C`)
3. Rose (`CD5A5A`)
4. Pink Light (`F5C3C3`)
5. Gray Mid (`7F7F7F`)
6. Gray Silver (`BFBFBF`)
7. Blue Medium (`234B9B`)
8. Gray Light (`A6A6A6`)

---

## Slide Background

Always **white** (`FFFFFF`). No gradients, no textures, no dark backgrounds.

---

## Logo

The logo is the HSE GSB circular emblem with "Высшая школа бизнеса" text beside it.
- File: `hse_gsb_logo.png` (555 × 277 px, RGBA)
- Position: top-left corner of every slide
- Approx placement: x=0.38", y=0.30", w=0.70", h=0.35"
- The text "Высшая школа бизнеса" appears next to or is part of the logo image

---

## Header Bar (Content Slides)

Every content slide (not the title slide) has a structured header bar in the top ~1.2" of the slide.

### Structure (left to right):
1. **Logo** (top-left)
2. **Vertical line** at x≈3.61" (navy, 1pt, height 0.64")
3. **Presentation name** — 10pt, black, at x≈3.68"
4. **Vertical line** at x≈6.67"
5. **Section name** — 10pt, black, at x≈6.73"
6. **Vertical line** at x≈11.24"
7. **Slide number** — 20pt, navy, at x≈11.31"
8. **Vertical line** at x≈12.73"

All vertical lines share: y=0.51", h=0.64", color=`0F2D69` (navy), weight=1pt.

A thin horizontal rule at approximately y≈1.20" separates the header from content.

---

## Slide Layouts

### Layout 1: Title / Cover Slide (Slide 2 in template)

- Large title: 43pt navy, positioned at x=1.39", y=3.00", max width 11.08"
- Subtitle: 16pt black, positioned at x=1.39", y=5.70"
- Two **red accent rectangles** (`E61E3C`):
  - Left: x=0.00", y=4.02", w=0.74", h=1.00"
  - Right: x=11.20", y=4.02", w=2.13", h=1.00"
- Department name and city/year appear in the header area with vertical line separators
- Logo in top-left corner

### Layout 2: Title + Body Text (Slide 3)

- Heading: 24pt navy at x=0.54", y=1.53"
- Body text area starts at y=2.50"
- Left column: x=0.54", w≈4.59" for regular 13pt body text
- Right column: x=6.63", w≈6.10" for callout text (32pt navy)
- Footnote at y=5.55", 10pt

### Layout 3: Multi-Column Text (Slide 4)

- Heading: 24pt navy
- 2 or 3 text columns below, each with 13pt body text
- Columns have roughly equal widths spanning the content area
- Aim for 7-9 words per line

### Layout 4: Text + Image (Slide 5)

- Heading: 24pt navy (left-aligned)
- Left half: 13pt body text, max ~half slide width
- Right half: image placeholder (circular gray area in template)
- Images can be circular or rectangular

### Layout 5: 2-Image Grid (Slide 6)

- Two large circular/rectangular image areas side by side
- 16pt caption text below each image
- No heading — images dominate

### Layout 6: 3-Image Grid (Slide 7)

- Three image areas in a row
- 16pt caption text below each
- Vertical separator lines between sections

### Layout 7: Chart + Text (Slides 8, 9, 10, 14)

- Left: heading (24pt) + body text (13pt) + optional footnote (10pt)
- Right: chart with 16pt title
- Chart types used: horizontal bar, pie, doughnut
- Charts use the HSE color palette (reds, pinks, navy, grays)

### Layout 8: Big Stats (Slide 11)

- Heading: 24pt navy
- Three stat columns side by side
- Giant number: **96pt dark red** (`C00000`)
- Unit label (e.g. "МЛН"): 16pt navy, positioned next to the number
- Description: 13pt body text below each number

### Layout 9: Full-Width Table (Slide 12)

- 16pt subtitle/table name above the table
- Table spans nearly the full slide width
- Header row: pink background (`F5C3C3`), navy text, bold
- Data rows: white background, black text, regular weight
- Total row: bold text
- Borders: thin silver lines between cells, with heavier navy line under header
- Footnote text below the table

### Layout 10: Table + Text (Slide 13)

- Narrower table (left/center) with text column on the right
- Same table styling as Layout 9

---

## Table Formatting

- Header row fill: `F5C3C3` (light pink)
- Header text: navy, bold, 13pt
- Body text: black, regular, 13pt
- Borders: thin silver (`BFBFBF`), ≈0.5pt
- Heavy line under header: navy, ≈1.5pt
- Total row: bold text
- No alternating row colors
- Use bold sparingly — only for the most important values
- Do not combine bold with colored cell fills

---

## Key Design Principles

1. **White space is intentional** — don't fill every inch of the slide
2. **Reduce words, not font size** — if text overflows, cut content
3. **Consistent typography** — all HSE Sans, follow the size scale exactly
4. **Navy is dominant** — it appears in headings, lines, and numbers
5. **Red is accent only** — used sparingly for visual punctuation (title slide blocks, stat numbers)
6. **Charts use the brand palette** — never use default PowerPoint colors
7. **Header bar is mandatory** on all content slides
8. **7-9 words per line** — if text is long, use 2-3 columns
9. **Images deserve space** — when using images, give them half the slide or more
10. **Footnotes exist** — use 10pt text at the bottom for sources and annotations
