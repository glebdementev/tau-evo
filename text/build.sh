#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

pandoc \
  --defaults=defaults.yaml \
  metadata.yaml \
  ch1_introduction.md \
  ch2_literature_review.md \
  ch3_methodology.md \
  ch5_conclusion.md \
  -o full_thesis.docx

echo "Built: full_thesis.docx"
