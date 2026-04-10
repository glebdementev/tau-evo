## 2.4 Implementation and Experimental Setup

This section describes the technology stack, benchmark configuration, model choices, experimental conditions, evaluation metrics, and reproducibility provisions.

### 2.4.1 Technology Stack

The framework is implemented in Python 3.12 with the following key dependencies:

- **$\tau^2$-bench** [@barres2025]: evaluation benchmark, integrated as a git submodule pinned to commit 37bfc31 (based on tag v0.1.1), installed as an editable Python package. No modifications were made to the upstream codebase; all integration occurs through $\tau^2$-bench's public API.
- **litellm**: LLM routing library used by $\tau^2$-bench for model inference, providing a unified interface across providers.
- **OpenAI Python SDK** ($\geq$1.0): used for direct teacher model API calls with function calling support.
- **OpenRouter**: API routing service providing access to all models through a single API key.
- **uv** with hatchling backend: build system for dependency management and reproducible environments.

The source code is publicly available at github.com/glebdementev/tau-evo.

### 2.4.2 Benchmark: $\tau^2$-bench Airline Domain

$\tau^2$-bench was selected over four alternative benchmarks (AgentBench, SWE-bench, GAIA, ToolBench) because it is the only benchmark that combines: (1) multi-turn conversations with an LLM-simulated user providing partial information, (2) domain-specific policies, (3) tool-calling APIs that modify database state, and (4) the pass$^k$ reliability metric. Customer service is the natural evaluation domain because it represents the largest addressable market for AI agent automation: approximately 17 million contact center agents globally, with labor constituting up to 95% of operating costs [@gartner2022labor].

The experiments use the airline domain (50 tasks total). Each task defines a user scenario, expected agent actions, post-conversation database state assertions, and natural-language assertions. A task passes if and only if the agent satisfies all criteria simultaneously---the strict binary pass$^1$ metric standard in $\tau$-bench publications.

A simulated orchestrator manages turn-by-turn conversation between the agent and user simulator. On each turn the agent may either send a text message or invoke a tool. Tool calls are executed against a simulated database. The conversation ends when the user simulator signals completion or a maximum step count is reached. The full trace is preserved for analysis by the teacher model.

![Conversation mechanics in $\tau^2$-bench: turn-by-turn interaction between agent and user simulator.](figures/fig_07_conversation_mechanics.png){#fig:conversation-mechanics}

### 2.4.3 Model Selection

All models are accessed through OpenRouter using a single API key.

| Role | Model | Access Method |
|------|-------|---------------|
| Student agent | Qwen3 30B-A3B | litellm via $\tau^2$-bench |
| User simulator | Qwen3 30B-A3B | litellm via $\tau^2$-bench |
| Teacher | Kimi K2.5 | OpenAI client direct |

: Model assignments and access methods. {#tbl:models}

The primary student model is Qwen3 30B-A3B [@qwen2025], a Mixture-of-Experts Transformer with 30.5 billion total parameters but only 3.3 billion active per token. It employs 128 experts with top-8 routing across 48 layers and supports 32,768 native context tokens. Despite activating barely 10% of its parameters per forward pass, the model outperforms Qwen2.5-14B on all reported benchmarks and leads the Berkeley Function Calling Leaderboard (BFCL v3).

The selection reflects a trade-off that mirrors the real enterprise deployment decision: organizations choose cost-efficient models precisely because frontier models are prohibitively expensive at production volumes, then need a mechanism to close the resulting performance gap.

Alternative student models---Qwen3.5 Flash and GLM 4.7 Flash---are evaluated for cross-student comparison.

The teacher model is Kimi K2.5 [@kimi2026], a MoE Transformer with approximately one trillion total parameters and 32 billion active per token. Its 256K-token context window accommodates full conversation traces, the system prompt, all tool schemas, and task requirements in a single prompt. The teacher was chosen for significantly stronger performance than the student, strong tool-calling comprehension, a long context window, architectural independence from the student (Moonshot AI, not Alibaba), and cost-effectiveness for hundreds of reflection calls.

The user simulator uses Qwen3 30B-A3B. $\tau^2$-bench's user simulator follows scripted scenarios and does not require frontier-level capabilities.

### 2.4.4 Experimental Conditions

Two conditions are evaluated, differing only in the agent's prompt and tool configuration:

- **Baseline.** The student model runs with $\tau^2$-bench's default system prompt and original tool schemas. This establishes the performance floor.

- **Evolved.** The student model runs with the evolved prompt and tool configuration produced by the DPV framework: modified system prompt, modified tool schemas, and tool preprocessors.

### 2.4.5 Experimental Design: Three Scales $\times$ Three Models

The experiments span three task-pool sizes and three student models:

| Scale | Task IDs | Qwen3 30B | Qwen3.5 Flash | GLM 4.7 |
|-------|----------|-----------|---------------|---------|
| 5 | 0, 1, 3, 4, 5 | Done | Done (base only) | Done |
| 10 | 0--5, 7, 9--12 | Done | Done | Done |
| 20 | 0--5, 7, 9--12, 14, 15, 17, 20, 21, 23, 27, 28, 33, 34 | Done | Done | Dropped |

: Experimental conditions across scales and models. GLM 4.7 Flash is dropped at 20 tasks due to poor performance at 10 tasks. {#tbl:conditions}

Each experiment runs the evolution loop for up to three sweeps with up to two retries per failed task per sweep. Every task is evaluated with three trials. A task passes in a given sweep if it passes in at least two of three trials (majority vote). The seed is fixed at 42 throughout.

The scaling sequence is deliberate: if gains are task-specific, they should be largest at small scale and diminish as the denominator grows. The multi-model comparison tests whether a stronger student benefits differently from evolution.

### 2.4.6 Evaluation Metrics

The primary metric is pass$^1$---the fraction of tasks achieving a perfect reward of 1.0:

$$\text{pass}^1 = \frac{1}{N} \sum_{i=1}^{N} \mathbb{1}[r_i = 1.0]$$

This is the standard metric in $\tau$-bench publications. Any reward below 1.0 constitutes failure.

![Reward breakdown for a sample task: the binary pass$^1$ metric aggregates sub-criteria scores into a single pass/fail outcome.](figures/fig_09_reward_breakdown.png){#fig:reward-breakdown}

The fix success rate is defined as:

$$\text{FSR} = \frac{|\{i : \text{fix}_i \text{ succeeds}\}|}{M}$$

where $M$ is the number of attempted fixes. A fix succeeds when the patched student passes the task unanimously across all trials.

The statistical analysis plan comprises two hypothesis tests plus interval reporting:

- **Effectiveness.** Paired one-sided $t$-test on per-task trial-pass-rate deltas (evolved minus baseline) at $\alpha = 0.05$. Sensitivity checks via McNemar's exact test and Wilcoxon signed-rank test.
- **Diminishing returns.** Cochran-Armitage trend test [@cochran1954; @armitage1955] on fix success rate across ordered pool sizes (5, 10, 20 tasks).
- **Confidence intervals:** Exact Clopper-Pearson intervals for pass rates, following @bowyer2025 for evaluations with fewer than 300 data points.

### 2.4.7 Reproducibility

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Random seed | 42 | Deterministic task selection and ordering |
| Trials per task | 3 | Unanimous pass required across all trials |
| Teacher temperature | 0.3 | Focused diagnostic output |
| Reasoning suppression | Enabled | Prevents reasoning tokens from breaking content parsing |
| Max teacher rounds | 10 | Multi-step diagnosis without unbounded cost |

: Fixed experimental parameters. {#tbl:parameters}

The complete evolution state is serialized to JSON after each iteration: the current system prompt, all tool schemas, all preprocessor source, iteration history, and metadata. Task IDs are locked after the first evaluation.

### 2.4.8 Threats to Validity

Regarding *internal validity*, three trials per task with a unanimous-pass criterion reduces the probability of accepting fragile patches, though more trials would tighten estimates at higher cost. The teacher's patches reflect Kimi K2.5's capabilities; only patches that demonstrably improve performance enter the global state, mitigating teacher model bias. The string-matching failure taxonomy is heuristic and may misclassify some failures, but this affects per-category analysis rather than primary pass-rate results.

Regarding *external validity*, $\tau^2$-bench tasks are simulated, while production interactions are more diverse and adversarial. The framework is evaluated with one teacher and three student models; generalization to other pairs is untested. Patches are domain-specific by design, and cross-domain transfer is not claimed. Each $\tau^2$-bench task is a unique scenario, not a draw from a homogeneous distribution---the contribution is the framework, not the specific patches. The teacher prompt prohibits task-specific hardcoding, and unanimous validation guards against brittle patches.

Regarding *construct validity*, the pass$^1$ metric treats all failures equally, whereas @rabanser2025 decompose reliability into four dimensions; pass$^1$ captures only consistency. Patches may encode surface-level heuristics without transferring deep domain understanding, and their durability under distribution shift is untested.
