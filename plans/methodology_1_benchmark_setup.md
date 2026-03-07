# Methodology Document 1: Benchmark Setup and Evaluation Infrastructure

**Purpose**: Exhaustively document how tau2-bench is integrated, configured, and executed within the tau-evo framework, with enough detail for exact reproduction.

---

## 1. tau2-bench: What It Is and Why It Was Chosen

tau2-bench is a benchmark for evaluating LLM-based customer service agents across simulated multi-turn conversations. It was developed by Sierra Research and provides:

- **Three domains**: airline, retail, telecom — each with its own database, domain policy, tool set, and task catalog.
- **A simulated user**: an LLM-based user simulator that plays the customer role, following a scripted scenario.
- **An orchestrator**: manages the turn-by-turn conversation between the agent and user, executing tool calls against a simulated environment (database).
- **A multi-dimensional evaluator**: scores each conversation on action correctness, environment state assertions, and communication quality.
- **Deterministic tasks**: each task defines a user scenario, expected agent actions, environment assertions, and evaluation criteria.

tau2-bench was chosen because it provides a controlled, reproducible environment where agent performance can be measured precisely (reward 0.0–1.0) and where failures leave clear traces that a teacher model can diagnose.

### Version and Pinning

tau2-bench is included as a **git submodule** at `tau2-bench/` in the repository root, pinned to commit `37bfc31cb90f9d7796702291d165aeb63ad164fd` (based on tag `v0.1.1`, 37 commits ahead). The `.gitmodules` file specifies `ignore = dirty` to suppress working-tree noise from the submodule.

The submodule is installed as an **editable Python package** via uv's source configuration in `pyproject.toml`:

```toml
[tool.uv.sources]
tau2 = { path = "tau2-bench", editable = true }
```

This means tau2's data directory (`tau2-bench/data/`) resolves automatically — no environment variables or manual path configuration is needed. The tau2 package is imported directly (`from tau2.run import run_domain`, etc.).

**No modifications were made to upstream tau2-bench.** All integration happens through tau2's public API: the `RunConfig` data model, the `run_domain()` function, the agent `registry`, and the `Tool`/`Environment` classes.

---

## 2. Domain Configuration

### Domains and Task Counts

Three customer service domains are evaluated. Each has a fixed set of tasks defined in tau2-bench's data directory:

| Domain | Total Tasks | Description |
|--------|------------|-------------|
| `airline` | 50 | Flight reservations, cancellations, upgrades, baggage |
| `retail` | 114 | Order management, returns, exchanges, account issues |
| `telecom` | 114 | Mobile plans, data issues, billing, service changes |

These counts are hardcoded in `evo/config.py:49` as `DOMAIN_NUM_TASKS` and enforced as upper bounds — the CLI clamps `--num-tasks` to the domain maximum (`evo/__main__.py:43-46`).

### What a "Task" Consists Of

Each tau2-bench task (defined in `tau2/data_model/tasks.py`) contains:

- **`id`**: a string identifier (e.g., `"0"`, `"1"`, or descriptive IDs like `"[mobile_data_issue]airplane_mode_on|bad_network_preference[PERSONA:Hard]"` in telecom).
- **`user_scenario`**: a natural-language description of what the simulated user wants (visible to the user simulator LLM, NOT to the agent).
- **`evaluation_criteria`**: structured criteria including:
  - **`actions`**: expected agent actions (tool calls with specific arguments) — this is what the evaluator checks.
  - **`env_assertions`**: post-conversation database state assertions.
  - **`nl_assertions`**: natural-language assertions about the conversation content.
- **`initial_state`** (optional): pre-set database state or conversation history.
- **`ticket`** (optional): used by solo-agent mode (not used in this work).

### Domain Policy

Each domain has a detailed policy document that defines the agent's behavioral rules (e.g., refund eligibility, verification requirements, escalation procedures). This policy is loaded at runtime via:

```python
env = tau2_registry.get_env_constructor(domain)()
domain_policy = env.get_policy()
```

The policy is injected into the agent's system prompt inside `<policy>` tags (see Section 4 below).

### Domain Tools

Each domain provides a set of tools (API functions) the agent can call. Tools are defined as Python functions wrapped in tau2's `Tool` class, which provides:

- **`name`**: function name (e.g., `get_reservation_details`, `cancel_reservation`)
- **`short_desc`** / **`long_desc`**: textual descriptions
- **`params`**: a Pydantic model defining input parameters with types, descriptions, and required/optional flags
- **`returns`**: a Pydantic model defining the return schema
- **`raises`**: list of exceptions the tool can raise
- **`openai_schema`**: property that generates the OpenAI function-calling schema dict

Tools are loaded via:
```python
tools = env.get_tools()
```

The number of tools varies by domain (the current `loop_state.json` shows 15 tool schemas for retail). Tool schemas are serialized to JSON for the teacher model to inspect.

---

## 3. Evaluation Execution

### The `run_baseline()` Function

All evaluation runs — baseline, validation during fix attempts, and re-evaluation after patching — go through a single function: `evo/evaluation/runner.py:run_baseline()`. This function:

1. **Constructs a `RunConfig`** (tau2's configuration object) with:
   - `domain`: which domain to evaluate
   - `agent`: `"evolvable_agent"` (registered name for `EvolvableAgent`)
   - `llm_agent`: the student model with litellm prefix (e.g., `"openrouter/qwen/qwen3-30b-a3b"`)
   - `llm_args_agent`: a dict containing:
     - `extra_body.reasoning.effort = "none"` (to disable reasoning tokens — see Section 5)
     - Optionally: `system_prompt`, `prompt_instruction`, `tool_schemas`, `tool_code` (for evolved agents)
   - `user`: `"user_simulator"` (tau2's built-in user simulator)
   - `llm_user`: same model as student, with litellm prefix
   - `llm_args_user`: same reasoning suppression args
   - `num_trials`: always `1` (single trial per task)
   - `task_ids`: optional list of specific task IDs to run
   - `num_tasks`: number of tasks to sample (if `task_ids` is None)
   - `seed`: for deterministic task selection and ordering (default: `42`)
   - `max_concurrency`: number of parallel task evaluations

2. **Calls `run_domain(config)`**: tau2's main entry point, which:
   - Loads the domain environment and tasks
   - For each task, spins up an `Orchestrator` that manages the agent-user conversation loop
   - The orchestrator alternates between: user sends message → agent responds (text or tool call) → if tool call, environment executes it and returns result → agent continues
   - Conversation ends when the user simulator signals completion or max steps are reached
   - Each completed conversation is evaluated against the task's criteria

3. **Returns a `Results` object** containing:
   - `simulations`: list of `SimulationRun` objects, each with:
     - `task_id`: which task was run
     - `messages`: the full conversation trace (list of `Message` objects — `SystemMessage`, `UserMessage`, `AssistantMessage`, `ToolMessage`)
     - `reward_info`: evaluation results including `reward` (float 0.0–1.0) and `reward_breakdown`
   - `tasks`: the task definitions used
   - Metadata (config, timestamps, etc.)

### The litellm Prefix Convention

tau2-bench uses litellm for LLM calls. litellm requires a provider prefix to route to the correct API. Since all models are accessed through OpenRouter, the prefix `"openrouter/"` is prepended at runtime in `runner.py`:

```python
LITELLM_PREFIX = "openrouter/"
# ...
llm_agent=LITELLM_PREFIX + model,  # "openrouter/qwen/qwen3-30b-a3b"
```

Config stores bare model IDs (e.g., `"qwen/qwen3-30b-a3b"`) — the prefix is added only at the point of use.

### Reasoning Token Suppression

Qwen 3.5 models produce reasoning/thinking tokens by default on OpenRouter, which causes `content` to come back as `null` with reasoning in a separate field. This breaks tau2's message handling.

The solution is `NO_THINK_ARGS` defined in `config.py:45`:
```python
NO_THINK_ARGS: dict = {"extra_body": {"reasoning": {"effort": "none"}}}
```

This is passed through `llm_args_agent` and `llm_args_user` in the RunConfig. tau2 passes these kwargs directly to `litellm.completion()`, which forwards them to OpenRouter. tau2 also sets `drop_params=True`, so unsupported kwargs are silently ignored.

### Failure Extraction

After evaluation, failures are extracted by `extract_failures()` (`runner.py:67-72`):

```python
def extract_failures(results: Results) -> list[SimulationRun]:
    return [
        sim for sim in results.simulations
        if sim.reward_info is not None and sim.reward_info.reward < 1.0
    ]
```

A task "fails" if its reward is strictly less than 1.0. There is no partial-credit threshold — even 0.99 is a failure. This binary criterion aligns with tau2-bench's `pass^1` metric (pass rate at threshold 1.0).

### Concurrency

tau2-bench supports concurrent task evaluation. The `max_concurrency` field on `RunConfig` (set via `--parallelism` CLI flag, default 4) controls how many tasks run in parallel threads. This is separate from the parallelism used in the evolution loop's fix phase (see Document 3).

---

## 4. The Agent: EvolvableAgent

### How tau2 Constructs Agents

tau2 uses a registry pattern. Agent classes register themselves with a string name:

```python
registry.register_agent(EvolvableAgent, "evolvable_agent")
```

When `run_domain()` processes a `RunConfig` with `agent="evolvable_agent"`, tau2 looks up this class and calls its constructor with:

```python
agent = EvolvableAgent(
    tools=tools,           # list of Tool objects from the domain environment
    domain_policy=policy,  # string, the domain's policy document
    llm=llm_agent,         # model ID string (with litellm prefix)
    llm_args=llm_args_agent,  # dict of additional kwargs
)
```

### EvolvableAgent's Constructor

`EvolvableAgent` (`evo/agents/evolvable.py`) subclasses tau2's `LLMAgent` and adds three patch surfaces. In its `__init__`:

1. **Extracts custom params from `llm_args`** (lines 73-77):
   - `prompt_instruction`: optional replacement for the default agent instruction
   - `system_prompt`: optional full system prompt override
   - `tool_schemas`: optional dict of tool name → patched schema
   - `tool_code`: optional dict of tool name → preprocessor source code

   These are popped from `llm_args` before passing the rest to `super().__init__()`, so tau2 never sees them — they're consumed entirely by EvolvableAgent.

2. **Calls `super().__init__()`** with the cleaned `llm_args`, setting up the base LLMAgent with the model ID and any remaining kwargs (like `extra_body` for reasoning suppression).

3. **Applies tool patches** if `tool_schemas` or `tool_code` are provided, by wrapping tools in `PatchedTool` objects.

### System Prompt Construction

The `system_prompt` property (lines 82-89) has three modes:

1. **Full override**: if `_system_prompt_override` is set, return it directly. This is used after evolution when the loop has a fully-patched prompt.
2. **Instruction override**: if `prompt_instruction` is set, use it in place of the default `AGENT_INSTRUCTION` within tau2's template.
3. **Default**: use tau2's `SYSTEM_PROMPT` template with the default `AGENT_INSTRUCTION`.

tau2's default system prompt template is:
```
<instructions>
{agent_instruction}
</instructions>
<policy>
{domain_policy}
</policy>
```

Where `AGENT_INSTRUCTION` is:
```
You are a customer service agent that helps the user according to the <policy> provided below.
In each turn you can either:
- Send a message to the user.
- Make a tool call.
You cannot do both at the same time.

Try to be helpful and always follow the policy. Always make sure you generate valid JSON only.
```

### PatchedTool: Schema and Preprocessor Overrides

`PatchedTool` (`evolvable.py:15-48`) is a wrapper that delegates to the original `Tool` but can override two things:

1. **`openai_schema`**: if a patched schema dict is provided, returns it instead of the original. This allows the teacher to modify tool descriptions, parameter descriptions, or add clarifying notes to tool definitions.

2. **`__call__`**: if a preprocessor function is provided, runs it on the kwargs before calling the original tool. The preprocessor is a Python function `preprocess(kwargs) -> kwargs` that can transform inputs — e.g., adding a `#` prefix to reservation IDs, casting strings to ints, normalizing formats.

The `__getattr__` fallback ensures all other attribute access (`.name`, `.params`, etc.) delegates to the original tool.

---

## 5. Models and API Access

### Model Selection

All models are accessed through OpenRouter using a single API key.

| Role | Model ID | Display Name | Access Method |
|------|----------|-------------|---------------|
| Student agent | `qwen/qwen3-30b-a3b` | Qwen3 30B-A3B | litellm via tau2 |
| User simulator | `qwen/qwen3-30b-a3b` | Qwen3 30B-A3B | litellm via tau2 |
| Teacher | `moonshotai/kimi-k2.5` | Kimi K2.5 | OpenAI client direct |

Note: The config also lists alternative student models (`qwen/qwen3.5-flash-02-23` and `z-ai/glm-4.7-flash-20260119`) in `STUDENT_MODELS`, which can be selected via the web dashboard. The default is `qwen/qwen3-30b-a3b`.

### Student and User Simulator: litellm Path

tau2's `generate()` function (in `tau2/utils/llm_utils.py`) calls `litellm.completion()`. The model string `"openrouter/qwen/qwen3-30b-a3b"` tells litellm to route through OpenRouter's API. Additional kwargs from `llm_args` (like `extra_body` for reasoning suppression) are passed through as `**kwargs`.

### Teacher: Direct OpenAI Client

The teacher model uses the `openai` Python library directly, not litellm. A singleton `OpenAI` client is created (thread-safe via lock) pointed at OpenRouter's base URL:

```python
_client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
```

Where `OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"`.

Teacher calls use:
- `model="moonshotai/kimi-k2.5"`
- `temperature=0.3` (low temperature for consistent, focused diagnostic output)
- `tools=TEACHER_TOOLS` (function-calling tools for patching — see Document 3)
- Retries: 3 attempts with exponential backoff (2s, 4s, 6s)

---

## 6. Evaluation Metrics

### Primary Metric: pass^1

The primary metric is **pass^1** — the fraction of tasks where the agent achieves a perfect reward of 1.0. This is the standard metric used in tau2-bench publications.

A task passes if and only if `reward_info.reward == 1.0`. Any reward below 1.0 (even 0.99) is a failure. This strict criterion is used throughout:
- `extract_failures()` uses `reward < 1.0`
- Charts compute pass rates with `reward >= 1.0`
- A fix is considered successful when `patched_reward > baseline_reward` (any improvement, not necessarily to 1.0)

### Reward Breakdown

tau2-bench's evaluator produces a detailed `reward_info` object that includes:
- **Overall reward** (0.0–1.0): weighted combination of sub-scores
- **Action score**: did the agent call the correct tools with correct arguments?
- **Environment assertions**: is the database in the expected state after the conversation?
- **Communication score**: did the agent communicate correctly with the user?

This breakdown is passed to the teacher model in full JSON format to enable precise diagnosis of *what* went wrong.

### Gap Closure (Planned)

For the thesis, gap closure is computed as:
```
gap_closure = (evolved_pass_rate - baseline_pass_rate) / (frontier_pass_rate - baseline_pass_rate)
```

This normalizes for domain difficulty — a 50% gap closure means the evolved prompt captured half the teacher model's performance advantage through prompt and tool-schema patching alone.

### Statistical Considerations

- **Seed**: a fixed seed (default 42) is used for task selection and ordering, ensuring the same tasks are evaluated across iterations. tau2 uses this seed for `random.seed()` in task sampling.
- **Single trial**: `num_trials=1` per task (no repeated runs of the same task in a single evaluation). Variance comes from: (a) the stochastic nature of LLM generation, and (b) the user simulator's behavior.
- **Task locking**: after the first evaluation in a loop run, the exact task IDs are locked (`parallel_loop.py:225-227`), ensuring subsequent iterations evaluate the same tasks. This is critical for measuring improvement — you can't compare pass rates if the task set changes.
