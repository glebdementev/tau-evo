#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

pandoc \
  --defaults=defaults.yaml \
  abstract.md \
  -o conference_abstract.pdf

echo "Built: conference_abstract.pdf"
