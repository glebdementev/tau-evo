#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

TITLE_PDF="../Title Page.pdf"
BODY_PDF="project_thesis.body.pdf"
OUTPUT_PDF="project_thesis.pdf"

pandoc \
  --defaults=defaults.yaml \
  metadata.yaml \
  00_introduction.md \
  ch1_0_chapter.md \
  ch1_1_organizational_problem.md \
  ch1_2_literature_and_practice.md \
  ch1_3_diagnostic_study.md \
  ch2_0_chapter.md \
  ch2_1_methodology_choice.md \
  ch2_2_phase_by_phase_plan.md \
  ch2_3_solution_architecture.md \
  ch2_4_implementation.md \
  ch3_0_chapter.md \
  ch3_1_1_five_task.md \
  ch3_1_2_ten_task.md \
  ch3_1_3_twenty_task.md \
  ch3_1_4_cross_scale.md \
  ch3_2_effectiveness_evaluation.md \
  99_conclusion.md \
  100_appendices.md \
  -o "$BODY_PDF"

if command -v pdfunite >/dev/null 2>&1; then
  pdfunite "$TITLE_PDF" "$BODY_PDF" "$OUTPUT_PDF"
elif command -v qpdf >/dev/null 2>&1; then
  qpdf --empty --pages "$TITLE_PDF" "$BODY_PDF" -- "$OUTPUT_PDF"
elif command -v uv >/dev/null 2>&1; then
  uv run --with pypdf python - "$TITLE_PDF" "$BODY_PDF" "$OUTPUT_PDF" <<'PY'
import sys
from pathlib import Path

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
  python - "$TITLE_PDF" "$BODY_PDF" "$OUTPUT_PDF" <<'PY'
import sys
from pathlib import Path

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

echo "Built: $OUTPUT_PDF"
