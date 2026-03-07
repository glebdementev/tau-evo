# tau-evo

Self-evolving LLM agents via reflective prompt and tool-schema patching, evaluated on [tau2-bench](https://github.com/sierra-research/tau2-bench).

A teacher model (Kimi K2) diagnoses failures from a student model (Qwen) on customer-service tasks, then proposes patches to the student's system prompt and tool descriptions. The patched student is re-evaluated to verify the fix.

## How it works

```
┌─────────────────────────────────────────────────────┐
│                   Evolution Loop                    │
│                                                     │
│  1. Run student on tau2-bench tasks                 │
│  2. Extract failed conversations                    │
│  3. Send failures to teacher for diagnosis          │
│  4. Teacher proposes prompt / tool-schema patches   │
│  5. Re-run failed tasks with patches applied        │
│  6. Repeat until convergence                        │
└─────────────────────────────────────────────────────┘
```

The student agent (`EvolvableAgent`) subclasses tau2's `LLMAgent` and supports two patch surfaces:
- **Prompt patches** — rules appended to the system prompt
- **Tool patches** — overridden tool/parameter descriptions in the OpenAI function-calling schema

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone --recurse-submodules https://github.com/<you>/tau-evo.git
cd tau-evo
uv venv && uv pip install -e .
cp .env.example .env
# Add your OpenRouter API key to .env
```

tau2-bench is included as a git submodule (`vendor/tau2-bench`) with an editable install, so its data directory resolves automatically.

## Usage

### CLI

```bash
# Run the full evolution loop
uv run python -m tau_evo loop --domain airline --num-tasks 5 --max-iterations 3

# Launch the TUI dashboard
uv run python -m tau_evo ui
```

### As a library

```python
from tau_evo.loop import run_loop

state = run_loop(
    domain="airline",
    num_tasks=5,
    max_iterations=3,
    on_status=print,
)

for r in state.history:
    print(f"Task {r.task_id}: {r.baseline_reward:.2f} -> {r.patched_reward:.2f} ({'fixed' if r.fixed else 'not fixed'})")
```

## Project structure

```
tau-evo/
├── src/tau_evo/
│   ├── config.py              # Paths, API keys, model IDs, defaults
│   ├── loop.py                # Core evolution loop
│   ├── agents/
│   │   └── evolvable.py       # EvolvableAgent + PatchedTool
│   ├── evaluation/
│   │   └── runner.py          # tau2-bench runner, failure extraction
│   ├── reflection/
│   │   └── teacher.py         # Teacher model reflection + patch merging
│   └── ui/
│       └── app.py             # Textual TUI dashboard
├── vendor/tau2-bench/         # Git submodule
├── prompts/evolved/           # Saved prompt patches per iteration
├── patches/                   # Loop state JSON
└── results/                   # Raw evaluation outputs (gitignored)
```

## Models

All models are accessed through [OpenRouter](https://openrouter.ai) — one API key.

| Role | Model | OpenRouter ID |
|------|-------|---------------|
| Student | Qwen 3 32B | `openrouter/qwen/qwen3-32b` |
| Teacher | Kimi K2 | `openrouter/moonshotai/kimi-k2` |
| User simulator | GPT-4.1 | `openrouter/openai/gpt-4.1` |

## License

MIT
