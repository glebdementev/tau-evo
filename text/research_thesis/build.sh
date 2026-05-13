#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

TITLE_PDF="../Title Page.pdf"
BODY_PDF="full_thesis.body.pdf"
OUTPUT_PDF="full_thesis.pdf"
MERGED_PDF="full_thesis.with_title.pdf"

trap 'rm -f "$BODY_PDF" "$MERGED_PDF"' EXIT

# Regenerate diagrams if requested
if [[ "${1:-}" == "--figures" ]]; then
  echo "Regenerating figures..."
  uv run python gen_diagrams.py
fi

if [[ ! -f "$TITLE_PDF" ]]; then
  echo "Missing title page PDF: $TITLE_PDF" >&2
  exit 1
fi

rm -f "$BODY_PDF" "$MERGED_PDF"

pandoc \
  --defaults=defaults.yaml \
  metadata.yaml \
  ch1_introduction.md \
  ch2_literature_review.md \
  ch3_methodology.md \
  ch4_results.md \
  ch5_conclusion.md \
  -o "$BODY_PDF"

if command -v pdfunite >/dev/null 2>&1; then
  pdfunite "$TITLE_PDF" "$BODY_PDF" "$MERGED_PDF"
elif command -v qpdf >/dev/null 2>&1; then
  qpdf --empty --pages "$TITLE_PDF" "$BODY_PDF" -- "$MERGED_PDF"
elif command -v uv >/dev/null 2>&1; then
  uv run --with pypdf python - "$TITLE_PDF" "$BODY_PDF" "$MERGED_PDF" <<'PY'
from pathlib import Path
import sys

from pypdf import PdfReader, PdfWriter

title_pdf, body_pdf, output_pdf = map(Path, sys.argv[1:])
writer = PdfWriter()

for pdf_path in (title_pdf, body_pdf):
    reader = PdfReader(str(pdf_path))
    for page in reader.pages:
        writer.add_page(page)

with output_pdf.open("wb") as f:
    writer.write(f)
PY
else
  python - "$TITLE_PDF" "$BODY_PDF" "$MERGED_PDF" <<'PY'
from pathlib import Path
import sys

try:
    from pypdf import PdfReader, PdfWriter
except ImportError as exc:
    raise SystemExit(
        "PDF merge requires pdfunite, qpdf, uv, or Python package pypdf."
    ) from exc

title_pdf, body_pdf, output_pdf = map(Path, sys.argv[1:])
writer = PdfWriter()

for pdf_path in (title_pdf, body_pdf):
    reader = PdfReader(str(pdf_path))
    for page in reader.pages:
        writer.add_page(page)

with output_pdf.open("wb") as f:
    writer.write(f)
PY
fi

mv "$MERGED_PDF" "$OUTPUT_PDF"

echo "Built: full_thesis.pdf"
