# 4. Results

This chapter presents the experimental results. Section 4.1 describes the shared experimental setup. Sections 4.2--4.4 report results at increasing task-set sizes (5, 10, and 20 tasks), each comparing three student models---Qwen3 30B-A3B, Qwen3.5 Flash, and GLM 4.7 Flash---to test whether the evolution framework's gains hold as the evaluation surface grows and how baseline student capability affects the framework's value proposition. Section 4.5 compares results across scales and models, and Section 4.6 discusses implications and limitations.

## 4.1 Experimental Setup

All experiments use the airline domain of τ²-bench with the configuration described in Section 3.9. Three student models are evaluated:

- **Qwen3 30B-A3B** (non-thinking mode): a mixture-of-experts model with 30 billion total parameters and 3 billion active. Represents a weak non-thinking student with moderate baseline capability.
- **Qwen3.5 Flash**: a newer-generation model in the Qwen family with substantially stronger instruction following and tool-use capabilities. Represents a stronger non-thinking student to test how baseline capability affects the framework's value.
- **GLM 4.7 Flash**: a dense model from the GLM family with moderate instruction-following capability but distinct architectural characteristics from the Qwen models. Included to test whether the framework generalises beyond a single model family and to provide a third data point for the relationship between baseline capability and evolution effectiveness.

The teacher model is Kimi K2.5 in all experiments, and the user simulator is Qwen3 30B-A3B. Each experiment runs the evolution loop for up to three sweeps with up to two retries per failed task per sweep. Every task is evaluated with three trials to capture stochastic variation; a task is considered passing in a given sweep if it passes in at least two of three trials (majority vote, i.e., task $i$ passes iff $\sum_{t=1}^{3} \mathbb{1}[r_i^{(t)} = 1.0] \geq 2$). The seed is fixed at 42 throughout. Task IDs are locked after the first evaluation so that pass-rate changes between sweeps reflect the effect of accumulated patches, not sampling variation.

The experiments span three scales and eight conditions:

| Scale | Task IDs | Qwen3 30B | Q3.5 Flash | GLM 4.7 |
|-------|----------|-----------|------------|---------|
| 5 | 0, 1, 3, 4, 5 | Done | Done (base only) | Done |
| 10 | 0--5, 7, 9--12 | Done | Done | Done |
| 20 | 0--5, 7, 9--12, 14, 15, 17, 20, 21, 23, 27, 28, 33, 34 | Done | Done | Dropped |

: Experimental conditions across scales and models. All other parameters (teacher, user simulator, seed, sweep count) are identical. GLM 4.7 Flash is dropped at 20 tasks due to poor performance at 10 tasks (see Section 4.3.3). {#tbl:conditions}

The scaling sequence is deliberate. If the evolution framework captures task-specific fixes that do not generalise, then gains should be largest when the task set is smallest---each fix represents a larger share of the total---and should diminish as the denominator grows. The multi-model comparison tests a complementary question: if a stronger student already passes most tasks at baseline, does the framework still provide value, and does it address qualitatively different failure modes? The inclusion of GLM 4.7 Flash tests whether the framework generalises beyond the Qwen model family.

## 4.2 Five-Task Evaluation

### 4.2.1 Qwen3 30B-A3B

#### Baseline and Evolution

The baseline evaluates the unmodified student on five airline tasks with three trials each. @Fig:exp1-heatmap shows the per-task, per-trial results across all three sweeps, and @tbl:exp1-passrate summarises pass rates.

| Sweep | T0 | T1 | T3 | T4 | T5 | Trial rate | Maj. rate |
|-------|-----|-----|-----|-----|-----|------------|-----------|
| 1 (base) | 0/3 | 2/3 | 1/3 | 3/3 | 2/3 | 8/15 (53%) | 3/5 (60%) |
| 2 (post-S1) | 1/3 | 2/3 | 2/3 | 3/3 | 3/3 | 11/15 (73%) | 4/5 (80%) |
| 3 (post-S2) | 1/3 | 3/3 | 3/3 | 3/3 | 1/3 | 11/15 (73%) | 3/5 (60%) |

: Per-sweep evaluation results for Qwen3 30B-A3B on 5 tasks. Each cell shows trial passes out of three. {#tbl:exp1-passrate}

@Fig:exp1-heatmap provides a visual representation of the same data. Each cell represents a single trial; green indicates a pass, red a fail. The heatmap makes the per-task trajectories immediately legible: Task 4's solid green column, Task 0's persistent red, and the progressive greening of Tasks 1 and 3 across sweeps.

![Per-task, per-trial pass/fail heatmap for Qwen3 30B-A3B across three sweeps (5 tasks). Green cells indicate passing trials, red cells indicate failures.](../runs/5/sweep_heatmap_print.svg){#fig:exp1-heatmap}

The baseline is non-trivial: the student already passes 60% of tasks by majority vote without any intervention. This confirms that the student is not helplessly incapable---the teacher is refining, not teaching from scratch. The headroom for improvement is 40 percentage points (two tasks: 0 and 3).

#### Evolution Trajectory

The evolution loop ran three sweeps. @Tbl:exp1-outcomes shows the per-sweep breakdown of task outcomes during the evolution process.

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 1 | 3 | 1 | 0 |
| 2 | 2 | 2 | 1 | 0 |
| 3 | 3 | 0 | 0 | 2 |

: Per-sweep task outcomes during the evolution loop for Qwen3 30B-A3B on 5 tasks. {#tbl:exp1-outcomes}

@Fig:exp1-outcomes visualises the same data as a stacked bar chart. The shrinking of the "Fixed" segments and the growth of the "Already passing" segment across sweeps illustrates the diminishing-returns dynamic.

![Stacked bar chart of per-sweep task outcomes for Qwen3 30B-A3B on 5 tasks.](../runs/5/sweep_outcomes_print.svg){#fig:exp1-outcomes}

Sweep 1 is the most productive: all four failing tasks are repaired, three by instruction patches and one by a guardrail preprocessor. Sweep 2 fixes three of three failing tasks. Sweep 3 produces no new fixes; the two remaining failures resist further patching.

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

: Individual fix attempts for Qwen3 30B-A3B on 5 tasks. {#tbl:exp1-fixes}

#### Fix Type Analysis

@Fig:exp1-fix-attempts shows the number of tasks fixed per attempt and tier across sweeps.

![Fix attempts by tier and sweep for Qwen3 30B-A3B on 5 tasks.](../runs/5/fix_attempts_print.svg){#fig:exp1-fix-attempts}

Of seven successful fixes across sweeps 1 and 2, five (71%) were instruction-tier patches and two (29%) were guardrail-tier. Instruction-tier fixes are also cheaper. The median instruction fix took 2 attempts, 10 messages, and 2.5 tool calls; the median guardrail fix took 3 attempts, 32 messages, and 12 tool calls.

The dominance of instruction-tier patches supports the Superficial Alignment Hypothesis [@zhou2023lima]: the student model's failures are primarily failures of instruction following, not of capability.

#### Patch Interference and Regression

The most notable negative result is the regression of Task 5 between sweeps 2 and 3. In sweep 2, Task 5 passes all three trials (3/3). In sweep 3, it passes only one (1/3). Since no patches targeted Task 5 between sweeps 2 and 3 (it was already passing), the regression is attributable either to stochastic variation or to interference from patches accumulated during sweep 2's fixes of other tasks.

#### Summary

The aggregate trial pass rate rises from 53% (baseline) to 73% (after two sweeps of evolution). Instruction-level patches account for the majority of successful fixes. However, the five-task setting saturates quickly: by sweep 3, no further fixes are possible, and patch interference introduces mild regression.

### 4.2.2 Qwen3.5 Flash

The same five tasks (0, 1, 3, 4, 5) were evaluated with Qwen3.5 Flash as the student model. At baseline, Qwen3.5 Flash achieves a perfect 5/5 majority-vote pass rate (15/15 trials), requiring no evolution intervention. Every task that Qwen3 30B-A3B struggled with---including Task 0 (which never reliably passed even after evolution) and Task 3 (which required multi-sweep patching)---is solved by Qwen3.5 Flash out of the box.

This result establishes a ceiling reference: the five-task airline configuration is within the unassisted capability of a stronger non-thinking model. The evolution framework's contribution on these tasks is to bridge the gap between a weaker model's capability and this ceiling---a gap that a stronger student does not have.

### 4.2.3 GLM 4.7 Flash

#### Baseline and Evolution

@Tbl:glm5-passrate summarises pass rates across sweeps for GLM 4.7 Flash on five tasks. @Fig:glm47-5-heatmap visualises the per-task, per-trial results.

| Sweep | T0 | T1 | T3 | T4 | T5 | Trial rate | Maj. rate |
|-------|-----|-----|-----|-----|-----|------------|-----------|
| 1 (base) | 2/3 | 1/3 | 1/3 | 3/3 | 0/3 | 7/15 (47%) | 2/5 (40%) |
| 2 (post-S1) | 3/3 | 3/3 | 2/3 | 2/3 | 1/3 | 11/15 (73%) | 4/5 (80%) |
| 3 (post-S2) | 1/3 | 2/3 | 1/3 | 2/3 | 1/3 | 7/15 (47%) | 2/5 (40%) |

: Per-sweep evaluation results for GLM 4.7 Flash on 5 tasks. {#tbl:glm5-passrate}

![Per-task, per-trial pass/fail heatmap for GLM 4.7 Flash across three sweeps (5 tasks).](../runs/glm47_5/sweep_heatmap_print.svg){#fig:glm47-5-heatmap}

The baseline is comparable to Qwen3 30B-A3B's: 47% trial rate and 40% majority rate, with Tasks 0 and 4 passing by majority vote. The three failing tasks (1, 3, 5) represent the headroom for evolution.

#### Evolution Trajectory

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 1 | 3 | 0 | 1 |
| 2 | 2 | 0 | 1 | 2 |
| 3 | 0 | 0 | 0 | 5 |

: Per-sweep task outcomes during the evolution loop for GLM 4.7 Flash on 5 tasks. {#tbl:glm5-outcomes}

![Stacked bar chart of per-sweep task outcomes for GLM 4.7 Flash on 5 tasks.](../runs/glm47_5/sweep_outcomes_print.svg){#fig:glm47-5-outcomes}

Sweep 1 fixes three tasks (all instruction-tier): Tasks 1, 5, and 0. Task 3 resists repair. Sweep 2 adds one guardrail fix for Task 4 (which was already passing by majority but had failed during the evolution loop's single-trial check). Sweep 3 produces no new fixes; the evolution loop sees all five tasks as failing, reflecting severe regression.

@Tbl:glm5-fixes details the individual fix attempts.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|-------|------|-------------|------|---------|-------------|------------|----------|
| 1 | 1 | Fail → Pass | instruction | 1 | 8 | 3 | 2m 59s |
| 1 | 5 | Fail → Pass | instruction | 1 | 8 | 3 | 3m 35s |
| 1 | 0 | Fail → Pass | instruction | 1 | 4 | 1 | 5m 0s |
| 1 | 3 | Fail → Fail | --- | --- | 25 | 9 | 6m 5s |
| 2 | 3 | Fail → Fail | --- | --- | 16 | 5 | 3m 10s |
| 2 | 4 | Fail → Pass | guardrail | 3 | 21 | 7 | 3m 16s |
| 2 | 5 | Fail → Fail | --- | --- | 54 | 24 | 7m 23s |

: Individual fix attempts for GLM 4.7 Flash on 5 tasks. {#tbl:glm5-fixes}

![Fix attempts by tier and sweep for GLM 4.7 Flash on 5 tasks.](../runs/glm47_5/fix_attempts_print.svg){#fig:glm47-5-fix-attempts}

Total fixes: 4 (3 instruction, 1 guardrail). Of the three genuinely failing tasks at baseline (1, 3, 5), two were fixed---a 67% fix rate, comparable to Qwen3 30B-A3B's performance.

#### Catastrophic Regression in Sweep 3

The defining result for GLM 4.7 Flash at five tasks is the catastrophic regression between sweeps 2 and 3. The majority pass rate drops from 80% (4/5) to 40% (2/5)---a 40-percentage-point collapse. The trial rate drops from 73% to 47%, returning exactly to the baseline. Tasks 0 and 3, which had improved in sweep 2, revert to their baseline state. Even Task 4, which passed perfectly at baseline (3/3), degrades to 2/3.

This regression is far more severe than anything observed with Qwen3 30B-A3B (which lost only one task between sweeps 2 and 3) or Qwen3.5 Flash at ten tasks (which lost 10 percentage points). It suggests that GLM 4.7 Flash is particularly vulnerable to patch interference: the accumulated patches from sweeps 1 and 2 create conflicting directives that the model cannot reconcile.

#### Summary

GLM 4.7 Flash achieves a strong peak improvement (+40pp majority, +26pp trial at sweep 2), demonstrating that the evolution framework can work with this model. However, the gains are entirely erased by sweep 3, indicating that the model lacks the robustness to maintain improvements under patch accumulation. Task 3 is never fixed across either sweep, remaining the sole resistant task.

### 4.2.4 Comparative Analysis at Five Tasks

| Metric | Qwen3 30B-A3B | Qwen3.5 Flash | GLM 4.7 Flash |
|--------|---------------|---------------|---------------|
| Baseline trial rate | 53% (8/15) | 100% (15/15) | 47% (7/15) |
| Baseline majority rate | 60% (3/5) | 100% (5/5) | 40% (2/5) |
| Best trial rate (post-evo) | 73% (11/15) | 100% (15/15) | 73% (11/15) |
| Best majority rate (post-evo) | 80% (4/5) | 100% (5/5) | 80% (4/5) |
| Sweep 3 majority | 60% (3/5) | 100% (5/5) | 40% (2/5) |
| Evolution needed? | Yes | No | Yes |
| Genuinely failing tasks | 2 | 0 | 3 |
| Fix rate on failing tasks | 100% | N/A | 67% |
| Total fixes (instr/guard) | 7 (5/2) | 0 | 4 (3/1) |

: Five-task comparison across three student models. "Best" refers to the sweep with the highest pass rate. {#tbl:5task-comparison}

Three patterns emerge. First, both weaker models reach the same peak performance (80% majority, 73% trial), suggesting a common ceiling for the five-task setting that prompt evolution can approach but not exceed. Second, the models diverge sharply in their ability to retain gains: Qwen3 30B-A3B holds most of its improvement through sweep 3, while GLM 4.7 Flash collapses back to baseline. Third, Qwen3.5 Flash's perfect baseline confirms that these five tasks are within reach of a sufficiently capable model without any evolution intervention.

## 4.3 Ten-Task Experiments

### 4.3.1 Qwen3 30B-A3B

#### Baseline Performance

Experiment 2 doubles the task set from five to ten, introducing five additional tasks (7, 9, 10, 11, 12). @Fig:exp2-heatmap shows the per-task, per-trial results across all three sweeps, and @tbl:exp2-passrate summarises pass rates.

| Sweep | T0 | T1 | T3 | T4 | T5 | T7 | T9 | T10 | T11 | T12 | Trial rate | Maj. rate |
|-------|-----|-----|-----|-----|-----|-----|-----|------|------|------|------------|-----------|
| 1 (base) | 0/3 | 2/3 | 0/3 | 3/3 | 2/3 | 0/3 | 0/3 | 1/3 | 0/3 | 0/3 | 8/30 (27%) | 3/10 (30%) |
| 2 (post-S1) | 1/3 | 2/3 | 0/3 | 3/3 | 2/3 | 0/3 | 0/3 | 1/3 | 0/3 | 0/3 | 9/30 (30%) | 3/10 (30%) |
| 3 (post-S2) | 3/3 | 3/3 | 2/3 | 3/3 | 3/3 | 0/3 | 0/3 | 1/3 | 0/3 | 0/3 | 15/30 (50%) | 5/10 (50%) |

: Per-sweep evaluation results for Qwen3 30B-A3B on 10 tasks. {#tbl:exp2-passrate}

@Fig:exp2-heatmap visualises the same data. Compared to the five-task heatmap, the ten-task version makes the bifurcation between fixable and resistant tasks immediately visible: a cluster of tasks (0, 1, 3, 4, 5) greens progressively across sweeps, while a second cluster (7, 9, 11, 12) remains solidly red throughout. Task 10 occupies a middle ground---it was fixed during sweep 1's evolution but never passed more than 1/3 trials in re-evaluation, suggesting a fragile fix.

![Per-task, per-trial pass/fail heatmap for Qwen3 30B-A3B across three sweeps (10 tasks).](../runs/10/sweep_heatmap_print.svg){#fig:exp2-heatmap}

The baseline is substantially weaker than in the five-task setting: only 27% of trials pass (8/30), versus 53% (8/15). By majority vote, 3 of 10 tasks pass (30%), versus 3 of 5 (60%). The five tasks shared with the five-task experiment exhibit identical baseline performance, confirming that the seed and configuration reproduce consistently.

#### Evolution Trajectory

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 1 | 4 | 1 | 4 |
| 2 | 1 | 1 | 1 | 7 |
| 3 | 4 | 0 | 0 | 6 |

: Per-sweep task outcomes for Qwen3 30B-A3B on 10 tasks. {#tbl:exp2-outcomes}

@Fig:exp2-outcomes visualises the same data. The persistent red "Unfixed" segment, absent in the five-task sweeps 1 and 2, dominates the chart---reflecting a hard core of tasks that resist prompt-level repair.

![Stacked bar chart of per-sweep task outcomes for Qwen3 30B-A3B on 10 tasks.](../runs/10/sweep_outcomes_print.svg){#fig:exp2-outcomes}

The trajectory differs markedly from the five-task experiment. In the five-task run, sweep 1 achieved a 100% fix rate on failing tasks; here, sweep 1 fixes only 5 of 9 failing tasks (56%). The four unfixed tasks (7, 9, 11, 12) consumed substantial teacher effort---a combined 150 messages, 61 tool calls, and 36 minutes of wall-clock time---without producing a single viable patch.

A second notable difference is the delayed improvement in evaluation metrics. Sweep 2's re-evaluation shows essentially no change from baseline (9/30 trials, 30% majority), despite sweep 1 having fixed five tasks during the evolution loop. The full improvement materialises only in sweep 3 (15/30 trials, 50% majority), after sweep 2's fixes had a chance to reinforce the earlier patches.

@Tbl:exp2-fixes details the individual fix attempts.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|-------|------|-------------|------|---------|-------------|------------|----------|
| 1 | 0 | Fail → Pass | instruction | 1 | 10 | 4 | 51s |
| 1 | 1 | Fail → Pass | instruction | 1 | 4 | 1 | 21s |
| 1 | 5 | Fail → Pass | instruction | 2 | 16 | 6 | 5m 11s |
| 1 | 3 | Fail → Pass | guardrail | 3 | 36 | 15 | 5m 54s |
| 1 | 10 | Fail → Pass | instruction | 2 | 35 | 14 | 6m 59s |
| 1 | 12 | Fail → Fail | --- | --- | 36 | 15 | 8m 37s |
| 1 | 9 | Fail → Fail | --- | --- | 37 | 14 | 12m 36s |
| 1 | 11 | Fail → Fail | --- | --- | 38 | 16 | 6m 21s |
| 1 | 7 | Fail → Fail | --- | --- | 39 | 16 | 8m 40s |
| 2 | 1 | Fail → Pass | instruction | 2 | 12 | 4 | 3m 42s |
| 2 | 5 | Fail → Pass | guardrail | 3 | 59 | 26 | 11m 49s |
| 2 | 3 | Fail → Fail | --- | --- | 26 | 10 | 3m 33s |
| 2 | 0 | Fail → Fail | --- | --- | 35 | 12 | 5m 9s |
| 2 | 12 | Fail → Fail | --- | --- | 46 | 19 | 7m 50s |
| 2 | 11 | Fail → Fail | --- | --- | 37 | 15 | 8m 45s |
| 2 | 7 | Fail → Fail | --- | --- | 22 | 8 | 7m 22s |
| 2 | 9 | Fail → Fail | --- | --- | 39 | 17 | 10m 0s |
| 2 | 10 | Fail → Fail | --- | --- | 38 | 16 | 19m 0s |

: Individual fix attempts for Qwen3 30B-A3B on 10 tasks. {#tbl:exp2-fixes}

#### Fix Type Analysis

@Fig:exp2-fix-attempts shows the number of tasks fixed per attempt and tier across sweeps.

![Fix attempts by tier and sweep for Qwen3 30B-A3B on 10 tasks.](../runs/10/fix_attempts_print.svg){#fig:exp2-fix-attempts}

Across sweeps 1 and 2, seven successful fixes were applied: five instruction-tier (71%) and two guardrail-tier (29%). This ratio is identical to the five-task experiment's, suggesting that the instruction-guardrail balance is a stable property of the framework rather than an artefact of the specific task set.

The cost distribution shifts substantially. In the five-task run, the teacher encountered no unfixable tasks until sweep 3. In the ten-task run, the teacher exhausted all retries on four tasks in sweep 1 and seven in sweep 2, burning 393 messages, 162 tool calls, and over 107 minutes on failed attempts.

#### Summary

The trial pass rate rises from 27% (baseline) to 50% (after two sweeps), a 23-percentage-point gain comparable to the five-task run's +20pp. The instruction-guardrail ratio (71%/29%) is identical. However, four of nine failing tasks resist all fix attempts, and improvement is delayed by one sweep due to patch fragility.

### 4.3.2 Qwen3.5 Flash

The same ten tasks were evaluated with Qwen3.5 Flash as the student model. @Tbl:exp2-flash-passrate summarises pass rates across sweeps.

| Sweep | T0 | T1 | T3 | T4 | T5 | T7 | T9 | T10 | T11 | T12 | Trial rate | Maj. rate |
|-------|-----|-----|-----|-----|-----|-----|-----|------|------|------|------------|-----------|
| 1 (base) | 3/3 | 3/3 | 3/3 | 3/3 | 1/3 | 0/3 | 0/3 | 3/3 | 1/3 | 1/3 | 18/30 (60%) | 5/10 (50%) |
| 2 (post-S1) | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | 0/3 | 3/3 | 3/3 | 3/3 | 24/30 (80%) | 8/10 (80%) |
| 3 (post-S2) | 3/3 | 3/3 | 3/3 | 2/3 | 2/3 | 0/3 | 1/3 | 2/3 | 0/3 | 3/3 | 19/30 (63%) | 7/10 (70%) |

: Per-sweep evaluation results for Qwen3.5 Flash on 10 tasks. {#tbl:exp2-flash-passrate}

![Per-task, per-trial pass/fail heatmap for Qwen3.5 Flash across three sweeps (10 tasks). The heatmap reveals a much greener baseline than Qwen3 30B-A3B, with five tasks passing perfectly from the start.](../runs/qwen35-flash_10/sweep_heatmap_print.svg){#fig:exp2-flash-heatmap}

The baseline is dramatically stronger than Qwen3 30B-A3B's on the same tasks: 60% trial pass rate versus 27%, and 50% majority pass rate versus 30%. Crucially, the five tasks that Qwen3 30B-A3B needed evolution to pass (0, 1, 3, 4, 10) are already solved by Qwen3.5 Flash at baseline. The failing tasks are a different set: Tasks 5, 7, 9, 11, and 12. Of these, Tasks 7 and 9 are the same resistant tasks that Qwen3 30B-A3B also could not fix, suggesting these tasks represent genuinely hard problems rather than model-specific weaknesses.

#### Evolution Trajectory

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 5 | 4 | 0 | 1 |
| 2 | 8 | 0 | 1 | 1 |
| 3 | 4 | 0 | 0 | 6 |

: Per-sweep task outcomes during the evolution loop for Qwen3.5 Flash on 10 tasks. {#tbl:exp2-flash-outcomes}

![Stacked bar chart of per-sweep task outcomes for Qwen3.5 Flash on 10 tasks. The large green "Passed" segment reflects the stronger baseline; the evolution loop mainly addresses edge-case failures.](../runs/qwen35-flash_10/sweep_outcomes_print.svg){#fig:exp2-flash-outcomes}

The evolution trajectory is markedly more efficient than Qwen3 30B-A3B's. In sweep 1, 5 of 10 tasks are already passing; of the 5 failing tasks, 4 are fixed by instruction patches and only Task 7 resists repair. Sweep 2 sees 8 tasks already passing; the one remaining fixable task (Task 9) requires escalation to a guardrail fix. By sweep 2, the framework has raised Qwen3.5 Flash's majority pass rate from 50% to 80%---a +30pp gain.

@Tbl:exp2-flash-fixes details the individual fix attempts.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|-------|------|-------------|------|---------|-------------|------------|----------|
| 1 | 11 | Fail → Pass | instruction | 1 | 6 | 2 | 42s |
| 1 | 12 | Fail → Pass | instruction | 2 | 21 | 8 | 3m 25s |
| 1 | 9 | Fail → Pass | instruction | 2 | 26 | 11 | 6m 34s |
| 1 | 7 | Fail → Fail | --- | --- | 50 | 22 | 8m 37s |
| 1 | 5 | Fail → Pass | instruction | 2 | 8 | 2 | 72m 27s |
| 2 | 7 | Fail → Fail | --- | --- | 24 | 9 | 6m 18s |
| 2 | 9 | Fail → Pass | guardrail | 3 | 39 | 16 | 7m 28s |

: Individual fix attempts for Qwen3.5 Flash on 10 tasks. {#tbl:exp2-flash-fixes}

A notable finding is that Qwen3.5 Flash can fix tasks that Qwen3 30B-A3B could not. Tasks 11 and 12---part of Qwen3 30B-A3B's "hard core" of unfixable tasks---are both fixed by instruction patches on Qwen3.5 Flash (Task 11 on the first attempt in just 42 seconds, Task 12 on the second attempt). This confirms that these tasks are not inherently beyond the reach of prompt-level correction; rather, Qwen3 30B-A3B lacked the baseline capability to execute even well-specified instructions for these tasks. The stronger student can act on the same guidance that the weaker student could not.

Task 7, however, resists repair on both models, consuming substantial teacher effort (50 messages, 22 tool calls in sweep 1; 24 messages, 9 tool calls in sweep 2) without success. This task appears to represent a genuinely structural challenge that neither model can handle through prompt-level intervention alone.

#### Fix Type Analysis

![Fix attempts by tier and sweep for Qwen3.5 Flash on 10 tasks.](../runs/qwen35-flash_10/fix_attempts_print.svg){#fig:exp2-flash-fix-attempts}

Across sweeps 1 and 2, five successful fixes were applied: four instruction-tier (80%) and one guardrail-tier (20%). The instruction dominance is even more pronounced than with Qwen3 30B-A3B (71%), consistent with the hypothesis that a stronger student can execute instruction-level guidance more reliably and therefore requires less escalation to guardrail interventions.

#### Regression in Sweep 3

The most striking result is the regression in sweep 3. The majority pass rate drops from 80% (sweep 2) to 70% (sweep 3), and the trial pass rate drops sharply from 80% to 63%. Tasks 4, 5, 10, and 11 all degrade: Task 4 drops from 3/3 to 2/3, Task 5 from 3/3 to 2/3, Task 10 from 3/3 to 2/3, and Task 11 from 3/3 to 0/3. This is a more severe regression than observed with Qwen3 30B-A3B, where only Task 5 regressed significantly.

The likely explanation is patch interference compounded by the stronger model's sensitivity to instruction changes. A model that follows instructions more precisely may also be more disrupted when accumulated patches create conflicting directives. Task 11's complete regression (3/3 → 0/3) is particularly concerning---this task was successfully fixed in sweep 1 with a simple instruction patch (42 seconds, 6 messages), yet the patches accumulated during sweep 2 appear to have undone this fix entirely.

### 4.3.3 GLM 4.7 Flash

#### Baseline Performance

@Tbl:glm10-passrate summarises pass rates across sweeps. @Fig:glm47-10-heatmap visualises the per-task, per-trial results.

| Sweep | T0 | T1 | T3 | T4 | T5 | T7 | T9 | T10 | T11 | T12 | Trial rate | Maj. rate |
|-------|-----|-----|-----|-----|-----|-----|-----|------|------|------|------------|-----------|
| 1 (base) | 3/3 | 2/3 | 3/3 | 3/3 | 2/3 | 0/3 | 0/3 | 2/3 | 0/3 | 0/3 | 15/30 (50%) | 6/10 (60%) |
| 2 (post-S1) | 3/3 | 1/3 | 3/3 | 2/3 | 2/3 | 0/3 | 0/3 | 2/3 | 0/3 | 0/3 | 13/30 (43%) | 5/10 (50%) |
| 3 (post-S2) | 2/3 | 2/3 | 2/3 | 2/3 | 1/3 | 0/3 | 0/3 | 2/3 | 1/3 | 0/3 | 12/30 (40%) | 5/10 (50%) |

: Per-sweep evaluation results for GLM 4.7 Flash on 10 tasks. {#tbl:glm10-passrate}

![Per-task, per-trial pass/fail heatmap for GLM 4.7 Flash across three sweeps (10 tasks).](../runs/glm47_10/sweep_heatmap_print.svg){#fig:glm47-10-heatmap}

The baseline is the strongest of any model at this scale: 50% trial rate and 60% majority rate, compared to 27%/30% for Qwen3 30B-A3B and 60%/50% for Qwen3.5 Flash. Six of ten tasks pass at baseline (0, 1, 3, 4, 5, 10). The four genuinely failing tasks are the same hard core seen across other models: Tasks 7, 9, 11, and 12.

#### Evolution Trajectory

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 3 | 1 | 1 | 5 |
| 2 | 2 | 2 | 0 | 6 |
| 3 | 0 | 0 | 0 | 10 |

: Per-sweep task outcomes during the evolution loop for GLM 4.7 Flash on 10 tasks. {#tbl:glm10-outcomes}

![Stacked bar chart of per-sweep task outcomes for GLM 4.7 Flash on 10 tasks.](../runs/glm47_10/sweep_outcomes_print.svg){#fig:glm47-10-outcomes}

The evolution trajectory tells a story of failure. @Tbl:glm10-fixes details the individual fix attempts.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|-------|------|-------------|------|---------|-------------|------------|----------|
| 1 | 10 | Fail → Pass | instruction | 2 | 18 | 7 | 4m 25s |
| 1 | 1 | Fail → Pass | guardrail | 3 | 18 | 6 | 5m 53s |
| 1 | 7 | Fail → Fail | --- | --- | 26 | 10 | 4m 0s |
| 1 | 11 | Fail → Fail | --- | --- | 56 | 24 | 5m 11s |
| 1 | 5 | Fail → Fail | --- | --- | 44 | 18 | 5m 41s |
| 1 | 12 | Fail → Fail | --- | --- | 56 | 24 | 8m 37s |
| 1 | 9 | Fail → Fail | --- | --- | 54 | 21 | 8m 40s |
| 2 | 4 | Fail → Pass | instruction | 1 | 8 | 3 | 1m 10s |
| 2 | 1 | Fail → Pass | instruction | 1 | 13 | 5 | 1m 19s |
| 2 | 7 | Fail → Fail | --- | --- | 45 | 20 | 3m 52s |
| 2 | 12 | Fail → Fail | --- | --- | 71 | 30 | 5m 46s |
| 2 | 11 | Fail → Fail | --- | --- | 43 | 19 | 6m 39s |
| 2 | 10 | Fail → Fail | --- | --- | 45 | 20 | 7m 41s |
| 2 | 9 | Fail → Fail | --- | --- | 58 | 24 | 29m 3s |
| 2 | 5 | Fail → Fail | --- | --- | 35 | 14 | 30m 38s |

: Individual fix attempts for GLM 4.7 Flash on 10 tasks. {#tbl:glm10-fixes}

![Fix attempts by tier and sweep for GLM 4.7 Flash on 10 tasks.](../runs/glm47_10/fix_attempts_print.svg){#fig:glm47-10-fix-attempts}

The critical finding is that **all four successful fixes targeted tasks that were already passing by majority vote at baseline**. Tasks 10 and 1 (sweep 1) and Tasks 4 and 1 (sweep 2) all had majority-vote baselines of ≥2/3. The four genuinely failing tasks---7, 9, 11, 12---were attempted in both sweeps and failed every time, yielding a **0% fix rate on genuinely failing tasks**.

#### Why the Framework Fails

The evolution loop produces patches, and the teacher diagnoses failures correctly, but GLM 4.7 Flash cannot translate these patches into reliable execution at this scale. The patches fix one behaviour but introduce new errors elsewhere. This is visible in the progressive degradation of the trial rate across sweeps: 50% → 43% → 40%. Even tasks that were comfortably passing at baseline (e.g., Task 1 at 2/3, Task 5 at 2/3) become more fragile after patches are applied.

The sweep 3 result is especially revealing: the evolution loop sees all ten tasks as failing, even though the 3-trial re-evaluation shows five passing by majority. The model's behaviour is becoming increasingly unstable as patches accumulate.

#### Summary

GLM 4.7 Flash at ten tasks represents the framework's clearest failure mode. Despite a strong baseline (60% majority), the evolution loop cannot fix any genuinely failing task and actively degrades performance on passing tasks. The trial rate declines monotonically from 50% to 40% across three sweeps. This result motivated dropping GLM 4.7 Flash from the 20-task experiment.

### 4.3.4 Comparative Analysis at Ten Tasks

@Tbl:10task-comparison summarises the key metrics for all three models at ten tasks.

| Metric | Qwen3 30B-A3B | Qwen3.5 Flash | GLM 4.7 Flash |
|--------|---------------|---------------|---------------|
| Baseline trial rate | 27% (8/30) | 60% (18/30) | 50% (15/30) |
| Baseline majority rate | 30% (3/10) | 50% (5/10) | 60% (6/10) |
| Best trial rate (post-evo) | 50% (15/30) | 80% (24/30) | 50% (15/30) |
| Best majority rate (post-evo) | 50% (5/10) | 80% (8/10) | 60% (6/10) |
| Improvement (pp, trial) | +23 | +20 | 0 |
| Improvement (pp, majority) | +20 | +30 | 0 |
| Fix rate on failing tasks | 5/7 (71%) | 4/5 (80%) | 0/4 (0%) |
| Total fixes (instr/guard) | 7 (5/2) | 5 (4/1) | 4 (3/1) |
| Unfixable tasks | 4 (7, 9, 11, 12) | 1 (7) | 4 (7, 9, 11, 12) |
| Sweep 3 regression? | Mild | Severe (-17pp trial) | Continuous decline |

: Ten-task comparison across three student models. "Best" refers to the sweep with the highest pass rate. GLM 4.7 Flash's "best" is the baseline itself, since evolution produces no net improvement. {#tbl:10task-comparison}

Four patterns emerge from the three-model comparison:

**The framework is not universally beneficial.** GLM 4.7 Flash receives the same teacher patches as the other models but cannot convert them into durable improvements at this scale. The framework's value is contingent on the student model's ability to execute patched instructions reliably.

**The stronger student benefits most from evolution.** Qwen3.5 Flash achieves the highest ceiling (80% majority) and the highest fix rate on genuinely failing tasks (80%). Qwen3 30B-A3B achieves moderate improvement (+20pp majority). GLM 4.7 Flash achieves none.

**The hard core of resistant tasks is consistent.** Tasks 7, 9, 11, and 12 resist repair for both Qwen3 30B-A3B and GLM 4.7 Flash. With Qwen3.5 Flash, three of these (9, 11, 12) become fixable, leaving only Task 7 as genuinely resistant across all three models.

**Regression risk varies by model architecture.** Qwen3.5 Flash shows discrete regression in sweep 3 (-17pp trial, -10pp majority). GLM 4.7 Flash shows continuous decline across all sweeps. Qwen3 30B-A3B shows the mildest regression. The relationship between instruction-following quality and regression severity is not monotonic---GLM 4.7 Flash's regression is the worst despite not being the strongest instruction follower.

## 4.4 Twenty-Task Experiments

### 4.4.1 Qwen3 30B-A3B

Experiment 3 doubles the task set again to twenty, introducing ten additional tasks (14, 15, 17, 20, 21, 23, 27, 28, 33, 34) alongside the original ten. This tests whether the framework's gains continue to scale and how the teacher's strategy adapts to a larger and more diverse failure surface.

#### Baseline Performance

@Tbl:exp3-passrate summarises pass rates across sweeps.

| Sweep | Trial rate | Maj. rate |
|-------|------------|-----------|
| 1 (base) | 13/60 (22%) | 5/20 (25%) |
| 2 (post-S1) | 20/60 (33%) | 5/20 (25%) |
| 3 (post-S2) | 18/60 (30%) | 6/20 (30%) |

: Per-sweep pass rates for Qwen3 30B-A3B on 20 tasks. {#tbl:exp3-passrate}

The per-task baseline results reveal the scale of the challenge. Of 20 tasks, only 5 pass by majority vote at baseline: Tasks 1 (2/3), 4 (3/3), 5 (2/3), 10 (2/3), and 34 (2/3). The remaining 15 tasks fail, with 11 scoring 0/3. The baseline trial rate (22%) is the lowest of any experiment, confirming the expected dilution effect as harder tasks are added.

![Per-task, per-trial pass/fail heatmap for Qwen3 30B-A3B across three sweeps (20 tasks). The heatmap illustrates the dominance of red (failing) cells, with improvement concentrated in a small subset of tasks on the left side.](../runs/20/sweep_heatmap_print.svg){#fig:exp3-heatmap}

@Fig:exp3-heatmap visualises the per-task trajectories. The heatmap is overwhelmingly red, with progressive greening visible only in the leftmost cluster (Tasks 0, 1, 3, 4, 5) and scattered improvements in Tasks 28, 33, and 34. The right half of the heatmap---Tasks 14 through 27---remains solidly red across all three sweeps, representing a wall of failures that no amount of prompt evolution can penetrate.

The per-task breakdown for all three sweeps:

| Task | Sweep 1 | Sweep 2 | Sweep 3 | Trajectory |
|------|---------|---------|---------|------------|
| 0 | 1/3 | 2/3 | 3/3 | Improving |
| 1 | 2/3 | 3/3 | 2/3 | Stable pass |
| 3 | 0/3 | 1/3 | 0/3 | Fragile |
| 4 | 3/3 | 3/3 | 2/3 | Stable pass |
| 5 | 2/3 | 2/3 | 3/3 | Improving |
| 7 | 0/3 | 0/3 | 0/3 | Resistant |
| 9 | 0/3 | 0/3 | 0/3 | Resistant |
| 10 | 2/3 | 1/3 | 1/3 | Regressing |
| 11 | 1/3 | 1/3 | 0/3 | Regressing |
| 12 | 0/3 | 1/3 | 0/3 | Resistant |
| 14 | 0/3 | 0/3 | 0/3 | Resistant |
| 15 | 0/3 | 1/3 | 1/3 | Fragile |
| 17 | 0/3 | 0/3 | 0/3 | Resistant |
| 20 | 0/3 | 0/3 | 0/3 | Resistant |
| 21 | 0/3 | 0/3 | 0/3 | Resistant |
| 23 | 0/3 | 0/3 | 0/3 | Resistant |
| 27 | 0/3 | 0/3 | 0/3 | Resistant |
| 28 | 0/3 | 1/3 | 3/3 | Late bloomer |
| 33 | 0/3 | 1/3 | 1/3 | Fragile |
| 34 | 2/3 | 3/3 | 2/3 | Stable pass |

: Per-task trajectories for Qwen3 30B-A3B on 20 tasks. Trajectories classify tasks by their evolution arc: "Improving" tasks trend from fail to pass; "Stable pass" tasks pass throughout; "Fragile" tasks show inconsistent results; "Resistant" tasks never pass by majority vote; "Regressing" tasks degrade across sweeps; "Late bloomer" tasks only pass in the final sweep. {#tbl:exp3-trajectories}

#### Evolution Trajectory

| Sweep | Already passing | Fixed (instruction) | Fixed (tools) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|----|---------|---------|
| 1 | 1 | 3 | 1 | 1 | 14 |
| 2 | 3 | 4 | 1 | 0 | 12 |
| 3 | 3 | 0 | 0 | 0 | 17 |

: Per-sweep task outcomes for Qwen3 30B-A3B on 20 tasks. A new fix tier---"tools" (tool-schema patching)---appears for the first time. {#tbl:exp3-outcomes}

![Stacked bar chart of per-sweep task outcomes for Qwen3 30B-A3B on 20 tasks. The overwhelming red "Unfixed" segment reflects the dominance of resistant tasks at this scale.](../runs/20/sweep_outcomes_print.svg){#fig:exp3-outcomes}

A new phenomenon appears at this scale: **tool-schema fixes** emerge as a distinct tier. In both sweeps 1 and 2, one task (Task 0) was fixed via tool-schema patching rather than instruction or guardrail modification. This is the first time in any experiment that tool-level patches contributed to successful fixes, suggesting that the larger and more diverse failure surface exposes failure modes that cannot be addressed at the instruction or guardrail level alone.

@Tbl:exp3-fixes details the individual fix attempts.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|-------|------|-------------|------|---------|-------------|------------|----------|
| 1 | 5 | Fail → Pass | instruction | 1 | 8 | 3 | 17s |
| 1 | 1 | Fail → Pass | instruction | 1 | 6 | 2 | 1m 2s |
| 1 | 0 | Fail → Pass | tools | 2 | 18 | 7 | 3m 33s |
| 1 | 3 | Fail → Pass | guardrail | 3 | 26 | 9 | 5m 15s |
| 1 | 34 | Fail → Pass | instruction | 2 | 20 | 8 | 5m 31s |
| 1 | 28 | Fail → Fail | --- | --- | 48 | 17 | 5m 28s |
| 1 | 14 | Fail → Fail | --- | --- | 20 | 7 | 8m 28s |
| 1 | 11 | Fail → Fail | --- | --- | 42 | 17 | 7m 53s |
| 1 | 17 | Fail → Fail | --- | --- | 39 | 16 | 8m 40s |
| 1 | 7 | Fail → Fail | --- | --- | 36 | 14 | 8m 15s |
| 1 | 9 | Fail → Fail | --- | --- | 40 | 15 | 11m 2s |
| 1 | 15 | Fail → Fail | --- | --- | 34 | 14 | 11m 4s |
| 1 | 27 | Fail → Fail | --- | --- | 36 | 15 | 9m 33s |
| 1 | 33 | Fail → Fail | --- | --- | 44 | 19 | 13m 17s |
| 1 | 10 | Fail → Fail | --- | --- | 38 | 14 | 13m 23s |
| 1 | 21 | Fail → Fail | --- | --- | 36 | 14 | 12m 38s |
| 1 | 23 | Fail → Fail | --- | --- | 30 | 12 | 10m 38s |
| 1 | 12 | Fail → Fail | --- | --- | 38 | 15 | 16m 48s |
| 1 | 20 | Fail → Fail | --- | --- | 55 | 25 | 19m 38s |
| 2 | 3 | Fail → Pass | instruction | 1 | 8 | 3 | 2m 7s |
| 2 | 10 | Fail → Pass | instruction | 1 | 12 | 5 | 3m 46s |
| 2 | 28 | Fail → Pass | instruction | 2 | 12 | 4 | 7m 16s |
| 2 | 5 | Fail → Pass | instruction | 2 | 15 | 5 | 6m 32s |
| 2 | 0 | Fail → Pass | tools | 2 | 32 | 12 | 8m 9s |
| 2 | 17 | Fail → Fail | --- | --- | 20 | 7 | 7m 22s |
| 2 | 11 | Fail → Fail | --- | --- | 45 | 19 | 10m 41s |
| 2 | 15 | Fail → Fail | --- | --- | 38 | 15 | 14m 47s |
| 2 | 20 | Fail → Fail | --- | --- | 43 | 18 | 16m 23s |
| 2 | 14 | Fail → Fail | --- | --- | 41 | 17 | 13m 55s |
| 2 | 27 | Fail → Fail | --- | --- | 22 | 8 | 11m 2s |
| 2 | 12 | Fail → Fail | --- | --- | 54 | 21 | 16m 23s |
| 2 | 7 | Fail → Fail | --- | --- | 34 | 14 | 20m 21s |
| 2 | 9 | Fail → Fail | --- | --- | 44 | 19 | 19m 18s |
| 2 | 23 | Fail → Fail | --- | --- | 36 | 15 | 18m 44s |
| 2 | 21 | Fail → Fail | --- | --- | 44 | 19 | 16m 29s |
| 2 | 33 | Fail → Fail | --- | --- | 2 | --- | 72m 6s |

: Individual fix attempts for Qwen3 30B-A3B on 20 tasks. {#tbl:exp3-fixes}

The wasted effort is staggering. Across sweeps 1 and 2, the teacher exhausted all retries on 25 task-sweep combinations (14 in sweep 1, 11 in sweep 2), spending a combined 800+ messages, 300+ tool calls, and over 7 hours of wall-clock time on failed attempts. The most expensive single failed attempt was Task 33 in sweep 2, which consumed 72 minutes---more than any successful fix in the entire experimental programme---likely due to a timeout or network issue during the teacher's analysis. Task 20 in sweep 1 was the next most expensive at nearly 20 minutes (55 messages, 25 tool calls).

#### Fix Type Analysis

![Fix attempts by tier and sweep for Qwen3 30B-A3B on 20 tasks.](../runs/20/fix_attempts_print.svg){#fig:exp3-fix-attempts}

Across sweeps 1 and 2, ten successful fixes were applied: seven instruction-tier (70%), two tools-tier (20%), and one guardrail-tier (10%). The instruction-tier dominance persists but its share drops slightly compared to the 71% observed in both previous experiments. The emergence of tool-schema fixes as a meaningful category is a new development: at 5 and 10 tasks, no tools-tier fixes were recorded.

The fix success rate continues its decline with scale: $\text{FSR}_{20} = 8/19 \approx 42\%$ of unique failing tasks were fixed at least once, down from 56% at 10 tasks and 100% at 5 tasks. Of the 15 tasks that failed at baseline, only 8 were ever successfully fixed (0, 1, 3, 5, 10, 28, 33, 34). The remaining 11 tasks constitute an expanded hard core: 7, 9, 11, 12, 14, 15, 17, 20, 21, 23, 27.

#### Scaling Observations

**Task 28 is a late bloomer.** It fails all trials in sweeps 1 and 2 but passes 3/3 in sweep 3---the only task to achieve a perfect sweep after two rounds of evolution. This suggests that accumulated patches from earlier sweeps can produce delayed, cross-task benefits: patches targeting other tasks may have incidentally improved the student's handling of Task 28's underlying policy or tool-use pattern.

**Improvement is real but modest.** The trial pass rate rises from 22% (baseline) to 33% (sweep 2), a +11pp gain---roughly half the improvement observed at 5 and 10 tasks. By majority vote, the improvement is smaller still: 25% → 30% (+5pp). The framework's impact is diluted by the large denominator of resistant tasks.

**Patch fragility persists.** The trial pass rate actually drops between sweeps 2 and 3 (33% → 30%), and the majority rate barely changes (25% → 30%, but this is driven entirely by Task 28's late bloom). Several tasks that showed marginal improvement in sweep 2 (Tasks 3, 11, 12, 15, 33) regress in sweep 3.

#### Summary

The twenty-task experiment confirms the diminishing returns hypothesis. The evolution framework produces a smaller absolute improvement (+8pp trial rate from baseline to best sweep) compared to 10 tasks (+23pp) and 5 tasks (+20pp). The fix success rate drops to 42%. The hard core of resistant tasks expands from 4 (at 10 tasks) to 11 (at 20 tasks). Tool-schema fixes emerge as a new category, but their frequency (2 of 10 fixes) is too low to offset the growing proportion of unfixable failures. The practical implication is clear: at 20 tasks, the teacher spends the vast majority of its time and tokens on tasks it cannot repair.

### 4.4.2 Qwen3.5 Flash

#### Baseline Performance

@Tbl:flash20-passrate summarises pass rates across sweeps. @Fig:flash20-heatmap visualises the per-task, per-trial results.

| Sweep | Trial rate | Maj. rate |
|-------|------------|-----------|
| 1 (base) | 28/60 (47%) | 9/20 (45%) |
| 2 (post-S1) | 34/60 (57%) | 13/20 (65%) |
| 3 (post-S2) | 35/60 (58%) | 13/20 (65%) |

: Per-sweep pass rates for Qwen3.5 Flash on 20 tasks. {#tbl:flash20-passrate}

![Per-task, per-trial pass/fail heatmap for Qwen3.5 Flash across three sweeps (20 tasks).](../runs/qwen35-flash_20/sweep_heatmap_print.svg){#fig:flash20-heatmap}

The per-task baseline results:

| Task | Sweep 1 | Sweep 2 | Sweep 3 | Trajectory |
|------|---------|---------|---------|------------|
| 0 | 3/3 | 3/3 | 3/3 | Stable pass |
| 1 | 3/3 | 3/3 | 3/3 | Stable pass |
| 3 | 3/3 | 3/3 | 3/3 | Stable pass |
| 4 | 3/3 | 3/3 | 3/3 | Stable pass |
| 5 | 2/3 | 3/3 | 3/3 | Improving |
| 7 | 0/3 | 0/3 | 0/3 | Resistant |
| 9 | 0/3 | 0/3 | 0/3 | Resistant |
| 10 | 3/3 | 2/3 | 3/3 | Stable pass |
| 11 | 1/3 | 1/3 | 2/3 | Late improver |
| 12 | 0/3 | 2/3 | 3/3 | Improving |
| 14 | 0/3 | 0/3 | 0/3 | Resistant |
| 15 | 1/3 | 3/3 | 1/3 | Fragile |
| 17 | 2/3 | 2/3 | 3/3 | Stable pass |
| 20 | 2/3 | 2/3 | 2/3 | Stable pass |
| 21 | 1/3 | 2/3 | 2/3 | Improving |
| 23 | 0/3 | 0/3 | 0/3 | Resistant |
| 27 | 0/3 | 0/3 | 3/3 | Late bloomer |
| 28 | 3/3 | 3/3 | 3/3 | Stable pass |
| 33 | 0/3 | 0/3 | 0/3 | Resistant |
| 34 | 1/3 | 2/3 | 1/3 | Fragile |

: Per-task trajectories for Qwen3.5 Flash on 20 tasks. {#tbl:flash20-trajectories}

The baseline is dramatically stronger than Qwen3 30B-A3B's at the same scale: 47% trial rate versus 22%, and 45% majority versus 25%. Nine tasks pass at baseline, compared to five for Qwen3 30B-A3B. Critically, Qwen3.5 Flash passes Tasks 17, 20, and 28 at baseline---tasks that Qwen3 30B-A3B scored 0/3 on. The eleven failing tasks include familiar resistant cases (7, 9, 14, 23, 33) as well as tasks that responded to evolution (5, 11, 12, 15, 21, 27, 34).

#### Evolution Trajectory

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 6 | 6 | 0 | 8 |
| 2 | 7 | 5 | 1 | 7 |
| 3 | 10 | 0 | 0 | 10 |

: Per-sweep task outcomes during the evolution loop for Qwen3.5 Flash on 20 tasks. {#tbl:flash20-outcomes}

![Stacked bar chart of per-sweep task outcomes for Qwen3.5 Flash on 20 tasks.](../runs/qwen35-flash_20/sweep_outcomes_print.svg){#fig:flash20-outcomes}

The evolution loop is productive across two sweeps. Sweep 1 fixes six tasks (all instruction-tier): Tasks 17, 20, 11, 34, 21, and 5. Sweep 2 fixes six more: Tasks 11, 17, 12, 20, 10 (instruction) and Task 27 (guardrail). Sweep 3 produces no new fixes.

@Tbl:flash20-fixes details the individual fix attempts.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|-------|------|-------------|------|---------|-------------|------------|----------|
| 1 | 17 | Fail → Pass | instruction | 1 | 4 | 1 | 1m 51s |
| 1 | 20 | Fail → Pass | instruction | 1 | 6 | 2 | 2m 10s |
| 1 | 11 | Fail → Pass | instruction | 1 | 10 | 4 | 3m 44s |
| 1 | 34 | Fail → Pass | instruction | 1 | 12 | 5 | 3m 54s |
| 1 | 21 | Fail → Pass | instruction | 1 | 8 | 3 | 4m 33s |
| 1 | 5 | Fail → Pass | instruction | 1 | 4 | 1 | 11m 25s |
| 1 | 12 | Fail → Fail | --- | --- | 26 | 10 | 11m 29s |
| 1 | 33 | Fail → Fail | --- | --- | 39 | 16 | 12m 56s |
| 1 | 27 | Fail → Fail | --- | --- | 32 | 13 | 12m 57s |
| 1 | 15 | Fail → Fail | --- | --- | 21 | 7 | 17m 21s |
| 1 | 23 | Fail → Fail | --- | --- | 32 | 13 | 16m 28s |
| 1 | 7 | Fail → Fail | --- | --- | 31 | 12 | 25m 58s |
| 1 | 14 | Fail → Fail | --- | --- | 2 | --- | 76m 3s |
| 1 | 9 | Fail → Fail | --- | --- | 24 | 9 | 82m 51s |
| 2 | 11 | Fail → Pass | instruction | 1 | 8 | 3 | 1m 7s |
| 2 | 17 | Fail → Pass | instruction | 2 | 14 | 5 | 3m 23s |
| 2 | 12 | Fail → Pass | instruction | 2 | 26 | 11 | 4m 15s |
| 2 | 20 | Fail → Pass | instruction | 2 | 22 | 9 | 4m 53s |
| 2 | 27 | Fail → Pass | guardrail | 3 | 35 | 14 | 5m 56s |
| 2 | 10 | Fail → Pass | instruction | 1 | 6 | 2 | 50s |
| 2 | 7 | Fail → Fail | --- | --- | 24 | 9 | 7m 50s |
| 2 | 21 | Fail → Fail | --- | --- | 39 | 16 | 8m 34s |
| 2 | 33 | Fail → Fail | --- | --- | 37 | 15 | 8m 50s |
| 2 | 9 | Fail → Fail | --- | --- | 46 | 18 | 11m 35s |
| 2 | 23 | Fail → Fail | --- | --- | 33 | 13 | 11m 29s |
| 2 | 14 | Fail → Fail | --- | --- | 2 | --- | 15m 45s |
| 2 | 34 | Fail → Fail | --- | --- | 2 | --- | 19m 29s |

: Individual fix attempts for Qwen3.5 Flash on 20 tasks. {#tbl:flash20-fixes}

![Fix attempts by tier and sweep for Qwen3.5 Flash on 20 tasks.](../runs/qwen35-flash_20/fix_attempts_print.svg){#fig:flash20-fix-attempts}

#### Fix Type Analysis

Across sweeps 1 and 2, twelve successful fixes were applied: eleven instruction-tier (92%) and one guardrail-tier (8%). No tool-schema fixes appeared---a notable contrast with Qwen3 30B-A3B, which required two tool-schema fixes at the same scale. The stronger student's instruction-following capability makes prompt-level corrections sufficient for tasks that required tool-level intervention with the weaker model.

The fix success rate on genuinely failing tasks is 45%: of the eleven tasks failing at baseline, five unique tasks were fixed at least once (11, 12, 21, 27, 34). The five persistently unfixable tasks are 7, 9, 14, 23, and 33.

#### Cross-Task Benefits and Regression

Two tasks show notable indirect effects. **Task 15** improves from 1/3 (baseline) to 3/3 (sweep 2) without being directly fixed by the teacher---no successful fix for Task 15 appears in the teachers log. This cross-task benefit likely arises from instruction patches targeting other tasks that incidentally clarify a policy relevant to Task 15. However, Task 15 regresses to 1/3 in sweep 3, suggesting the improvement was fragile.

**Task 27** follows a late-bloomer pattern: 0/3 across sweeps 1 and 2, then suddenly 3/3 in sweep 3. Task 27 received a guardrail fix in sweep 2, but the fix's effect only materialises in the sweep 3 re-evaluation. This mirrors the delayed improvement observed with Task 28 for Qwen3 30B-A3B at the same scale.

The most notable regression is **Task 34**, which is fixed in sweep 1 (1/3 → 2/3 in sweep 2) but regresses to 1/3 in sweep 3. Task 15 similarly regresses (3/3 → 1/3). However, these losses are offset by gains in Tasks 11, 12, and 27, resulting in no net change in the majority pass rate between sweeps 2 and 3 (both 65%).

#### Summary

Qwen3.5 Flash at 20 tasks achieves a +20pp majority improvement (45% → 65%) and +10pp trial improvement (47% → 57%), both substantially larger than Qwen3 30B-A3B's gains at the same scale (+5pp majority, +11pp trial). The fix breakdown is overwhelmingly instruction-tier (92%), with no tool-schema fixes needed. Unlike the severe sweep-3 regression observed at 10 tasks (-17pp trial, -10pp majority), the 20-task experiment shows remarkable stability between sweeps 2 and 3, with the majority rate holding at 65% despite individual task-level churn.

### 4.4.3 Comparative Analysis at Twenty Tasks

@Tbl:20task-comparison summarises the key metrics for both models at twenty tasks. GLM 4.7 Flash is excluded, having been dropped at this scale due to poor performance at ten tasks.

| Metric | Qwen3 30B-A3B | Qwen3.5 Flash |
|--------|---------------|---------------|
| Baseline trial rate | 22% (13/60) | 47% (28/60) |
| Baseline majority rate | 25% (5/20) | 45% (9/20) |
| Best trial rate (post-evo) | 33% (20/60) | 58% (35/60) |
| Best majority rate (post-evo) | 30% (6/20) | 65% (13/20) |
| Improvement (pp, trial) | +11 | +11 |
| Improvement (pp, majority) | +5 | +20 |
| Fix rate on failing tasks | 8/15 (53%) | 5/11 (45%) |
| Total fixes (instr/guard/tools) | 10 (7/1/2) | 12 (11/1/0) |
| Unfixable tasks | 11 | 5 (7, 9, 14, 23, 33) |
| Sweep 3 majority change | +5pp (25→30%) | 0pp (65→65%) |

: Twenty-task comparison between student models. {#tbl:20task-comparison}

Three key findings emerge:

**The stronger student achieves a dramatically higher ceiling.** Qwen3.5 Flash reaches 65% majority (13/20), more than double Qwen3 30B-A3B's 30% (6/20). The gap between the models is larger post-evolution than at baseline, confirming that the framework amplifies rather than equalises capability differences.

**Tool-schema fixes are model-dependent.** Qwen3 30B-A3B required two tool-schema fixes (20% of its total), while Qwen3.5 Flash needed none. The stronger student's instruction-following capability makes prompt-level corrections sufficient for tasks that the weaker student could only address through tool-level intervention.

**The unfixable set shrinks but does not disappear.** Qwen3 30B-A3B has eleven unfixable tasks at this scale; Qwen3.5 Flash has five (7, 9, 14, 23, 33). Of these five, Tasks 7 and 9 are the same cross-model resistant tasks seen at ten tasks. Tasks 14, 23, and 33 represent genuinely hard problems that neither model can address through prompt evolution alone.

## 4.5 Cross-Scale and Cross-Model Comparison

### 4.5.1 Scaling Curve: Qwen3 30B-A3B

@Tbl:cross-experiment-qwen3 summarises the key metrics across all three scales for Qwen3 30B-A3B.

| Tasks | Base trial | Best trial | Gain (pp) | Failing | Fixed | Fix rate |
|-------|------------|------------|-----------|---------|-------|----------|
| 5 | 53% (8/15) | 73% (11/15) | +20 | 4 | 4 | 100% |
| 10 | 27% (8/30) | 50% (15/30) | +23 | 9 | 5 | 56% |
| 20 | 22% (13/60) | 33% (20/60) | +11 | 15 | 8 | 53% |

: Cross-scale summary for Qwen3 30B-A3B. Improvement is measured in percentage points of trial pass rate. Fix rate is the fraction of unique failing tasks that were successfully fixed at least once across sweeps 1--2. {#tbl:cross-experiment-qwen3}

The scaling curve reveals two regimes. From 5 to 10 tasks, the absolute improvement is remarkably stable (+20pp to +23pp), and the fix rate drops sharply (100% to 56%) as harder tasks enter the pool. From 10 to 20 tasks, the absolute improvement halves (+23pp to +11pp) while the fix rate stabilises (56% to 53%). This suggests that the framework reaches a capacity ceiling around 5--8 fixable tasks regardless of pool size, and additional tasks primarily contribute unfixable failures that consume teacher effort.

The number of successful fixes is also instructive: 7 at 5 tasks, 7 at 10 tasks, and 10 at 20 tasks. While the absolute count grows slightly with scale, the growth is sub-linear---doubling the task set from 10 to 20 yields only 3 additional fixes. The framework does not discover fundamentally more failure modes at larger scales; it mostly encounters more instances of the same resistant patterns.

### 4.5.2 Scaling Curve: Qwen3.5 Flash

| Tasks | Base trial | Best trial | Gain (pp) | Failing | Fixed | Fix rate |
|-------|------------|------------|-----------|---------|-------|----------|
| 5 | 100% (15/15) | 100% (15/15) | 0 | 0 | 0 | N/A |
| 10 | 60% (18/30) | 80% (24/30) | +20 | 5 | 4 | 80% |
| 20 | 47% (28/60) | 58% (35/60) | +11 | 11 | 5 | 45% |

: Cross-scale summary for Qwen3.5 Flash. {#tbl:cross-experiment-flash}

The scaling curve for Qwen3.5 Flash shows a pattern distinct from Qwen3 30B-A3B. At 5 tasks, no evolution is needed. At 10 tasks, the improvement is large (+20pp) with a high fix rate (80%). At 20 tasks, the improvement halves (+11pp trial) and the fix rate drops to 45%, mirroring the diminishing-returns pattern seen with Qwen3 30B-A3B. However, the majority-vote improvement at 20 tasks is more substantial (+20pp, from 45% to 65%) because the stronger student converts more fixes into reliable majority-vote passes.

A notable difference is the regression profile. At 10 tasks, Qwen3.5 Flash shows severe sweep-3 regression (-17pp trial, -10pp majority). At 20 tasks, this regression disappears: the majority rate holds steady at 65% across sweeps 2 and 3, with only marginal trial-rate improvement (+1pp). The larger task pool may have a stabilising effect, diluting the impact of any single conflicting patch across more tasks.

### 4.5.3 Scaling Curve: GLM 4.7 Flash

| Tasks | Base trial | Best trial | Gain (pp) | Failing | Fixed | Fix rate |
|-------|------------|------------|-----------|---------|-------|----------|
| 5 | 47% (7/15) | 73% (11/15) | +26 | 3 | 2 | 67% |
| 10 | 50% (15/30) | 50% (15/30) | 0 | 4 | 0 | 0% |

: Cross-scale summary for GLM 4.7 Flash. The model is dropped at 20 tasks. {#tbl:cross-experiment-glm}

GLM 4.7 Flash presents a cautionary tale. At 5 tasks, the framework produces a substantial peak improvement (+26pp trial, +40pp majority at sweep 2), comparable to the other models. At 10 tasks, the framework produces zero net improvement---worse, it actively degrades performance from the baseline. The fix rate on genuinely failing tasks drops from 67% to 0%.

The contrast between scales is stark. At 5 tasks, the model can absorb three instruction patches and one guardrail patch without destabilisation. At 10 tasks, the larger patch surface creates enough interference to prevent any gains. This scale-dependent collapse motivated the decision to drop GLM 4.7 Flash from the 20-task experiment.

### 4.5.4 Cross-Model Comparison at Matched Scales

| Scale | Model | Base maj. | Best maj. | Fix rate | Fixes (I/G/T) | Unfixable |
|-------|-------|-----------|-----------|----------|---------------|-----------|
| 5 | Qwen3 30B-A3B | 60% | 80% | 100% | 5/2/0 | 0 |
| 5 | Qwen3.5 Flash | 100% | 100% | N/A | 0/0/0 | 0 |
| 5 | GLM 4.7 Flash | 40% | 80% | 67% | 3/1/0 | 1 |
| 10 | Qwen3 30B-A3B | 30% | 50% | 71% | 5/2/0 | 4 |
| 10 | Qwen3.5 Flash | 50% | 80% | 80% | 4/1/0 | 1 |
| 10 | GLM 4.7 Flash | 60% | 60% | 0% | 3/1/0 | 4 |

: Cross-model comparison at matched scales (5 and 10 tasks). Fixes column shows instruction/guardrail/tools counts. {#tbl:cross-model}

At 20 tasks, only two models are compared:

| Metric | Qwen3 30B-A3B | Qwen3.5 Flash |
|--------|---------------|---------------|
| Baseline majority | 25% | 45% |
| Best majority | 30% | 65% |
| Fix rate (failing) | 53% | 45% |
| Fixes (instr/guard/tools) | 7/1/2 | 11/1/0 |
| Unfixable tasks | 11 | 5 |

: Cross-model comparison at 20 tasks. {#tbl:cross-model-20}

The most important finding is that the set of unfixable tasks is model-dependent, not task-intrinsic. At 10 tasks, Qwen3 30B-A3B and GLM 4.7 Flash share the same four unfixable tasks (7, 9, 11, 12). With Qwen3.5 Flash, three of these (9, 11, 12) become fixable, leaving only Task 7 as genuinely resistant across all three models. At 20 tasks, the unfixable set shrinks further for Qwen3.5 Flash (5 tasks vs 11), with Tasks 7, 9, 14, 23, and 33 forming the persistent hard core.

### 4.5.5 Instruction vs Guardrail Ratio Across All Experiments

| Experiment | Total fixes | Instruction | Tools | Guardrail |
|------------|------------|-------------|-------|-----------|
| Qwen3 30B, 5 tasks | 7 | 5 (71%) | 0 | 2 (29%) |
| Qwen3 30B, 10 tasks | 7 | 5 (71%) | 0 | 2 (29%) |
| Qwen3 30B, 20 tasks | 10 | 7 (70%) | 2 (20%) | 1 (10%) |
| Qwen3.5 Flash, 10 tasks | 5 | 4 (80%) | 0 | 1 (20%) |
| Qwen3.5 Flash, 20 tasks | 12 | 11 (92%) | 0 | 1 (8%) |
| GLM 4.7, 5 tasks | 4 | 3 (75%) | 0 | 1 (25%) |
| GLM 4.7, 10 tasks | 4 | 3 (75%) | 0 | 1 (25%) |

: Fix tier breakdown across all eight experiments. {#tbl:cross-tier-all}

Instruction-level patching dominates across all experiments (70--92% of fixes), confirming it as the primary mechanism of improvement. Two trends stand out. First, the stronger student (Qwen3.5 Flash) shows a progressively higher instruction-tier share as scale increases (80% at 10 tasks, 92% at 20 tasks), suggesting that stronger instruction-following capability reduces the need for guardrail or tool-level interventions. Second, tool-schema patches appear only for Qwen3 30B-A3B at 20 tasks (2 of 10 fixes)---neither Qwen3.5 Flash nor GLM 4.7 Flash required tool-level intervention at any scale.

### 4.5.6 Saturation Analysis

All experiments saturate by sweep 3 (zero new fixes). However, the improvement timeline and regression pattern vary markedly:

- **Qwen3 30B, 5 tasks**: improvement materialises immediately (sweep 1 → 2: +20pp trial). Sweep 3 shows no further gain and mild regression (-20pp majority).
- **Qwen3 30B, 10 tasks**: improvement is delayed (sweep 1 → 2: +3pp; sweep 2 → 3: +20pp). The delay reflects patch fragility at larger scale.
- **Qwen3 30B, 20 tasks**: improvement is immediate but modest (sweep 1 → 2: +11pp). Sweep 3 shows slight regression (-3pp trial rate).
- **Qwen3.5 Flash, 10 tasks**: improvement is immediate and large (sweep 1 → 2: +20pp). Sweep 3 shows significant regression (-17pp trial rate, -10pp majority).
- **Qwen3.5 Flash, 20 tasks**: improvement is immediate (sweep 1 → 2: +10pp trial, +20pp majority). Sweep 3 shows stability (+1pp trial, 0pp majority).
- **GLM 4.7, 5 tasks**: improvement peaks at sweep 2 (+26pp trial, +40pp majority). Sweep 3 collapses to baseline (-26pp trial, -40pp majority).
- **GLM 4.7, 10 tasks**: continuous decline across all sweeps (-10pp trial from baseline to sweep 3, -10pp majority).

The GLM 4.7 Flash results introduce a new failure pattern not seen with the Qwen models: monotonic degradation under patch accumulation. In all Qwen experiments, the framework produces at least some improvement before saturating. With GLM 4.7 Flash at 10 tasks, no improvement occurs at any point. This suggests that the framework has a minimum student capability threshold below which patches cause net harm.

## 4.6 Discussion

### 4.6.1 Summary of Principal Findings

This thesis set out to investigate whether a lightweight, input-space-only evolution framework can measurably improve the performance of weaker, non-thinking LLM agents on the τ²-bench benchmark. The results across eight experiments---three with Qwen3 30B-A3B (5, 10, and 20 tasks), three with Qwen3.5 Flash (5, 10, and 20 tasks), and two with GLM 4.7 Flash (5 and 10 tasks)---provide a nuanced answer: the framework can produce substantial improvements, but its effectiveness is contingent on the student model's ability to absorb and execute patches.

Six principal conclusions emerge:

1. **Non-thinking models can be taught to perform better through input modifications.** Qwen3 30B-A3B improves from 53% to 73% (+20pp) at 5 tasks, 27% to 50% (+23pp) at 10 tasks, and 22% to 33% (+11pp) at 20 tasks. Qwen3.5 Flash improves from 60% to 80% (+20pp) at 10 tasks and from 47% to 58% (+11pp) at 20 tasks.

2. **Instruction-level patching is the dominant lever.** Across all experiments, 70--92% of successful fixes target the instruction section of the system prompt. This is consistent with the Superficial Alignment Hypothesis: the models' failures are primarily failures of instruction following, not of capability.

3. **Improvement diminishes with scale.** For both Qwen models, the trial-rate improvement drops from +20pp at small scales to +11pp at 20 tasks. The fix success rate declines as harder tasks enter the pool. The framework's capacity ceiling is approximately 5--8 fixable tasks per model, regardless of pool size.

4. **A stronger student shifts the framework's value proposition.** Qwen3.5 Flash fixes tasks that Qwen3 30B-A3B cannot (9, 11, 12), achieving a higher fix rate (80% vs 56% at 10 tasks) and a higher absolute ceiling (80% vs 50% at 10 tasks; 65% vs 30% at 20 tasks). The framework amplifies rather than equalises capability differences.

5. **Patch interference is a binding constraint.** All models show some form of regression under patch accumulation. Qwen3.5 Flash shows severe discrete regression at 10 tasks (-17pp trial). GLM 4.7 Flash shows catastrophic collapse at 5 tasks (-40pp majority) and continuous decline at 10 tasks. Qwen3 30B-A3B shows the mildest regression.

6. **Not all models benefit from evolution.** GLM 4.7 Flash at 10 tasks represents a clear failure mode: the framework fixes zero genuinely failing tasks and actively degrades performance on passing tasks. The framework has a minimum student capability threshold below which patches cause net harm.

### 4.6.2 Contextualising the Findings within Existing Literature

#### Prompt evolution as a viable alternative to weight updates

The central finding---that prompt-level patching can improve agent task success---aligns with a growing body of work demonstrating the power of prompt optimisation as a substitute for, or complement to, fine-tuning. @zhou2022 showed that LLMs themselves can serve as prompt engineers, automatically generating instructions that rival human-crafted prompts. More recently, the GEPA framework [@agrawal2025] demonstrated that reflective prompt evolution, where an LLM reads execution traces and diagnoses failures in natural language, can outperform reinforcement learning methods such as GRPO by up to 20% while requiring 35× fewer rollouts. The present work shares GEPA's core intuition---that natural-language traces are richer learning signals than scalar rewards---but differs in a crucial respect: whereas GEPA evolves prompts using the model's own self-reflection, our framework injects *external* human supervision as the source of corrective signal.

Similarly, the DSPy framework [@khattab2023] and TextGrad [@yuksekgonul2024] have demonstrated that structured optimisation of prompt components can yield substantial performance gains. Our framework occupies a middle ground: it does not require the formal program structure of DSPy, nor does it perform gradient-like back-propagation over textual losses. Instead, it relies on a teacher model to read a failed conversation trace alongside the corresponding human action trace and to propose a targeted patch---an approach that is arguably more transparent and interpretable to practitioners.

The observed improvements are broadly consistent with the magnitude of gains reported in the prompt optimisation literature. The stability of the absolute gain across task-set sizes (for Qwen3 30B-A3B: +20pp, +23pp, +11pp) is notable. The three-model comparison adds a dimension not present in most prior work: the same framework applied to different student models reveals that the *ceiling* of prompt-level improvement is set by the student's intrinsic capability, not by the framework's design. The GLM 4.7 Flash results further demonstrate that prompt evolution can be *harmful* when applied to a model that cannot reliably execute patched instructions---a negative result that, to our knowledge, has not been systematically documented in the prompt optimisation literature.

#### Teacher--student dynamics without weight transfer

The teacher--student architecture adopted in this work represents a form of knowledge distillation that operates entirely in the input space. Traditional knowledge distillation [@hinton2015] transfers a teacher's knowledge through soft probability targets used during student weight training. Our approach is more minimalist: the teacher's knowledge is distilled not into the student's weights or training data, but into the student's *operating instructions*.

The three-model results enrich this picture. When Kimi K2.5 proposes a patch for Task 11, that patch fails with Qwen3 30B-A3B but succeeds with Qwen3.5 Flash. The knowledge embedded in the patch is identical; what differs is the student's capacity to interpret and execute it. GLM 4.7 Flash adds a further dimension: this model receives patches and appears to follow them, but introduces new errors in the process, suggesting that the "compression" problem is not merely about whether the student can read the patch, but whether it can integrate it without disrupting existing behaviour. This mirrors findings from the knowledge distillation literature, where aggressive compression ratios lead to diminishing returns [@sanh2019; @jiao2020].

#### Instruction patching as the dominant lever

The finding that instruction-level patches account for the majority of successful fixes resonates with research on prompt sensitivity. @sclar2023 demonstrated that LLM performance is highly sensitive to the specific wording and formatting of instructions. From this perspective, it is unsurprising that targeted instruction amendments yield the most reliable gains. The instruction section is where the model receives its "mental model" of the task, and deficiencies in this mental model are the most directly addressable through text.

The emergence of tool-schema fixes at the 20-task scale (20% of fixes for Qwen3 30B-A3B, but 0% for Qwen3.5 Flash at the same scale) suggests that the need for tool-level intervention is model-dependent: a stronger student's instruction-following capability renders tool-schema patches unnecessary for the same tasks. This is consistent with the three-phase escalation design (Section 3.5.3) and confirms that the escalation tiers are correctly ordered by generality.

#### Saturation and the limits of input-space evolution

The rapid saturation observed across all experiments mirrors a well-documented pattern in iterative prompt optimisation. @fernando2023 observed similar plateau effects in PromptBreeder. In our framework, saturation arises from two distinct mechanisms: task-level saturation (once the prompt contains sufficient guidance for a given task, additional patches are redundant) and interference (accumulated patches degrade performance on previously solved tasks).

The three-model comparison reveals that the interference problem is more complex than a simple correlation with instruction-following quality. Qwen3.5 Flash shows severe regression at 10 tasks but stability at 20 tasks, suggesting that task-pool size mediates interference effects. GLM 4.7 Flash shows the worst interference of any model despite not being the strongest instruction follower, indicating that the model's architectural robustness to prompt perturbation---distinct from its instruction-following accuracy---may be the key variable. This creates a practical design constraint: the optimal prompt evolution strategy must account for both the student model's instruction sensitivity and its robustness to prompt length and complexity growth.

### 4.6.3 Answering the Research Sub-Questions

#### Which failure modes are most responsive to prompt/tool evolution?

The data strongly indicate that policy comprehension failures---where the agent misinterprets or overlooks specific business rules---are the most responsive to prompt evolution. The 70--92% instruction-tier fix rate is consistent across all experiments and all three models, confirming that the dominant failure mode is addressable through natural-language instruction.

The three-model comparison adds nuance in two directions. First, tasks that are unfixable for weaker students (Tasks 9, 11, 12 with Qwen3 30B-A3B and GLM 4.7 Flash) can be fixed for a stronger student with the same patches. This means that some failures attributed to "structural resistance" are actually failures of student capability. Second, GLM 4.7 Flash demonstrates that even when the teacher correctly diagnoses a failure mode, the fix can fail if the student model introduces new errors when executing the patched prompt---a failure mode distinct from simply not understanding the patch.

#### What is the minimal volume of human demonstrations required?

The five-task experiment achieved a 20-percentage-point improvement using one demonstration per failing task. This extreme sample efficiency is consistent with GEPA's finding that even a few rollouts can produce large quality gains when feedback is linguistically rich [@agrawal2025]. The 20-task results show diminishing returns: more tasks provide more diverse failure signals, but the teacher cannot convert most of them into successful fixes.

#### Can such a framework outperform static agents and match RLHF-tuned agents?

The framework outperforms the static baseline for both Qwen models across all conditions. However, GLM 4.7 Flash at 10 tasks demonstrates that the framework can *underperform* the static baseline when the student model cannot absorb patches reliably. Whether the framework can match RLHF-tuned agents remains open. The ceiling of input-space evolution is bounded by what the student model can achieve under ideal prompting. The three-model comparison makes this ceiling visible: Qwen3.5 Flash achieves 80% at 10 tasks and 65% at 20 tasks with evolution, Qwen3 30B-A3B tops out at 50% and 30%, and GLM 4.7 Flash cannot exceed its baseline. The framework's ceiling tracks the student's inherent capability, not the teacher's diagnostic power.

### 4.6.4 Implications for Enterprise Deployment

The three-model results have direct practical implications. First, enterprises should invest in the strongest feasible base model before applying prompt evolution. The framework amplifies capability differences: Qwen3.5 Flash reaches 65% majority at 20 tasks versus Qwen3 30B-A3B's 30%.

Second, **model compatibility testing is essential before deploying the framework**. The GLM 4.7 Flash results demonstrate that prompt evolution can be actively harmful with an incompatible student model. A brief pilot evaluation (e.g., at 5 tasks) can reveal whether a given model can absorb patches without destabilisation.

Third, patch management is critical. The regression patterns differ by model: Qwen3.5 Flash requires sweep limits (two sweeps suffice at 10 tasks), GLM 4.7 Flash should not be evolved at all beyond small scales, and Qwen3 30B-A3B tolerates three sweeps with mild degradation. Possible management strategies include periodic prompt consolidation, regression testing against a held-out task set, and automated rollback when performance degrades.

Fourth, the efficiency problem at scale is significant. At 20 tasks, the teacher spent over 7 hours and 800+ messages on failed fix attempts for Qwen3 30B-A3B (53% fix rate), and comparable effort for Qwen3.5 Flash (45% fix rate). Future iterations should incorporate early termination heuristics---detecting when a task is likely unfixable and abandoning the attempt before exhausting all retries.

### 4.6.5 Relation to Concurrent and Adjacent Work

Several concurrent projects explore themes closely adjacent to this thesis. The Automated Design of Agentic Systems (ADAS) framework [@hu2024] uses meta-learning to evolve entire agent architectures. While ADAS achieves impressive results, it treats the agent as a fully mutable artifact. Our framework is more conservative and arguably more practical for enterprises that operate with fixed model deployments behind APIs.

The SCOPE framework [@pei2025] addresses self-evolving context optimisation. The AgentOptimizer [@zhang2024] treats agent functions as learnable weights. The AvaTaR framework [@wu2024] optimises LLM agents for tool-assisted knowledge retrieval. What distinguishes the present work is the combination of four elements: (1) human action traces as the primary supervision signal, (2) a teacher model that converts these traces into structured prompt patches, (3) evaluation on a tool-agent benchmark (τ²-bench) that requires multi-turn conversation, policy compliance, and database-state verification, and (4) systematic analysis across three student models demonstrating that the framework's effectiveness is contingent on student capability---including the first documented case (GLM 4.7 Flash) where prompt evolution causes net harm.

### 4.6.6 Limitations

Several limitations qualify the conclusions drawn above. First, the experiments cover only one domain (airline) with up to twenty tasks, which restricts the generalisability of the findings. Different domains (e.g., retail, finance) may exhibit different failure-mode distributions and different responsiveness to prompt evolution.

Second, the human action traces used were generated by the author, not by professional customer service agents. In a real enterprise setting, the quality and diversity of human demonstrations would differ.

Third, the use of an LLM as the user simulator introduces a confounding variable. The dual use of the same model family (Qwen3 30B-A3B) as both student agent and user simulator in the Qwen3 30B-A3B experiments means that improvements could partially reflect a favourable alignment between agent and simulator behaviours. The Qwen3.5 Flash and GLM 4.7 Flash experiments use different student models but the same user simulator, partially mitigating this concern.

Fourth, the evaluation uses only three trials per task, which provides limited statistical power. The stochastic nature of LLM outputs means that a task passing 2/3 versus 1/3 could reflect sampling noise rather than genuine improvement.

Fifth, the framework applies patches cumulatively without a mechanism for patch selection or retirement. The regression observed across multiple models---from mild (Qwen3 30B-A3B) to catastrophic (GLM 4.7 Flash)---highlights the need for more sophisticated patch management.

Sixth, the choice of Kimi K2.5 as the teacher model is pragmatic (availability via OpenRouter) rather than principled. A different teacher model might produce different patches, and the sensitivity of the framework to teacher model choice has not been studied.

Finally, while three student models provide a richer picture than prior work, the sample remains too small to establish robust statistical relationships between model characteristics and evolution effectiveness. The relationship is clearly non-monotonic (GLM 4.7 Flash has moderate baseline capability but the worst evolution outcome), suggesting that factors beyond raw capability---such as architectural robustness to prompt perturbation---play a role that the current experiments cannot fully characterise.

### 4.6.7 Future Work

The findings motivate several directions for future investigation.

First, the GLM 4.7 Flash failure mode raises the question of **what makes a model "evolution-compatible."** A systematic study across a wider range of student models---varying architecture, parameter count, and training methodology---could identify predictive features (e.g., instruction-following benchmarks, prompt sensitivity metrics) that predict whether a given model will benefit from or be harmed by prompt evolution.

Second, the **patch management problem** deserves dedicated investigation. Techniques such as retrieval-augmented patch selection, periodic prompt consolidation, regression-aware patch acceptance, and model-specific sweep limits could significantly extend the framework's longevity. The contrast between Qwen3.5 Flash at 10 tasks (severe regression) and 20 tasks (stable) suggests that the optimal strategy is scale-dependent as well as model-dependent.

Third, the finding that instruction-level guidance is the dominant lever motivates exploration of **multi-agent decomposition architectures**. If a single prompt cannot grow indefinitely without interference, it may be more effective to decompose complex tasks into sub-agents, each with a focused prompt and a narrow set of tools.

Fourth, the emergence of tool-schema fixes only for Qwen3 30B-A3B suggests that **the patch vocabulary should be adapted to the student model**. A stronger student may need only instruction patches, while a weaker student may benefit from a richer set of intervention types including tool-schema modifications, few-shot examples, or retrieval-augmented context injection.

Fifth, a comparison with the GEPA framework [@agrawal2025] on the same τ²-bench tasks would provide a direct baseline for the value of human traces versus self-reflective evolution. The GLM 4.7 Flash results suggest that self-reflection might fare even worse for models that cannot execute externally provided patches.

### 4.6.8 Concluding Remarks

This discussion has situated the experimental results within the broader landscape of prompt optimisation, knowledge distillation, and agent reliability research. The core contribution---a supervised prompt evolution framework that converts human action traces into durable agent improvements---addresses a genuine gap in the literature. The three-model comparison reveals that the framework's effectiveness depends critically on the student model: Qwen3.5 Flash achieves the highest ceilings (65% majority at 20 tasks), Qwen3 30B-A3B shows moderate but consistent improvement, and GLM 4.7 Flash demonstrates that the framework can be counterproductive with an incompatible student.

For enterprises, the practical takeaway is fourfold. First, meaningful performance gains can be achieved without fine-tuning, weight access, or large-scale data collection. Second, the framework's value scales with model capability---investing in a stronger base model amplifies the returns from prompt evolution. Third, model compatibility must be verified before deployment: a brief pilot evaluation can prevent the kind of regression observed with GLM 4.7 Flash. Fourth, patch management is not optional: accumulated patches will eventually degrade performance, with the severity and timeline varying by model. The path toward enterprise-grade AI agent reliability requires this kind of supervised evolution as one component within a larger system that also includes model selection, patch lifecycle management, and continuous evaluation.
