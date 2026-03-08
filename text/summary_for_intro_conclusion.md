# Summary Document for Introduction & Conclusion Writing

## What This Thesis Does

A teacher-driven prompt evolution framework that improves a weak LLM agent's performance on structured benchmarks without any weight updates. A stronger teacher model (Kimi K2.5, ~1T params) analyzes a weaker student's (Qwen3 30B-A3B, 3.3B active params) failed conversation traces on τ²-bench, diagnoses failures, and proposes patches to the student's prompt, tool schemas, and tool preprocessors. Only patches that pass strict validation (unanimous across all trials) are merged. The student model never changes—only its operating instructions do.

## Research Question

How can AI agent performance on structured benchmarks be improved through automated, teacher-model-driven prompt and tool evolution?

## The Gap

- Tool-using LLM agents are unreliable at enterprise scale
- Static prompting helps but plateaus; fine-tuning/RLHF is expensive and impractical for rapid iteration
- Automated prompt optimization exists (GEPA, DSPy, TextGrad, PromptBreeder) but has NOT been tested on multi-turn tool-calling benchmarks
- Knowledge distillation exists but only at weight level—nobody has done prompt-level teacher→student transfer for agentic tasks
- Combining teacher-driven prompt evolution + tool-agent benchmarks + human action traces = unstudied

## Benchmark: τ²-bench

Multi-turn customer-service benchmark. Simulated user reveals info incrementally. Agent must follow domain policies, call tools correctly, modify DB state. Binary pass/fail (reward must be 1.0). Three domains: airline (50 tasks), retail (114), telecom (114). Only benchmark combining multi-turn dialogue + tool calling + simulated user + domain policies.

## Method: Diagnose-Patch-Validate Loop

**Outer loop**: Evaluate student on all tasks → extract failures → teacher fixes each failure in parallel → merge winning patches → re-evaluate all tasks (catches regressions). Up to 3 sweeps.

**Inner loop (per failure)**: Teacher gets full failed trace + system prompt + tool schemas + requirements + reward breakdown. Diagnoses root cause, classifies failure (TOOL_MISUSE | POLICY_VIOLATION | REASONING_ERROR | COMMUNICATION_ERROR), proposes patches via tool calls. Student re-runs for validation. Only unanimous passes accepted. If fail, revert and retry.

**Two-phase escalation**: Phase 1 = prompt + schema patches only. Phase 2 (if Phase 1 fails) = unlocks tool preprocessors (sandboxed Python that coerces tool inputs).

**Three patch surfaces**:
1. Prompt patches — add/modify behavioral rules in system prompt
2. Tool schema patches — clarify parameter descriptions, add constraints in JSON schemas
3. Tool preprocessors — defensive input coercion (e.g., ensure ID has "#" prefix)

**Three experimental conditions**:
- B (Baseline): unmodified student, default prompt
- K (Evolved): student with teacher-patched prompt/tools
- F (Frontier ceiling): teacher model runs as agent directly

**Gap closure metric**: (K − B) / (F − B) × 100%

## Results

### Experiment 1: 5 tasks (airline, Qwen3 30B-A3B)

| Metric | Baseline | After Evolution |
|--------|----------|-----------------|
| Trial pass rate | 53% (8/15) | 73% (11/15) |
| Majority-vote pass rate | 60% (3/5) | 80% (4/5) peak, 60% final |
| Improvement | +20pp trial rate |
| Failing tasks | 4 | Fixed: 4 (100% fix rate) |

- Sweep 1: all 4 failures fixed (3 instruction, 1 guardrail). 100% fix success.
- Sweep 2: 3 tasks regressed and were re-fixed.
- Sweep 3: 0 new fixes, mild regression on Task 5 (patch interference).
- Saturates by sweep 3.

### Experiment 2: 10 tasks (airline, Qwen3 30B-A3B)

| Metric | Baseline | After Evolution |
|--------|----------|-----------------|
| Trial pass rate | 27% (8/30) | 50% (15/30) |
| Majority-vote pass rate | 30% (3/10) | 50% (5/10) |
| Improvement | +23pp trial rate |
| Failing tasks | 9 | Fixed: 5 (56% fix rate) |

- 4 tasks (7, 9, 11, 12) formed a "hard core" — resisted ALL fix attempts across both sweeps. 150+ msgs, 61 tool calls, 36 min wasted on them in sweep 1 alone.
- Improvement delayed by 1 sweep vs Exp 1 (patch fragility at scale).
- Same 7 successful fixes total, same 71/29 instruction/guardrail split.

### Experiment 3: 20 tasks (airline, Qwen3 30B-A3B) — NOT YET RUN

Pending.

### Qwen3.5 Flash as alternative student (projected)

- 5-task baseline: 5/5 perfect pass rate (no evolution needed)
- 10-task baseline: ~5/10 pass rate + ~3 additional from edits → ~8/10 projected (TBD)
- 20-task: will run next

### Cross-Experiment Patterns

| | 5 tasks | 10 tasks |
|--|---------|----------|
| Baseline trial rate | 53% | 27% |
| Final trial rate | 73% | 50% |
| Absolute gain | +20pp | +23pp |
| Fix rate | 100% (4/4) | 56% (5/9) |
| Successful fixes | 7 | 7 |
| Instruction tier | 71% | 71% |
| Guardrail tier | 29% | 29% |
| Sweeps to saturate | 3 | 3 |

## Key Findings (for intro/conclusion framing)

1. **It works**: Teacher-driven prompt evolution produces measurable, repeatable improvement on a multi-turn tool-calling benchmark. +20-23pp absolute gain.

2. **Instruction patches dominate**: 71% of fixes are prompt-level (adding missing policy rules, clarifying procedures). Supports Superficial Alignment Hypothesis — the model CAN do the task, it just doesn't know it SHOULD. Telling it in plain text suffices most of the time.

3. **Stable absolute gain, declining fix rate**: The framework fixes ~5 tasks regardless of pool size. Absolute pp gain is constant (~20pp), but fix rate drops as harder tasks dilute the pool (100% → 56%). More tasks = more unfixable ones.

4. **Hard core of resistant tasks**: Some failures require capabilities beyond what prompt/schema editing can provide. These tasks resist all attempts — likely need stronger models, fine-tuning, or architectural changes.

5. **Rapid saturation**: 3 sweeps exhaust the framework's capacity. Diminishing returns after sweep 1-2.

6. **Patch interference**: Accumulated patches can degrade previously-passing tasks. Analogous to catastrophic forgetting but in prompt space. Needs patch management for production.

7. **No weight updates needed**: Everything operates in the input space. Patches are versionable, reviewable, rollback-able. Compatible with API-only model access.

8. **Qwen3.5 Flash shifts the picture**: A stronger student starts at 100% on 5 tasks — evolution's value moves from "fixing fundamentals" to "edge case reliability." The framework's utility depends on the baseline gap.

## Contributions (unique combo)

1. Human action traces as supervision signal for prompt evolution (not self-reflection)
2. Teacher→student knowledge transfer at the prompt level (not weights)
3. Three patch surfaces (prompt + tool schemas + tool preprocessors)
4. Validated on a multi-turn tool-calling benchmark (τ²-bench) — first time automated prompt optimization is tested on this class of benchmark
5. Empirical evidence of scaling behavior (fix rate decline, hard core emergence, patch interference)

## Limitations to Acknowledge

- Single domain (airline only), up to 10-20 tasks
- One teacher-student pair tested
- 3 trials per task = limited statistical power
- User simulator = same model family as student (confound)
- No cross-domain transfer tested
- No comparison with RLHF/fine-tuning baselines
- Cumulative patching with no retirement mechanism
- Far from enterprise 99.99% reliability (best: 73% at 5 tasks)

## Theoretical Anchors

- **Superficial Alignment Hypothesis** (Zhou et al. 2023/LIMA): alignment mostly teaches style/format → prompt text should suffice
- **Knowledge distillation** (Hinton 2015): but at prompt level, not weight level
- **Prompt sensitivity** (Sclar et al. 2023): up to 76pp swing from formatting alone; diagnostic-driven edits are meaning-bearing, not noise
- **Agent reliability gap** (Rabanser et al. 2025): accuracy improves faster than reliability; 3-5 nines needed for enterprise; current agents nowhere close
- **GEPA** (Agrawal et al. 2025, ICLR 2026 oral): closest methodological precedent — reflective prompt evolution with LLM traces, but uses self-reflection not external teacher, and targets reasoning/classification not tool-calling
