# 4. Results

This chapter presents the experimental results. Section 4.1 describes the shared experimental setup. Sections 4.2--4.4 report the results for three experiments at increasing task-set sizes (5, 10, and 20 tasks), designed to test whether the evolution framework's gains hold as the evaluation surface grows. Section 4.5 compares results across experiments, and Section 4.6 discusses implications and limitations.

## 4.1 Experimental Setup

All experiments use the airline domain of τ²-bench with the configuration described in Section 3.9. The student model is Qwen3 30B-A3B in non-thinking mode, the teacher is Kimi K2.5, and the user simulator is Qwen3 30B-A3B. Each experiment runs the evolution loop for up to three sweeps with up to two retries per failed task per sweep. Every task is evaluated with three trials to capture stochastic variation; a task is considered passing in a given sweep if it passes in at least two of three trials (majority vote). The seed is fixed at 42 throughout. Task IDs are locked after the first evaluation so that pass-rate changes between sweeps reflect the effect of accumulated patches, not sampling variation.

The three experiments differ only in the number of tasks drawn from the airline domain:

| Experiment | Tasks | Task IDs | Status |
|------------|-------|----------|--------|
| 1 | 5 | 0, 1, 3, 4, 5 | Complete |
| 2 | 10 | TBD | In progress |
| 3 | 20 | TBD | Planned |

: Experimental conditions. All other parameters are identical across experiments.

The scaling sequence is deliberate. If the evolution framework captures task-specific fixes that do not generalise, then gains should be largest when the task set is smallest---each fix represents a larger share of the total---and should diminish as the denominator grows. If, on the other hand, the teacher discovers transferable rules, gains should persist or even compound across larger task sets.

## 4.2 Experiment 1: Five-Task Evolution

### 4.2.1 Baseline Performance

The baseline (Condition B) evaluates the unmodified student on five airline tasks with three trials each. @Tbl:exp1-heatmap shows the per-task, per-trial results across all three sweeps, and @tbl:exp1-passrate summarises pass rates.

| Sweep | Task 0 | Task 1 | Task 3 | Task 4 | Task 5 | Trial pass rate | Majority-vote pass rate |
|-------|--------|--------|--------|--------|--------|-----------------|-------------------------|
| 1 (baseline) | 0/3 | 2/3 | 1/3 | 3/3 | 2/3 | 8/15 (53%) | 3/5 (60%) |
| 2 (after sweep 1 patches) | 1/3 | 2/3 | 2/3 | 3/3 | 3/3 | 11/15 (73%) | 4/5 (80%) |
| 3 (after sweep 2 patches) | 1/3 | 3/3 | 3/3 | 3/3 | 1/3 | 11/15 (73%) | 3/5 (60%) |

: Per-sweep evaluation results for Experiment 1 (5 tasks, airline domain). Each cell shows trial passes out of three. Majority-vote pass rate treats a task as passing if it passes in at least two of three trials. {#tbl:exp1-passrate}

@Fig:exp1-heatmap provides a visual representation of the same data. Each cell represents a single trial; green indicates a pass, red a fail. The heatmap makes the per-task trajectories immediately legible: Task 4's solid green column, Task 0's persistent red, and the progressive greening of Tasks 1 and 3 across sweeps.

![Per-task, per-trial pass/fail heatmap for Experiment 1 across three sweeps. Green cells indicate passing trials, red cells indicate failures. Each task is evaluated three times per sweep; tasks are separated by dotted vertical lines. The progression from sweep 1 (top) to sweep 3 (bottom) visualises the effect of accumulated patches.](figures/fig_r01_sweep_heatmap.svg){#fig:exp1-heatmap}

The baseline is non-trivial: the student already passes 60% of tasks by majority vote without any intervention. This is consistent with the model's strong showing on the Berkeley Function Calling Leaderboard and confirms that the student is not helplessly incapable---the teacher is refining, not teaching from scratch. The headroom for improvement is 40 percentage points (two tasks: 0 and 3).

### 4.2.2 Evolution Trajectory

The evolution loop ran three sweeps. @Tbl:exp1-outcomes shows the per-sweep breakdown of task outcomes during the evolution process.

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 1 | 3 | 1 | 0 |
| 2 | 2 | 2 | 1 | 0 |
| 3 | 3 | 0 | 0 | 2 |

: Per-sweep task outcomes during the evolution loop. "Already passing" means the task passed before the teacher intervened; "Fixed" means the teacher's patches caused the task to pass validation; "Unfixed" means all retry attempts were exhausted without success. {#tbl:exp1-outcomes}

@Fig:exp1-outcomes visualises the same data as a stacked bar chart. The shrinking of the "Fixed" segments and the growth of the "Already passing" segment across sweeps illustrates the diminishing-returns dynamic: each sweep has fewer tasks to fix because previous patches have promoted them to the passing pool.

![Stacked bar chart of per-sweep task outcomes for Experiment 1. Each bar represents one sweep; segments show how many tasks were already passing (green), fixed by instruction patches (orange), fixed by guardrail patches (yellow), or remained unfixed (red). The shift from orange/yellow to green across sweeps reflects accumulated improvement.](figures/fig_r02_sweep_outcomes.svg){#fig:exp1-outcomes}

Sweep 1 is the most productive: all four failing tasks are repaired, three by instruction patches and one by a guardrail preprocessor. The loop achieves 100% fix success rate in sweep 1---every failing task is repaired within the allotted retries. Sweep 2 fixes three of three failing tasks (Tasks 0, 1, and 3 failed again in re-evaluation despite sweep 1 patches, likely due to stochastic variation and the strict majority-vote criterion). Sweep 3 produces no new fixes; the two remaining failures resist further patching.

@Tbl:exp1-fixes details the individual fix attempts, including the teacher's patch tier, retry count, and session cost.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|-------|------|-------------|------|---------|-------------|------------|----------|
| 1 | 3 | Fail → Pass | instruction | 2 | 10 | 3 | 2m 26s |
| 1 | 0 | Fail → Pass | instruction | 2 | 8 | 2 | 2m 33s |
| 1 | 1 | Fail → Pass | instruction | 1 | 15 | 6 | 1m 13s |
| 1 | 5 | Fail → Pass | guardrail | 3 | 44 | 18 | 8m 22s |
| 2 | 0 | Fail → Pass | instruction | 1 | 6 | 2 | 2m 3s |
| 2 | 3 | Fail → Pass | guardrail | 3 | 20 | 6 | 9m 28s |
| 2 | 1 | Fail → Pass | instruction | 2 | 14 | 5 | 7m 32s |

: Individual fix attempts across sweeps in Experiment 1. Tier indicates the escalation phase: "instruction" means the fix was achieved with prompt or schema patches only (Phase 1); "guardrail" means the teacher escalated to tool preprocessors (Phase 2). Attempt is the retry number within the sweep. {#tbl:exp1-fixes}

### 4.2.3 Fix Type Analysis

@Fig:exp1-fix-attempts shows the number of tasks fixed per attempt and tier across sweeps as a grouped bar chart.

![Fix attempts by tier and sweep for Experiment 1. Each group represents one sweep; bars show the number of tasks fixed at each attempt (instruction attempts 1--2, guardrail attempt 3). Sweep 3 has no bars: all retry attempts were exhausted without fixing the two remaining failures.](figures/fig_r03_fix_attempts.svg){#fig:exp1-fix-attempts}

Of seven successful fixes across sweeps 1 and 2, five (71%) were instruction-tier patches and two (29%) were guardrail-tier. This is consistent with the two-phase escalation design (Section 3.5.3): instruction patches are attempted first and succeed most of the time; guardrail preprocessors serve as a fallback for failures that resist prompt-level correction.

Instruction-tier fixes are also cheaper. The median instruction fix took 2 attempts, 10 messages, and 2.5 tool calls; the median guardrail fix took 3 attempts, 32 messages, and 12 tool calls. Guardrail fixes required the teacher to exhaust Phase 1 attempts before escalating to Phase 2, explaining the higher cost. Task 5 in sweep 1 is the most expensive fix in the dataset: 44 messages, 18 tool calls, and over 8 minutes of wall-clock time, suggesting that the underlying failure mode was difficult for the teacher to diagnose at the prompt level and required a defensive code intervention.

The dominance of instruction-tier patches supports the Superficial Alignment Hypothesis [@zhou2023lima]: the student model's failures are primarily failures of instruction following, not of capability. The model *can* perform the required actions---it simply does not know that it should, or in what order. Telling it, in explicit natural language, is sufficient in the majority of cases.

### 4.2.4 Diminishing Returns and Saturation

The trajectory across sweeps shows clear diminishing returns. Sweep 1 fixes 4 of 4 failing tasks (100%). Sweep 2 fixes 3 of 3 (100%, but two of these tasks had already been fixed in sweep 1 and regressed). Sweep 3 fixes 0 of 2 (0%). By sweep 3, the pool of fixable failures is exhausted; the remaining two tasks appear to require interventions beyond what prompt and tool-schema patching can provide---or the specific failure modes interact adversely with existing patches.

This saturation effect is expected on a small task set. With only five tasks, each sweep's patches target a narrow set of failure modes. Once those modes are addressed, the marginal value of further sweeps drops to zero. Whether this saturation persists at larger task-set sizes---or whether more tasks provide more diverse failure signals that keep the teacher productive for longer---is the question that Experiments 2 and 3 address.

### 4.2.5 Patch Interference and Regression

The most notable negative result is the regression of Task 5 between sweeps 2 and 3. In sweep 2, Task 5 passes all three trials (3/3). In sweep 3, it passes only one (1/3). Since no patches targeted Task 5 between sweeps 2 and 3 (it was already passing), the regression is attributable either to stochastic variation or to interference from patches accumulated during sweep 2's fixes of other tasks.

Patch interference is a known risk in prompt optimisation. @sclar2023 showed that meaning-preserving formatting changes can swing accuracy by up to 76 percentage points; meaning-bearing changes---the kind the teacher produces---could interact in unpredictable ways. In this experiment the interference is mild (one task regresses while two others improve), but it highlights a limitation of the greedy, per-task patching strategy: patches are validated against the target task but not against all other tasks, so global side effects go undetected until the next full evaluation.

### 4.2.6 Task-Level Analysis

Task 4 is the easiest: it passes 3/3 in all three sweeps, requiring no intervention. Whatever this task tests, the baseline student already handles it reliably.

Task 0 is the hardest: even after evolution, it never passes more than 1/3 trials. The teacher fixes it in every sweep (it keeps regressing), but the fixes produce only marginal reliability improvement. This suggests that the underlying failure mode is not addressable through instruction-level guidance alone---the student understands what to do but fails stochastically in execution, possibly due to long-horizon planning or multi-step tool-call sequencing that the model handles unreliably regardless of prompt quality.

Tasks 1 and 3 show the clearest improvement arc: from baseline failure (2/3 and 1/3 respectively) to reliable passing (3/3 each in sweep 3). These are the tasks where prompt evolution delivers its intended effect---converting intermittent failures into consistent passes through targeted behavioral rules.

### 4.2.7 Summary

Experiment 1 demonstrates that teacher-driven prompt evolution can improve a weak non-thinking model's performance on τ²-bench tasks. The aggregate trial pass rate rises from 53% (baseline) to 73% (after two sweeps of evolution). Instruction-level patches account for the majority of successful fixes. However, the five-task setting saturates quickly: by sweep 3, no further fixes are possible, and patch interference introduces mild regression. The improvement is real but bounded by the small evaluation surface.

## 4.3 Experiment 2: Ten-Task Evolution

<!-- TEMPLATE: To be filled when 10-task run completes -->

### 4.3.1 Baseline Performance

| Sweep | Trial pass rate | Majority-vote pass rate |
|-------|-----------------|-------------------------|
| 1 (baseline) | —/30 (—%) | —/10 (—%) |
| 2 | —/30 (—%) | —/10 (—%) |
| 3 | —/30 (—%) | —/10 (—%) |

: Per-sweep pass rates for Experiment 2 (10 tasks, airline domain). {#tbl:exp2-passrate}

### 4.3.2 Evolution Trajectory

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | — | — | — | — |
| 2 | — | — | — | — |
| 3 | — | — | — | — |

: Per-sweep task outcomes for Experiment 2. {#tbl:exp2-outcomes}

### 4.3.3 Fix Type Analysis

<!-- Compare instruction vs guardrail ratio to Experiment 1. Does the ratio shift with more tasks? -->

### 4.3.4 Scaling Observations

<!-- Key question: does the per-task improvement rate hold, diminish, or improve with 2x tasks?
     - If improvement is purely task-specific, expect ~same absolute gains but lower percentage improvement
     - If patches transfer across tasks, expect percentage improvement to hold or even improve -->

### 4.3.5 Summary

<!-- Fill after run completes -->

## 4.4 Experiment 3: Twenty-Task Evolution

<!-- TEMPLATE: To be filled if 20-task run is executed -->

### 4.4.1 Baseline Performance

| Sweep | Trial pass rate | Majority-vote pass rate |
|-------|-----------------|-------------------------|
| 1 (baseline) | —/60 (—%) | —/20 (—%) |
| 2 | —/60 (—%) | —/20 (—%) |
| 3 | —/60 (—%) | —/20 (—%) |

: Per-sweep pass rates for Experiment 3 (20 tasks, airline domain). {#tbl:exp3-passrate}

### 4.4.2 Evolution Trajectory

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | — | — | — | — |
| 2 | — | — | — | — |
| 3 | — | — | — | — |

: Per-sweep task outcomes for Experiment 3. {#tbl:exp3-outcomes}

### 4.4.3 Scaling Observations

<!-- At 20 tasks, the denominator is large enough that task-specific fixes have diminishing percentage impact.
     Key questions:
     - Does the teacher discover more general rules when exposed to more diverse failures?
     - Does patch interference worsen with more accumulated patches?
     - What is the fix success rate compared to Experiments 1 and 2? -->

### 4.4.4 Summary

<!-- Fill after run completes -->

## 4.5 Cross-Experiment Comparison

<!-- TEMPLATE: To be filled once Experiments 2 and 3 have data -->

### 4.5.1 Scaling Curve

<!-- Plot: x-axis = number of tasks, y-axis = improvement in pass rate (percentage points).
     Expected pattern: improvement decreases as task count increases, confirming limited generalisation.
     Alternative pattern: improvement holds, suggesting transferable rules. -->

| Experiment | Tasks | Baseline pass rate | Final pass rate | Improvement (pp) | Fix success rate |
|------------|-------|--------------------|-----------------|-------------------|------------------|
| 1 | 5 | 53% | 73% | +20 | 100% (sweep 1--2) |
| 2 | 10 | —% | —% | — | — |
| 3 | 20 | —% | —% | — | — |

: Cross-experiment summary. Improvement is measured in percentage points of trial pass rate. {#tbl:cross-experiment}

### 4.5.2 Instruction vs Guardrail Ratio Across Scales

<!-- Does the dominance of instruction patches hold at larger scales, or do more diverse failures require more guardrails? -->

### 4.5.3 Saturation Analysis

<!-- At what sweep does each experiment saturate? If saturation occurs later with more tasks, the teacher benefits from richer failure signals. -->

## 4.6 Discussion

### 4.6.1 Instruction Patching as the Primary Lever

Across Experiment 1, instruction-level patches account for 71% of successful fixes. The teacher's most effective intervention is not defensive code or schema refinement but simply telling the student, in explicit natural language, what to do. This suggests that the student model's failures are primarily failures of specification, not of capability. The model is able to follow complex multi-step procedures---it was not told to. This finding is consistent with @zhou2023lima's Superficial Alignment Hypothesis and with practical experience in prompt engineering: the gap between a model that fails and one that succeeds is often a single sentence of instruction.

The implication for enterprise deployment is that many agent failures can be addressed through prompt management rather than model retraining or architectural changes. The teacher automates what a human prompt engineer would do manually: observe failures, hypothesise about root causes, add clarifying instructions, and verify that the fix works. The automation is the contribution, not the technique.

### 4.6.2 Limits of Input-Space-Only Evolution

The evolution framework operates entirely in input space: it modifies the prompt, tool schemas, and tool preprocessors, but never touches the model's weights. This is simultaneously its greatest strength (reversible, cheap, no alignment tax) and its ceiling. Some failures cannot be addressed by telling the model what to do, because the model lacks the capability to do it even when correctly instructed. Task 0 in Experiment 1 is illustrative: the teacher fixes it in every sweep, yet it never passes reliably. The fix addresses the specification gap but not the execution gap.

This ceiling is the motivation for future work on multi-agent decomposition. If a single agent cannot reliably execute a complex task despite correct instructions, the task can be decomposed into subtasks that are individually within the agent's capability. The teacher, having diagnosed which tasks resist single-agent patching, is well-positioned to identify decomposition candidates. The evolution framework could be extended to propose not just prompt patches but agent topology changes---adding a verification subagent, splitting a task into retrieval and action phases, or inserting a self-check step. This would move the framework from prompt evolution to architecture evolution, while remaining in input space (no weight changes).

### 4.6.3 Patch Interference

The regression of Task 5 in Experiment 1 highlights a fundamental tension in greedy per-task optimisation: patches are validated locally (against the target task) but applied globally (to all future tasks). A patch that fixes Task 3 may degrade Task 5 if the two tasks require contradictory behavioral rules---for instance, if one requires aggressive tool use and the other requires conservative confirmation steps.

Mitigation strategies include full-suite validation (re-running all tasks after each patch merge, at higher API cost), patch isolation (maintaining per-task prompt overlays rather than a single global prompt), and multi-objective optimisation (the teacher considers impact on all tasks, not just the target). These are left for future work, but the regression observed here is mild enough that the net effect of evolution is still positive.

### 4.6.4 Generalisability

<!-- To be expanded once Experiments 2 and 3 provide data on scaling behaviour.
     Key question: do patches learned from 5 tasks transfer to unseen tasks?
     The current design does not test this directly (all tasks are seen during evolution),
     but the 10-task and 20-task experiments provide indirect evidence:
     if patches from early sweeps help later tasks pass on first evaluation,
     some generalisation is occurring. -->

Experiment 1 alone cannot establish whether prompt evolution generalises beyond the specific tasks it is trained on. The five-task setting is too small to distinguish task-specific memorisation from rule-level learning. The pending experiments at 10 and 20 tasks will provide indirect evidence: if the baseline pass rate in later experiments is higher than in Experiment 1 (despite using the same unmodified student), the improvement is attributable to task selection; if evolved pass rates scale proportionally, the teacher is discovering generalisable rules.
