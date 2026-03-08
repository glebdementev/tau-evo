# Results Chapter Plan

## User Requests

### Main Conclusions

1. **A weak non-thinking model can be taught to perform better through input modifications** (prompt/tool-schema patching by a stronger teacher model)
2. **Most successful interventions target the instruction section** of the prompt (not tool schemas or guardrails)
3. **The weaker model has limited capacity to generalise**, so the largest gains appear on the smallest number of tasks -- as the task pool grows, per-task improvement shrinks

### Future Work

1. Testing on other weak non-thinking models already configured in the application (Qwen3.5 Flash, GLM 4.7 Flash)
2. Showing that end-to-end performance can be improved by autonomously decomposing tasks into subagents (motivated by finding that instruction-level guidance is the dominant lever)

### Experiment Status

- **Completed:** 1 experiment -- 5-task airline run (runs/5)
- **In progress:** 10-task airline run
- **Planned:** possibly a 20-task run
- Results section should be structured to accommodate 2--3 experiments with comparative analysis

---

## Data from runs/5 (5-task airline experiment)

### Setup

- Domain: airline (tau2-bench)
- Student: Qwen3 30B-A3B (non-thinking, via OpenRouter)
- Teacher: Kimi K2.5 (via OpenRouter)
- User simulator: Qwen3 30B-A3B
- 5 tasks evaluated (IDs: 0, 1, 3, 4, 5), 3 trials each, 3 sweeps
- Seed: 42

### Quantitative Results

**Aggregate pass rates (majority-vote per task, 3 trials):**

| Sweep | Task 0 | Task 1 | Task 3 | Task 4 | Task 5 | Overall pass rate |
|-------|--------|--------|--------|--------|--------|-------------------|
| 1 (baseline) | 0/3 | 2/3 | 1/3 | 3/3 | 2/3 | 8/15 (53%) |
| 2 | 1/3 | 2/3 | 2/3 | 3/3 | 3/3 | 11/15 (73%) |
| 3 | 1/3 | 3/3 | 3/3 | 3/3 | 1/3 | 11/15 (73%) |

**Task-level majority-vote outcomes by sweep:**

| Sweep | Passed (already OK) | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|---------------------|--------------------|--------------------|---------|
| 1 | 1 | 3 | 1 | 0 |
| 2 | 2 | 2 | 1 | 0 |
| 3 | 3 | 0 | 0 | 2 |

**Fix attempts (how many teacher tries needed):**

| Sweep | Attempt 1 (instruction) | Attempt 2 (instruction) | Attempt 3 (guardrail) |
|-------|------------------------|------------------------|-----------------------|
| 1 | 1 | 2 | 1 |
| 2 | 1 | 1 | 1 |
| 3 | 0 | 0 | 0 |

**Totals: 7 successful fixes across sweeps 1--2; 5 instruction, 2 guardrail.**

### Observations from Data (suggested additions for results)

1. **Rapid saturation on small task sets.** By sweep 3, all fixable tasks already pass -- the 2 remaining failures (Tasks 0 and 5) resist further patching. This is consistent with conclusion 3 (limited generalisation capacity).

2. **Diminishing returns across sweeps.** Sweep 1 fixes 4/5 failing tasks, sweep 2 fixes 3/5, sweep 3 fixes 0. The low-hanging fruit is consumed first; remaining failures may require qualitatively different interventions.

3. **Instruction patching dominates.** 5 of 7 fixes were instruction-type (71%), only 2 were guardrail-type. Guardrail fixes only appeared as attempt 3 (fallback). This strongly supports conclusion 2.

4. **Variance within tasks.** Task 0 never reliably passes (max 1/3 across all sweeps) -- the patches improve average behaviour but don't eliminate stochastic failure. Task 5 regresses from 2/3 to 1/3 in sweep 3, suggesting patches can introduce interference.

5. **Stable tasks stay stable.** Task 4 passes 3/3 in all sweeps -- evolution does not degrade already-passing tasks.

6. **Baseline is non-trivial.** The student already passes 53% at baseline, so the teacher is refining rather than teaching from scratch.

7. **Patch interference / regression.** Task 5 goes from pass in sweep 2 (3/3) to mostly fail in sweep 3 (1/3). Worth investigating whether accumulated patches cause interference on previously solved tasks.

---

## Proposed Results Chapter Structure

### 4.1 Experimental Setup
- Benchmark (tau2-bench airline domain), models, evolution loop parameters
- How metrics are computed (majority-vote over 3 trials per task)

### 4.2 Experiment 1: 5-Task Evolution (runs/5)
- Baseline performance
- Per-sweep improvement trajectory (heatmap figure, outcomes bar chart)
- Fix type breakdown (instruction vs guardrail)
- Qualitative examples of patches applied (from teacher.txt logs)

### 4.3 Experiment 2: 10-Task Evolution (pending)
- Same structure as 4.2
- Compare: does improvement rate hold with more tasks?
- Test generalisation hypothesis -- expect smaller per-task gains

### 4.4 Experiment 3: 20-Task Evolution (if run)
- Further scaling analysis

### 4.5 Cross-Experiment Comparison
- Scaling curve: improvement vs task count
- Saturation analysis
- Does the teacher's strategy change with more failures?

### 4.6 Discussion
- Instruction patching as the primary lever
- Limits of input-space-only evolution (no weight updates)
- Patch interference and regression
- Implications for multi-agent decomposition (motivation for future work)
