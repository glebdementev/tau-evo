# tau-evo

Self-evolving LLM agents via reflective prompt and tool-schema patching, evaluated on [tau2-bench](https://github.com/sierra-research/tau2-bench).

A teacher model (Kimi K2.5) diagnoses failures from a student model (Qwen 3.5) on customer-service tasks, then proposes patches to the student's system prompt and tool descriptions. The patched student is re-evaluated to verify the fix.

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
git clone --recurse-submodules https://github.com/glebdementev/tau-evo.git
cd tau-evo
uv sync
cp .env.example .env
# Add your OpenRouter API key to .env
```

### Repository structure

This repo contains only our code (`evo/`). The evaluation framework
[tau2-bench](https://github.com/sierra-research/tau2-bench) is pinned as a
**git submodule** at `tau2-bench/` and installed as an editable
dependency. We never modify upstream tau2-bench — all integration happens
through tau2's public API.

```
tau-evo/
├── evo/               # Our code
│   ├── config.py              # Paths, API keys, model IDs, defaults
│   ├── loop.py                # Core evolution loop
│   ├── __main__.py            # CLI entry point
│   ├── agents/
│   │   └── evolvable.py       # EvolvableAgent + PatchedTool
│   ├── evaluation/
│   │   └── runner.py          # tau2-bench runner, failure extraction
│   ├── reflection/
│   │   └── teacher.py         # Teacher model reflection + patch merging
│   └── ui/
│       └── app.py             # Textual TUI dashboard
├── tau2-bench/                # Git submodule (upstream, never modified)
├── .env.example               # Template for API keys
├── results/                   # Raw evaluation outputs (gitignored)
├── patches/                   # Loop state JSON (gitignored)
└── pyproject.toml
```

### Reproducing

After cloning with `--recurse-submodules`, the submodule is pinned to a
specific commit of tau2-bench. Running `uv sync` installs it as an editable
package, so tau2's data directory (`tau2-bench/data/`) resolves
automatically. No environment variables or manual paths needed.

If you cloned without `--recurse-submodules`:
```bash
git submodule update --init
```

## Usage

### CLI

```bash
# Run the full evolution loop
uv run python -m evo loop --domain airline --num-tasks 5 --max-iterations 3

# Run on specific task IDs only
uv run python -m evo loop --domain airline --task-ids 42 57

# Launch the TUI dashboard
uv run python -m evo ui
```

### As a library

```python
from evo.loop import run_loop

state = run_loop(
    domain="airline",
    num_tasks=5,
    max_iterations=3,
    on_status=print,
)

for r in state.history:
    print(f"Task {r.task_id}: {r.baseline_reward:.2f} -> {r.patched_reward:.2f} ({'fixed' if r.fixed else 'not fixed'})")
```

## Models

All models are accessed through [OpenRouter](https://openrouter.ai) — one API key.

| Role | Model | ID |
|------|-------|----|
| Student | Qwen 3.5 35B-A3B | `qwen/qwen3.5-35b-a3b` |
| Teacher | Kimi K2.5 | `moonshotai/kimi-k2.5` |
| User simulator | Qwen 3.5 35B-A3B | `qwen/qwen3.5-35b-a3b` |

The student and user simulator go through litellm (with `openrouter/` prefix added at runtime). The teacher uses the OpenAI client directly against OpenRouter's API.

## License

MIT
