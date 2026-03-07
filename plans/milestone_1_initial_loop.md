# Milestone 1: The Initial Loop

**Goal**: Before running large-scale evaluations, prove the core mechanism works end-to-end on a single task. One mistake caught, one fix applied, one validation passed.

**All LLM calls go through OpenRouter. No DashScope, no Moonshot API, no direct OpenAI. One provider, one API key.**

---

## tau2-bench: What We Learned

Key findings from investigating the `sierra-research/tau2-bench` repo:

| Question | Answer |
|----------|--------|
| Install method | `pip install -e .` (uses PDM backend, but pip works) |
| Custom system prompt via CLI? | **No.** Must subclass `LLMAgent` and override `system_prompt` property |
| Custom tool descriptions? | **No CLI flag.** Must modify `Tool` objects before they reach `generate()` |
| OpenRouter support? | **Yes.** LiteLLM supports `openrouter/<model_id>` out of the box |
| Programmatic API? | **Yes.** `RunConfig`, `run_domain()`, `run_tasks()`, custom agent registration |
| Results format | JSON with full message traces, rewards, costs, token usage |
| Custom agents? | Register via `registry.register_agent(MyAgent, "my_agent")` |

**Implication**: We `pip install` tau2-bench from GitHub, then in our own code we subclass `LLMAgent` to override the system prompt and tool schemas. No need to fork or vendor tau2-bench.

### How tool definitions flow

```
@is_tool() decorated methods in domain toolkit classes (e.g. AirlineTools)
    → Tool objects (parsed from docstrings + type hints)
        → tool.openai_schema property generates JSON
            → passed to LiteLLM completion() call
```

Each `Tool` object has:
- `name` — function name
- `short_desc` — first line of docstring
- `long_desc` — rest of docstring (Args, Returns, Raises sections)
- `params` — Pydantic model built from function signature (field descriptions come from docstring `Args:` section)
- `openai_schema` — property that generates the final `{"type": "function", "function": {...}}` dict

**Override points for our EvolvableAgent:**
1. Override `openai_schema` on individual `Tool` objects — lets us rewrite descriptions and parameter descriptions
2. Modify `self.tools` list in the agent before it reaches `generate()`
3. Both system prompt AND tool schemas are patchable without touching tau2-bench source

---

## The Five Steps

### Step 1 — Run Qwen on a tau2-bench task

Run Qwen 3.5 via OpenRouter on a small subset of tasks (5-10 airline tasks). We use the programmatic API because we need a custom agent with an overridable system prompt.

```python
from copy import deepcopy
from tau2.agent.llm_agent import LLMAgent, SYSTEM_PROMPT, AGENT_INSTRUCTION
from tau2.environment.tool import Tool
from tau2.registry import registry
from tau2.run import run_domain
from tau2.data_model.simulation import RunConfig

class EvolvableAgent(LLMAgent):
    """LLMAgent subclass that allows patching both system prompt and tool schemas."""

    custom_instruction: str | None = None
    tool_patches: dict | None = None  # {tool_name: {description: str, params: {param_name: str}}}

    @property
    def system_prompt(self) -> str:
        instruction = self.custom_instruction or AGENT_INSTRUCTION
        return SYSTEM_PROMPT.format(
            domain_policy=self.domain_policy,
            agent_instruction=instruction,
        )

    def _get_patched_tools(self) -> list[Tool]:
        """Return tools with any description/param patches applied."""
        if not self.tool_patches:
            return self.tools

        patched = []
        for tool in self.tools:
            if tool.name in self.tool_patches:
                patch = self.tool_patches[tool.name]
                tool = deepcopy(tool)

                # Patch tool description
                if "description" in patch:
                    tool.short_desc = patch["description"]
                    tool.long_desc = ""  # Use only patched description

                # Patch parameter descriptions by modifying the Pydantic schema
                if "params" in patch:
                    for param_name, new_desc in patch["params"].items():
                        if param_name in tool.params.model_fields:
                            tool.params.model_fields[param_name].description = new_desc

            patched.append(tool)
        return patched

registry.register_agent(EvolvableAgent, "evolvable_agent")

config = RunConfig(
    domain="airline",
    agent="evolvable_agent",
    llm_agent="openrouter/qwen/qwen3.5-27b",       # Qwen via OpenRouter
    user="user_simulator",
    llm_user="openrouter/openai/gpt-4.1",           # User sim via OpenRouter
    num_trials=1,
    task_split_name="train",
    num_tasks=5,
    seed=42,
)

results = run_domain(config)
results.save(Path("results/baseline_airline_5tasks.json"))
```

**Output**: Results JSON with full conversation traces. At least one task should fail.

### Step 2 — Catch one mistake

Parse the results, find a failed simulation, extract the trace.

```python
from tau2.data_model.simulation import Results

results = Results.load(Path("results/baseline_airline_5tasks.json"))

for sim in results.simulations:
    if sim.reward_info.reward < 1.0:
        failed_trace = sim.messages
        task_id = sim.task_id
        break
```

Classify failure type:
- `TOOL_MISUSE` — wrong tool, wrong parameters, missing tool call
- `POLICY_VIOLATION` — skipped a validation step, broke a constraint
- `REASONING_ERROR` — incorrect assumption, incomplete plan
- `COMMUNICATION_ERROR` — confusing message, failed to guide user

Package the failed trace + task requirements + domain policy + current system prompt as input for the teacher.

### Step 3 — Send it to Kimi

Send the failed trace to Kimi K2.5 via OpenRouter. Kimi receives:
- The current system prompt
- The domain policy
- The tool definitions
- The failed conversation trace
- The task requirements

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
)

response = client.chat.completions.create(
    model="moonshotai/kimi-k2",          # Kimi via OpenRouter
    messages=[{"role": "user", "content": reflection_prompt}],
)

patch = parse_patch(response.choices[0].message.content)
```

> **Note**: Check OpenRouter for exact Kimi K2.5 model ID availability. May need to use `moonshotai/kimi-k2` or similar. Verify before first run.

The reflection prompt must tell Kimi it can propose **two types of patches**:
1. **Prompt patch** — a rule to add to the system prompt
2. **Tool patch** — a modified tool description or parameter description (e.g., if the agent misused a tool because the description was ambiguous)

Kimi receives the full tool schemas as part of its input, so it can see exactly what the agent was told about each tool.

**Output**: A diagnosis + one or both patch types (prompt patch, tool patch).

### Step 4 — Have Kimi fix it

Kimi's patch can target two surfaces:

**A) System prompt patch** — a rule added to the agent instruction:
```python
evolved_instruction = base_instruction + "\n\n## Learned Rules\n" + patch["prompt_patch"]
Path("prompts/evolved/airline_iter1.txt").write_text(evolved_instruction)
```

**B) Tool schema patch** — a modified description or parameter description:
```python
# Example: Kimi says the "refuel_data" param description is misleading
tool_patches = {
    "update_reservation_flights": {
        "description": "Update flights on an existing reservation. IMPORTANT: always verify the new flight exists before calling.",
        "params": {
            "cabin": "Must be one of: economy, business, first. Ask customer to clarify if ambiguous."
        }
    }
}
```

Both patch types are saved as JSON for reproducibility and loaded into `EvolvableAgent` before re-running.

### Step 5 — Validate the mistake is gone

Re-run the *same failed task* with the patched prompt and/or tool descriptions.

```python
# Apply both patch types to the agent
EvolvableAgent.custom_instruction = evolved_instruction
EvolvableAgent.tool_patches = tool_patches  # May be None if Kimi only patched the prompt

config = RunConfig(
    domain="airline",
    agent="evolvable_agent",
    llm_agent="openrouter/qwen/qwen3.5-27b",
    user="user_simulator",
    llm_user="openrouter/openai/gpt-4.1",
    num_trials=1,
    task_ids=[task_id],           # Only re-run the failed task
    seed=42,
)

results = run_domain(config)
passed = results.simulations[0].reward_info.reward == 1.0
print(f"Task {task_id}: {'PASSED' if passed else 'STILL FAILING'}")
```

**Success criteria**: The previously-failed task now passes. The loop works.

---

## Project Setup & Dependency Management

Since this code will be published, we properly depend on tau2-bench via pip from GitHub. No forking, no vendoring, no submodules needed — we only subclass `LLMAgent` in our own code.

### pyproject.toml

```toml
[project]
name = "thesis-experiment"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "tau2-bench @ git+https://github.com/sierra-research/tau2-bench.git",
    "openai>=1.0",
    "python-dotenv",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

Anyone can clone and run:
```bash
pip install -e .
```

This pulls tau2-bench (and its LiteLLM dependency) from GitHub automatically.

### Environment variables

Create a `.env.example` (committed) and `.env` (gitignored):

```env
# All models are accessed through OpenRouter
OPENROUTER_API_KEY=your_openrouter_key
```

That's it. One key. OpenRouter routes to Qwen, Kimi, GPT-4.1, and anything else we need.

---

## Proposed File Structure

```
thesis-experiment/
├── pyproject.toml            # Dependencies, including tau2-bench from GitHub
├── .env.example              # Template: just OPENROUTER_API_KEY
├── .gitignore                # .env, results/, __pycache__, etc.
├── src/
│   └── thesis/
│       ├── __init__.py
│       ├── agent.py          # EvolvableAgent subclass + registration
│       ├── run_baseline.py   # Step 1: run Qwen on tau2-bench
│       ├── extract_failure.py # Step 2: parse results, extract failed trace
│       ├── reflect.py        # Step 3-4: send to Kimi via OpenRouter, get patch
│       └── validate.py       # Step 5: re-run with patched prompt
├── prompts/
│   ├── base_airline.txt      # Default agent instruction (extracted from tau2)
│   └── evolved/              # Patched prompts per iteration
├── results/                  # gitignored, raw eval outputs
└── plans/                    # This file lives here
```

---

## OpenRouter Model IDs (to verify)

| Role | Model | OpenRouter ID (verify before use) |
|------|-------|-----------------------------------|
| Student (agent) | Qwen 3.5 27B | `openrouter/qwen/qwen3.5-27b` |
| Teacher (reflection) | Kimi K2.5 | `moonshotai/kimi-k2` |
| User simulator | GPT-4.1 | `openrouter/openai/gpt-4.1` |

Check https://openrouter.ai/models for exact IDs and availability before first run.

---

## What This Proves

If the loop completes successfully:
1. Qwen 3.5 works with tau2-bench via OpenRouter.
2. Our `EvolvableAgent` subclass correctly overrides both system prompt and tool schemas.
3. tau2-bench produces structured traces we can programmatically parse.
4. Kimi K2.5 (via OpenRouter) can diagnose a failure and produce usable patches (prompt and/or tool).
5. The patch actually improves behavior on the failed task.

This is the foundation. Everything else — batch evaluation, patch accumulation, GEPA/TextGrad/MIPROv2 comparisons — builds on this proven loop.

---

## Things to Validate During Implementation

- **Pydantic schema caching**: Modifying `tool.params.model_fields[x].description` may not propagate to `model_json_schema()` if Pydantic caches the schema. If it doesn't work, fall back to overriding `openai_schema` directly on the `Tool` object (deepcopy it, mutate the dict).
- **Agent instantiation**: Verify how tau2-bench instantiates custom agents — `custom_instruction` and `tool_patches` may need to be instance attributes set via constructor args rather than class-level attributes, depending on how `registry.register_agent` + `RunConfig` create agent instances.
- **OpenRouter model IDs**: Confirm exact model IDs for Qwen 3.5 and Kimi K2.5 on openrouter.ai/models before first run. IDs in this doc are guesses.
