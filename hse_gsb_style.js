// =============================================================================
// HSE Graduate School of Business (ВШБ) — PptxGenJS Style Kit
// =============================================================================
// Usage: const hse = require("./hse_gsb_style.js");
//        const pres = hse.createPresentation();
//        const slide = hse.addContentSlide(pres, { ... });
//
// This file encodes every visual rule from the official ВШБ template so that
// presentations can be generated programmatically while staying on-brand.
// =============================================================================

const pptxgen = require("pptxgenjs");

// ---------------------------------------------------------------------------
// 1. COLOR PALETTE
// ---------------------------------------------------------------------------
const COLORS = {
  // Primary colors (Основные цвета)
  NAVY:       "0F2D69",   // R=15  G=45  B=105  — dominant brand color
  RED:        "E61E3C",   // R=230 G=30  B=60   — accent rectangles on title slide
  DARK_RED:   "C00000",   // big stat numbers
  PINK_LIGHT: "F5C3C3",   // R=245 G=195 B=195  — table header row background
  ROSE:       "CD5A5A",   // R=205 G=90  B=90   — chart series / secondary accent

  // Secondary colors (Дополнительные цвета)
  BLUE_MED:   "234B9B",   // R=35  G=75  B=155
  GRAY_MID:   "7F7F7F",   // R=127 G=127 B=127
  GRAY_LIGHT: "A6A6A6",   // R=166 G=166 B=166
  GRAY_SILVER:"BFBFBF",   // R=191 G=191 B=191

  // Functional
  WHITE:      "FFFFFF",
  BLACK:      "000000",
  BG:         "FFFFFF",    // slide background is always white
};

// Chart series palette (reds/pinks matching the template bar/pie charts)
const CHART_COLORS = [
  COLORS.NAVY,        // series 1
  COLORS.RED,         // series 2
  COLORS.ROSE,        // series 3
  COLORS.PINK_LIGHT,  // series 4
  COLORS.GRAY_MID,    // series 5
  COLORS.GRAY_SILVER, // series 6
  COLORS.BLUE_MED,    // series 7
  COLORS.GRAY_LIGHT,  // series 8
];

// ---------------------------------------------------------------------------
// 2. TYPOGRAPHY
// ---------------------------------------------------------------------------
// The official font is "HSE Sans". Since it's a custom font that may not be
// installed everywhere, we provide a FALLBACK option. When generating PPTX
// for systems without HSE Sans, set hse.FONT = hse.FONT_FALLBACK.
//
const FONT = "HSE Sans";
const FONT_FALLBACK = "Arial";  // closest widely-available sans-serif

const FONT_SIZES = {
  TITLE_COVER: 43,   // cover slide title
  SUBTITLE:    16,    // cover slide subtitle / chart names / image captions
  HEADING:     24,    // content slide headings
  CALLOUT:     32,    // large callout text
  BODY:        13,    // standard body text
  HEADER_META: 10,    // presentation name / section name in header bar
  HEADER_INFO: 12,    // department name / city+year on cover
  FOOTNOTE:    10,    // footnotes and annotations
  SLIDE_NUM:   20,    // slide number
  BIG_STAT:    96,    // huge stat numbers (like "152 МЛН")
};

// ---------------------------------------------------------------------------
// 3. SLIDE DIMENSIONS & LAYOUT GRID  (inches)
// ---------------------------------------------------------------------------
// The template uses a custom 13.33" × 7.50" slide (not standard 16:9 10×5.625)
const SLIDE_W = 13.33;
const SLIDE_H = 7.50;

const MARGIN = {
  LEFT:   0.54,   // left content margin
  RIGHT:  0.60,   // right content margin (≈ 13.33 - 12.73)
  TOP:    0.51,   // top of header separator lines
};

// Header bar (repeated on every content slide)
const HEADER = {
  LOGO_X:       0.38,
  LOGO_Y:       0.30,
  LOGO_W:       0.70,
  LOGO_H:       0.35,
  LOGO_TEXT_X:   1.15,   // "Высшая школа бизнеса" text next to logo
  LOGO_TEXT_Y:   0.35,
  LOGO_TEXT_SZ:  10,

  // Vertical separator lines (navy, 1pt weight)
  LINE_Y:       0.51,
  LINE_H:       0.64,
  LINE_1_X:     3.61,   // after logo area
  LINE_2_X:     6.67,   // between pres name and section name
  LINE_3_X:     11.24,  // before slide number
  LINE_4_X:     12.73,  // after slide number
  LINE_WEIGHT:  1,      // pt

  // Text boxes within header
  PRES_NAME_X:  3.68,
  SECTION_NAME_X: 6.73,
  META_Y:       0.54,
  META_W:       2.57,
  SLIDE_NUM_X:  11.31,
  SLIDE_NUM_Y:  0.54,
};

// Horizontal line under header (full width, thin navy)
const HEADER_LINE = {
  X:     0.00,
  Y:     1.20,    // approximate y where the header area ends
  W:     SLIDE_W,
  COLOR: COLORS.NAVY,
  WEIGHT: 0.5,
};

// Content areas
const CONTENT = {
  // Title starts below header
  TITLE_Y:       1.53,
  TITLE_W:       11.08,

  // Body text area
  BODY_Y:        2.50,

  // Two-column layout
  COL_LEFT_W:    4.59,
  COL_RIGHT_X:   6.63,
  COL_RIGHT_W:   6.10,

  // Three-column layout (for 3-image or 3-stat slides)
  COL3_W:        3.80,
  COL3_GAP:      0.30,

  // Footnote
  FOOTNOTE_Y:    5.55,
};

// Title slide specifics
const TITLE_SLIDE = {
  TITLE_X:         1.39,
  TITLE_Y:         3.00,
  TITLE_W:         11.08,
  SUBTITLE_X:      1.39,
  SUBTITLE_Y:      5.70,
  DEPT_X:          6.24,
  DEPT_Y:          0.67,
  CITY_X:          9.14,
  CITY_Y:          0.67,
  // Red accent rectangles
  RED_LEFT_X:      0.00,
  RED_LEFT_Y:      4.02,
  RED_LEFT_W:      0.74,
  RED_LEFT_H:      1.00,
  RED_RIGHT_X:     11.20,
  RED_RIGHT_Y:     4.02,
  RED_RIGHT_W:     2.13,
  RED_RIGHT_H:     1.00,
};


// ---------------------------------------------------------------------------
// 4. TABLE STYLING
// ---------------------------------------------------------------------------
const TABLE_STYLE = {
  HEADER_FILL:    COLORS.PINK_LIGHT,
  HEADER_COLOR:   COLORS.NAVY,
  HEADER_BOLD:    true,
  HEADER_FONTSIZE: 13,
  BODY_COLOR:     COLORS.BLACK,
  BODY_FONTSIZE:  13,
  TOTAL_BOLD:     true,
  BORDER:         { pt: 0.5, color: COLORS.GRAY_SILVER },
  BORDER_HEADER_BOTTOM: { pt: 1.5, color: COLORS.NAVY },
  ROW_ALT_FILL:   null,   // no alternating row fills in this template
};


// ---------------------------------------------------------------------------
// 5. CHART STYLING
// ---------------------------------------------------------------------------
const CHART_STYLE = {
  COLORS:         CHART_COLORS,
  FONT_FACE:      FONT,
  TITLE_FONTSIZE: 16,
  TITLE_COLOR:    COLORS.NAVY,
  LABEL_COLOR:    COLORS.BLACK,
  GRID_COLOR:     COLORS.GRAY_SILVER,
  LEGEND_POS:     "b",    // bottom
};


// ---------------------------------------------------------------------------
// 6. HELPER FUNCTIONS
// ---------------------------------------------------------------------------

/**
 * Create a new HSE GSB-branded presentation instance.
 */
function createPresentation(opts = {}) {
  const pres = new pptxgen();
  pres.defineLayout({ name: "HSE_CUSTOM", width: SLIDE_W, height: SLIDE_H });
  pres.layout = "HSE_CUSTOM";
  pres.author = opts.author || "HSE GSB";
  pres.title  = opts.title  || "Presentation";
  return pres;
}

/**
 * Get a fresh text style object (to avoid PptxGenJS mutation issues).
 */
function textStyle(role) {
  const font = FONT;
  const styles = {
    title_cover: { fontFace: font, fontSize: FONT_SIZES.TITLE_COVER, color: COLORS.NAVY },
    subtitle:    { fontFace: font, fontSize: FONT_SIZES.SUBTITLE,    color: COLORS.BLACK },
    heading:     { fontFace: font, fontSize: FONT_SIZES.HEADING,     color: COLORS.NAVY },
    body:        { fontFace: font, fontSize: FONT_SIZES.BODY,        color: COLORS.BLACK },
    callout:     { fontFace: font, fontSize: FONT_SIZES.CALLOUT,     color: COLORS.NAVY },
    footnote:    { fontFace: font, fontSize: FONT_SIZES.FOOTNOTE,    color: COLORS.BLACK },
    meta:        { fontFace: font, fontSize: FONT_SIZES.HEADER_META, color: COLORS.BLACK },
    big_stat:    { fontFace: font, fontSize: FONT_SIZES.BIG_STAT,    color: COLORS.DARK_RED },
    chart_title: { fontFace: font, fontSize: FONT_SIZES.SUBTITLE,    color: COLORS.NAVY },
  };
  return { ...styles[role] };
}

/**
 * Add the standard header bar to a content slide.
 * @param {object} pres - PptxGenJS presentation
 * @param {object} slide - slide object
 * @param {object} opts - { presName, sectionName, slideNum, logoPath }
 */
function addHeader(pres, slide, opts = {}) {
  const H = HEADER;

  // Logo image (if provided)
  if (opts.logoPath) {
    slide.addImage({
      path: opts.logoPath,
      x: H.LOGO_X, y: H.LOGO_Y,
      w: H.LOGO_W, h: H.LOGO_H,
    });
  }

  // Vertical separator lines
  [H.LINE_1_X, H.LINE_2_X, H.LINE_3_X, H.LINE_4_X].forEach(lx => {
    slide.addShape(pres.shapes.LINE, {
      x: lx, y: H.LINE_Y, w: 0, h: H.LINE_H,
      line: { color: COLORS.NAVY, width: H.LINE_WEIGHT },
    });
  });

  // Presentation name
  if (opts.presName) {
    slide.addText(opts.presName, {
      x: H.PRES_NAME_X, y: H.META_Y, w: H.META_W, h: 0.44,
      ...textStyle("meta"),
      valign: "top",
      margin: 0,
    });
  }

  // Section name
  if (opts.sectionName) {
    slide.addText(opts.sectionName, {
      x: H.SECTION_NAME_X, y: H.META_Y, w: H.META_W, h: 0.44,
      ...textStyle("meta"),
      valign: "top",
      margin: 0,
    });
  }

  // Slide number
  if (opts.slideNum !== undefined) {
    slide.addText(String(opts.slideNum), {
      x: H.SLIDE_NUM_X, y: H.SLIDE_NUM_Y, w: 0.73, h: 0.44,
      fontFace: FONT, fontSize: FONT_SIZES.SLIDE_NUM,
      color: COLORS.NAVY,
      valign: "top",
      margin: 0,
    });
  }
}

/**
 * Add a standard content slide with header, title, and body area.
 */
function addContentSlide(pres, opts = {}) {
  const slide = pres.addSlide();
  slide.background = { color: COLORS.BG };

  addHeader(pres, slide, opts);

  // Title
  if (opts.title) {
    slide.addText(opts.title, {
      x: MARGIN.LEFT, y: CONTENT.TITLE_Y,
      w: CONTENT.TITLE_W, h: 0.91,
      ...textStyle("heading"),
      valign: "top",
      margin: 0,
    });
  }

  return slide;
}

/**
 * Add the cover / title slide.
 */
function addTitleSlide(pres, opts = {}) {
  const slide = pres.addSlide();
  slide.background = { color: COLORS.BG };
  const T = TITLE_SLIDE;

  // Logo
  if (opts.logoPath) {
    slide.addImage({
      path: opts.logoPath,
      x: HEADER.LOGO_X, y: HEADER.LOGO_Y,
      w: HEADER.LOGO_W, h: HEADER.LOGO_H,
    });
  }

  // Header separator lines and department/city info
  if (opts.department || opts.city) {
    // Lines on title slide are at different positions
    slide.addShape(pres.shapes.LINE, {
      x: 5.65, y: 0.51, w: 0, h: 0.92,
      line: { color: COLORS.NAVY, width: 1 },
    });
    slide.addShape(pres.shapes.LINE, {
      x: 8.97, y: 0.51, w: 0, h: 0.92,
      line: { color: COLORS.NAVY, width: 1 },
    });
  }

  if (opts.department) {
    slide.addText(opts.department, {
      x: T.DEPT_X, y: T.DEPT_Y, w: 2.57, h: 0.50,
      fontFace: FONT, fontSize: FONT_SIZES.HEADER_INFO,
      color: COLORS.BLACK, valign: "top", margin: 0,
    });
  }

  if (opts.city) {
    slide.addText(opts.city, {
      x: T.CITY_X, y: T.CITY_Y, w: 2.27, h: 0.50,
      fontFace: FONT, fontSize: FONT_SIZES.HEADER_INFO,
      color: COLORS.BLACK, valign: "top", margin: 0,
    });
  }

  // Main title
  if (opts.title) {
    slide.addText(opts.title, {
      x: T.TITLE_X, y: T.TITLE_Y, w: T.TITLE_W, h: 2.27,
      ...textStyle("title_cover"),
      valign: "top", margin: 0,
    });
  }

  // Subtitle
  if (opts.subtitle) {
    slide.addText(opts.subtitle, {
      x: T.SUBTITLE_X, y: T.SUBTITLE_Y, w: 4.85, h: 0.64,
      ...textStyle("subtitle"),
      valign: "top", margin: 0,
    });
  }

  // Red accent rectangles
  slide.addShape(pres.shapes.RECTANGLE, {
    x: T.RED_LEFT_X,  y: T.RED_LEFT_Y,
    w: T.RED_LEFT_W,  h: T.RED_LEFT_H,
    fill: { color: COLORS.RED },
    line: { color: COLORS.RED, width: 0 },
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: T.RED_RIGHT_X, y: T.RED_RIGHT_Y,
    w: T.RED_RIGHT_W, h: T.RED_RIGHT_H,
    fill: { color: COLORS.RED },
    line: { color: COLORS.RED, width: 0 },
  });

  return slide;
}


// ---------------------------------------------------------------------------
// 7. EXPORTS
// ---------------------------------------------------------------------------
module.exports = {
  // Constants
  COLORS,
  CHART_COLORS,
  FONT,
  FONT_FALLBACK,
  FONT_SIZES,
  SLIDE_W,
  SLIDE_H,
  MARGIN,
  HEADER,
  HEADER_LINE,
  CONTENT,
  TITLE_SLIDE,
  TABLE_STYLE,
  CHART_STYLE,

  // Functions
  createPresentation,
  textStyle,
  addHeader,
  addContentSlide,
  addTitleSlide,
};
