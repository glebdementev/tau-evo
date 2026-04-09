# 2.1 Methodology Choice and Rationale

This section selects and justifies the project methodology. Section 2.1.1 reviews three candidate methodologies relevant to designing and evaluating a software framework. Section 2.1.2 presents the selection rationale.

## 2.1.1 Candidate Methodologies

Three methodologies were considered for this project. Each is well-suited to a different class of technical work; the question is which best fits a project whose deliverable is a software framework evaluated empirically against a benchmark.

### Design Science Research (DSR)

Design Science Research [@hevner2004; @peffers2007] is a paradigm for creating and evaluating IT artifacts. It prescribes a rigorous process: identify a problem, define objectives, design and develop an artifact, demonstrate it, evaluate it, and communicate results. DSR emphasizes the dual contribution of practical utility (the artifact works) and knowledge contribution (the artifact advances understanding).

**Strengths for this project:** DSR provides strong theoretical grounding for framing the DPV framework as a design artifact. Its emphasis on evaluation against a baseline aligns with the three-condition experimental design (baseline, evolved, frontier). The framework's contribution to knowledge---demonstrating that prompt-level evolution works on multi-turn tool-calling benchmarks---maps naturally to DSR's knowledge contribution requirement.

**Limitations for this project:** DSR prescribes artifact taxonomy, design theory, and formal knowledge contribution framing that exceed the scope of a project-based thesis. The methodology's emphasis on generalizable design theory is more appropriate for research dissertations than for project work aimed at solving a specific organizational problem.

### CRISP-DM

The Cross-Industry Standard Process for Data Mining (CRISP-DM) [@chapman2000] is a six-phase methodology for data mining and machine learning projects: business understanding, data understanding, data preparation, modeling, evaluation, and deployment. It is the most widely used methodology in applied ML.

**Strengths for this project:** CRISP-DM is well-understood, widely cited, and provides clear phase boundaries.

**Limitations for this project:** The deliverable of this project is a software framework, not a trained model. CRISP-DM's core phases---data preparation, modeling, hyperparameter tuning---do not map to the work performed here. The DPV framework does not train a model; it edits prompts and tool schemas. Forcing the project into CRISP-DM's phase structure would misrepresent what was actually done.

### Engineering Design Process (EDP)

The Engineering Design Process [@dym2005] is a systematic methodology for developing engineering artifacts through iterative design-test cycles. Its seven phases---define the problem, do background research, specify requirements, brainstorm and evaluate solutions, develop and prototype, test, and communicate results---provide a natural structure for building and evaluating a software framework.

**Strengths for this project:** EDP places the engineering artifact at center. Its iterative test-redesign cycle directly mirrors the DPV framework's own evolve-evaluate loop: both operate by testing, identifying failures, and iterating. EDP emphasizes requirements specification and alternative evaluation, which map to the benchmark selection and three-condition experimental design. The methodology is explicitly practical and deliverable-focused, fitting a project-based thesis.

**Limitations for this project:** EDP lacks the formal knowledge contribution framing of DSR. It does not explicitly prescribe statistical evaluation methods or theoretical positioning.

## 2.1.2 Methodology Selection

@Tbl:methodology-comparison summarizes the comparison.

| Criterion | Design Science Research | CRISP-DM | Engineering Design Process |
|-----------|----------------------|----------|---------------------------|
| Artifact focus | IT artifacts with theory | ML models | Engineering artifacts |
| Iterative design | Yes (evaluate → refine) | Yes (model → evaluate) | Yes (test → redesign) |
| Fit to deliverable | Partial (framework, not theory) | Poor (framework, not model) | **Strong** (framework) |
| Requirements emphasis | Moderate | Low | **High** |
| Alternative evaluation | Design alternatives | Model alternatives | **Solution alternatives** |
| Practical orientation | Research-oriented | Industry-oriented | **Project-oriented** |
| Thesis scope fit | Exceeds scope | Misaligned phases | **Appropriate scope** |

: Methodology comparison for the DPV framework project. {#tbl:methodology-comparison}

**Selected methodology: Engineering Design Process.**

The selection is justified on three grounds:

1. **Deliverable alignment.** The project's deliverable is a software framework (the DPV loop), not a trained model (CRISP-DM) or a generalizable design theory (DSR). EDP is designed for exactly this class of artifact: an engineered system that must meet specified requirements and be evaluated against measurable criteria.

2. **Structural mirror.** The EDP's test-redesign cycle directly mirrors the framework's own operation. The framework iterates by evaluating agents, identifying failures, and applying patches; the project methodology iterates by prototyping the framework, testing it on benchmarks, and refining the design. This structural alignment means the methodology description naturally explains the work that was actually done.

3. **Scope appropriateness.** EDP provides sufficient rigor for a project-based thesis without the theoretical apparatus (artifact taxonomy, design theory formalization, knowledge base contribution) that DSR would require. Design science provides useful grounding---the framework is a design artifact evaluated against a baseline and ceiling---but EDP is the operational methodology that structures the actual work.

The design science perspective is not discarded; it informs the evaluation design (three-condition floor-intervention-ceiling comparison per @hevner2004's evaluation guideline). But the project follows EDP as its primary methodology, with design science as a complementary theoretical lens.
