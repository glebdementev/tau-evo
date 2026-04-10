# 2.2 Phase-by-Phase Implementation Plan

This section maps each phase of the Engineering Design Process to the specific project activities performed in this thesis, demonstrating how the methodology was applied in practice. @Tbl:edp-mapping provides the complete mapping; each phase is then discussed in detail.

| EDP Phase | Project Activity | Output | Thesis Location |
|-----------|-----------------|--------|-----------------|
| 1. Define Problem | Diagnose target ai's systems-analyst bottleneck on the TOS line | Problem statement and scope | Chapter 1, Section 1.1 |
| 2. Background Research | Literature review + diagnostic study | Knowledge base and market analysis | Chapter 1, Sections 1.2--1.3 |
| 3. Specify Requirements | Derive requirements from problem and research | Requirements specification | Section 2.2.3 below |
| 4. Brainstorm/Evaluate/Choose | Compare solution alternatives via decision matrix | Solution selection with rationale | Section 2.2.4 below |
| 5. Develop Prototype | Implement the DPV framework | Working framework in Python | Chapter 2, Sections 2.3--2.4 |
| 6. Test | Run $\tau^2$-bench experiments across 3 scales $\times$ 3 models | Experimental results | Chapter 3, Section 3.1 |
| 7. Communicate | Thesis document + target ai recommendations | This thesis + management roadmap | Chapter 3, Sections 3.2--3.3 |

: Mapping of EDP phases to project activities. {#tbl:edp-mapping}

## 2.2.1 Phase 1: Define the Problem

The problem was defined through analysis of target ai's operational context (Section 1.1): the TOS line's delivery model depends on a team of specialized systems analysts who translate customer requirements into agent prompts and tool schemas, and the same scarce headcount must absorb every downstream policy change, so the cost of aligning agents to customer preferences scales linearly with the number of deployments. The constraint --- API-only model access --- rules out weight-modification approaches. Five project objectives were formulated to address this problem (Section 1.1.6).

## 2.2.2 Phase 2: Background Research

Background research comprised two activities. The literature and practice review (Section 1.2) surveyed six approaches to agent improvement---static prompting, fine-tuning/RLHF, automated prompt optimization, self-reflective agents, tool description optimization, and knowledge distillation---and identified the gap: no existing method combines teacher-driven diagnosis with prompt-level patching validated on a multi-turn tool-calling benchmark. The diagnostic study (Section 1.3) applied the diagnostic frameworks selected in Section 2.1.2---Porter's Five Forces, Value Chain Analysis, and Cost Structure Analysis---to establish the competitive necessity and economic viability of the proposed solution.

## 2.2.3 Phase 3: Specify Requirements

The problem definition, literature review, and diagnostic study converge on seven requirements that the solution must satisfy:

| # | Requirement | Source | Testable Criterion |
|---|------------|--------|-------------------|
| 1 | **API-only compatibility.** The framework must operate without access to model weights---no fine-tuning, no RLHF, no gradient computation. | Section 1.1.4 (constraint), Section 1.2.2 (fine-tuning impracticality), Section 1.3.4 | All patches modify only prompt text, tool schemas, or preprocessor code; no weight files are created or modified. |
| 2 | **Auditability and reversibility.** All changes must be human-readable, versionable, and rollback-able. | Section 1.3.1 (buyer SLA requirements), Section 1.2.2 (alignment tax irreversibility) | Every patch is logged with rationale; the evolved state is serialized to JSON; any prior state can be restored. |
| 3 | **Measurable improvement.** The framework must produce statistically detectable improvement on a recognized benchmark. | Section 1.1.6 (Objective 2), Section 1.2.3 (Conclusion 4) | Pass rate on $\tau^2$-bench increases from baseline to evolved condition, evaluated with paired statistical tests. |
| 4 | **Multi-surface patching.** The framework must address failures across prompt, tool schema, and tool preprocessing surfaces. | Section 1.2.3 (Conclusion 4) | Successful fixes are recorded across at least two distinct patch surfaces. |
| 5 | **Scalability characterization.** The framework's behavior must be characterized across increasing task-pool sizes. | Section 1.1.6 (Objective 4) | Experiments run at 5, 10, and 20 tasks with fix rate and improvement tracked at each scale. |
| 6 | **Model-agnostic operation.** The framework must work across multiple LLM providers and model families without architectural changes. | Section 1.3.1 (supplier power, geopolitical access constraints) | Experiments run on multiple student model families (Qwen3, Qwen3.5, GLM 4.7) through the same routing layer; no model-specific code paths in the evolution loop. |
| 7 | **Per-deployment cost reduction.** The framework's per-deployment maintenance cost must be lower than the manual baseline of \$50,000--\$100,000/year. | Section 1.3.3 (cost structure analysis) | Token-based cost of an evolution sweep, multiplied by expected sweep frequency, falls below the manual FTE cost (evaluated in Section 3.2.2). |

: Solution requirements derived from problem analysis and background research. {#tbl:requirements}

## 2.2.4 Phase 4: Brainstorm, Evaluate, and Choose Solution

Five candidate approaches to automating agent improvement were considered. @Tbl:decision-matrix evaluates each against the seven requirements; column numbers correspond to the rows of @tbl:requirements above.

| Approach | 1 | 2 | 3 | 4 | 5 | 6 | 7 | Verdict |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---------|
| Manual prompt engineering | Yes | Yes | Yes | Yes | Yes | Yes | **No** | Baseline practice; cost does not scale |
| Fine-tuning (SFT/LoRA) | **No** | No | Yes | No | Yes | **No** | Yes | Requires weight access |
| RLHF/DPO | **No** | No | Yes | No | Yes | **No** | Yes | Requires weight access + preference data |
| Self-reflective evolution (Reflexion-style) | Yes | Partial | Untested | No | Unknown | Yes | Yes | Ephemeral; no teacher supervision |
| **Teacher-driven DPV framework** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | Selected |

: Decision matrix evaluating candidate approaches against requirements. {#tbl:decision-matrix}

**Fine-tuning and RLHF** are eliminated by the API-only constraint: target ai cannot access model weights. They also fail the model-agnostic requirement, since model-specific weights cannot be ported across providers. Even if weight access were available, the alignment tax [@lin2024; @young2026]---degradation of general capabilities under weight modification---and catastrophic forgetting [@luo2023] make these approaches incompatible with reversibility.

**Manual prompt engineering** satisfies all requirements except cost reduction: it works, but at a per-deployment cost that scales linearly with the client base (Section 1.3.3), making it the problem rather than the solution.

**Self-reflective evolution** (Reflexion-style) is API-only and model-agnostic but only partially auditable (reflections are ephemeral, not persisted as auditable patches), and has not been validated on multi-turn tool-calling benchmarks. It also operates on a single surface and uses the agent's own capabilities for diagnosis, limiting diagnostic quality to the agent's own level.

**The teacher-driven DPV framework** satisfies all seven requirements:

- *API-only compatibility:* operates entirely in the input space; no weights are modified.
- *Auditability and reversibility:* all patches are human-readable text edits serialized to JSON with a full audit trail.
- *Measurable improvement:* evaluated on $\tau^2$-bench with statistical analysis.
- *Multi-surface patching:* three distinct patch surfaces (system prompt, tool schemas, tool preprocessors).
- *Scalability characterization:* evaluated at 5, 10, and 20 tasks with scaling behavior characterized.
- *Model-agnostic operation:* validated across three student model families (Qwen3, Qwen3.5, GLM 4.7) through a single routing layer.
- *Per-deployment cost reduction:* per-deployment cost dominated by API token consumption, several orders of magnitude below the manual FTE baseline at current pricing (quantified in Section 3.2.2).

The framework also incorporates a design science element: the paired baseline-versus-evolved experimental design follows @hevner2004's evaluation guideline of demonstrating improvement over an explicit baseline.

## 2.2.5 Phases 5--7: Prototype, Test, and Communicate

Phases 5--7 are documented primarily in the chapters they produce; this section records only what is specific to the EDP mapping. **Phase 5** (Develop and Prototype): the framework was implemented in Python 3.12 using $\tau^2$-bench as the evaluation substrate, with architecture and implementation details presented in Sections 2.3 and 2.4. **Phase 6** (Test): testing comprised eight experiments across three scales (5, 10, 20 tasks) and three student models (Qwen3 30B-A3B, Qwen3.5 Flash, GLM 4.7 Flash), reported in Chapter 3, Section 3.1. The iterative nature of EDP is visible in the experimental design: results at 5 tasks informed the 10-task experimental design, and the GLM 4.7 Flash failure at 10 tasks led to the decision to drop it from the 20-task evaluation. **Phase 7** (Communicate): communication takes three forms---this thesis document, the effectiveness evaluation against project objectives (Section 3.2), and the management roadmap for integration into target ai's operations (Section 3.2.5).
