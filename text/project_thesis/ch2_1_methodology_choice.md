## 2.1 Methodology Choice and Rationale

This section selects and justifies the methodologies used in this project. Two distinct methodological choices are required: (1) a project design methodology that structures the overall work of building and evaluating the framework (Section 2.1.1), and (2) a diagnostic methodology for analyzing the organization's internal and external environment (Section 2.1.2). Section 2.1.3 describes the selected project design methodology in detail.

### 2.1.1 Project Design Methodology

Five methodologies were considered for structuring the project. Each is suited to a different class of technical work; the question is which best fits a project whose deliverable is a software framework evaluated empirically against a benchmark.

TOGAF (The Open Group Architecture Framework) is the most widely used framework for enterprise architecture [@togaf2022]. It provides a comprehensive approach for designing, planning, implementing, and governing enterprise IT architecture, structured around four domains (Business, Application, Data, Technology) and an iterative Architecture Development Method (ADM). TOGAF is designed for multi-system enterprise transformations where the deliverable is an architecture governing multiple interacting systems. However, this project develops and evaluates a single software framework, not an enterprise architecture. The ADM's phases (Architecture Vision, Business Architecture, Information Systems Architecture, Technology Architecture, Migration Planning) do not map to the work of building a prompt-evolution loop and testing it on a benchmark, and TOGAF's scope far exceeds what is needed.

SDLC models (Waterfall, Agile, Scrum) govern the process of delivering production software. Waterfall prescribes sequential phases (requirements, design, implementation, testing, deployment); Agile and Scrum organize work into iterative sprints with continuous delivery and stakeholder feedback. These models structure the software delivery process---sprints, releases, CI/CD pipelines, user stories, backlog management---but this project is not delivering production software to end users; it is building a framework prototype and evaluating it against a benchmark. The project has no deployment phase, no user acceptance testing, and no maintenance releases. SDLC models would govern how the code is written but would not structure the evaluation of the framework as a research artifact---which is the core of the thesis.

Design Science Research (DSR) [@hevner2004; @peffers2007] is a paradigm for creating and evaluating IT artifacts. It prescribes a rigorous process: identify a problem, define objectives, design and develop an artifact, demonstrate it, evaluate it, and communicate results. DSR emphasizes the dual contribution of practical utility (the artifact works) and knowledge contribution (the artifact advances understanding). DSR provides strong theoretical grounding for framing the DPV framework as a design artifact, and its emphasis on evaluation against a baseline aligns with the paired baseline-versus-evolved experimental design. The framework's contribution to knowledge---demonstrating that prompt-level evolution works on multi-turn tool-calling benchmarks---maps naturally to DSR's knowledge contribution requirement. However, DSR prescribes artifact taxonomy, design theory, and formal knowledge contribution framing that exceed the scope of a project-based thesis; the methodology's emphasis on generalizable design theory is more appropriate for research dissertations than for project work aimed at solving a specific organizational problem.

CRISP-DM (Cross-Industry Standard Process for Data Mining) [@chapman2000] is a six-phase methodology for data mining and machine learning projects: business understanding, data understanding, data preparation, modeling, evaluation, and deployment. It is the most widely used methodology in applied ML, well-understood, and provides clear phase boundaries. However, the deliverable of this project is a software framework, not a trained model. CRISP-DM's core phases---data preparation, modeling, hyperparameter tuning---do not map to the work performed here. The DPV framework does not train a model; it edits prompts and tool schemas. Forcing the project into CRISP-DM's phase structure would misrepresent what was actually done.

The Engineering Design Process (EDP) [@dym2005] is a systematic methodology for developing engineering artifacts through iterative design-test cycles. Its seven phases---define the problem, do background research, specify requirements, brainstorm and evaluate solutions, develop and prototype, test, and communicate results---provide a natural structure for building and evaluating a software framework. EDP places the engineering artifact at center. Its iterative test-redesign cycle directly mirrors the DPV framework's own evolve-evaluate loop: both operate by testing, identifying failures, and iterating. EDP emphasizes requirements specification and alternative evaluation, which map to the benchmark selection and paired baseline-versus-evolved experimental design. The methodology is explicitly practical and deliverable-focused, fitting a project-based thesis. Its limitation is the lack of formal knowledge contribution framing of DSR; it does not explicitly prescribe statistical evaluation methods or theoretical positioning.

@Tbl:methodology-comparison summarizes the comparison.

\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.15}
\caption{Methodology comparison for the DPV framework project.\label{tbl:methodology-comparison}}
\begin{tabularx}{\textwidth}{@{}l *{5}{>{\raggedright\arraybackslash}X}@{}}
\toprule
\textbf{Criterion} & \textbf{TOGAF} & \textbf{SDLC (Agile/ Waterfall)} & \textbf{DSR} & \textbf{CRISP-DM} & \textbf{EDP} \\
\midrule
Artifact focus        & Enterprise architecture & Production software     & IT artifacts with theory            & ML models                    & Engineering artifacts \\
Iterative design      & Yes (ADM cycle)         & Yes (sprints/phases)    & Yes (evaluate $\to$ refine)         & Yes (model $\to$ evaluate)   & Yes (test $\to$ redesign) \\
Fit to deliverable    & Poor (enterprise scope) & Poor (delivery process) & Partial (framework, not theory)     & Poor (framework, not model)  & \textbf{Strong} (framework) \\
Requirements emphasis & High (enterprise-level) & Moderate (user stories) & Moderate                            & Low                          & \textbf{High} \\
Evaluation emphasis   & Low (governance focus)  & Low (delivery focus)    & \textbf{High} (artifact evaluation) & High (model metrics)         & \textbf{High} (test against criteria) \\
Practical orientation & Enterprise governance   & Software delivery       & Research-oriented                   & Industry-oriented            & \textbf{Project-oriented} \\
Thesis scope fit      & Far exceeds scope       & Misaligned focus        & Exceeds scope                       & Misaligned phases            & \textbf{Appropriate scope} \\
\bottomrule
\end{tabularx}
\end{table}

Selected methodology: Engineering Design Process.

The selection is justified on three grounds:

1. **Deliverable alignment.** The project's deliverable is a software framework (the DPV loop), not an enterprise architecture (TOGAF), production software (SDLC), a trained model (CRISP-DM), or a generalizable design theory (DSR). EDP is designed for exactly this class of artifact: an engineered system that must meet specified requirements and be evaluated against measurable criteria.

2. **Structural mirror.** The EDP's test-redesign cycle directly mirrors the framework's own operation. The framework iterates by evaluating agents, identifying failures, and applying patches; the project methodology iterates by prototyping the framework, testing it on benchmarks, and refining the design. This structural alignment means the methodology description naturally explains the work that was actually done.

3. **Scope appropriateness.** EDP provides sufficient rigor for a project-based thesis without the theoretical apparatus (artifact taxonomy, design theory formalization, knowledge base contribution) that DSR would require, the enterprise governance scope of TOGAF, or the delivery-process focus of SDLC. Design science provides useful grounding---the framework is a design artifact evaluated against an explicit baseline---but EDP is the operational methodology that structures the actual work.

The design science perspective is not discarded; it informs the evaluation design (paired baseline-versus-intervention comparison per @hevner2004's evaluation guideline). But the project follows EDP as its primary methodology, with design science as a complementary theoretical lens.

### 2.1.2 Diagnostic Methodology

Section 7.5.3 of the thesis requirements calls for a diagnostic study of the organization's internal and external environment. Three analytical frameworks were considered for this purpose.

SWOT analysis identifies an organization's Strengths, Weaknesses, Opportunities, and Threats by examining internal capabilities and external factors [@humphrey2005]. It is the most widely taught strategic analysis tool. However, SWOT is descriptive rather than analytical: it classifies observations into four quadrants but does not generate causal relationships or directional conclusions. The framework's output---lists of strengths, weaknesses, opportunities, and threats---does not directly constrain solution design. SWOT is also commonly criticized for subjectivity: the same observation can be classified as a strength or weakness depending on framing [@helms2010]. For a project that needs the diagnostic study to produce specific requirements for the technical solution, SWOT's output is too open-ended.

PESTEL analysis scans the macro-environment across six dimensions: Political, Economic, Social, Technological, Environmental, and Legal factors [@aguilar1967]. It is designed for understanding the broad external context in which an organization operates, typically for market entry or strategic planning decisions. PESTEL's breadth is a liability when the problem is already well-scoped. The organizational problem---*target ai*'s agent maintenance bottleneck---is an internal operational issue driven by technology and economics, not by political, environmental, or legal factors. A PESTEL analysis would produce tangential observations (e.g., Russian data localization laws, environmental impact of compute) that do not constrain the solution design. The framework is more suitable for market entry analysis than for diagnosing a specific value-chain bottleneck.

Porter's Five Forces [@porter1980] analyzes industry structure through five competitive forces (buyer power, supplier power, substitutes, new entrants, rivalry). Porter's Value Chain Analysis [@porter1985] decomposes a firm's activities into value-creating and supporting activities, identifying where competitive advantage or disadvantage originates. Cost structure analysis quantifies the unit economics of current versus proposed operations. The three frameworks operate at complementary levels of abstraction---industry structure, firm operations, and unit economics---and each produces conclusions that directly constrain the solution requirements developed in Section 2.2.

@Tbl:diagnostic-comparison summarizes the comparison.

\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.15}
\caption{Diagnostic methodology comparison.\label{tbl:diagnostic-comparison}}
\begin{tabularx}{\textwidth}{@{}l
  >{\hsize=0.8\hsize\raggedright\arraybackslash}X
  >{\hsize=0.8\hsize\raggedright\arraybackslash}X
  >{\hsize=1.4\hsize\raggedright\arraybackslash}X@{}}
\toprule
\textbf{Criterion} & \textbf{SWOT} & \textbf{PESTEL} & \textbf{Porter's Five Forces + VCA + Cost Analysis} \\
\midrule
Output type             & Descriptive lists                & Environmental scan               & \textbf{Causal conclusions} \\
Analytical rigor        & Low (subjective classification)  & Moderate (structured dimensions) & \textbf{High} (structural analysis) \\
Fit to problem scope    & Generic (any organization)       & Macro-level (market entry)       & \textbf{Targeted} (industry + firm + economics) \\
Solution design linkage & Indirect                         & Indirect                         & \textbf{Direct} (each conclusion constrains a requirement) \\
Level of abstraction    & Single (internal/external)       & Single (macro-environment)       & \textbf{Three levels} (industry, firm operations, unit economics) \\
\bottomrule
\end{tabularx}
\end{table}

Selected diagnostic methodology: Porter's Five Forces combined with Value Chain Analysis and Cost Structure Analysis.

The selection is justified on two grounds:

1. **Actionable output.** Each framework produces conclusions that directly feed into the solution requirements: Five Forces establishes that the market demands automated agent improvement; Value Chain Analysis identifies maintenance as the single binding constraint on profitable scaling; Cost Structure Analysis quantifies the economic viability threshold. SWOT and PESTEL produce observations that would require additional interpretation to derive requirements.

2. **Complementary levels of abstraction.** The three frameworks cover industry structure (external), firm operations (internal), and unit economics (quantitative) without redundancy or filler quadrants. This provides the complete diagnostic arc from market context to investment justification that the thesis requires, while remaining focused on the specific problem.

The diagnostic frameworks are applied in Chapter 1, Section 1.3.

### 2.1.3 The Engineering Design Process

The Engineering Design Process is a systematic, iterative methodology for developing engineering solutions to defined problems [@dym2005]. It is widely used in engineering education and practice, recognized by ABET accreditation criteria, and provides a structured yet flexible framework for projects where the deliverable is a functional artifact evaluated against measurable requirements.

The EDP consists of seven phases:

1. **Define the Problem.** Clearly articulate the problem to be solved, including constraints, stakeholders, and success criteria. The problem definition must be specific enough to guide the design process and measurable enough to evaluate the solution.

2. **Do Background Research.** Review existing solutions, relevant literature, available technologies, and prior art. Understand what has been tried, what works, what does not, and why. This phase establishes the knowledge base from which design decisions are made.

3. **Specify Requirements.** Translate the problem definition and background research into concrete requirements that the solution must satisfy. Requirements should be measurable, testable, and prioritized. They constrain the design space and provide the criteria against which the solution will be evaluated.

4. **Brainstorm, Evaluate, and Choose Solution.** Generate multiple candidate solutions, evaluate each against the specified requirements, and select the most promising approach. This phase involves systematic comparison (e.g., decision matrices) rather than ad-hoc selection.

5. **Develop and Prototype Solution.** Implement the chosen solution as a working prototype. The prototype must be functional enough to test against the requirements specified in Phase 3.

6. **Test Solution.** Evaluate the prototype against the requirements using structured tests. Collect data, analyze results, and determine whether the solution meets the success criteria. If not, the process iterates back to earlier phases.

7. **Communicate Results.** Document the design process, test results, conclusions, and recommendations. This includes both the technical documentation of the solution and the communication of findings to stakeholders.

A defining feature of the EDP is its iterative structure. The process is not strictly linear: test results in Phase 6 may reveal deficiencies that require returning to Phase 4 (choosing a different approach), Phase 5 (modifying the prototype), or even Phase 3 (revising requirements based on what testing reveals is feasible). This iterative loop---design, test, learn, redesign---is what distinguishes engineering design from a waterfall process.

The iterative nature of EDP is particularly well-suited to this project for two reasons:

1. **The framework itself is iterative.** The DPV framework operates through repeated sweeps: evaluate the agent, identify failures, apply patches, re-evaluate. The project methodology mirrors the artifact's operation---both iterate by testing, learning from failures, and improving.

2. **The experimental design evolved during the project.** Initial experiments at 5 tasks informed the design of 10-task experiments, which in turn shaped the 20-task evaluation. The three-model comparison (Qwen3 30B-A3B, Qwen3.5 Flash, GLM 4.7 Flash) was expanded as early results revealed model-dependent behavior. This adaptive experimental design is natural within EDP's iterative framework but would be awkward to justify under a strictly sequential methodology.

@Fig:edp-cycle illustrates the iterative EDP cycle and its application to this project.

![The Engineering Design Process cycle applied to this project. Solid arrows show the primary flow; dashed arrows show iteration paths triggered by test results.](figures/fig_edp_cycle.png){#fig:edp-cycle}
