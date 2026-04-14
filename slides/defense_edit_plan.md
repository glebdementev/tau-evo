# Defense Presentation Edit Plan

Based on full inspection of `slides/defense.pptx` (16 slides) against
`text/project_thesis/` chapters. Each slide inventoried for shapes, tables,
images, and text.

## Current slide inventory

| # | Title | Key visual content |
|---|-------|--------------------|
| S1 | Title slide | Text only (title, author, supervisor, programme, date) |
| S2 | Key Concepts | 4 columns (LLM, Agent, Benchmark, Prompt Evo) + 4 images (concept illustrations) + example lists |
| S3 | Relevance & Research Gap | 2 text claims + 1 large image (right half) + 1 bottom image bar |
| S4 | Problem, Goal, Q1-Q3, Tasks | Problem/Goal text boxes + 3 question cards (Q1/Q2/Q3) + 5-row objectives table |
| S5 | Literature Review (4-column) | 4 columns with papers + transition questions at bottom. Text-heavy, no images |
| S6 | Dataset: tau2-bench | Text description + 1 large architecture image |
| S7 | Model Selection | Title + 5-row x 3-col table (Role/Model/Rationale). Already populated. |
| S8 | Outer/Inner Loop | 5-step numbered flow + 2 images (outer loop diagram, inner loop diagram) |
| S9 | Teacher patch surfaces | Text list (6 steps) + 1 large image (teacher session screenshot) |
| S10 | Experimental UI | 3 screenshots (run summary, teacher fix, heatmap) |
| S11 | Results overview | 3 text bullets + 4-row x 4-col pass rate table (model x scale) |
| S12 | F1: Failure modes | Q1 sub-header + 22-row x 7-col per-task table (all models) + text findings + 1 fix-tier image |
| S13 | F2: Scaling | Q2 sub-header + 3x3 grid of heatmap images (model x scale) + text findings. 2 cells have annotation text ("Nothing to fix", "Not tested") |
| S14 | F3: Gap closure | Q3 sub-header + 9-row x 6-col gap closure table (B/K/Δ/GC) + 1 bar chart image + text findings |
| S15 | Conclusion | Outcomes table (3 Q's with verdicts) + Contributions text (3 items) |
| S16 | Limitations & Further Work | 2-column text (limitations left, further work right) |

---

## Edit plan: slide by slide

### S1: Title — KEEP
No changes needed.

### S2: Key Concepts — EDIT (minor)
**What's there:** 4-column layout with concept definitions, example lists,
and illustrative images.
**What to fix:**
- Change "GPT-5.4, Opus 4.6, Gemini 3.1" examples → keep or replace with
  models used in thesis (Qwen3, Kimi K2.5, GLM 4.7) since those are what
  the audience will hear about for the next 20 minutes.
- Change "Claude Code, OpenAI Codex, Manus" → customer-service agents
  (Intercom AI, Sierra, Klarna AI) or keep generic but add "customer service"
  framing since the thesis is about CX, not coding.
- Images are fine.

### — INSERT after S2: Organizational Problem (NEW S3)
**Why:** This is a project-based thesis at HSE GSB. The organizational problem
at target ai must appear before any theory. The committee expects it.
**Content:**
- target ai: 75 people, 25 systems analysts (largest group), 19 developers
- tos1 = 200M RUB revenue; analyst team = 75M RUB/yr = 37% of revenue
- Every deployment adds linear load to the same 25-person pool
- Target Voice migration pressure (210M → 60M RUB, 2024→2025)
- The thesis's aim: replace analyst-driven alignment with automated DPV
**Visual:** Proportional blocks/treemap for headcount, revenue vs cost bars.
Use `inspo_org_problem.pptx` as starting point.
**Source:** Section 1.1

### S3 (old): Relevance & Research Gap — REPLACE → Market & Diagnostic Study (NEW S4)
**What's there:** Two text claims ("98.5% pass rate → 1.5pp churn" — unsourced),
a large image on right (looks like a benchmark comparison), a bottom image bar.
**What's wrong:**
- The 98.5% / 1.5pp claim doesn't appear in the thesis.
- No mention of Porter's Five Forces, Value Chain, or Cost Analysis — all
  required by the project-based thesis format.
- The "relevance" is framed as pure research, not organizational.
**What to replace with:**
- Title: "Why Automated Alignment Is Necessary"
- Left: Porter's 5 Forces synthesis (1 sentence each force, all converge on
  "market demands automated agent alignment"). Use `fig_ds_01_five_forces.png`.
- Right: Value Chain bottleneck — activities 2 (requirements translation) and
  5 (maintenance) share the same 25-person headcount pool. This is the only
  activity that doesn't amortize. Use `fig_ds_02_value_chain.png`.
- Bottom: cost structure shift — linear (FTE) to near-fixed (compute).
**Source:** Section 1.3

### S4 (old): Problem, Goal, Q1-Q3, Tasks — EDIT (significant)
**What's there:** Problem text + Goal text + 3 question cards + 5-row
objectives table.
**What to fix:**
- **Problem text** says "LLM agents are unreliable at enterprise scale and
  tasks, as shown by agentic benchmarks." This is the research-level problem,
  not the organizational problem. Rewrite to: "target ai's 25-person analyst
  team is the binding constraint on scaling the tos line. The cost of aligning
  agents to customer preferences scales linearly with deployments."
- **Goal text** says "Demonstrate automatic benchmark pass rate improvement
  and show its limitations." Too vague. Rewrite to: "Design, implement, and
  evaluate a DPV framework that aligns a weaker student to a customer preference
  function without modifying weights."
- **Q1-Q3 cards** are fine but should reference the 5 objectives. Consider
  relabeling: "Obj 3 / Q1", "Obj 4 / Q2", "Obj 3+4 / Q3"
- **Objectives table** (5 rows x 2 cols: Objective, Outcome) — verify that
  Objective 5 ("Produce actionable recommendations for target ai") is present.
  Check if it currently lists 5 rows. From the data: rows are baseline eval,
  DPV framework, scaling data, gap closure metric, failure mode boundaries.
  This maps to Obj 1-4 but is missing Obj 5 (recommendations). **Add row 6
  for Objective 5: "Recommendations for target ai → Phased integration roadmap."**
**Source:** Introduction

### S5: Literature Review — EDIT (minor)
**What's there:** 4-column layout (Agents fail / Prompting is brittle /
Fine-tuning is costly / Auto-optimization exists). Paper citations in each
column. Transition questions at bottom of each column.
**What works:** The 4-column structure is excellent. The transition questions
("Can we just prompt-engineer?" → "Can we fine-tune instead?" → "Can we
optimize prompts automatically?") create a clear argument chain.
**What to fix:**
- Column 4 bottom text says "Tools exist, benchmarks exist, but the two have
  not met." This IS the gap statement but it's buried in 8pt font. Make it
  visually prominent — bold, or add the `fig_lr_05_optimization_coverage.png`
  showing the empty "Tool-Calling Benchmark" column.
- Consider adding one line to column 3 about Training-Free GRPO (Cai 2025)
  — "Even RL community moving to context-space optimization."
- Consider adding Superficial Alignment Hypothesis (LIMA, Zhou 2023) to
  column 3 — it's theoretically central to the thesis.

### — INSERT after S5: Methodology (NEW S7)
**Why:** The committee will ask "What methodology did you use?" Having one
slide prevents a 5-minute detour.
**Content:**
- Left half: "Project Design Methodology" — EDP selected over TOGAF, SDLC,
  DSR, CRISP-DM. Key reasons: deliverable is a framework (not architecture,
  not production software, not a model). EDP's test-redesign cycle mirrors
  the DPV loop itself.
- Right half: "Diagnostic Methodology" — Porter's 5 Forces + Value Chain +
  Cost Analysis selected over SWOT, PESTEL. Key reason: produces actionable
  requirements, not descriptive lists.
- Visual: `fig_edp_cycle.png` showing the 7-phase cycle with iteration arrows.
**Source:** Section 2.1

### S6: Dataset tau2-bench — EDIT (minor)
**What's there:** Text description + large benchmark architecture image.
**What to fix:**
- Add why tau2-bench over alternatives: "Only benchmark combining multi-turn
  conversations + domain-specific policies + tool-calling + pass^k metric."
- Add the framing: "Each task encodes a customer preference function — mirrors
  enterprise acceptance criteria."
- The architecture image is good. Keep it.

### S7 (old): Model Selection — EDIT (minor)
**What's there:** Title + 5-row x 3-col table with Role/Model/Rationale.
Already has Qwen3 30B, Qwen3.5 Flash, GLM 4.7, Kimi K2.5, user sim.
**What's wrong:** Title is "We chose SOTA OSS for benchmarking. Student
models had to be non-thinking." — too casual for a defense.
**What to fix:**
- Retitle: "Model Selection and Roles"
- Add one line about temporal disjunction: "System 2 reasoning (teacher) at
  design time improves System 1 performance (student) at runtime."
- Verify table content matches thesis Table in Section 2.4.

### S8: Outer/Inner Loop — EDIT (minor)
**What's there:** 5-step numbered flow at top, 2 diagrams (outer loop, inner
loop) below.
**What to fix:**
- Add note: "All tasks re-evaluated every sweep (catches regressions from
  merge step)."
- The step flow 1→2→3→4→5 is clear. Keep it.

### S9: Teacher patch surfaces — EDIT (moderate)
**What's there:** 6-step text list on left + 1 large teacher session screenshot
on right.
**What to fix:**
- Add the two-phase escalation: "Phase 1 (teaching): prompt + schema only.
  Phase 2 (guardrails): unlock tool preprocessor editing."
- Add: "Fix accepted only if ALL trials pass (unanimous validation)."
- The 6-step list (evaluate → classify → give to teacher → teacher calls
  tools → apply patches → test) is good but should mention the phase split.

### S10: Experimental UI — CUT (move to backup)
**What's there:** 3 screenshots of the framework's web UI.
**Why cut:** Burns a slide slot on something the committee won't ask about.
The screenshots are impressive but don't advance the argument. Move to
a backup/appendix section after S16. If someone asks "do you have a UI?"
you can flip to it.
**Alternative:** If the deck feels too short after restructuring, keep it.

### S11: Results overview — EDIT (moderate)
**What's there:** 3 text bullets (qualitative) + 4-row x 4-col table with
pass rates (Task count | Qwen 30 | Qwen 3.5 | GLM-4.7).
**What's wrong:** Table values are inconsistent with thesis. Current table
shows "47 -> 47" for GLM 5t but thesis says peak was 73% before collapse.
Table shows "100 -> N/A" for Qwen3.5 5t but thesis says baseline was 100%.
The "GLM-4.7" column seems to show sweep-3 (collapsed) values rather than
best values.
**What to fix:**
- Decide on a consistent metric: best post-evolution or final sweep? The
  thesis uses "best" for primary reporting. If showing "best", GLM 5t should
  be 73 (not 47).
- Add ↑/↓ indicators or color-coding to make improvement/regression visible.
- Add a footnote: "* = peak before regression"
- Text bullets should include actual numbers, not just "most consistent
  improvement."

### S12: F1 Failure modes — EDIT (moderate)
**What's there:** 22-row per-task table (all 3 models x base/evolved) + text
findings + fix-tier chart image.
**What's wrong:** The 22-row table is too dense for a defense slide — the
committee can't read 22 rows in 2 minutes. The text says "Many tasks are
fully resistant... Most fixes are powered by instruction... Guardrail fixes
are mostly applied at later stages."
**What to fix:**
- The 22-row table should be a visual summary, not raw data. Consider
  replacing with the heatmap from `runs/20/sweep_heatmap_print.svg` or a
  summary bar chart.
- Lead with the 71/29 (or 70-92%) instruction-to-guardrail ratio as the
  headline finding. This is the key Q1 answer.
- Add: "Supports the Superficial Alignment Hypothesis (Zhou et al., 2023):
  failures are primarily in instruction-following, not capability."
- The fix-tier chart image is good — keep it but make sure it's the updated
  `slides/fix_tier_breakdown.png` with all 7 experiments.

### S13: F2 Scaling — EDIT (moderate)
**What's there:** 3x3 grid of heatmap images (model x scale) with annotation
labels ("Nothing to fix; all green", "Not tested due to continuous regression").
Left column has text findings.
**What's good:** The heatmap grid is the most visual slide in the deck and
clearly shows the pattern. Keep it.
**What to fix:**
- The left-column text is disorganized. Rewrite as structured findings:
  "Fix rate: 100% → 43% → 20% (Qwen3 30B)"
  "Fix rate: N/A → 80% → 45% (Qwen3.5 Flash)"
  "Fix rate: 67% → 0% (GLM 4.7 — dropped at 20t)"
- Add the Cochran-Armitage result: "Declining trend significant (p = 0.031)"
- Fix the claim "All models poorly retain pass rate improvement" — thesis
  shows Qwen3.5 Flash at 20t is remarkably stable (65% in both sweep 2 and 3).

### S14: F3 Gap closure — EDIT (minor)
**What's there:** 9-row gap closure table (B%/K%/Δ/GC%) + bar chart image +
text findings.
**What's good:** The table and bar chart are already well-structured and
match the thesis data from the gen_q3_slide.py script. This slide has the
most complete data of any results slide.
**What to fix:**
- Text says "Cannot yet infer any pattern what drives more/less gap closure."
  This is incorrect — the thesis HAS findings: the stronger student achieves
  dramatically higher ceilings; the framework amplifies rather than equalizes
  capability differences.
- Replace with: "Framework amplifies capability differences. Stronger student
  (Qwen3.5 Flash) benefits most. GLM 4.7 degrades below baseline."
- Verify FRONTIER_RATE: currently 82% (Claude 3.5 Sonnet?). Per CLAUDE.md,
  the placeholder is 0.80 and needs actual Kimi K2.5 pass rate. Confirm
  before defense.

### — INSERT after S14: Economic Analysis (NEW S17)
**Why:** Most compelling slide for a business school defense. The thesis has
extensive economic analysis (Section 3.5) that is completely absent from the
current deck.
**Content:**
- Headline: "$0.05 per fix vs $22-$86 manual (440-1,720x cheaper)"
- Annual per-deployment: $3,102 (automated) vs $45,000-$55,000 (manual)
- Break-even: ~2 months
- ROI: 1,732% (3 deployments) to 19,119% (30 deployments)
- Sensitivity: robust — even worst-case is 6.5x cheaper
**Visual:** Use `slides/fig_economic_cost_comparison.png` and/or
`slides/fig_economic_roi.png` (already generated).
Or use `inspo_economic.pptx` layout as template.
**Source:** Section 3.5

### — INSERT after Economic: Recommendations & Roadmap (NEW S18)
**Why:** Objective 5 of the thesis. The committee expects project-based
theses to deliver actionable recommendations.
**Content:**
- Phase 1: Validation — internal benchmarks, full patch review (4-6 weeks)
- Phase 2: Shadow Mode — production traces, selective approval (2-3 months)
- Phase 3: Automated — closed-loop with regression guard (ongoing)
- Key extras: model compatibility screening, patch consolidation, early
  termination heuristics, stronger teachers as available
**Visual:** Use `slides/fig_roadmap.png` (already generated).
**Source:** Section 3.5 "Recommendations for target ai"

### S15 (old): Conclusion — EDIT (significant)
**What's there:** Left: 3-row outcomes table (Q1/Q2/Q3 with verdicts and
checkmarks). Right: 3 contributions text.
**What to fix:**
- **Outcomes table** is good — maps Q1-Q3 to results with checkmarks. Keep
  but verify verdicts match thesis. Q3 should be "Partial ✓" not full ✓.
- **Contributions** currently lists 3 items:
  1. Teacher-driven framework — 3 patch surfaces, validate-before-merge
  2. Empirical eval on multi-turn tool-calling benchmark
  3. Scaling evidence: stable gain, declining fix rate, hard core
  The thesis has 4 contributions. Missing: "The 71/29 instruction-to-guardrail
  ratio as a practitioner heuristic." Add as item 3, renumber.
- **Missing:** Loop back to target ai. Add one line: "Shifts cost from linear
  (per-FTE, per-deployment) to near-fixed (teacher model compute)." This
  closes the narrative arc opened by the organizational problem slide.

### S16: Limitations & Further Work — EDIT (moderate)
**What's there:** 2-column layout. Left: 4 limitations. Right: 4 further
work items.
**What to fix in Limitations:**
- "Only OSS models" — misleading. The teacher (Kimi K2.5) IS an OSS model
  but with frontier-class capability. Rephrase: "Single teacher model (Kimi
  K2.5) across three students; teacher sensitivity uncharacterized."
- Add: "No patch retirement mechanism — accumulation causes interference"
- Add: "Best result (80%) far from 3-5 nines required for autonomous operation"
- Add: "User simulator is LLM-based — production behavior untested"
**What to fix in Further Work:**
- "Vary teachers and students" — fine but vague. Specify: "Systematic
  teacher-student ablations to map the design space."
- Add: "Hybrid prompt + weight evolution for the resistant hard core"
- Add: "Patch consolidation / retirement policies (prompt-space continual
  learning)"
- Add: "Production deployment study on real customer interaction traces"

---

## Summary of changes

| Action | Count | Slides |
|--------|-------|--------|
| KEEP as-is | 1 | S1 |
| EDIT minor | 6 | S2, S5, S6, S7 (models), S8, S14 |
| EDIT moderate | 4 | S9, S11, S12, S13 |
| EDIT significant | 2 | S4 (problem/goal), S15 (conclusion) |
| REPLACE | 1 | S3 (relevance → market/diagnostic) |
| INSERT | 4 | Org Problem, Methodology, Economic, Roadmap |
| CUT (→ backup) | 1 | S10 (UI screenshots) |

**Net: 16 → 19 slides** (or 20 if UI is kept)

## New slide order

| # | Content | Section tag | Source |
|---|---------|-------------|--------|
| 1 | Title | -- | KEEP S1 |
| 2 | Key Concepts | Introduction | EDIT S2 |
| 3 | **Organizational Problem** | **Ch 1.1** | **INSERT** |
| 4 | Market & Diagnostic Study | Ch 1.3 | REPLACE S3 |
| 5 | Literature Review (4-column) | Ch 1.2 | EDIT S5 |
| 6 | Problem, Goal, 5 Objectives | Introduction | EDIT S4 |
| 7 | **Methodology (EDP + Diagnostics)** | **Ch 2.1** | **INSERT** |
| 8 | Dataset: tau2-bench | Ch 2.4 | EDIT S6 |
| 9 | Model Selection | Ch 2.4 | EDIT S7 |
| 10 | Outer/Inner Loop | Ch 2.3 | EDIT S8 |
| 11 | Teacher + Patch Surfaces | Ch 2.3 | EDIT S9 |
| 12 | Results overview | Ch 3.1-3.4 | EDIT S11 |
| 13 | F1: Failure modes (Q1) | Ch 3.4 | EDIT S12 |
| 14 | F2: Scaling (Q2) | Ch 3.4 | EDIT S13 |
| 15 | F3: Gap closure (Q3) | Ch 3.4 | EDIT S14 |
| 16 | **Economic Analysis** | **Ch 3.5** | **INSERT** |
| 17 | **Recommendations & Roadmap** | **Ch 3.5** | **INSERT** |
| 18 | Conclusion + 4 Contributions | Conclusion | EDIT S15 |
| 19 | Limitations & Further Work | Conclusion | EDIT S16 |
| -- | *Backup: Experimental UI* | -- | *S10 moved here* |

## Narrative arc

1-2: What we're talking about (concepts)
3-4: Why it matters (company problem → market forces)
5-6: What's known and what I set out to do (lit gap → objectives)
7: How I structured the work (methodology)
8-11: What I built and how (benchmark, models, architecture)
12-15: What happened (results matrix, 3 findings)
16-17: What it means for the business (economics, roadmap)
18-19: What I proved and what's left (contributions, limitations)

## Available visualizations

| For slide | Figure | Path |
|-----------|--------|------|
| 3 (Org Problem) | Proportional blocks | Build from `inspo_org_problem.pptx` |
| 4 (Diagnostic) | Five Forces diagram | `text/figures/fig_ds_01_five_forces.png` |
| 4 (Diagnostic) | Value Chain | `text/figures/fig_ds_02_value_chain.png` |
| 5 (Lit Review) | Optimization coverage | `text/figures/fig_lr_05_optimization_coverage.png` |
| 7 (Methodology) | EDP cycle | `text/figures/fig_edp_cycle.png` |
| 13 (F1) | Fix tier breakdown | `slides/fix_tier_breakdown.png` |
| 14 (F2) | Heatmaps | `runs/*/sweep_heatmap_print.svg` (already on slide) |
| 14 (F2) | Knowledge transfer | `text/figures/fig_14_knowledge_transfer.png` |
| 15 (F3) | Gap closure | `text/figures/fig_13_gap_closure.png` (already on slide) |
| 16 (Economic) | Cost comparison | `slides/fig_economic_cost_comparison.png` |
| 16 (Economic) | ROI scenarios | `slides/fig_economic_roi.png` |
| 17 (Roadmap) | Phased roadmap | `slides/fig_roadmap.png` |
