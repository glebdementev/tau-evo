# Revised Experimental Plan: Model-Fixes-Model Architecture

**Gleb Dementev — BABDS242**
**Revised: March 2026**

---

## 1. The Core Idea

Drop all manual trace labeling and on-premise GPU serving. Instead, the entire pipeline runs through APIs:

- **Qwen 3.5** (the "student") runs as the agent on τ²-bench. It fails on some tasks.
- **Kimi K2.5** (the "teacher") receives the failed conversation traces, analyzes what went wrong, and proposes prompt/tool patches.
- The patched prompt goes back to Qwen. Repeat until convergence.

This replaces "human-in-the-loop" with **"strong-model-in-the-loop."** The thesis question becomes: *can a stronger model serve as a scalable, automated substitute for human supervisors in the supervised evolution framework?*

---

## 2. Why These Two Models

### Qwen 3.5 — the Student

Qwen 3.5 was released February 16, 2026, under Apache 2.0. The family includes several sizes worth considering:

| Variant | Total Params | Active Params | Notes |
|---------|-------------|---------------|-------|
| Qwen3.5-397B-A17B | 397B | 17B | Flagship MoE, 256K context, 201 languages |
| Qwen3.5-35B-A3B | 35B | 3B | Best efficiency — outperforms Qwen3-235B |
| Qwen3.5-27B | 27B | 27B (dense) | Strong agentic reasoning |

**Recommended: Qwen3.5-27B or Qwen3.5-35B-A3B.** Either is strong enough to produce meaningful tau2 scores but weak enough (relative to frontier) that there is real room for improvement. The 397B flagship would likely score too high, leaving little headroom for the framework to demonstrate gains.

Access: via Alibaba DashScope API or any OpenAI-compatible endpoint (LiteLLM handles routing).

### Kimi K2.5 — the Teacher

Released January 26, 2026 by Moonshot AI. It is a frontier-class model with strong agentic and reasoning capabilities, 256K context, and an OpenAI-compatible API. API pricing is approximately $0.60/M input tokens and $2.50/M output tokens — roughly 13× cheaper than Claude Opus 4.6.

Kimi K2.5 has four modes (Instant, Thinking, Agent, Agent Swarm). For the reflection/teaching role, use **Thinking mode** — it produces extended reasoning chains that are ideal for failure diagnosis.

Why Kimi specifically:
- Strong tool-calling understanding (important for analyzing *tool-use* failures).
- Long context window (256K) — can ingest full multi-turn conversation traces without truncation.
- Cost-effective — the optimization loop requires many reflection calls.
- Architecturally independent from Qwen — avoids the criticism that the "teacher" is just a bigger version of the same model.

---

## 3. Revised Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Optimization Loop                             │
│                                                                 │
│  Iteration 0: Seed prompt (τ²-bench default)                   │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────────┐     ┌──────────────────┐                     │
│  │ Qwen 3.5     │────▸│ τ²-bench eval    │                     │
│  │ (Student)     │     │ (airline/retail/  │                     │
│  │ via API       │     │  telecom)        │                     │
│  └──────────────┘     └───────┬──────────┘                     │
│                               │                                 │
│                    pass/fail scores + full traces                │
│                               │                                 │
│                               ▼                                 │
│                  ┌────────────────────────┐                     │
│                  │ Failure Filter         │                     │
│                  │ - extract failed tasks │                     │
│                  │ - classify failure type│                     │
│                  └───────────┬────────────┘                     │
│                              │                                  │
│                    failed traces + context                      │
│                              │                                  │
│                              ▼                                  │
│                  ┌────────────────────────┐                     │
│                  │ Kimi K2.5 (Teacher)    │                     │
│                  │ Thinking mode          │                     │
│                  │                        │                     │
│                  │ Input:                 │                     │
│                  │  - failed trace        │                     │
│                  │  - domain policy       │                     │
│                  │  - current prompt      │                     │
│                  │  - tool definitions    │                     │
│                  │                        │                     │
│                  │ Output:                │                     │
│                  │  - diagnosis           │                     │
│                  │  - proposed patch      │                     │
│                  └───────────┬────────────┘                     │
│                              │                                  │
│                     prompt patch                                │
│                              │                                  │
│                              ▼                                  │
│                  ┌────────────────────────┐                     │
│                  │ Patch Validator        │                     │
│                  │ Re-run patched prompt  │                     │
│                  │ on the same failed     │                     │
│                  │ tasks (sanity check)   │                     │
│                  └───────────┬────────────┘                     │
│                              │                                  │
│                   if improved → accept patch                    │
│                   if not → discard or retry                     │
│                              │                                  │
│                              ▼                                  │
│                  ┌────────────────────────┐                     │
│                  │ Evolved Prompt         │──── next iteration  │
│                  └────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

### What Changed vs. the Original Plan

| Original Plan | Revised Plan |
|--------------|-------------|
| Human plays agent in τ²-bench gym, produces 1000+ manual actions | Kimi K2.5 analyzes failed traces and proposes fixes automatically |
| vLLM on-premise GPU serving | All models accessed via API |
| Manual annotation of corrective principles | Kimi generates the corrective principles from trace comparison |
| GEPA/DSPy as the optimizer scaffold | Custom loop (simpler); GEPA can still be used as a comparison baseline |
| Months of data collection | Iteration can begin immediately |

### What Stays the Same

- τ²-bench as the evaluation benchmark (three domains).
- Prompt/tool evolution as the improvement mechanism (no fine-tuning).
- Pass rate (pass^1) as the primary metric.
- The core thesis claim: supervised signals can improve agent performance without RLHF.

---

## 4. The Kimi Reflection Prompt — the Critical Engineering Piece

The quality of the optimization loop depends entirely on how well you prompt Kimi K2.5 to analyze failures and propose patches. Here is a template:

```
You are an expert AI agent debugger. You will be given:

1. THE CURRENT SYSTEM PROMPT used by an AI customer service agent.
2. THE DOMAIN POLICY the agent must follow.
3. THE TOOL DEFINITIONS available to the agent.
4. A FAILED CONVERSATION TRACE where the agent failed to complete a task.
5. THE TASK REQUIREMENTS that define success.

Your job:
A) DIAGNOSE: Identify exactly where and why the agent failed. Classify the
   failure as one of:
   - TOOL_MISUSE: wrong tool, wrong parameters, missing required tool call
   - POLICY_VIOLATION: skipped a validation step, broke a constraint
   - REASONING_ERROR: incorrect assumption, incomplete multi-step plan
   - COMMUNICATION_ERROR: confusing message to user, failed to guide user

B) PROPOSE A PATCH: Write a specific, minimal addition to the system prompt
   that would prevent this class of failure. The patch should be:
   - A concrete rule (not vague advice)
   - Generalizable (not task-specific — it should help across similar tasks)
   - Non-conflicting with existing prompt content

C) EXPLAIN: In one sentence, state what the patch teaches the agent.

Format your response as:
DIAGNOSIS: ...
FAILURE_TYPE: [TOOL_MISUSE | POLICY_VIOLATION | REASONING_ERROR | COMMUNICATION_ERROR]
PATCH:
"""
[exact text to insert into the system prompt]
"""
RATIONALE: ...
```

### Patch Accumulation Strategy

Patches are not applied one-at-a-time to a monolithic prompt. Instead:

1. **Batch reflection**: After a full eval run, collect all failed traces. Send each to Kimi K2.5 independently.
2. **Cluster patches**: Group similar patches (Kimi will likely propose similar fixes for similar failures). Deduplicate.
3. **Merge into prompt**: Append the deduplicated patches to the system prompt as a "Learned Rules" section.
4. **Re-evaluate**: Run the full benchmark with the evolved prompt.
5. **Prune**: If a patch doesn't improve pass rate (or hurts it), remove it. Keep patches that help.

This loop runs 3–5 iterations. Each iteration adds refinement.

---

## 5. Connecting to GEPA / DSPy / TextGrad (for the Thesis Comparison)

Your PTE objectives require comparing these frameworks. Here is how:

### Option A: Custom Loop (primary approach, described above)
- You build the Qwen→fail→Kimi→patch→re-eval loop yourself in Python.
- Advantage: full control, easy to explain in the thesis, directly aligned with the "model-fixes-model" narrative.
- This is your main contribution.

### Option B: GEPA as the optimizer
- Wrap the tau2 agent as a GEPA adapter.
- Use Kimi K2.5 as the `reflection_lm` in GEPA's config.
- GEPA handles the Pareto frontier, candidate sampling, and iteration logic.
- Advantage: you get GEPA's sophisticated search strategy (Pareto-based diversity) for free.
- In the thesis, compare whether GEPA's structured search outperforms your simpler batch-and-prune loop.

### Option C: TextGrad comparison
- Define the system prompt as a `tg.Variable(requires_grad=True)`.
- The loss function = 1 − pass_rate on a minibatch of tau2 tasks.
- TextGrad uses Kimi K2.5 as the backward engine to generate "textual gradients."
- Expected: weaker than GEPA or your custom loop, because TextGrad isn't designed for multi-turn agentic traces. But it's a valid comparison point.

### Option D: DSPy MIPROv2 comparison
- Wrap the tau2 agent as a DSPy module.
- Run MIPROv2 with Kimi K2.5 as the teacher model.
- MIPROv2 will try both instruction optimization and few-shot example selection.

**The thesis chapter structure then becomes:**
1. Describe the model-fixes-model architecture (your contribution).
2. Implement it as a custom loop (primary results).
3. Implement the same idea through GEPA, TextGrad, and MIPROv2.
4. Compare all four on the same test split.
5. Discuss trade-offs (simplicity, cost, effectiveness, generalizability).

---

## 6. Experimental Conditions

| Condition | Student Model | Teacher / Optimizer | Prompt |
|-----------|--------------|-------------------|--------|
| **B** (baseline) | Qwen 3.5 | — | Default tau2 prompt |
| **K** (Kimi-evolved, your method) | Qwen 3.5 | Kimi K2.5 custom loop | Evolved prompt |
| **G** (GEPA-evolved) | Qwen 3.5 | Kimi K2.5 via GEPA | GEPA-optimized prompt |
| **T** (TextGrad-evolved) | Qwen 3.5 | Kimi K2.5 via TextGrad | TextGrad-optimized prompt |
| **M** (MIPROv2-evolved) | Qwen 3.5 | Kimi K2.5 via DSPy | MIPROv2-optimized prompt |
| **F** (frontier ceiling) | Kimi K2.5 itself | — | Default tau2 prompt |

Condition **F** is important: it shows the "ceiling" — what happens if you just use the teacher model directly as the agent. If your evolved Qwen 3.5 approaches Kimi K2.5's native performance, that's a powerful result: you've transferred knowledge from a stronger model into a weaker model's prompt without any weight changes.

---

## 7. Ablations

| Ablation | Tests |
|----------|-------|
| **Iteration depth** | 1, 2, 3, 5 iterations of the loop — where do gains saturate? |
| **Patch type** | Apply only tool-use patches, only policy patches, etc. |
| **Cross-domain transfer** | Train on airline failures, test on retail/telecom |
| **Teacher model swap** | Replace Kimi K2.5 with GPT-4.1 or Claude Sonnet as teacher — is teacher identity important? |
| **Student model swap** | Run the same evolved prompt on Qwen3-32B (older) and Qwen3.5-35B-A3B — does the improvement transfer across student models? |
| **Prompt size** | Track prompt length (tokens) across iterations — does it bloat? Does pruning help? |

---

## 8. Cost Estimate

All via API. No GPUs to rent.

| Component | Est. Tokens | Price | Est. Cost |
|-----------|------------|-------|-----------|
| Qwen 3.5 eval runs (5 conditions × 3 domains × ~100 tasks × 3 trials × ~5K tokens/task) | ~22.5M | ~$0.08–0.24/M | ~$2–5 |
| User simulator (GPT-4.1, ~same volume) | ~22.5M | ~$2/M input | ~$45 |
| Kimi K2.5 reflection (5 iterations × ~200 failed traces × ~10K tokens each) | ~10M | ~$0.60/M in + $2.50/M out | ~$30 |
| Kimi K2.5 as agent (ceiling condition F) | ~4.5M | ~$0.60/M in + $2.50/M out | ~$15 |
| GEPA/TextGrad/MIPROv2 comparison runs | ~20M | mixed | ~$50 |
| **Total estimate** | | | **~$150–200** |

This is dramatically cheaper than the original plan (which required GPU rental for vLLM).

---

## 9. Implementation Sketch

### 9.1 Project Structure

```
thesis-experiment/
├── config.py              # API keys, model names, domains
├── run_baseline.py        # Run Qwen 3.5 on tau2-bench, save results
├── extract_failures.py    # Parse results, extract failed traces
├── reflect.py             # Send failed traces to Kimi K2.5, get patches
├── merge_patches.py       # Deduplicate and merge patches into prompt
├── run_evolved.py         # Re-run with evolved prompt
├── compare.py             # Run GEPA/TextGrad/MIPROv2 conditions
├── analyze.py             # Compute metrics, generate tables/figures
├── prompts/
│   ├── base_airline.txt
│   ├── base_retail.txt
│   ├── base_telecom.txt
│   └── evolved/           # Versioned evolved prompts per iteration
├── results/
│   ├── baseline/
│   ├── evolved_iter1/
│   ├── evolved_iter2/
│   └── ...
└── analysis/
    ├── figures/
    └── tables/
```

### 9.2 Key Integration Point — LiteLLM

τ²-bench uses LiteLLM under the hood, which means you can point it at any OpenAI-compatible endpoint. To use Qwen 3.5 via DashScope:

```python
# In .env
DASHSCOPE_API_KEY=your_key_here

# tau2 run command
tau2 run \
  --domain airline \
  --agent-llm dashscope/qwen-plus \   # or the specific 3.5 model name
  --user-llm gpt-4.1 \
  --num-trials 3
```

For Kimi K2.5, use its OpenAI-compatible endpoint:
```python
from openai import OpenAI

client = OpenAI(
    api_key="your_moonshot_key",
    base_url="https://api.moonshot.cn/v1"
)

response = client.chat.completions.create(
    model="kimi-k2.5-thinking",
    messages=[{"role": "user", "content": reflection_prompt}]
)
```

---

## 10. Reframing the Thesis Narrative

The original thesis proposed "human-in-the-loop" as the source of supervision. With this change, the narrative shifts to:

**Original framing**: "How can human action traces improve AI agents?"
**Revised framing**: "How can a stronger model's diagnostic capabilities substitute for human supervision in agent evolution — and at what cost/quality trade-off?"

This is arguably a *stronger* contribution because:

1. **Scalability**: Human labeling doesn't scale. Model-as-teacher does.
2. **Reproducibility**: Other researchers can replicate the pipeline with any two models.
3. **Cost**: ~$150 vs. hundreds of hours of manual trace annotation.
4. **Generality**: The framework isn't tied to a specific model pair — the ablation where you swap teachers proves this.

The thesis can still reference the human-in-the-loop literature (your lit review stays valid) and position the model-as-teacher approach as an *automation* of what humans do. The "pressure valve" (ask-a-human tool) becomes an optional comparison condition rather than a core dependency.

---

## 11. Risk Register (Revised)

| Risk | Mitigation |
|------|-----------|
| Qwen 3.5 API access becomes unstable | Have Qwen3-32B (older, well-supported) as fallback student |
| Kimi K2.5 API rate limits | Batch reflection calls; use Instant mode for simple failures, Thinking mode only for complex ones |
| Kimi proposes bad patches that hurt performance | Patch validator step rejects regressions; pruning in merge step |
| The evolved prompt becomes too long / bloated | Track token count per iteration; impose a budget; test with and without pruning |
| Reviewer questions why "model fixes model" still counts as "human-in-the-loop" | Frame it as automating the human supervisory role; include a small manual comparison (you solve 20 tasks yourself, compare patch quality to Kimi's patches) |
| Gains are small because Qwen 3.5 is already strong | Choose the 27B dense variant (weaker than 397B flagship), or deliberately use non-thinking mode to create headroom |
