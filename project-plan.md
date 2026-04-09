# Plan: Restructure Thesis into Project-Based Format (7.5.x)

## Context

The current thesis "Self-Evolving LLM Agents via Reflective Prompt and Tool-Schema Patching" follows a scientific IMRaD structure (Introduction → Literature Review → Methodology → Results → Conclusion). It needs to be restructured into a **project-based thesis** following the 7.5.x format, framing the work as solving an organizational problem at TargetAI using the Engineering Design Process methodology.

Following the exemplar (credit scoring thesis), 7.5.1–7.5.3 collapse into Chapter 1, 7.5.4 becomes Chapter 2, and 7.5.5 becomes Chapter 3. Files are split by **subchapter**, plus Introduction and Conclusion.

---

## File Structure: `text/project_thesis/`

```
text/project_thesis/
├── 00_introduction.md
│
├── ch1_1_organizational_problem.md        (7.5.1)
├── ch1_2_literature_and_practice.md       (7.5.2)
├── ch1_3_diagnostic_study.md              (7.5.3)
│
├── ch2_1_methodology_choice.md            (7.5.4)
├── ch2_2_engineering_design_process.md    (7.5.4)
├── ch2_3_phase_by_phase_plan.md           (7.5.4)
│
├── ch3_1_solution_architecture.md         (7.5.5)
├── ch3_2_implementation.md                (7.5.5)
├── ch3_3_1_experimental_setup.md          (7.5.5)
├── ch3_3_2_five_task.md                   (7.5.5)
├── ch3_3_3_ten_task.md                    (7.5.5)
├── ch3_3_4_twenty_task.md                 (7.5.5)
├── ch3_3_5_cross_scale.md                 (7.5.5)
├── ch3_4_effectiveness_evaluation.md      (7.5.5)
│
├── 99_conclusion.md
└── references.bib
```

---

## 00 — Introduction

- Commercial context: AI agents 5-10x cheaper than humans, but 80%+ projects fail, maintenance costs $50-100K/year
- The paradox: TargetAI deploys API-served LLM agents that cannot self-improve post-deployment
- Object: TargetAI's CX automation platform
- Subject: the process of post-deployment AI agent improvement
- Aim: design, implement, and evaluate an automated diagnose-patch-validate framework
- Five project objectives (reframed from H1-H3):
  1. Design an automated framework for teacher-driven prompt evolution
  2. Evaluate on tau2-bench (proxy for TargetAI's domains)
  3. Characterize which failure types respond to prompt-level intervention
  4. Assess scaling behavior and practical boundaries
  5. Produce actionable recommendations for TargetAI's deployment pipeline
- Thesis structure roadmap

**Sources:** `text/ch1_introduction.md` (business context, research gap), `gen_internship_report.py` (TargetAI description)
**New:** Subject/object/aim framing, five objectives as project deliverables, structure roadmap

---

## Chapter 1: Theoretical Foundations and Problem Analysis

### 1.1 — The Organizational Problem (7.5.1) → `ch1_1_organizational_problem.md`

**Sections:**
- TargetAI LLC: company profile, products (Platform, TargetSpeak, TargetSkill), market position in Russian CX automation
- The problem: agents fail on edge cases; failures persist until manually diagnosed and fixed
- Quantified impact: 0.5-3 FTEs and $50-100K/year per deployment for maintenance
- The constraint: API-only model access → no fine-tuning/RLHF
- Subject, object, scope, five research objectives
- Relevance: business ($4.6T market), industry (outcome-based pricing), organizational (TargetAI's margins)

**Reuse ~40%:** `ch1_introduction.md` §1.1-1.6 (business context, implementation tax)
**New:** Expanded TargetAI profile, subject/object/scope, objectives as deliverables

### 1.2 — Literature & Practice Review (7.5.2) → `ch1_2_literature_and_practice.md`

**Sections:**
- **The enterprise agent reliability gap:**
  - Benchmark evidence (tau-bench, tau2-bench): even frontier models fail 30-50% of multi-turn tool-calling tasks
  - Economics of AI agent deployment (cost comparison, failure rates, Klarna case)
  - The maintenance bottleneck: failures persist until manually diagnosed and fixed
- **Approaches to automated prompt/agent improvement** (organized by method, not by company):
  - Static prompting techniques and their ceiling (CoT, ReAct, Tree of Thoughts)
  - Fine-tuning/RLHF: effective but requires weight access, impractical for API-served models
  - Automated prompt optimization: DSPy (prompt compilation), TextGrad (gradient-based), EvoPrompt/PromptBreeder (evolutionary) — all validated on classification/QA, none on multi-turn tool-calling agents
  - Self-reflective agents: Reflexion (Shinn et al. 2023) — proves automated diagnosis works, but reflections are ephemeral (not persisted across episodes)
  - Tool description optimization: Artemis, PLAY2PROMPT — closest to our patch-surface idea, but operate on tool schemas only, no teacher-student setup
  - Knowledge distillation: weight-level (Hinton et al.) vs prompt-level gap — LIMA's superficial alignment hypothesis suggests prompt-level transfer may suffice
- **Synthesis:** conclusions that shape the solution design
  1. Prompt-level optimization is feasible and academically validated
  2. No existing work applies it to multi-turn tool-calling agents
  3. Teacher-student setup enables knowledge transfer without weight access
  4. Three patch surfaces needed (prompt, schema, preprocessor) — each addresses failures that the others cannot

**Reuse ~70%:** `ch2_literature_review.md` (reorganized), `ch1_introduction.md` (condensed arguments)
**New:** Practice-oriented grouping of approaches, synthesized conclusions

### 1.3 — Diagnostic Study (7.5.3) → `ch1_3_diagnostic_study.md`

**Framework choice:** Porter's Five Forces (external) + Value Chain Analysis (internal) + Cost Structure Analysis (quantitative).
Rationale: all three produce conclusions that directly feed into the solution design. No filler quadrants.

**Sections:**
- **Framework selection and justification** — why Porter's Five Forces + Value Chain over SWOT/PESTEL (more analytical rigor, conclusions drive solution requirements)
- **Porter's Five Forces — CX Automation Market:**
  - Buyer power: enterprises can switch vendors, demand SLAs and outcome-based pricing → vendors must automate maintenance to protect margins
  - Supplier power: model providers (OpenAI, Anthropic, open-source via OpenRouter) control API access/pricing; sanctions limit foreign provider availability in Russia → need for model-agnostic solutions
  - Threat of substitutes: in-house prompt engineering teams, fine-tuning services, RLHF-as-a-service → automated prompt evolution must outperform manual alternatives
  - Threat of new entrants: low barrier (API access is commodity), but evaluation infrastructure and domain expertise create moat
  - Industry rivalry: Intercom, Sierra, Yandex, Sber AI competing on agent quality and cost → maintenance automation is a competitive differentiator
  - **Conclusion:** structural competitive pressure demands automated agent improvement; manual maintenance is unsustainable at scale
- **Value Chain Analysis — TargetAI's Service Delivery:**
  - Primary activities: Model Selection → Agent Configuration → Deployment → Monitoring → **Maintenance (bottleneck)** → Client Reporting
  - Support activities: Evaluation infrastructure, benchmark development, API routing (litellm/OpenRouter)
  - The bottleneck: maintenance is the only primary activity that scales linearly with deployments (0.5-3 FTEs per client)
  - **Conclusion:** the DPV framework targets the single highest-cost, lowest-automation activity in the chain
- **Cost Structure Analysis:**
  - Current: $50-100K/year per deployment for manual diagnosis-fix-test cycles
  - Proposed: teacher model API cost per evolution sweep (estimate from actual token usage)
  - Cost structure shift: linear (per-incident, per-deployment) → near-fixed (compute)
  - **Conclusion:** quantified justification for the framework's economic viability
- **Synthesis:** Five Forces shows the market demands this; Value Chain shows where it fits; Cost analysis shows it's economically viable

**Reuse ~30%:** `ch2_literature_review.md` §2.1.1 (market data, competitive landscape), `ch5_conclusion.md` (practical implications, cost arguments)
**New:** Porter's Five Forces structure, Value Chain mapping of TargetAI's operations, cost structure quantification

---

## Chapter 2: Implementation Methodology

### 2.1 — Methodology Choice and Rationale → `ch2_1_methodology_choice.md`

Compare three candidates relevant to building and evaluating a software framework:

| Methodology | Focus | Fit |
|-------------|-------|-----|
| Design Science Research (Hevner et al. 2004) | IT artifacts evaluated rigorously | Strong theoretical grounding, but prescribes artifact taxonomy and knowledge contribution framing that exceeds thesis scope |
| CRISP-DM | Data mining/ML model lifecycle | Deliverable is a framework, not a trained model — CRISP-DM phases (data prep, modelling) don't map to the work |
| **Engineering Design Process** | **Engineering artifacts via iterative design-test cycles** | **Best fit: deliverable is a software framework; iterative test→redesign mirrors the evolution loop; emphasizes requirements and alternative evaluation** |

Justification: EDP places the engineering artifact at center, is explicitly iterative, and its test→redesign cycle directly mirrors the framework's own evolve→evaluate loop. Design Science Research provides theoretical grounding (the framework as a design artifact) but EDP is the operational methodology.

**Reuse ~30%:** `ch3_methodology.md` §3.1 (design science rationale)
**New:** Comparison table with domain-relevant alternatives, rationale for each

### 2.2 — The Engineering Design Process → `ch2_2_engineering_design_process.md`

Description of the 7-phase EDP methodology:
1. Define the Problem
2. Do Background Research
3. Specify Requirements
4. Brainstorm, Evaluate, and Choose Solution
5. Develop and Prototype Solution
6. Test Solution
7. Communicate Results

Iterative nature: test results feed back to design refinement. Reference to Dym et al. (2005), ABET criteria.

**New:** Methodology description (not in current thesis)

### 2.3 — Phase-by-Phase Implementation Plan → `ch2_3_phase_by_phase_plan.md`

| EDP Phase | Project Activity | Output |
|-----------|-----------------|--------|
| 1. Define Problem | TargetAI's maintenance bottleneck | Ch1 §1.1 |
| 2. Background Research | Literature review + diagnostics | Ch1 §1.2-1.3 |
| 3. Specify Requirements | API-only, auditable, reversible, measurable improvement | Requirements spec |
| 4. Brainstorm/Evaluate/Choose | Decision matrix: manual prompt eng. vs fine-tuning vs RLHF vs self-reflection vs teacher-driven evolution | Solution selection with rationale |
| 5. Develop Prototype | DPV framework: outer/inner loops, 3 patch surfaces, 2-phase escalation | Framework implementation |
| 6. Test | tau2-bench experiments: 3 scales × 3 models, statistical analysis | Ch3 §3.3 |
| 7. Communicate | Thesis + TargetAI recommendations | Ch3 §3.4-3.5 |

Design science grounding (Hevner et al. 2004): the framework as a design artifact evaluated against baseline + frontier.

**Reuse ~50%:** `ch3_methodology.md` §3.2-3.4, 3.8-3.10 (benchmark selection, conditions, metrics)
**New:** Phase mapping, decision matrix for Phase 4

---

## Chapter 3: Development and Evaluation

### 3.1 — Solution Architecture → `ch3_1_solution_architecture.md`

- Outer loop: evaluate all tasks → extract failures → parallel teacher fix → merge patches → re-evaluate
- Inner loop: per-failure reflect-validate with two-phase escalation (teaching → guardrails)
- Three patch surfaces: system prompt, tool schemas, tool preprocessors
- Failure taxonomy: TOOL_MISUSE, POLICY_VIOLATION, REASONING_ERROR, COMMUNICATION_ERROR
- Quality assurance: unanimous validation, LLM-based deduplication, state persistence and rollback

**Reuse ~90%:** `ch3_methodology.md` §3.5-3.7 (framework architecture, patch surfaces, taxonomy)

### 3.2 — Implementation → `ch3_2_implementation.md`

- Technology stack: Python 3.12, tau2-bench, litellm, OpenAI SDK, OpenRouter
- Benchmark: tau2-bench airline domain (50 tasks, 30 training), binary pass/fail
- Models: Student (Qwen3 30B-A3B), Teacher (Kimi K2.5), Simulator (Qwen3 30B-A3B)
- Experimental conditions: Baseline (B), Evolved (K), Frontier (F)
- Three scales: 5, 10, 20 tasks × three student models
- Metrics: trial pass rate, majority-vote pass rate, fix rate, gap closure
- Reproducibility: seeds, parallelism config, trial count

**Reuse ~90%:** `ch3_methodology.md` §3.2-3.4, 3.8-3.10

### 3.3 — Results (split into subchapter files)

Results are split from the monolithic `ch3_3_results.md` into individual sub-files:

#### 3.3.1 — Experimental Setup → `ch3_3_1_experimental_setup.md`
- Three student models (Qwen3 30B-A3B, Qwen3.5 Flash, GLM 4.7 Flash), teacher (Kimi K2.5), simulator
- Three scales (5, 10, 20 tasks), evaluation protocol (3 trials, majority vote, seed 42)
- Conditions table across scales and models

#### 3.3.2 — Five-Task Evaluation → `ch3_3_2_five_task.md`
- Qwen3: 53%→73% (+20pp), GLM: 47%→73% then catastrophic regression in sweep 3
- Qwen3.5: 100% baseline (ceiling effect)
- Comparative analysis at five tasks

#### 3.3.3 — Ten-Task Experiments → `ch3_3_3_ten_task.md`
- Qwen3: 27%→50% (+23pp), fix rate 100%→56%, resistant tasks (7, 9, 11, 12)
- Qwen3.5: evolution trajectory + regression in sweep 3
- GLM: framework fails — why it's dropped at 20 tasks
- Comparative analysis at ten tasks

#### 3.3.4 — Twenty-Task Experiments → `ch3_3_4_twenty_task.md`
- Qwen3 and Qwen3.5 at 20 tasks
- Scaling observations, cross-task benefits and regression
- Comparative analysis at twenty tasks

#### 3.3.5 — Cross-Scale and Cross-Model Comparison → `ch3_3_5_cross_scale.md`
- Scaling curves per model
- Cross-model comparison at matched scales
- Instruction vs guardrail ratio across all experiments
- Saturation analysis

**Reuse ~95%:** `ch4_results.md` (all experimental results), reorganized from monolithic `ch3_3_results.md`

### 3.4 — Effectiveness Evaluation → `ch3_4_effectiveness_evaluation.md`

- **Against project objectives:** map each of the 5 objectives to evidence
- **Economic effectiveness:**
  - Framework cost: teacher API calls per sweep (estimate from actual token usage)
  - vs. manual FTE cost: $50-100K/year → compute cost of ~$X per domain
  - Shift from linear (per-incident) to near-fixed (compute) cost
  - ROI estimation for TargetAI
- **Statistical hypothesis evaluation:** H1 (paired t-test), H2 (Cochran-Armitage), H3 (bootstrap gap closure)
- **Limitations:** single domain, low statistical power, benchmark vs production gap, hard ceiling

- **Recommendations for TargetAI:**
  - Integration into deployment pipeline, phased rollout (shadow mode → human-approved patches → automated)
  - Extend to retail/telecom domains, patch versioning, stronger teachers

**Reuse ~50%:** `ch5_conclusion.md` §5.2-5.6 (findings, implications, limitations, future work)
**New:** Economic ROI analysis, objective-by-objective evaluation, recommendations as part of effectiveness section

---

## 99 — Conclusion → `99_conclusion.md`

- Summary of findings across all 3 chapters
- Contributions (teacher-to-student prompt distillation, first empirical eval on tool-calling benchmark, three patch surfaces, scaling characterization)
- Practical implications for TargetAI
- Directions for further research

**Reuse ~70%:** `ch5_conclusion.md`

---

## Content Reuse Summary

| File | Reuse % | Primary Sources | Key New Content |
|------|---------|-----------------|-----------------|
| 00_introduction | ~40% | ch1 | Subject/object/aim, 5 objectives, roadmap |
| ch1_1 | ~40% | ch1, internship report | TargetAI profile, scope framing |
| ch1_2 | ~70% | ch2, ch1 | Practice-oriented approach grouping, synthesized conclusions |
| ch1_3 | ~30% | ch2 §2.1.1, ch5 | Porter's Five Forces, Value Chain, Cost Analysis |
| ch2_1 | ~30% | ch3 §3.1 | Methodology comparison table |
| ch2_2 | ~0% | — | EDP description (fully new) |
| ch2_3 | ~50% | ch3 §3.2-3.4 | Phase mapping, decision matrix |
| ch3_1 | ~90% | ch3 §3.5-3.7 | Minor reframing |
| ch3_2 | ~90% | ch3 §3.2-3.4, 3.8 | Minor reframing |
| ch3_3_1 | ~95% | ch4, ch3_3_results.md | Experimental setup extracted |
| ch3_3_2 | ~95% | ch4, ch3_3_results.md | Five-task results extracted |
| ch3_3_3 | ~95% | ch4, ch3_3_results.md | Ten-task results extracted |
| ch3_3_4 | ~95% | ch4, ch3_3_results.md | Twenty-task results extracted |
| ch3_3_5 | ~95% | ch4, ch3_3_results.md | Cross-scale comparison extracted |
| ch3_4 | ~50% | ch5 | Economic ROI, objective evaluation, recommendations |
| 99_conclusion | ~70% | ch5 | Reframed for project format |

## Methodology Choice: Engineering Design Process

Selected over Design Science Research (theoretically strong but overly prescriptive for thesis scope) and CRISP-DM (designed for ML model lifecycle, not framework engineering). EDP fits because: (1) deliverable is a software framework, (2) iterative test→redesign mirrors the evolution loop, (3) emphasizes requirements and alternative evaluation.

## Implementation Order

1. Create `text/project_thesis/` folder
2. Write files in order: introduction → ch1_1 → ch1_2 → ch1_3 → ch2_1 → ch2_2 → ch2_3 → ch3_1 → ch3_2 → ch3_3 → ch3_4 → conclusion
3. Copy/adapt `references.bib`

## Verification

- Cross-check all 7.5.x requirements are covered
- Ensure experimental results are accurately represented
- Verify Five Forces/Value Chain data sourced from existing thesis where possible
- Confirm EDP phases map cleanly to actual work done
- Compare structure against credit scoring exemplar for consistency
