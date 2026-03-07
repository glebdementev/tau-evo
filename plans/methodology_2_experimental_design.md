# Methodology Document 2: Experimental Design and Conditions

**Purpose**: Define the experimental conditions, justify model choices, and explain the logic of the three-way comparison.

---

## 1. Experimental Conditions

The experiment evaluates three conditions across three domains (airline, retail, telecom). Each condition uses the same tau2-bench evaluation infrastructure.

| Condition | Label | Student Model | Teacher Model | Prompt State |
|-----------|-------|--------------|---------------|-------------|
| **Baseline** | B | Qwen3 30B-A3B | — | Default tau2-bench prompt (unmodified) |
| **Kimi-evolved** | K | Qwen3 30B-A3B | Kimi K2.5 | Prompt + tool schemas evolved via reflection loop |
| **Frontier ceiling** | F | Kimi K2.5 | — | Default tau2-bench prompt (unmodified) |

### Condition B: Baseline

The student model runs on tau2-bench tasks with no modifications whatsoever. The system prompt is tau2's default:

```
<instructions>
You are a customer service agent that helps the user according to the <policy> provided below.
In each turn you can either:
- Send a message to the user.
- Make a tool call.
You cannot do both at the same time.

Try to be helpful and always follow the policy. Always make sure you generate valid JSON only.
</instructions>
<policy>
{domain_policy}
</policy>
```

Tool schemas are the originals from tau2-bench. No preprocessors. This establishes the performance floor.

In code, this is simply a call to `run_baseline()` with no `system_prompt`, `tool_schemas`, or `tool_code` arguments — EvolvableAgent falls through to its default behavior, which replicates LLMAgent exactly.

### Condition K: Kimi-Evolved

The student model runs with an evolved prompt and tool configuration produced by the evolution loop (Document 3). The evolved state includes:

1. **A modified system prompt**: the original prompt with additions/replacements made by the teacher's `patch_prompt` tool calls. These additions are typically concrete behavioral rules like "Always verify the customer's identity before making changes" or "When the reservation ID doesn't start with #, prepend # before calling the tool."

2. **Modified tool schemas**: tool description JSON with changes made by `patch_tool` calls. These might clarify parameter formats, add constraints to descriptions, or note edge cases.

3. **Tool preprocessors**: Python functions that transform tool inputs before execution, added by `patch_tool_code` calls. These act as guardrails — e.g., ensuring ID formats are correct even if the LLM produces them wrong.

The evolved state is the output of `run_loop()` — specifically `LoopState.system_prompt`, `LoopState.tool_schemas`, and `LoopState.tool_code`. These are passed into `run_baseline()` for the final evaluation.

### Condition F: Frontier Ceiling

Kimi K2.5 runs as the student agent directly, using the default (unmodified) tau2-bench prompt and tools. This measures the upper bound — how well the strongest available model performs on the same tasks without any evolution.

In code, this is `run_baseline()` with `student_model="moonshotai/kimi-k2.5"` and no prompt/tool modifications.

The frontier ceiling serves two purposes:
1. **Upper bound**: defines the maximum achievable performance with current models, against which evolved performance is measured.
2. **Gap closure denominator**: enables computing `(K - B) / (F - B)`, which normalizes for domain difficulty.

---

## 2. Model Selection Justification

### Why Qwen3 30B-A3B as Student

The student model must be:
1. **Strong enough** to produce meaningful tau2-bench scores (not 0% baseline).
2. **Weak enough** relative to frontier that there is headroom for improvement.
3. **Cost-effective** for many evaluation runs (each evolution iteration requires multiple full benchmark runs).

Qwen3 30B-A3B (released by Alibaba, February 2026) is a Mixture-of-Experts model with 30B total parameters but only 3B active per token. This makes it:
- Fast and cheap via OpenRouter API
- Capable enough for tool-calling and multi-turn dialogue
- Demonstrably imperfect on tau2-bench tasks, leaving room for evolution

The `config.py` also lists `qwen/qwen3.5-flash-02-23` (Qwen3.5 Flash) and `z-ai/glm-4.7-flash-20260119` (GLM 4.7 Flash) as alternative student models, selectable from the web dashboard. These enable cross-student ablation experiments.

### Why Kimi K2.5 as Teacher

The teacher model must be:
1. **Significantly stronger** than the student at the target task domain.
2. **Strong at tool-calling comprehension** — it needs to analyze multi-turn conversations involving function calls and diagnose tool-use errors.
3. **Long context** — it ingests full conversation traces (often 5-15 turns with tool calls and results), the system prompt, all tool schemas, and task requirements in a single prompt.
4. **Architecturally independent** from the student — avoids the criticism that improvement comes from "a bigger version of the same model."
5. **Cost-effective** for hundreds of reflection calls.

Kimi K2.5 (Moonshot AI, January 2026) meets all criteria:
- 256K context window
- Strong agentic reasoning capabilities
- OpenAI-compatible API at ~$0.60/M input, ~$2.50/M output
- Built by a different organization (Moonshot AI) than the student (Alibaba/Qwen)

### Why the Same Model for User Simulation

The user simulator uses the same model as the student (`qwen/qwen3-30b-a3b`). tau2-bench's user simulator follows scripted scenarios, so it doesn't need frontier-level capabilities — it just needs to coherently play the customer role. Using the same cheap model for both keeps costs low.

---

## 3. Three-Way Comparison Logic

The three conditions form a **floor–intervention–ceiling** comparison:

```
B (Baseline) ──── K (Evolved) ──── F (Frontier)
     │                  │                 │
   Floor          Intervention         Ceiling
  "How bad       "How much did       "How good
   is it?"       evolution help?"     can it get?"
```

**Why this structure matters:**

1. **B alone is insufficient**: a pass rate of, say, 60% tells you nothing without context. Is 60% good? Bad? Improvable?

2. **K vs B shows improvement**: if evolved pass rate exceeds baseline, the framework demonstrably helps. But by how much? Is a 10% improvement impressive or trivial?

3. **F provides normalization**: if the frontier model achieves 90% and baseline is 60%, then the gap is 30 percentage points. If evolution reaches 75%, that's 50% gap closure — half the teacher's advantage was transferred to the student through prompt engineering alone, with no weight changes.

4. **F also tests the premise**: if the frontier model scores similarly to the student, there's no meaningful gap to close and the entire approach is moot for that domain.

---

## 4. Per-Domain Independence

Each domain is evolved independently. There is no cross-domain transfer of patches.

**Why**: each domain has a unique policy, unique tools, and unique failure patterns. A rule learned from airline cancellation failures (e.g., "always check refund eligibility before cancelling") is meaningless in the telecom domain. The evolution loop runs separately for each domain, producing domain-specific evolved prompts.

In code, this is natural — `run_loop()` takes a `domain` parameter, loads that domain's environment/tools/policy, and all evolution happens within that domain. The `LoopState` output contains the evolved prompt for one specific domain.

---

## 5. Reproducibility Parameters

### Fixed Parameters Across All Conditions

| Parameter | Value | Location |
|-----------|-------|----------|
| Seed | 42 | `config.py:57`, passed to RunConfig |
| Trials per task | 1 | Hardcoded in `runner.py:56` |
| Teacher temperature | 0.3 | `teacher.py:169` |
| Reasoning suppression | `{"extra_body": {"reasoning": {"effort": "none"}}}` | `config.py:45` |
| Max conversation steps | tau2 default (varies by domain) | Set by tau2 internally |

### Variable Parameters (CLI-configurable)

| Parameter | Default | CLI Flag | Description |
|-----------|---------|----------|-------------|
| Domain | `airline` | `--domain` | Which domain to evaluate |
| Num tasks | 5 | `--num-tasks` | Tasks per evaluation (clamped to domain max) |
| Max iterations | 3 | `--max-iterations` | Outer loop iterations |
| Max retries | 2 | `--max-retries` | Teacher retries per failed task |
| Parallelism | 4 | `--parallelism` | Max concurrent workers |
| Seed | 42 | `--seed` | Random seed for task selection |
| Task IDs | None | `--task-ids` | Specific tasks (overrides num-tasks) |

### Software Versions

| Component | Version/Source |
|-----------|---------------|
| Python | 3.12 (required >=3.11) |
| tau2-bench | Commit `37bfc31` (v0.1.1+37) |
| Build system | uv + hatchling |
| LLM routing | litellm (via tau2) |
| Teacher client | openai Python SDK >=1.0 |
| API provider | OpenRouter (`https://openrouter.ai/api/v1`) |

---

## 6. What Constitutes "Passing" and "Failing"

### Binary Pass/Fail

A task **passes** if `reward_info.reward >= 1.0`. A task **fails** if `reward_info.reward < 1.0`.

This is the strictest possible criterion — the agent must satisfy ALL evaluation criteria (correct actions, correct database state, correct communication) to pass. A single missed action or wrong parameter value results in failure.

### Reward Composition

tau2-bench's evaluator combines multiple sub-scores:
- **Action evaluator**: checks that the agent called the expected tools with the expected arguments, in the expected order.
- **Environment evaluator**: checks post-conversation database state against assertions.
- **Communication evaluator**: checks natural-language assertions about the conversation.

The overall reward is a weighted combination. A reward of 0.0 typically means a complete failure (wrong actions entirely); a reward of 0.5 might mean some actions were correct but others were missed; a reward of 0.8 might mean all actions were correct but a communication criterion was missed.

### Fix Success Criterion

During the evolution loop, a fix is considered successful when:
```python
fixed = patched_reward > baseline_reward
```

Note this is a **strict improvement** criterion, not "reaches 1.0." A fix that improves reward from 0.0 to 0.5 counts as successful and its patches are merged into the global state. This allows incremental progress — the evolved prompt accumulates partial improvements across iterations.
