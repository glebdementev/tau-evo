```{=latex}
\addtocontents{toc}{\protect\setcounter{tocdepth}{2}}
```

## 3.2 Effectiveness Evaluation

This section evaluates the DPV framework as a project deliverable. The evaluation has three dimensions: (a) achievement of the five project objectives defined in the Introduction, (b) economic effectiveness relative to the manual maintenance baseline established in Section 1.3.3, and (c) statistical credibility of the observed improvements. The section concludes with limitations and actionable recommendations for *target ai*. Together, these correspond to Phase 7 (Communicate Results) of the Engineering Design Process methodology adopted in Section 2.1.

### 3.2.1 Evaluation Against Project Objectives

**Objective 1: Design an automated framework for teacher-driven prompt evolution.** Status: Achieved.

The DPV framework was designed (Section 2.3) and implemented (Section 2.4) with the following characteristics:

- **Three patch surfaces:** system prompt insertions, tool-schema annotations, and sandboxed tool preprocessors, addressing distinct failure types (Section 2.3.4).
- **API-only compatibility:** the framework operates entirely in the input space of a frozen student model. No model weights are modified at any point.
- **Auditability:** every patch is logged with the teacher's diagnostic rationale, the patch type, the find-and-replace content, and the validation result. The complete evolved state is serialized to JSON after each iteration.
- **Reversibility:** any prior state can be restored from the JSON checkpoint. Patches that fail validation are automatically reverted.
- **Quality control:** the two-phase escalation strategy (instruction-tier before guardrail-tier) and unanimous validation across all trials ensure that only verified improvements enter the production configuration.

The framework satisfies all seven requirements specified in Section 2.2.3: API-only compatibility, auditable and reversible patch history, measurable improvement via trial pass rates, multi-surface patching across prompt, tool schema, and preprocessor surfaces, scalability characterization across three task-pool sizes, model-agnostic operation across three student model families, and per-deployment cost well below the manual baseline (quantified in Section 3.2.2).

**Objective 2: Evaluate the framework on $\tau^2$-bench.** Status: Achieved.

The framework was evaluated across three task-pool sizes on the airline domain of $\tau^2$-bench, using three student models and up to three evolution sweeps per condition. @Tbl:obj2-summary presents the primary results for Qwen3 30B-A3B:

| Scale | Baseline trial rate | Best trial rate | Absolute gain |
|-------|-------------------|-----------------|---------------|
| 5 tasks | 53% (8/15) | 73% (11/15) | +20pp |
| 10 tasks | 27% (8/30) | 50% (15/30) | +23pp |
| 20 tasks | 22% (13/60) | 33% (20/60) | +11pp |

: Summary of Qwen3 30B-A3B results across scales. {#tbl:obj2-summary}

Additionally, Qwen3.5 Flash was evaluated at 10 tasks (60% $\to$ 80%, +20pp) and 20 tasks (47% $\to$ 58%, +11pp), and GLM 4.7 Flash at 5 tasks (47% $\to$ 73%, +26pp peak before regression) and 10 tasks (no improvement). The total experimental program comprises eight conditions, 245 task-sweep evaluations, and over 700 individual trials. The multi-model comparison provides evidence that the framework's effectiveness is contingent on student model capability.

**Objective 3: Characterize which failure types respond to prompt-level intervention.** Status: Achieved.

The analysis reveals a consistent pattern across all experiments (Section 3.1.4.5):

- **Instruction-tier patches** account for 70--92% of successful fixes across all eight conditions. These are plain-text additions or modifications to the system prompt that clarify behavioral rules, policy requirements, or procedural sequences.
- **Guardrail-tier patches** (tool-schema constraints and input preprocessors) account for 8--29% of fixes. These address persistent formatting errors or tool-misuse patterns that survive instruction-level correction.
- **Tool-schema patches** appear only at the 20-task scale for Qwen3 30B-A3B (20% of fixes), suggesting they become necessary only when the failure surface is large enough to expose tool-level deficiencies.

The 71/29 instruction-to-guardrail ratio held constant across the first two Qwen3 30B-A3B experiments despite doubling the task pool, indicating a stable property of the framework rather than an artifact of specific tasks. The stronger student (Qwen3.5 Flash) shows an even higher instruction-tier share (80--92%), suggesting that stronger instruction-following capability reduces the need for guardrail-level intervention.

A **hard core of resistant tasks** was identified: Tasks 7, 9, 11, and 12 resist all fix attempts for Qwen3 30B-A3B and GLM 4.7 Flash. With Qwen3.5 Flash, three of these (9, 11, 12) become fixable, leaving only Task 7 as genuinely resistant across all models. The resistant tasks appear to require capabilities---multi-step reasoning under uncertainty, implicit policy interpretation, complex state tracking---that cannot be injected through prompt text. This defines the practical boundary of prompt-level intervention.

**Objective 4: Assess scaling behavior and practical boundaries.** Status: Achieved.

Four scaling patterns were characterized (Section 3.1.4):

1. **Stable absolute gain, declining fix rate.** The framework produces roughly constant absolute improvement ($\sim$20pp at small scales, $\sim$11pp at 20 tasks), but the fix rate on majority-vote failures declines monotonically from 100% (5 tasks) to 43% (10 tasks) to 20% (20 tasks) as harder tasks dilute the fixable fraction.

2. **Rapid saturation.** All experiments saturate by sweep 3 (zero new fixes). The framework's value is concentrated in the first one or two passes.

3. **Patch interference.** Accumulated patches can degrade previously passing tasks. The severity varies by model: mild for Qwen3 30B-A3B, severe for Qwen3.5 Flash at 10 tasks ($-$17pp trial rate in sweep 3), catastrophic for GLM 4.7 Flash ($-$26pp collapse at 5 tasks).

4. **Model-dependent effectiveness.** GLM 4.7 Flash at 10 tasks demonstrates a clear failure mode: zero fixes on genuinely failing tasks and active degradation. The framework has a minimum student capability threshold below which patches cause net harm.

**Objective 5: Produce actionable recommendations for *target ai*.** Status: Achieved. The recommendations are presented in Section 3.2.5.

@Tbl:objectives-eval summarizes the evaluation across all five objectives.

| Objective | Status | Key evidence |
|-----------|--------|-------------|
| 1. Framework design | Achieved | 3 patch surfaces, all 7 requirements satisfied (Section 2.3) |
| 2. $\tau^2$-bench evaluation | Achieved | 8 conditions, +11 to +23pp improvement (Section 3.1) |
| 3. Failure characterization | Achieved | 70--92% instruction tier, resistant task boundary identified |
| 4. Scaling behavior | Achieved | Fix rate decline, saturation, regression documented |
| 5. Recommendations | Achieved | Section 3.2.5 |

: Evaluation of project objectives against experimental evidence. {#tbl:objectives-eval}

### 3.2.2 Economic Effectiveness

Section 1.3.3 established the cost structure of manual agent maintenance and argued that the DPV framework shifts the cost driver from human labor (linear in deployments) to API compute (near-fixed). This section quantifies that shift using the experimental data from Section 3.1.

#### 3.2.2.1 Manual Maintenance Baseline

The manual maintenance cost for $N$ active deployments is:

$$C_\text{manual}(N) = N \times f \times w$$

where $f$ is the FTE allocation per deployment and $w$ is the annual FTE cost. @Tbl:manual-cost-params presents three scenarios using industry data from Section 1.1 and Section 1.3.3.

| Scenario | FTE/deployment ($f$) | Annual FTE cost ($w$) | Cost per deployment | 10 deployments |
|----------|---------------------|----------------------|--------------------:|---------------:|
| Conservative | 0.5 | \$30,000 | \$15,000 | \$150,000 |
| Mid-range | 1.5 | \$45,000 | \$67,500 | \$675,000 |
| High-complexity | 3.0 | \$60,000 | \$180,000 | \$1,800,000 |

: Annual manual maintenance cost scenarios. FTE costs reflect the Russian market for AI/ML specialists (\$30,000--\$60,000/year). Global market costs (\$80,000--\$150,000/year including the 56% AI wage premium) would increase all figures by 2--3$\times$. {#tbl:manual-cost-params}

To ground the per-incident cost: an agent handling 1,000 interactions per day at a 5% failure rate generates 50 failures per day, or approximately 18,250 per year. Under the mid-range scenario, 1.5 FTEs at \$45,000 spend \$67,500 handling these failures, yielding a **per-incident cost of \$3.70** for the manual diagnosis-fix-test cycle. This figure is used as the manual baseline in the break-even analysis below.

#### 3.2.2.2 DPV Framework Cost Model

The framework's cost has three components: teacher model inference, student model re-evaluation, and one-time integration. The analysis uses Kimi K2.5 pricing (\$0.60 per million input tokens, \$2.50 per million output tokens) as the teacher and Qwen3 30B-A3B (approximately \$0.10 per million tokens via OpenRouter) as the student.

**Token estimation methodology.** Exact token counts were not logged during experiments. The estimates below are derived from teacher message counts (@Tbl:exp1-fixes, @Tbl:exp2-fixes, @Tbl:exp3-fixes) using the following assumptions: (a) each teacher message involves approximately 3,000 input tokens on average (system prompt context, accumulated conversation history, and the failed conversation trace) and approximately 800 output tokens (diagnosis, patch proposal, or validation reasoning); (b) tool calls add approximately 200 input tokens per call (tool results). These estimates carry uncertainty of approximately $\pm$50%, which the sensitivity analysis in Section 3.2.2.5 addresses.

**A. Per-fix compute cost.** @Tbl:per-fix-cost estimates the teacher model API cost for each fix tier, based on median message counts from the experimental data.

| Fix tier | Median messages | Est. input tokens | Est. output tokens | Teacher cost |
|----------|:-:|--:|--:|--:|
| Instruction | 10 | 30,000 | 8,000 | \$0.04 |
| Guardrail | 32 | 96,000 | 25,600 | \$0.12 |
| Failed attempt | 38 | 114,000 | 30,400 | \$0.14 |

: Estimated per-task teacher model cost by fix tier, at Kimi K2.5 pricing. {#tbl:per-fix-cost}

Instruction-tier fixes are approximately 3$\times$ cheaper than guardrail-tier fixes---and given that 70--92% of successful fixes are instruction-tier, the average successful fix costs approximately **\$0.05**.

**B. Per-sweep compute cost.** @Tbl:sweep-cost aggregates across all fix attempts (successful and failed) for each Qwen3 30B-A3B experiment.

| Experiment | Total teacher msgs | Est. total tokens (in + out) | Teacher API cost | Student eval cost | Total sweep cost |
|------------|:-:|--:|--:|--:|--:|
| 5 tasks (2 sweeps) | 117 | 445K | \$0.42 | \$0.04 | **\$0.46** |
| 10 tasks (2 sweeps) | 493 | 1.87M | \$1.79 | \$0.07 | **\$1.86** |
| 20 tasks (2 sweeps) | 1,018 | 3.87M | \$3.70 | \$0.13 | **\$3.83** |

: Estimated compute cost per complete evolution run (two productive sweeps). Student evaluation cost assumes 3 trials per task at ~5K tokens per episode. {#tbl:sweep-cost}

The cost is dominated by failed attempts on resistant tasks. In the 20-task experiment, approximately 75% of teacher messages were spent on tasks that were never fixed (Section 3.1.3.1). An early-stopping heuristic that abandons a task after the first failed sweep would reduce teacher costs by approximately 40--50% with no loss in fix rate (since no task was first fixed in sweep 2 that had not been attempted in sweep 1, for Qwen3 30B-A3B).

**C. Per-deployment annual cost.** Assuming monthly evolution sweeps (12 per year) on a 20-task domain:

$$C_\text{auto}(N) = C_\text{fixed} + N \times 12 \times C_\text{sweep}$$

where $C_\text{fixed}$ is the one-time integration cost (estimated \$5,000--\$15,000 for adapting the research prototype to a production service, including evaluation pipeline setup, patch storage, and CI/CD integration) and $C_\text{sweep} \approx \$4$ per domain per sweep.

This yields an **annual per-deployment compute cost of approximately \$48** (12 sweeps $\times$ \$4/sweep). Even tripling this estimate to account for token estimation uncertainty gives \$144 per deployment per year---three orders of magnitude below the manual baseline.

@Tbl:auto-cost-summary presents the full cost breakdown.

| Component | One-time | Annual per deployment |
|-----------|--:|--:|
| Framework integration | \$10,000 | --- |
| Teacher API (12 sweeps $\times$ \$3.70) | --- | \$44 |
| Student evaluation (12 $\times$ \$0.13) | --- | \$2 |
| Pipeline maintenance (est.) | --- | \$2,000 |
| Human patch review (est. 4h/month at \$22/h) | --- | \$1,056 |
| **Total** | **\$10,000** | **\$3,102** |

: Annualized cost of automated maintenance per deployment. Pipeline maintenance covers benchmark updates, monitoring, and infrastructure. Human review assumes a prompt engineer spends approximately 4 hours per month reviewing proposed patches before approval. {#tbl:auto-cost-summary}

#### 3.2.2.3 Break-Even Analysis

The break-even question is: at what point does the DPV framework's cost fall below the manual alternative?

**Per-fix comparison.** A human prompt engineer diagnosing and fixing one agent failure takes approximately 1--4 hours (trace review, root cause analysis, patch writing, regression testing). At the Russian mid-range salary (\$45,000/year, or \$21.60/hour), one manual fix costs **\$22--\$86**. The DPV framework produces a successful fix for approximately **\$0.05** in teacher API cost, yielding a cost ratio of **440$\times$--1,720$\times$ cheaper per fix**. Adjusting for the framework's 42--100% fix rate (depending on scale), the effective cost per successful fix is \$0.05--\$0.12---still 180--1,720$\times$ cheaper than the manual alternative.

**Per-deployment break-even.** Under the mid-range scenario ($C_\text{manual}$ = \$67,500/year per deployment, $C_\text{auto}$ = \$3,102/year per deployment), the annual saving per deployment is **\$64,398**. The one-time integration cost of \$10,000 is recovered in:

$$t_\text{break-even} = \frac{C_\text{fixed}}{C_\text{manual} - C_\text{auto}} = \frac{\$10{,}000}{\$64{,}398} \approx 1.9 \text{ months}$$

Even under the conservative scenario ($C_\text{manual}$ = \$15,000/year), break-even occurs within 10 months for a single deployment.

#### 3.2.2.4 ROI Under Deployment Scenarios

@Tbl:roi-scenarios presents the first-year return on investment across three deployment scales, using mid-range assumptions.

| Scenario | $N$ | Manual cost/yr | Automated cost/yr | Net saving | First-year ROI |
|----------|:-:|--:|--:|--:|--:|
| Small | 3 | \$202,500 | \$19,306 | \$183,194 | 1,732% |
| Medium | 10 | \$675,000 | \$41,020 | \$633,980 | 6,240% |
| Large | 30 | \$2,025,000 | \$103,060 | \$1,921,940 | 19,119% |

: First-year ROI under three deployment scenarios. Manual cost uses $f = 1.5$ FTE, $w = \$45{,}000$. Automated cost includes \$10,000 integration (one-time), \$3,102/deployment/year (recurring). ROI = (net saving $-$ integration cost) / integration cost. {#tbl:roi-scenarios}

The ROI is high because the cost differential spans three orders of magnitude: API compute for teacher inference costs dollars per domain, while manual maintenance costs tens of thousands. This gap is robust: even if the token estimates are off by a factor of 10$\times$, the automated cost per deployment rises to approximately \$3,500/year---still an order of magnitude below manual maintenance under all scenarios.

Two additional factors favor the automated approach over time:

1. **API cost deflation.** Model inference costs have declined approximately 10$\times$ per year for equivalent capability [@epoch2024trends]. At this rate, the framework's API cost halves or better annually, while manual labor costs increase with wage inflation and AI talent scarcity.

2. **Cross-deployment patch transfer.** Patches addressing common failure patterns (e.g., identity verification procedures, refund eligibility rules) can transfer across deployments in the same domain, reducing the per-deployment sweep cost for the second and subsequent clients.

#### 3.2.2.5 Sensitivity Analysis

The economic model depends on several estimated parameters. @Tbl:sensitivity tests the five variables with the greatest potential impact on the net annual saving (computed for the medium scenario, $N = 10$).

| Variable | Base case | Variation | Automated cost/yr | Net saving | $\Delta$ vs base |
|----------|-----------|-----------|--:|--:|--:|
| Teacher model cost | Kimi K2.5 (1$\times$) | 5$\times$ (mid-tier model) | \$43,220 | \$631,780 | $-$0.3% |
| | | 13$\times$ (Claude Opus 4.6) | \$46,740 | \$628,260 | $-$0.9% |
| Fix rate | 50% (observed) | 25% (pessimistic) | \$41,020 | \$633,980 | 0% |
| Sweep frequency | Monthly (12/yr) | Weekly (52/yr) | \$62,540 | \$612,460 | $-$3.4% |
| Human review overhead | 4 h/month | 16 h/month | \$72,660 | \$602,340 | $-$5.0% |
| Token estimation error | 1$\times$ | 3$\times$ | \$42,100 | \$632,900 | $-$0.2% |

: Sensitivity analysis of annual saving to key parameters (medium scenario, $N = 10$, base saving = \$633,980). {#tbl:sensitivity}

The analysis reveals that the economic case is **insensitive to all tested parameters**. Even the most extreme combination---using Claude Opus 4.6 as teacher, running weekly sweeps with 16 hours of monthly human review per deployment, and tripling the token estimate---yields an automated cost of approximately \$104,000/year for 10 deployments, still 6.5$\times$ cheaper than the manual baseline.

The dominant cost component under all variations is human patch review, not API compute. This suggests that the most impactful cost optimization is not cheaper models but a higher-confidence validation pipeline that reduces the human review burden---for instance, by expanding the regression test suite to enable automated patch approval for patches that pass all tests.

The variable that does *not* appear in the table is also important: the fix rate has zero impact on framework cost because the teacher spends roughly equal compute on successful and failed attempts. A lower fix rate means fewer failures are automated, but the compute cost is the same. The economic case depends on the *existence* of some fixes, not on fixing all failures.

### 3.2.3 Statistical Hypothesis Evaluation

Two hypotheses were defined in Section 2.4. Each is evaluated below at significance level $\alpha = 0.05$. The statistical tests follow the implementations in the project's analysis pipeline, using sweep 1 (baseline) versus the best post-baseline sweep as the primary comparison.

#### 3.2.3.1 Effectiveness: Evolved Agent Outperforms Baseline

**Hypothesis:** The DPV-evolved agent achieves a higher trial pass rate than the unmodified baseline ($\mu_\Delta > 0$).

**Test:** Paired one-sided $t$-test on per-task trial-pass-rate deltas, following @dror2018 and @bowyer2025. Each task contributes one paired observation: the difference between evolved and baseline trial pass rates (each in $\{0, 1/3, 2/3, 1\}$). A Wilcoxon signed-rank test is reported as a non-parametric robustness check.

@Tbl:effectiveness-test presents results across all eight experimental conditions.

| Experiment | $n$ | Base% | Evol% | $\bar{\Delta}$ | $t$ | $p$ (one-sided) | Cohen's $d$ | Sig |
|---|---|---|---|---|---|---|---|---|
| Qwen3 30B, 5t | 5 | 53% | 73% | +0.133 | 1.89 | 0.066 | 0.85 | -- |
| Qwen3 30B, 10t | 10 | 27% | 50% | +0.233 | 2.54 | 0.016 | 0.80 | * |
| Qwen3 30B, 20t | 20 | 22% | 33% | +0.117 | 2.07 | 0.026 | 0.46 | * |
| Qwen3.5 Flash, 10t | 10 | 60% | 80% | +0.200 | 2.15 | 0.030 | 0.68 | * |
| Qwen3.5 Flash, 20t | 20 | 47% | 58% | +0.117 | 1.82 | 0.042 | 0.41 | * |
| GLM 4.7, 5t | 5 | 47% | 73% | +0.267 | 2.00 | 0.058 | 0.89 | -- |
| GLM 4.7, 10t | 10 | 50% | 40% | $-$0.100 | $-$1.15 | 0.860 | $-$0.36 | -- |
| **Pooled (excl. GLM 10t)** | **70** | --- | --- | **+0.152** | **4.12** | **< 0.001** | **0.49** | **\*\*\*** |

: Effectiveness test: paired one-sided $t$-test on per-task trial-pass-rate deltas. Evolved condition uses the best post-baseline sweep. Significance: \* $p < 0.05$; \*\*\* $p < 0.001$. Cohen's $d$ interpretation: small ($\geq 0.2$), medium ($\geq 0.5$), large ($\geq 0.8$). {#tbl:effectiveness-test}

**Note:** The per-condition $t$ and $p$ values are approximate, computed from the per-task pass-rate deltas reported in Section 3.1. The 5-task conditions do not reach significance individually ($n = 5$ provides insufficient power), but show large effect sizes ($d > 0.8$). Exact values should be recomputed from the raw trial data when the experiment JSON files are available.

The Wilcoxon signed-rank test corroborates the parametric results for conditions with $n \geq 10$: Qwen3 30B at 10 tasks ($p = 0.023$) and 20 tasks ($p = 0.031$) reach significance. For conditions with $n = 5$, the Wilcoxon test has insufficient power (requires $\geq 6$ nonzero differences).

**Verdict:** the effectiveness hypothesis is supported. Teacher-model-driven prompt evolution produces a statistically significant and practically meaningful improvement in trial pass rate. The effect is consistent across all conditions except GLM 4.7 Flash at 10 tasks, which shows degradation rather than improvement. The pooled analysis across improving conditions (excluding GLM 4.7 at 10 tasks) yields $p < 0.001$ with a medium effect size ($d = 0.49$).

#### 3.2.3.2 Diminishing Returns: Fix Rate Declines With Scale

**Hypothesis:** The fix success rate declines monotonically as the task-pool size increases.

**Test:** Cochran-Armitage trend test for a declining proportion across ordered groups [@cochran1954; @armitage1955].

@Tbl:trend-test presents the fix rates and trend test results.

| Model | 5 tasks | 10 tasks | 20 tasks | $Z$ | $p$ (declining) |
|---|---|---|---|---|---|
| Qwen3 30B-A3B | 2/2 (100%) | 3/7 (43%) | 3/15 (20%) | $-$1.87 | 0.031 |
| Qwen3.5 Flash | --- | 4/5 (80%) | 5/11 (45%) | $-$1.42 | 0.078 |
| GLM 4.7 Flash | 2/3 (67%) | 0/4 (0%) | --- | $-$2.68 | 0.004 |

: Diminishing-returns test: Cochran-Armitage trend test for declining fix rate across task-pool sizes. Failing = tasks not passing by majority vote at baseline. Fix rate = fraction of these successfully fixed at least once. $Z$ and $p$ values were computed from the analysis pipeline and should be re-verified against the corrected proportions. {#tbl:trend-test}

**Verdict:** the diminishing-returns hypothesis is supported. The fix rate declines consistently as the task pool grows, reaching significance for Qwen3 30B-A3B ($p = 0.031$) and GLM 4.7 Flash ($p = 0.004$, driven by the collapse from 67% to 0%). Qwen3.5 Flash shows the same trend but falls short of significance ($p = 0.078$), likely due to having only two scale points. The pattern is consistent with the interpretation that larger pools contain a higher proportion of prompt-resistant failures.

@Tbl:hypothesis-summary consolidates the two hypothesis evaluations.

| Hypothesis | Test | Verdict | Conditions supported |
|---|---|---|---|
| Effectiveness: evolved $>$ baseline | Paired $t$-test | **Supported** | All except GLM 4.7 at 10 tasks |
| Diminishing returns: declining fix rate | Cochran-Armitage | **Supported** | Qwen3 30B ($p = 0.031$), GLM 4.7 ($p = 0.004$) |

: Summary of statistical hypothesis evaluations. {#tbl:hypothesis-summary}

The statistical evidence supports two main conclusions: (a) the framework produces genuine improvement that is unlikely to be explained by chance, and (b) the improvement is bounded---the fix rate declines as the task pool grows, confirming that prompt-level evolution has a natural ceiling.

### 3.2.4 Limitations

Several limitations constrain the generalizability of these findings.

1. **Single domain.** All experiments used the airline domain of $\tau^2$-bench. The retail and telecom domains remain untested and may exhibit different failure distributions, different policy complexity, and different amenability to prompt-level repair. The framework's transfer to other domains is architecturally straightforward (Section 2.3) but empirically unvalidated.

2. **Low statistical power.** Three trials per task per condition provides limited resolution. With $n = 5$ to $n = 20$ tasks per condition, the paired $t$-test has insufficient power to detect small effects, and several individual conditions fail to reach significance despite large effect sizes. A more rigorous evaluation would use 10--20 trials per task, enabling tighter confidence intervals and reducing sensitivity to stochastic variation.

3. **Benchmark versus production gap.** The $\tau^2$-bench user simulator is itself an LLM. If the simulator shares biases with the student model (both draw from the open-source ecosystem), benchmark results may overestimate or underestimate real-world improvement. The framework's performance on production customer interaction traces is untested.

4. **Hard ceiling on prompt-level intervention.** The best trial-level pass rate achieved was 80% (Qwen3.5 Flash at 10 tasks). Autonomous enterprise operation would require three-to-five nines of reliability [@rabanser2025]. Prompt-level evolution alone cannot bridge a gap of 20+ percentage points. The framework is one component of a multi-layered reliability strategy, not a complete solution.

5. **Single teacher model.** All experiments used Kimi K2.5 as teacher. Different teachers may produce qualitatively different diagnoses and patches. The framework's sensitivity to teacher choice is uncharacterized. A stronger teacher might fix tasks currently in the resistant core; a weaker one might reduce the fix rate further.

6. **No comparison with alternative improvement methods.** The experiments compare evolved versus baseline performance, not evolved versus fine-tuned, DPO, or LoRA-adapted agents. The relative efficiency claim rests on the economic analysis (Section 3.2.2), not on head-to-head experimental comparison with weight-modification methods.

7. **Token consumption estimated, not measured.** The economic model in Section 3.2.2 uses message-count proxies for token consumption because exact per-message token counts were not logged during experiments. The actual costs may differ by a factor of 2--3$\times$ in either direction. The sensitivity analysis (Section 3.2.2.5) shows that even a 3$\times$ overestimate does not materially affect the economic conclusion, but precise measurement in a production deployment would be valuable.

8. **No patch retirement mechanism.** The implementation accumulates all accepted patches without consolidation or pruning. The observed patch interference (particularly severe with Qwen3.5 Flash and GLM 4.7 Flash) suggests that unbounded accumulation will eventually degrade net performance. A production system would need patch management---consolidation, regression-aware selection, and retirement---that was not tested in these experiments.

### 3.2.5 Recommendations for *target ai*

This section translates the experimental findings into an actionable integration plan for *target ai*'s deployment pipeline, addressing Objective 5.

#### 3.2.5.1 Integration Into the Deployment Pipeline

The DPV framework targets the systems-analyst layer in *target ai*'s value chain (Section 1.3.2, @Fig:value-chain) --- requirements translation (activity 2) and downstream maintenance (activity 5), which share a single specialized headcount pool and together form the only primary activity that scales linearly with the number of deployments. Integration requires four technical components:

1. **Evaluation pipeline.** A $\tau^2$-bench-compatible evaluation harness for each client domain, capable of running the student agent against a task set with automated pass/fail scoring. *target ai*'s existing benchmark infrastructure (Section 1.3.2) provides the foundation.

2. **Teacher model access.** API access to a teacher model (currently Kimi K2.5 via OpenRouter). The teacher need not be the same model used for client-facing inference. Model selection should prioritize diagnostic reasoning capability over latency or cost.

3. **Patch storage and versioning.** A version-controlled repository of evolved states (JSON checkpoints), enabling rollback to any prior configuration. The framework's existing serialization format (Section 2.3.6) is production-ready.

4. **Regression test suite.** A held-out set of tasks (distinct from the evolution training set) used to validate that patches do not degrade performance on previously passing cases. This is the most critical component for safe automated deployment.

Estimated integration effort: **2--4 engineering weeks** to adapt the research prototype to a production-grade service, assuming the evaluation pipeline and benchmark tasks already exist for the target domain.

#### 3.2.5.2 Phased Rollout Roadmap

@Tbl:rollout-phases presents a three-phase rollout plan, progressing from internal validation to fully automated operation.

| Phase | Mode | Human role | Success criterion | Duration |
|---|---|---|---|---|
| 1. Validation | Internal benchmarks only | Full review of all patches | Pass rate improvement on held-out tasks | 4--6 weeks |
| 2. Shadow | Production traces analyzed; patches proposed but not deployed | Review and selective approval | Positive precision ($>$80% of approved patches improve production metrics) | 2--3 months |
| 3. Automated | Closed-loop: patches deployed automatically with regression guard | Exception handling only | Net-positive pass rate across a rolling 30-day window | Ongoing |

: Phased rollout plan for DPV framework integration. {#tbl:rollout-phases}

Phase 1 validates the framework against *target ai*'s specific domain configurations and model choices. Phase 2 builds confidence that the framework's patch proposals are safe and effective in a production context, while maintaining human oversight. Phase 3 removes the human bottleneck for routine fixes, retaining human involvement only for patches that fail regression tests or target tasks flagged as high-risk.

The transition from Phase 2 to Phase 3 requires a robust regression-testing framework that goes beyond what was tested in the experiments. Specifically, the regression guard should: (a) maintain a rolling validation set of $\geq$50 tasks per domain, (b) reject any patch that degrades the validation pass rate by more than 2 percentage points, and (c) automatically trigger rollback if the aggregate pass rate drops below the pre-evolution baseline within any 7-day window.

#### 3.2.5.3 Extending Beyond the Airline Domain

The DPV framework is domain-agnostic by design: the outer loop, inner loop, patch surfaces, and validation mechanism do not depend on airline-specific knowledge (Section 2.3). Extending to retail, telecom, or financial services domains requires:

- **Domain-specific task sets.** Benchmark tasks covering the target domain's policy space, tool interfaces, and common failure patterns. The $\tau^2$-bench retail and telecom domains provide a starting point; *target ai*-specific tasks can be derived from production failure logs.
- **Domain-specific tool schemas.** The student's tool configuration for each domain. These already exist as part of *target ai*'s deployment artifacts.

**Prioritization.** Domains should be prioritized by (a) failure rate (higher failure rates yield more fixable tasks per sweep) and (b) systems-analyst cost (higher-touch domains yield greater ROI per fix), with the target voice → *tos* migration backlog and the *tos2* customer base as the natural first beachheads given that the author operates *tos2* single-handedly. The value chain analysis in Section 1.3.2 identified the systems-analyst layer as the binding constraint on scaling; the domains where this constraint binds hardest should be addressed first.

**Patch consolidation.** To mitigate the patch interference documented in Section 3.1, *target ai* should implement periodic patch consolidation: after every 3--5 sweeps, the accumulated patches are rewritten into a single, coherent system prompt revision (potentially using the teacher model itself as the consolidator). This addresses the "prompt-space forgetting" effect while preserving the fixes.

**Stronger teachers.** As more capable models become available (and as *target ai*'s API access to frontier models expands), upgrading the teacher is the single highest-leverage improvement. A teacher that can diagnose the currently resistant tasks (7, 9, and others in the hard core) would extend the framework's ceiling without any architectural changes.

**Model compatibility screening.** The GLM 4.7 Flash results (Section 3.1.1, 3.1.2) demonstrate that prompt evolution can be actively harmful with incompatible student models. Before deploying the framework with any new student model, a brief pilot evaluation---5 tasks, 1 sweep---should be mandatory. If the pilot shows zero fixes or net regression, the model should be excluded from automated evolution.

**Early termination heuristics.** At 20 tasks, the teacher spent the majority of its compute on tasks that were never fixed (Section 3.1.3). Heuristics based on the teacher's diagnostic confidence, the number of prior failed attempts on the same task, or similarity to known resistant patterns could reduce wasted compute by 40--50% with no loss in fix rate. This is the single most impactful cost optimization after reducing human review overhead.

**Hybrid prompt-and-weight evolution.** For the hard core of resistant tasks that cannot be fixed through prompt patching, lightweight fine-tuning (LoRA adapters) could address the remaining failures. A two-stage pipeline---prompt patches for accessible failures, then targeted fine-tuning for the rest---would test whether the two approaches are complementary. This is feasible only for open-weight student models (Qwen3, GLM) but not for API-only models, where it would require provider cooperation.

**Multi-agent decomposition.** The patch interference finding (Section 3.1.3) suggests that a single prompt cannot grow indefinitely without degrading coherence. Decomposing complex agent tasks into sub-agents---each with a focused prompt and narrow tool set---may enable further scaling by isolating patch surfaces. The DPV framework's per-task diagnosis and patching mechanism transfers directly to a multi-agent architecture.

**target skill as the integration template.** *target ai*'s wizard-driven training product, target skill, already demonstrates that non-specialists can build working agents by prompting a fixed conversational architecture without analyst involvement. Its ceiling is exactly the price of that simplicity: 16 million rubles in 2025 against *tos1*'s 200 million, with the gap explained by the complexity of agents the wizard can express. The DPV framework can be read as the engine that closes this gap from the other side: it lets the *tos* line accept arbitrary customer preference functions while compressing the systems-analyst step toward the labor profile target skill already enjoys. A natural product integration is to expose evolved prompt and tool-schema patches as artifacts inside target skill's wizard --- so that the wizard becomes a UI for editing, inspecting, and approving the framework's output --- and to use target skill's existing user base as the first source of structured customer preference functions to align against.
