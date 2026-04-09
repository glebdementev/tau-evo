# 2.2 The Engineering Design Process

This section describes the Engineering Design Process methodology and its application to the present project. Section 2.2.1 introduces the seven-phase EDP model. Section 2.2.2 discusses the iterative nature of the process.

## 2.2.1 The Seven-Phase Model

The Engineering Design Process is a systematic, iterative methodology for developing engineering solutions to defined problems [@dym2005]. It is widely used in engineering education and practice, recognized by ABET accreditation criteria, and provides a structured yet flexible framework for projects where the deliverable is a functional artifact evaluated against measurable requirements.

The EDP consists of seven phases:

1. **Define the Problem.** Clearly articulate the problem to be solved, including constraints, stakeholders, and success criteria. The problem definition must be specific enough to guide the design process and measurable enough to evaluate the solution.

2. **Do Background Research.** Review existing solutions, relevant literature, available technologies, and prior art. Understand what has been tried, what works, what does not, and why. This phase establishes the knowledge base from which design decisions are made.

3. **Specify Requirements.** Translate the problem definition and background research into concrete requirements that the solution must satisfy. Requirements should be measurable, testable, and prioritized. They constrain the design space and provide the criteria against which the solution will be evaluated.

4. **Brainstorm, Evaluate, and Choose Solution.** Generate multiple candidate solutions, evaluate each against the specified requirements, and select the most promising approach. This phase involves systematic comparison (e.g., decision matrices) rather than ad-hoc selection.

5. **Develop and Prototype Solution.** Implement the chosen solution as a working prototype. The prototype must be functional enough to test against the requirements specified in Phase 3.

6. **Test Solution.** Evaluate the prototype against the requirements using structured tests. Collect data, analyze results, and determine whether the solution meets the success criteria. If not, the process iterates back to earlier phases.

7. **Communicate Results.** Document the design process, test results, conclusions, and recommendations. This includes both the technical documentation of the solution and the communication of findings to stakeholders.

## 2.2.2 Iterative Nature

A defining feature of the EDP is its iterative structure. The process is not strictly linear: test results in Phase 6 may reveal deficiencies that require returning to Phase 4 (choosing a different approach), Phase 5 (modifying the prototype), or even Phase 3 (revising requirements based on what testing reveals is feasible). This iterative loop---design, test, learn, redesign---is what distinguishes engineering design from a waterfall process.

The iterative nature of EDP is particularly well-suited to this project for two reasons:

1. **The framework itself is iterative.** The DPV framework operates through repeated sweeps: evaluate the agent, identify failures, apply patches, re-evaluate. The project methodology mirrors the artifact's operation---both iterate by testing, learning from failures, and improving.

2. **The experimental design evolved during the project.** Initial experiments at 5 tasks informed the design of 10-task experiments, which in turn shaped the 20-task evaluation. The three-model comparison (Qwen3 30B-A3B, Qwen3.5 Flash, GLM 4.7 Flash) was expanded as early results revealed model-dependent behavior. This adaptive experimental design is natural within EDP's iterative framework but would be awkward to justify under a strictly sequential methodology.

@Fig:edp-cycle illustrates the iterative EDP cycle and its application to this project.

![The Engineering Design Process cycle applied to this project. Solid arrows show the primary flow; dashed arrows show iteration paths triggered by test results.](figures/fig_edp_cycle.png){#fig:edp-cycle}
