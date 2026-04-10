#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

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
  -o project_thesis.pdf

echo "Built: project_thesis.pdf"
