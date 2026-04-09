# Plan: Baseline Comparisons for Thesis

## Context

The thesis has been criticized for lacking comparison baselines. Currently, the 3 experimental conditions (Baseline B, Evolved K, Frontier F) evaluate the artifact's output but not the *optimization method* against alternatives. The GEPA paper (ICLR 2026 Oral) sets a high bar by comparing against 4 methods (GRPO, MIPROv2, TextGrad, Trace). The question is: what comparisons are both feasible and academically defensible for a master's thesis?

The key insight: **the right baselines test the thesis's specific design choices, not every conceivable alternative.** The thesis claims value from (a) a stronger external teacher, (b) per-failure iterative diagnosis, (c) validation before merge, and (d) three patch surfaces. Each baseline should isolate one of these.

---

## What to Include

### Baseline 1: Zero-Shot Teacher Rewrite ("batch rewrite")

**Tests:** Is iterative per-failure diagnosis better than giving the teacher everything at once?

**Context problem:** Each full failure trace is ~9K tokens (system prompt + tool schemas + conversation + requirements + reward). With 10-20 failures, sending full traces would be 90-180K tokens — technically within Kimi K2.5's 256K window but expensive, slow, and likely to degrade quality due to lost-in-the-middle effects.

**Solution: summary-based zero-shot.** Instead of full traces, give the teacher:
- The current system prompt + tool schemas (once, shared context)
- For each failure: only the **task requirements + reward breakdown** (what was expected and what went wrong), NOT the full conversation trace
- Ask the teacher to produce a single improved system prompt

This is actually a fairer baseline — it tests "can you improve the prompt from error reports alone?" vs the full framework's "per-failure full-trace deep diagnosis." It's what a human prompt engineer would realistically do: read failure summaries, not every transcript.

**Implementation:**
1. Load baseline evaluation results, call `extract_failures()`
2. For each failure, format: task requirements + `format_reward(reward_info)` (~500 tokens each)
3. Single prompt to Kimi K2.5: "Here is the agent's prompt, its tools, and N failure summaries. Write an improved system prompt."
4. No tool calling, no iteration, no validation — one completion
5. Evaluate via `run_tasks(system_prompt=result)` on the same task set

**Total context:** ~3K (system prompt) + ~5K (tool schemas) + N×500 (failure summaries) ≈ ~18K tokens for 20 failures. Very manageable.

**Why it matters:** This is the simplest reasonable automated baseline. If the full framework only marginally beats a single-shot rewrite, the elaborate per-failure loop isn't justified. If it beats it substantially, the iterative diagnosis with full traces is validated.

**Effort:** ~2h code, ~$3 API cost. New file: `evo/baselines/zero_shot_rewrite.py`

---

### Baseline 2: Student Self-Reflection (zero-shot variant)

**Tests:** Does using a stronger teacher model matter, or can the student fix itself?

**Implementation:**
- Same as Baseline 1, but use `STUDENT_MODEL` (Qwen3 30B-A3B) instead of `TEACHER_MODEL` (Kimi K2.5) for the rewrite
- Same failures, same prompt template, same evaluation

**Why it matters:** Directly tests the core claim that a capability gap enables better diagnosis. If the student can fix itself equally well, the teacher is unnecessary overhead. This also relates to Reflexion (Shinn et al., 2023) which uses self-reflection.

**Effort:** ~30min (modify Baseline 1 script), ~$5 API cost

---

### Baseline 3: Prompt-Only Ablation (ALREADY EXISTS)

**Tests:** Do tool schema patches and preprocessors add value beyond prompt changes?

**Status:** Already implemented in `_run_test_evaluation()` (parallel_loop.py:296-356). The test evaluation runs `prompt_only` (prompt + schemas, no preprocessors) alongside baseline and full evolved. Also, `FixResult.fix_tier` tracks which surface fixed each task.

**What to add:** Report the existing data properly as an ablation in the results chapter. Optionally add a pure prompt-only condition (no schema patches either) if the current prompt_only conflation is a concern.

**Effort:** ~2h analysis, $0 additional API cost

---

### Baseline 4: First-Come-First-Served Merge (no LLM merger)

**Tests:** Does the LLM merger step add value, or can a simpler deterministic strategy work?

**Known issue:** Naive sequential patch application causes conflicts — multiple teachers edit overlapping regions of the prompt. Simply concatenating patches in order will fail when a later patch's `old_text` no longer exists because an earlier patch already modified that region.

**Implementation: deterministic FCFS merge.**
- Load existing `LoopState` from a completed run
- Take all `FixResult` objects where `fixed=True`
- Apply patches sequentially via `apply_patches()` — when a patch's `old_text` isn't found, SKIP it (this already happens: `apply_patches` logs and skips failed patches)
- Report: how many patches applied vs skipped (conflict rate)
- Evaluate the partially-patched agent on test split

**Why it matters:** The conflict rate IS the finding. If 40% of patches conflict and the resulting agent underperforms, that validates the LLM merger as a necessary component. The comparison becomes: "FCFS merge applied X/Y patches (Z% conflict rate) and achieved A% pass rate vs B% with LLM-based merging."

**Effort:** ~2h code, ~$5 API cost. New file: `evo/baselines/fcfs_merge.py`

---

## What to Exclude (and Why)

### LoRA / GRPO -- EXCLUDE

**The argument (use this in the thesis defense):**

1. **Different problem setting.** The thesis explicitly defines an API-only constraint: the student model is accessed through OpenRouter with no weight access. LoRA/GRPO require model weights, gradient computation, and GPU infrastructure. Comparing them is comparing solutions to *different problems*: "how to improve an agent when you CAN modify weights" vs "how to improve an agent when you CANNOT." The thesis addresses the latter.

2. **Infrastructure impossibility.** Qwen3 30B-A3B via OpenRouter -- no local model, no GPU. Implementing LoRA would require downloading the model (~60GB), setting up training infrastructure, and running fine-tuning -- a completely different project.

3. **GEPA already made this comparison.** GEPA shows prompt evolution outperforms GRPO (24K rollouts) with 4-35x fewer rollouts across 6 benchmarks. The thesis can cite this result rather than reproducing it: "Agrawal et al. (2025) demonstrated that reflective prompt evolution outperforms GRPO by up to 20% with 35x fewer rollouts. The present work extends reflective evolution to multi-turn agentic settings, where RL methods face additional challenges from sparse, delayed rewards across multi-turn tool-calling conversations."

4. **Reframe the limitation.** Change ch5 Section 5.6 line 69 from comparing against "RLHF, DPO, or LoRA" to comparing against "alternative prompt optimization strategies." The thesis's scope is prompt-level methods, and the baselines above adequately cover that space.

### DSPy / MIPROv2 -- EXCLUDE (with caveat)

**The argument:**

1. **Task structure mismatch.** DSPy optimizes discrete NLP modules (classify, generate, retrieve) with few-shot example selection. tau2-bench tasks are multi-turn dialogues where the agent makes dozens of decisions across tool calls and messages. There is no natural "few-shot example" for a 15-turn customer service conversation -- each task has unique user scenarios, tool sequences, and policy requirements.

2. **MIPROv2's strength is example selection, which doesn't apply here.** MIPROv2's main innovation is joint optimization of instructions and few-shot demonstrations. tau2-bench evaluation doesn't use few-shot examples. Stripping MIPROv2 down to instruction-only optimization would remove its key advantage, making it an unfair comparison.

3. **Integration effort exceeds thesis scope.** Properly wrapping tau2-bench as a DSPy program with tool-use support would be a research project in itself -- weeks of engineering for a comparison that is likely unfair to DSPy.

4. **The zero-shot rewrite baseline IS a proxy.** A batch rewrite without iteration is essentially what generic prompt optimizers do: take feedback, produce a better prompt. The zero-shot baseline captures this idea without the integration overhead.

**Caveat:** If the advisor *insists* on DSPy, the minimum viable version would be: install DSPy, define a single `dspy.Module` that wraps the system prompt as a `dspy.Predict` signature, use MIPROv2 to optimize the instruction text, evaluate the result. This would take ~1-2 days and only test instruction optimization (no few-shot, no tool schemas). Have this as a fallback plan.

### Manual Prompt Engineering -- EXCLUDE

Not reproducible, depends on author skill, introduces human variable. The thesis is about automation.

### Random Patches -- EXCLUDE

Strawman. No reviewer will demand proof that random text edits are worse than targeted failure diagnosis.

---

## Implementation Plan

### Files to Create

1. **`evo/baselines/__init__.py`** -- empty
2. **`evo/baselines/zero_shot_rewrite.py`** -- Baselines 1 & 2
   - `zero_shot_rewrite(domain, failures, model) -> str` -- formats failures, calls teacher/student, returns new prompt
   - `run_zero_shot_comparison(domain, task_ids, seed, ...)` -- orchestrates full comparison
   - Reuses: `evo/evaluation/runner.py:run_tasks()`, `evo/evaluation/runner.py:extract_failures()`
   - Reuses: `evo/config.py` for model IDs, API keys
   - Uses `openai.OpenAI` client (same as teacher.py) for the rewrite call
3. **`evo/baselines/fcfs_merge.py`** -- Baseline 4
   - `apply_fcfs(loop_state) -> (prompt, schemas, code, conflict_count)` -- deterministic first-come-first-served
   - Reuses: `evo/reflection/patches.py:apply_patches()`, `evo/models.py:LoopState`
   - Reports conflict rate (patches skipped due to old_text not found)
4. **`evo/baselines/compare.py`** -- Analysis script
   - Loads all results, computes pass rates, generates comparison table

### Files to Modify

5. **`text/ch4_results.md`** -- Add "Comparison with Alternative Strategies" subsection
6. **`text/ch5_conclusion.md`** -- Update limitation at line 69 from "RLHF, DPO, LoRA" framing to "alternative prompt optimization strategies" framing
7. **`text/ch3_methodology.md`** -- Add brief description of comparison baselines in Section 3.3

### Execution Order

1. Run existing baseline evaluation to collect failure traces (or load from existing runs/)
2. Implement & run zero-shot teacher rewrite (Baseline 1)
3. Implement & run student self-reflection variant (Baseline 2)
4. Implement & run no-merge greedy (Baseline 4)
5. Analyze prompt-only ablation from existing data (Baseline 3)
6. Generate comparison table
7. Write up results subsection
8. Update methodology and limitations sections

---

## Expected Outcome Table (for results chapter)

| Condition | Type | pass^1 |
|-----------|------|--------|
| B: Unmodified baseline | Floor | X% |
| Zero-shot rewrite (teacher) | Baseline | ?% |
| Zero-shot rewrite (student) | Baseline | ?% |
| FCFS merge (no LLM merger) | Ablation | ?% |
| Prompt-only evolved | Ablation | X% |
| K: Full evolved | Intervention | X% |
| F: Frontier ceiling | Ceiling | X% |

---

## Note on Train/Test Splits

GEPA uses train/validation/test splits because it optimizes a prompt for a *task type* (all of HotpotQA) and must show the prompt generalizes to unseen questions. This thesis is different: the contribution is the *framework*, not the specific patches. The patches are domain-specific by design (Section 3.3.5). In production, the framework would run on the operator's specific tasks.

All baselines are therefore evaluated on the **same task set** as the main experiment. The question is "which optimization method fixes more failures on these tasks?" not "which one generalizes better." The existing test split infrastructure in `_run_test_evaluation()` can be used as a bonus analysis but is not required for the baseline comparisons.

---

## Verification

1. All baselines use **identical task IDs** as the main experiment
2. All baselines use identical evaluation: `run_tasks()` with same seed, num_trials, model
3. Compare pass^1 rates across conditions; compute gap closure for each
4. Report results in a single comparison table with all 7 conditions
5. Sanity check: baseline and frontier numbers should match existing experimental data exactly

---

## Total Cost Estimate

| Item | Engineering | API cost |
|------|------------|----------|
| Baseline 1 (zero-shot teacher) | 2h | ~$3 |
| Baseline 2 (self-reflection) | 30min | ~$5 |
| Baseline 3 (prompt-only analysis) | 2h | $0 |
| Baseline 4 (FCFS merge) | 2h | ~$5 |
| Results writeup | 3h | $0 |
| Methodology/limitations updates | 1h | $0 |
| **Total** | **~11h** | **~$13** |
