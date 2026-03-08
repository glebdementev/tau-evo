#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Regenerate diagrams if requested
if [[ "${1:-}" == "--figures" ]]; then
  echo "Regenerating figures..."
  uv run python gen_diagrams.py
fi

pandoc \
  --defaults=defaults.yaml \
  metadata.yaml \
  ch1_introduction.md \
  ch2_literature_review.md \
  ch3_methodology.md \
  ch5_conclusion.md \
  -o full_thesis.pdf

echo "Built: full_thesis.pdf"
