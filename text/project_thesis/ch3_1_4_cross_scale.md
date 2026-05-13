## 3.4 Cross-Scale and Cross-Model Comparison

#### Scaling Curve: Qwen3 30B-A3B

@Tbl:cross-experiment-qwen3 summarises the key metrics across all three scales for Qwen3 30B-A3B.

| Tasks | Base trial | Best trial | Gain (pp) | Failing | Fixed | Fix rate |
|-------|------------|------------|-----------|---------|-------|----------|
| 5 | 53% (8/15) | 73% (11/15) | +20 | 2 | 2 | 100% |
| 10 | 27% (8/30) | 50% (15/30) | +23 | 7 | 3 | 43% |
| 20 | 22% (13/60) | 33% (20/60) | +11 | 15 | 3 | 20% |

: Cross-scale summary for Qwen3 30B-A3B. Improvement is measured in percentage points of trial pass rate. Failing = tasks not passing by majority vote at baseline. Fix rate = fraction of these failing tasks successfully fixed at least once across sweeps 1--2. The teacher also produced verified fixes for additional tasks that passed by majority but failed individual trials (see Sections 3.1--3.4 per-experiment details). {#tbl:cross-experiment-qwen3}

The scaling curve reveals a consistent pattern: the absolute improvement is stable at small scales (+20pp to +23pp from 5 to 10 tasks) but halves at 20 tasks (+11pp), while the fix rate declines monotonically: from 100% (5 tasks) to 43% (10 tasks) to 20% (20 tasks). Each doubling of the task pool brings a larger proportion of majority-vote failures that resist prompt-level repair, and additional tasks primarily contribute unfixable failures that consume teacher effort.

The number of successful fixes is also instructive: 7 at 5 tasks, 7 at 10 tasks, and 10 at 20 tasks. While the absolute count grows slightly with scale, the growth is sub-linear; doubling the task set from 10 to 20 yields only 3 additional fixes. The framework does not discover fundamentally more failure modes at larger scales; it mostly encounters more instances of the same resistant patterns.

#### Scaling Curve: Qwen3.5 Flash

| Tasks | Base trial | Best trial | Gain (pp) | Failing | Fixed | Fix rate |
|-------|------------|------------|-----------|---------|-------|----------|
| 5 | 100% (15/15) | 100% (15/15) | 0 | 0 | 0 | N/A |
| 10 | 60% (18/30) | 80% (24/30) | +20 | 5 | 4 | 80% |
| 20 | 47% (28/60) | 58% (35/60) | +11 | 11 | 5 | 45% |

: Cross-scale summary for Qwen3.5 Flash. {#tbl:cross-experiment-flash}

The scaling curve for Qwen3.5 Flash shows a pattern distinct from Qwen3 30B-A3B. At 5 tasks, no evolution is needed. At 10 tasks, the improvement is +20pp with an 80% fix rate. At 20 tasks, the improvement halves (+11pp trial) and the fix rate drops to 45%, mirroring the diminishing-returns pattern seen with Qwen3 30B-A3B. However, the majority-vote improvement at 20 tasks is +20pp, from 45% to 65%, because the stronger student converts more fixes into reliable majority-vote passes.

The regression profile also differs. At 10 tasks, Qwen3.5 Flash shows sweep-3 regression (-17pp trial, -10pp majority). At 20 tasks, this regression disappears: the majority rate holds steady at 65% across sweeps 2 and 3, with only marginal trial-rate improvement (+1pp). The larger task pool may have a stabilising effect, diluting the impact of any single conflicting patch across more tasks.

#### Scaling Curve: GLM 4.7 Flash

| Tasks | Base trial | Best trial | Gain (pp) | Failing | Fixed | Fix rate |
|-------|------------|------------|-----------|---------|-------|----------|
| 5 | 47% (7/15) | 73% (11/15) | +26 | 3 | 2 | 67% |
| 10 | 50% (15/30) | 50% (15/30) | 0 | 4 | 0 | 0% |

: Cross-scale summary for GLM 4.7 Flash. The model is dropped at 20 tasks. {#tbl:cross-experiment-glm}

GLM 4.7 Flash presents a negative case. At 5 tasks, the framework produces a peak improvement of +26pp trial and +40pp majority at sweep 2, comparable to the other models. At 10 tasks, the framework produces zero net improvement; worse, it actively degrades performance from the baseline. The fix rate on genuinely failing tasks drops from 67% to 0%.

The contrast between scales is visible in the pass rates. At 5 tasks, the model can absorb three instruction patches and one guardrail patch without destabilisation. At 10 tasks, the larger patch surface creates enough interference to prevent any gains. This scale-dependent collapse motivated the decision to drop GLM 4.7 Flash from the 20-task experiment.

#### Cross-Model Comparison at Matched Scales

| Scale | Model | Base maj. | Best maj. | Fix rate | Fixes (I/G/T) | Unfixable |
|-------|-------|-----------|-----------|----------|---------------|-----------|
| 5 | Qwen3 30B-A3B | 60% | 80% | 100% | 5/2/0 | 0 |
| 5 | Qwen3.5 Flash | 100% | 100% | N/A | 0/0/0 | 0 |
| 5 | GLM 4.7 Flash | 40% | 80% | 67% | 3/1/0 | 1 |
| 10 | Qwen3 30B-A3B | 30% | 50% | 43% | 5/2/0 | 4 |
| 10 | Qwen3.5 Flash | 50% | 80% | 80% | 4/1/0 | 1 |
| 10 | GLM 4.7 Flash | 60% | 60% | 0% | 3/1/0 | 4 |

: Cross-model comparison at matched scales (5 and 10 tasks). Fixes column shows instruction/guardrail/tools counts. {#tbl:cross-model}

At 20 tasks, only two models are compared:

| Metric | Qwen3 30B-A3B | Qwen3.5 Flash |
|--------|---------------|---------------|
| Baseline majority | 25% | 45% |
| Best majority | 30% | 65% |
| Fix rate (failing) | 20% | 45% |
| Fixes (instr/guard/tools) | 7/1/2 | 11/1/0 |
| Unfixable tasks | 12 | 5 |

: Cross-model comparison at 20 tasks. {#tbl:cross-model-20}

![Knowledge transfer effectiveness: fix rates and improvement by model and scale, illustrating model-dependent framework utility.](figures/fig_14_knowledge_transfer.png){#fig:knowledge-transfer}

The unfixable set is model-dependent, not task-intrinsic. At 10 tasks, Qwen3 30B-A3B and GLM 4.7 Flash share the same four unfixable tasks (7, 9, 11, 12). With Qwen3.5 Flash, three of these (9, 11, 12) become fixable, leaving only Task 7 as genuinely resistant across all three models. At 20 tasks, the unfixable set shrinks further for Qwen3.5 Flash (5 tasks vs 12), with Tasks 7, 9, 14, 23, and 33 forming the persistent hard core.

#### Instruction vs Guardrail Ratio Across All Experiments

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

Instruction-level patching dominates across all experiments (70--92% of fixes), confirming it as the primary mechanism of improvement. Two trends stand out. First, the stronger student (Qwen3.5 Flash) shows a progressively higher instruction-tier share as scale increases (80% at 10 tasks, 92% at 20 tasks), suggesting that stronger instruction-following capability reduces the need for guardrail or tool-level interventions. Second, tool-schema patches appear only for Qwen3 30B-A3B at 20 tasks (2 of 10 fixes); neither Qwen3.5 Flash nor GLM 4.7 Flash required tool-level intervention at any scale.

#### Saturation Analysis

All experiments saturate by sweep 3 (zero new fixes). However, the improvement timeline and regression pattern vary markedly:

- **Qwen3 30B, 5 tasks**: improvement materialises immediately (sweep 1 → 2: +20pp trial). Sweep 3 shows no further gain and mild regression (-20pp majority).
- **Qwen3 30B, 10 tasks**: improvement is delayed (sweep 1 → 2: +3pp; sweep 2 → 3: +20pp). The delay reflects patch fragility at larger scale.
- **Qwen3 30B, 20 tasks**: improvement is immediate but modest (sweep 1 → 2: +11pp). Sweep 3 shows slight regression (-3pp trial rate).
- **Qwen3.5 Flash, 10 tasks**: improvement is immediate (sweep 1 → 2: +20pp). Sweep 3 shows regression (-17pp trial rate, -10pp majority).
- **Qwen3.5 Flash, 20 tasks**: improvement is immediate (sweep 1 → 2: +10pp trial, +20pp majority). Sweep 3 shows stability (+1pp trial, 0pp majority).
- **GLM 4.7, 5 tasks**: improvement peaks at sweep 2 (+26pp trial, +40pp majority). Sweep 3 collapses to baseline (-26pp trial, -40pp majority).
- **GLM 4.7, 10 tasks**: continuous decline across all sweeps (-10pp trial from baseline to sweep 3, -10pp majority).

The GLM 4.7 Flash results introduce a new failure pattern not seen with the Qwen models: monotonic degradation under patch accumulation. In all Qwen experiments, the framework produces at least some improvement before saturating. With GLM 4.7 Flash at 10 tasks, no improvement occurs at any point. This suggests that the framework has a minimum student capability threshold below which patches cause net harm.
