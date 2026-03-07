# Experimental Plan: Supervised AI Agent Evolution on τ²-Bench

**Gleb Dementev — BABDS242**
**Prepared: March 2026**

---

## 1. Overview and Goal

This plan lays out the concrete steps required to build the experimental section of the thesis. The end-to-end pipeline has four stages: (A) reproduce τ²-bench baselines, (B) collect human action traces via the built-in gymnasium, (C) engineer and apply prompt/tool evolution using an optimizer, and (D) re-evaluate on the benchmark to quantify improvement. Each stage is described below with tooling choices, rationale, and risk mitigations.

---

## 2. Reproducing the τ²-Bench Baseline

### 2.1 Repository and Installation

The canonical codebase lives at `sierra-research/tau2-bench` on GitHub. It supersedes the original `tau-bench` repo (which covered only airline and retail) by adding the telecom dual-control domain and a Gymnasium-compatible interface. Installation uses `pdm` (Python dependency manager) and the `tau2` CLI command.

Key setup steps:

1. Clone `sierra-research/tau2-bench`, create virtualenv (Python 3.10+).
2. Run `pip install -e .` for editable install (this registers the `tau2` CLI).
3. Copy `.env.example` to `.env` and add API keys for the LLM provider(s).
4. Verify the data directory is present; run `tau2 check` to confirm.

### 2.2 Running the Baseline Evaluation

The benchmark supports three domains — **airline**, **retail**, and **telecom** — and uses LiteLLM under the hood, so any provider (OpenAI, Anthropic, local vLLM) can be used.

A minimal baseline run looks like:

```
tau2 run \
  --domain airline \
  --agent-llm <model_name> \
  --user-llm gpt-4.1 \
  --num-trials 3 \
  --max-concurrency 10
```

The `--user-llm` flag sets the simulated user (which should remain a strong model like GPT-4.1 for consistency). Repeat for `retail` and `telecom` domains.

**For an open-source model served via vLLM**, configure LiteLLM to point at the local endpoint. The thesis proposal specifies vLLM with batch-invariant inference — this means ensuring that results don't change as a function of the batch size used during serving (temperature = 0 or fixed seeds).

### 2.3 Selecting the Open-Source Model

The thesis mentions benchmarking "an open-source model of choice." Practical candidates (as of early 2026):

- **Qwen3-8B / Qwen3-32B** — strong tool-calling, good function-calling format support.
- **Llama 3.3 70B** — well-supported by vLLM, solid agentic performance.
- **Mistral Large** variants — if accessible.

Recommendation: start with Qwen3-8B (fast iteration, lower GPU cost) and optionally scale to a 70B model for final results to show framework generality.

### 2.4 What to Log

Every run produces a results JSON with per-task outcomes. For the thesis, capture:

- **Pass rate (pass^1)** per domain and overall.
- **Full conversation trajectories** (agent messages, tool calls, tool results, user messages).
- **Failure classification** using the built-in auto error-identification tool (`tau2` has fault-assignment and fault-type classification via an LLM). Categorize failures into: tool misuse, policy violation, reasoning failure, communication failure.

### 2.5 Expected Baseline Numbers

From leaderboard data: frontier models (Opus 4.5, GPT-5) score ~88–98% on telecom and retail, with weaker showing on airline. An 8B open model will likely score substantially lower — expect 40–75% depending on domain. This gap is the thesis's opportunity: if the framework can close even part of it, the contribution is meaningful.

---

## 3. Human Action Trace Collection

### 3.1 The τ²-Bench Gymnasium

The tau2-bench repo now includes a Gymnasium-compatible interface with two modes:

- **AgentGymEnv ("Play as Agent")**: You step through the conversation playing the agent role, calling tools and responding to the simulated user.
- **UserGymEnv ("Play as User")**: You control the user while an LLM agent handles requests (available only in telecom and similar dual-control domains).

For the thesis, **"Play as Agent" mode is the primary data source**. The human (you or collaborators) takes over the agent role for tasks where the baseline AI agent failed, producing correct tool-call sequences and responses.

### 3.2 Data Collection Workflow

1. **Select failure cases**: From the baseline run, filter tasks that failed. Group by failure type.
2. **Prioritize by frequency**: Focus on the most common failure clusters first — these will yield the most improvement per trace.
3. **Play through each task**: Launch the gym interface, complete the task correctly, and export the action trace (the sequence of tool calls and messages you produced).
4. **Annotate the trace**: For each human action, note what the AI agent did wrong and what corrective principle the human action embodies (e.g., "always verify customer ID before modifying records," "check plan limits before suggesting a data refuel").

### 3.3 Target Scale

The thesis proposal requires **1000+ human actions** across three domains, with **no fewer than 200 per domain**. An "action" here is a single tool call or agent response within a conversation. A typical failed conversation might contain 5–15 actions, so completing ~100–150 failed task conversations should yield the required volume.

### 3.4 Dataset Schema

Each record in the human trace dataset should contain:

| Field | Description |
|-------|-------------|
| `task_id` | τ²-bench task identifier |
| `domain` | airline / retail / telecom |
| `turn_index` | Position in conversation |
| `ai_action` | What the baseline agent did (tool call or message) |
| `ai_outcome` | pass / fail at this turn |
| `human_action` | What the human did instead |
| `failure_type` | tool_misuse / policy_violation / reasoning_error / communication_error |
| `corrective_principle` | Natural-language summary of the rule the human followed |
| `conversation_context` | Preceding messages and tool results |

Store as JSONL or Parquet for easy processing.

---

## 4. Prompt / Tool Evolution Framework

This is the core contribution. Your PTE objectives explicitly require you to "analyze, compare and contrast DSPy, GEPA, and TextGrad and their applicability." Below is a comparative analysis and a recommended architecture.

### 4.1 Framework Comparison

**DSPy (Stanford NLP)**

- Treats prompts as learnable parameters within modular Python programs.
- Optimizers available: BootstrapFewShot, MIPROv2, COPRO, SIMBA, GEPA.
- Strength: mature ecosystem, native support for multi-step agentic programs, built-in evaluation loop.
- Limitation: the framework is designed to optimize DSPy programs — extracting the optimized prompt for use *outside* DSPy can lose effectiveness. The tau2-bench agent isn't natively a DSPy program, so an adapter is needed.

**GEPA (Genetic-Pareto, accepted ICLR 2026 Oral)**

- A reflective prompt optimizer that maintains a Pareto frontier of candidate prompts.
- Core loop: sample a candidate → collect execution traces + feedback → LLM reflection proposes a prompt edit → re-evaluate → update the Pareto frontier.
- Outperforms MIPROv2 by 10%+ and GRPO by 6% on average, using up to 35× fewer rollouts.
- Key advantage for this thesis: GEPA explicitly uses *natural-language traces and feedback* for reflection. This maps directly to the thesis concept of "mining human action traces for improvement signals."
- Available both standalone (`pip install gepa`) and as `dspy.GEPA`.

**TextGrad (Stanford / Zou Group, published in Nature)**

- Models AI systems as computation graphs; backpropagates "textual gradients" (LLM-generated feedback) through the graph.
- PyTorch-like API (Variable, loss, optimizer.step()).
- Strength: very general — can optimize code, molecules, prompts, etc.
- Limitation: designed primarily for instance-level optimization (improve one answer) and prompt optimization for simpler pipelines. Not natively designed for multi-turn agentic tool-calling flows. No built-in support for agentic trace formats.

### 4.2 Recommended Approach: GEPA as the Core Optimizer

**Rationale**: GEPA is the best fit because:

1. It is *trace-aware* — it reflects on full execution trajectories, which is exactly what human action traces provide.
2. It is *sample-efficient* — the thesis budget of ~1000 human actions is modest; GEPA is designed to produce gains from few rollouts.
3. It accepts *textual feedback* in addition to scalar scores, allowing human-annotated corrective principles to be fed directly into the reflection loop.
4. It maintains a Pareto frontier rather than a single best candidate, which naturally handles the diversity of failure types across three domains.
5. It is available as a DSPy optimizer (`dspy.GEPA`), providing infrastructure for the optimization loop, but also as a standalone library with a custom adapter interface — which can wrap the tau2-bench agent.

### 4.3 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    GEPA Optimization Loop                     │
│                                                              │
│  ┌─────────────┐   ┌─────────────────┐   ┌──────────────┐   │
│  │ Candidate    │──▸│ τ²-bench        │──▸│ Score +      │   │
│  │ Prompt Set   │   │ Evaluation      │   │ Trace Log    │   │
│  └──────▲──────┘   └─────────────────┘   └──────┬───────┘   │
│         │                                        │           │
│         │          ┌─────────────────┐            │           │
│         │◂─────────│ LLM Reflection  │◂───────────┘           │
│         │          │ + Human Traces  │                        │
│         │          │ as Feedback     │                        │
│         │          └─────────────────┘                        │
│         │                                                    │
│  ┌──────┴──────────────────────────────┐                     │
│  │ Pareto Frontier of Prompt Variants  │                     │
│  └─────────────────────────────────────┘                     │
└──────────────────────────────────────────────────────────────┘
```

**Concrete implementation steps**:

1. **Wrap the tau2 agent as a GEPA-compatible system.** Implement a `GEPAAdapter` that:
   - Takes a candidate (system prompt + tool descriptions + policy text).
   - Runs it through `tau2 run` on a minibatch of tasks.
   - Returns the pass/fail score and the full conversation trace.
   - Extracts relevant trace segments for the reflection LLM.

2. **Inject human traces as textual feedback.** When evaluating a candidate on a task that has a corresponding human trace, provide the human trace alongside the AI trace to the reflection LLM. The reflection prompt should say: "Here is the AI's trace (which failed) and a human expert's trace (which succeeded). Identify what the human did differently and propose a prompt edit that would teach the agent this behavior."

3. **Define the candidate structure.** Each candidate is a tuple of:
   - System prompt (the main agent instruction text).
   - Per-domain policy addenda (additional rules discovered from failure analysis).
   - Tool-call templates or constraints (e.g., "always call verify_customer before modify_order").

4. **Run the GEPA loop.** Start from the baseline prompt as the seed candidate. Run iterations with minibatches from the training split of tau2-bench tasks. GEPA will:
   - Evaluate the candidate → collect traces.
   - Reflect (using a strong model like GPT-4.1 or Claude Sonnet) on what went wrong.
   - Propose a mutated prompt.
   - Evaluate the mutation → update Pareto frontier.

5. **For comparison with TextGrad**: Implement a TextGrad-based version where the system prompt is a `tg.Variable(requires_grad=True)` and the loss is the tau2 pass/fail score. This will likely underperform GEPA for multi-turn agentic tasks but provides an important comparison point.

6. **For comparison with DSPy baselines**: Run MIPROv2 and BootstrapFewShot optimizers on the same DSPy-wrapped agent to establish how GEPA compares to other DSPy optimizers.

### 4.4 Types of "Patches" to Evolve

Based on the failure taxonomy from the literature and the Cleanlab case study on tau2-bench, the framework should target these intervention types:

| Patch Type | Example | Addresses |
|-----------|---------|-----------|
| Policy reminder insertion | "ALWAYS verify customer identity before any account modification" | Policy violations |
| Tool-call ordering constraint | "Call get_customer_details BEFORE update_customer" | Tool misuse |
| Parameter validation rule | "The refuel_amount must be a positive number matching the customer's request" | Tool misuse |
| Escalation heuristic | "If the customer's request is ambiguous after 2 clarification attempts, summarize what you understood and ask for confirmation" | Communication errors |
| Reasoning scaffold | "Before executing a multi-step plan, list the steps you will take and verify each precondition" | Reasoning failures |
| Few-shot demonstration | Include a successful conversation excerpt in the prompt | All types |

### 4.5 The "Pressure Valve" — Ask-a-Human Tool

As described in your PTE objectives, introduce an `ask_human()` tool that the agent can call when uncertain. Implementation:

1. Add a new tool to the tau2-bench tool registry: `ask_human(question: str) -> str`.
2. During human trace collection, record when and why the human would have been consulted.
3. In the first evaluation phase, measure how often the agent uses this tool and whether it improves pass rate (by routing hard cases to a simulated perfect human response).
4. In the final evaluation, remove the tool and test whether the prompt evolution alone (having learned from the human traces) achieves gains *without* the fallback.

This two-phase design is important: it shows that the framework can first use human support as training signal, then internalize the lessons into the prompt.

---

## 5. Evaluation Design

### 5.1 Metrics

| Metric | Definition | Purpose |
|--------|-----------|---------|
| **pass^1** | Fraction of tasks passed on a single attempt | Primary metric, matches tau2-bench leaderboard |
| **pass^1 by domain** | Per-domain breakdown (airline, retail, telecom) | Shows which domains respond to evolution |
| **Δ pass^1** | Change from baseline to evolved agent | The headline result |
| **pass^k (k=3 or 5)** | Fraction of tasks where all k attempts pass | Measures reliability, not just average performance |
| **Failure rate by type** | Breakdown of remaining failures after evolution | Shows which failure types are most/least responsive |
| **Escalation rate** | % of tasks routed to ask_human (pressure valve phase only) | Measures human dependency |

### 5.2 Experimental Conditions

Run and compare these conditions:

1. **Baseline (B)**: Unmodified open-source model on tau2-bench.
2. **B + Ask-Human**: Baseline with the pressure-valve tool.
3. **GEPA-evolved (G)**: After prompt evolution using GEPA with human traces.
4. **GEPA-evolved + Ask-Human (G+H)**: Both.
5. **TextGrad-evolved (T)**: After prompt optimization using TextGrad (comparison).
6. **DSPy-MIPROv2 (M)**: After prompt optimization using MIPROv2 (comparison).

### 5.3 Train/Test Split

τ²-bench now provides standardized train/test splits. Use the training split for human trace collection and GEPA optimization. Report all final numbers on the **test split** (or `base` split for full comparability with the leaderboard).

### 5.4 Ablation Studies

- **By patch type**: Apply only policy-reminder patches, only tool-constraint patches, etc. and measure which categories drive the most improvement.
- **By trace volume**: Run the evolution with 200, 500, and 1000+ human actions to answer the sub-question about minimal demonstration volume.
- **By domain**: Run evolution trained on one domain and test on another to assess cross-domain transfer.
- **With/without human feedback text**: Run GEPA with only scalar scores (no human trace feedback) vs. with the textual feedback from human annotations. This isolates the value of human traces specifically.

---

## 6. Infrastructure Requirements

| Component | Specification |
|-----------|--------------|
| GPU server | At least 1× A100 80GB (for 70B model) or 1× A6000 48GB (for 8B model) |
| vLLM | Latest version, configured for deterministic inference (seed + temperature 0) |
| API budget | ~$200–500 for GPT-4.1 as user simulator across all runs |
| GEPA reflection LLM | GPT-4.1 or Claude Sonnet 4.6 (strong model for reflective optimization) |
| Storage | ~50GB for all traces, logs, and model weights |
| Python environment | Python 3.10+, tau2-bench, dspy, gepa, textgrad, litellm, polars, matplotlib |

---

## 7. Risk Register and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Open-source model too weak on tau2 (pass^1 < 30%) | Small absolute gains even if relative improvement is large | Choose a capable 32B+ model, or reframe results in relative terms |
| Human trace collection takes longer than planned | Delays entire pipeline | Start collection immediately; use the gym interface which is purpose-built for this |
| GEPA overfits to training tasks | Good training scores, poor test scores | Use the Pareto frontier diversity mechanism; monitor train/test gap at each iteration |
| τ²-bench user simulator instability | Variance in results masks real improvement | Use multiple trials (num-trials ≥ 3), report confidence intervals, fix user-LLM to a single strong model |
| GEPA/TextGrad not directly compatible with tau2 agent format | Engineering overhead | Build a thin adapter layer (est. 1–2 days work); GEPA's custom adapter interface is designed for this |
| API costs spiral during optimization | Budget overrun | Use minibatch evaluation in GEPA (evaluate on 5–10 tasks per iteration, not the full benchmark); run full eval only at checkpoints |

---

## 8. Suggested Timeline Mapping

| Phase | Your Timeline | Activities |
|-------|--------------|------------|
| Baseline + Data | Now → early April | Reproduce tau2 baselines; begin human trace collection via gym; implement GEPA adapter |
| Framework Build | April | Complete 1000+ traces; implement and test GEPA evolution loop; run first optimization iterations |
| Evaluation + Ablation | April → May | Full evaluation on test split; run all comparison conditions; ablation studies |
| Writing | May → June | Results chapter, discussion, framework description |

---

## 9. Key References to Investigate Further

- **τ²-bench paper**: Barres et al. (2025), arXiv:2506.07982 — read the appendices for domain-specific policy details and the compositional task generator.
- **GEPA paper**: Agrawal et al. (2025), arXiv:2507.19457 — especially Section 3 (algorithm), Section 4 (experiments), and the MCP adapter example.
- **TextGrad paper**: Yuksekgonul et al. (2024), arXiv:2406.07496 — Section 3.3 on prompt optimization.
- **DSPy**: Khattab et al. (2024), ICLR — the optimization overview documentation at dspy.ai is more current than the paper.
- **Cleanlab tau2 case study**: cleanlab.ai/blog/tau-bench — directly relevant to trust-scoring and escalation; their code is at github.com/Tonyhrule/tau2-bench.
- **Alan (Shion Honda) benchmarking article**: Practical reproduction notes for tau2 across multiple models, including formatting adjustments for Claude models.
- **Reflexion** (Shinn et al., 2023): Verbal reinforcement learning for agents — a precursor concept to GEPA's reflection.
