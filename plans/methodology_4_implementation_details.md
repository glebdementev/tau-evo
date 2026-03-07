# Methodology Document 4: Implementation Details and Supplementary Information

**Purpose**: Cover the web dashboard, analysis/charting, testing, and miscellaneous implementation details relevant for reproducibility.

---

## 1. Software Architecture Overview

The project is structured as a single Python package (`evo/`) with the following module layout:

```
evo/
├── __init__.py
├── __main__.py          # CLI entry point: python -m evo {loop|ui|web}
├── config.py            # Centralized config: paths, API keys, model IDs, defaults
├── models.py            # Data models: Patch, FixResult, IterationResult, LoopState, RunMeta
├── parallel_loop.py     # Main evolution loop (outer + inner)
├── session_log.py       # Unified session logging (teacher + student)
├── agents/
│   ├── __init__.py
│   └── evolvable.py     # EvolvableAgent + PatchedTool
├── evaluation/
│   ├── __init__.py
│   └── runner.py        # tau2-bench runner, failure extraction
├── reflection/
│   ├── __init__.py
│   ├── teacher.py       # TeacherSession — stateful teacher conversation
│   ├── formatting.py    # Trace + tool formatting for teacher prompts
│   ├── patches.py       # Patch application logic (find-and-replace)
│   ├── preprocessor.py  # Preprocessor compilation + sandboxing
│   ├── prompts.py       # REFLECTION_PROMPT + RETRY_PROMPT templates
│   └── tools.py         # Pydantic tool models for teacher function calling
├── analysis/
│   ├── __init__.py
│   └── charts.py        # Plotly chart generation (7 chart types)
├── ui/
│   ├── __init__.py
│   └── app.py           # Textual TUI dashboard
└── web/
    ├── __init__.py
    ├── app.py           # FastAPI + SSE web dashboard
    └── templates/
        ├── index.html
        ├── _results.html
        ├── _summary.html
        └── _history.html
```

### Dependencies

From `pyproject.toml`:
- `tau2` — the benchmark framework (git submodule, editable install)
- `openai>=1.0` — for teacher model API calls
- `python-dotenv` — environment variable loading
- `rich>=13.0` — CLI formatting
- `textual>=1.0` — TUI dashboard
- `fastapi>=0.115` + `uvicorn[standard]>=0.34` + `jinja2>=3.1` + `sse-starlette>=2.0` + `python-multipart>=0.0.20` — web dashboard

Additional transitive dependencies (via tau2): `litellm`, `loguru`, `pydantic`, `plotly`, `pandas`.

Build: `uv` for dependency management, `hatchling` backend. The wheel includes only the `evo/` package.

---

## 2. CLI Interface

Entry point: `python -m evo` → `evo/__main__.py`.

Three subcommands:

### `python -m evo loop`

Runs the evolution loop headlessly, printing status to stdout via Rich console.

Arguments:
- `--domain {airline,retail,telecom}` (default: airline)
- `--num-tasks N` (default: 5, clamped to domain max)
- `--max-iterations N` (default: 3)
- `--max-retries N` (default: 2)
- `--parallelism N` (default: 4)
- `--seed N` (default: 42)
- `--task-ids ID [ID ...]` (optional, overrides --num-tasks)

### `python -m evo ui`

Launches a terminal-based dashboard using Textual. Provides:
- Start/quit buttons
- Live log panel
- Results table (iter, task ID, before/after reward, status)

Uses hardcoded defaults — no CLI customization of loop parameters.

### `python -m evo web`

Launches a web dashboard using FastAPI + Jinja2 + HTMX.

Arguments:
- `--port N` (default: 8080)
- `--reload` (enable auto-reload for development)

---

## 3. Web Dashboard Architecture

The web dashboard (`evo/web/app.py`) is the primary interface for running experiments and viewing results.

### Technology Stack

- **FastAPI**: async web framework
- **Jinja2**: server-side HTML templating
- **HTMX**: client-side partial page updates
- **SSE (Server-Sent Events)**: real-time log streaming via `sse-starlette`
- **Plotly.js**: client-side chart rendering from server-generated JSON

### Run Lifecycle

1. User fills out the configuration form (domain, model, num_tasks, etc.) and clicks "Run"
2. `POST /run` starts a background thread running `run_loop()`
3. The loop sends status messages to a `queue.Queue`
4. `GET /logs` returns an SSE stream that reads from the queue
5. Client-side JS listens for SSE events and updates the UI:
   - `log` events → append to log panel
   - `session` events → update session list
   - `live` events → refresh live fix progress
   - `save` events → refresh results table
   - `charts` events → reload charts
   - `done` event → mark run as complete

### State Management

The dashboard maintains several pieces of state:
- **Active run**: the currently-executing loop (if any). Only one run at a time.
- **Viewed run**: which run's results are displayed. Can be different from the active run (user can browse history).
- **Run history**: persisted as JSON files in `results/runs/`. Each file is a full `LoopState`.
- **Teacher sessions**: in-memory references to active `TeacherSession` objects for live message polling.

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Main dashboard page |
| POST | `/run` | Start a new evolution run |
| GET | `/logs` | SSE stream of log messages |
| GET | `/results` | Results table HTML partial |
| GET | `/summary` | Summary stats HTML partial |
| GET | `/api/live-fixes` | JSON: current fix attempts in progress |
| GET | `/api/state` | JSON: running status, active/viewed run IDs |
| GET | `/api/charts` | JSON: all Plotly chart data |
| GET | `/api/sessions` | JSON: session list (teacher + student) for viewed run |
| GET | `/api/sessions/{id}` | JSON: full session data |
| GET | `/api/sessions/{id}/messages?after=N` | JSON: incremental message fetch |
| GET | `/runs` | Run history HTML partial |
| GET | `/runs/{id}` | Load a historical run for viewing |
| DELETE | `/runs/{id}` | Delete a historical run |

### tau2 Orchestrator Log Forwarding

tau2's orchestrator uses loguru for logging conversation-level events (agent/user messages, tool calls). The web app adds a custom loguru sink (`_loguru_sink`) that forwards these messages to the SSE queue when a run is active:

```python
_loguru.add(_loguru_sink, filter="tau2.orchestrator", level="INFO")
```

This provides real-time visibility into individual conversations as they happen.

---

## 4. Analysis and Charts

`evo/analysis/charts.py` generates Plotly figures for thesis visualization and the web dashboard.

### Chart Types

1. **Reward Progression** (`chart_reward_progression`): Grouped bar chart showing baseline vs patched reward for each fix attempt. X-axis = task IDs, Y-axis = reward (0–1).

2. **Cumulative Fix Rate** (`chart_cumulative_fix_rate`): Line chart showing running fix success rate as fixes progress. X-axis = fix number, Y-axis = cumulative % fixed.

3. **Comparison Bar** (`chart_comparison_bar`): Three bars for one domain: Baseline, Evolved, Frontier pass rates. Used for the B/K/F comparison.

4. **Failure Types** (`chart_failure_types`): Stacked bar chart showing failure type distribution before vs after evolution. Counts of TOOL_MISUSE, POLICY_VIOLATION, REASONING_ERROR, COMMUNICATION_ERROR.

5. **Task Heatmap** (`chart_task_heatmap`): Binary heatmap with rows=tasks, columns=[baseline, patched], green=pass, red=fail.

6. **Evaluation Rewards** (`chart_eval_rewards`): Simple bar chart of per-task rewards from an evaluation run (used when there are no failures to fix).

7. **Pass Rate per Iteration** (`chart_eval_pass_rate`): Bar chart showing pass rate across outer loop iterations.

### Data Sources

Charts can be generated from two sources:
- **`all_charts(fixes)`**: from a list of `FixResult` objects (legacy path)
- **`all_charts_from_state(state)`**: from a `LoopState` object, which handles both the case where fixes exist and where all tasks pass (no fixes needed)

### Export Modes

The charts module can be run standalone:
```bash
# Interactive HTML files
python -m evo.analysis.charts

# PNG export (requires kaleido)
python -m evo.analysis.charts --export

# JSON to stdout
python -m evo.analysis.charts --json

# Synthetic demo data
python -m evo.analysis.charts --demo
```

### Styling

All charts use a consistent dark theme (`DARK_LAYOUT`) with transparent backgrounds, matching the web dashboard's dark UI. Color constants are defined in `COLORS` for consistency across charts.

---

## 5. Testing

### `tests/test_teacher_fidelity.py`

This is the primary test file, focusing on a critical invariant: **the teacher must see everything the student saw**. If the trace formatting loses information (truncates tool results, drops tool call arguments, etc.), the teacher cannot accurately diagnose failures.

Three test functions:

1. **`test_all_student_info_present_in_teacher_view`**: Builds a realistic multi-turn conversation with multiple tool calls, dual content (text + tool calls), and long tool results. Converts to both litellm format (what the student LLM saw) and teacher format (what `format_messages()` produces). Asserts that:
   - Every user message content is present
   - Every assistant text content is present
   - Every tool call name and arguments are present
   - Every tool result content is present IN FULL (no truncation)
   - Tool result labels resolve to correct tool names (not generic "tool")
   - System messages are NOT in the teacher view (shown separately)

2. **`test_no_data_loss_long_tool_result`**: Ensures tool results >500 characters are not truncated (regression test for an earlier bug).

3. **`test_assistant_content_with_tool_calls`**: Ensures that when an assistant message contains both text and tool calls, both appear in the teacher view.

---

## 6. Log Suppression and Noise Management

Multiple layers of logging are suppressed to keep output clean:

```python
# config.py:quiet_deps()
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("LiteLLM Router").setLevel(logging.CRITICAL)
logging.getLogger("LiteLLM Proxy").setLevel(logging.CRITICAL)
litellm.suppress_debug_info = True
logger.disable("tau2")            # silence all tau2 loguru logs
logger.enable("tau2.orchestrator") # except orchestrator-level conversation events
```

This is called in `__main__.py` before starting any loop or web server.

---

## 7. Directory Structure and Output Files

### Runtime Directories (created by `ensure_dirs()`)

| Directory | Purpose |
|-----------|---------|
| `results/` | Root for all output |
| `results/runs/` | Per-run `LoopState` JSON files (named `{domain}_{timestamp}.json`) |
| `results/session_logs/` | Individual session JSON files (teacher + student) |
| `results/figures/` | Exported chart images/HTML |
| `prompts/evolved/` | (Reserved for evolved prompt storage) |
| `patches/` | `loop_state.json` — the global evolution state |

### Output File Formats

**Evaluation results** (`results/eval_iter{N}.json`, `results/fix_{task_id}_a{attempt}.json`): tau2's `Results` format — contains full simulation data including messages, rewards, config, etc.

**Run state** (`results/runs/{run_id}.json`): `LoopState` serialized via `json.dumps(asdict(state))`. Contains the evolved prompt, tool schemas, tool code, all iteration history with fix results, session IDs, and metadata.

**Session logs** (`results/session_logs/{session_id}.json`): `SessionData` Pydantic model serialized via `model_dump_json()`. Contains all messages with timestamps, tool calls, response metadata (model, token usage), and errors.

**Global state** (`patches/loop_state.json`): same format as run state files, written at the end of each loop run. This is the "latest" state for quick access.

---

## 8. Error Handling and Resilience

### Teacher API Errors

`_call_teacher()` retries 3 times with exponential backoff (2s, 4s, 6s). Each failure is logged as an `ErrorRecord` in the session log. If all retries fail, the reflect loop stops early — partial patches (if any) are still collected.

### Patch Application Errors

Patches can fail for several reasons:
- `old_text` not found in the target (prompt, schema, or preprocessor)
- Patched schema JSON is invalid
- Patched preprocessor has syntax errors or forbidden constructs
- Tool name is unknown

All failures return descriptive error messages to the teacher, which can try again. Failed patches do not mutate state — they are atomic.

### Thread Crashes

If a teacher thread crashes during `_fix_single_failure()`, the outer loop catches the exception and creates a synthetic `FixResult` with `fixed=False` and the exception message as diagnosis. This ensures the loop continues even if individual fix attempts fail.

### Preprocessor Safety

Preprocessors are sandboxed:
- **Static analysis**: regex check for forbidden patterns (imports, eval, exec, file I/O, dunder access)
- **Restricted builtins**: the execution namespace only has safe builtins — no `__import__`, no `open`, no `print`
- **Runtime fallback**: if a preprocessor raises at tool-call time, the original kwargs are used and a warning is logged

---

## 9. Observed Behavior from Actual Runs

From the `loop_state.json` file in the repository, here is one complete run's outcome:

**Run**: `retail_20260307_190048` (retail domain, 3 tasks)

**Iteration 1**:
- Evaluated 3 tasks: task 0 passed, tasks 1 and 2 failed (reward 0.0)
- Teacher fixed both:
  - Task 1: 0.0 → 1.0, 2 patches
  - Task 2: 0.0 → 1.0, 9 patches
- Patches merged into global state

**Iteration 2**:
- Evaluated 1 remaining task (task 0, tasks 1 and 2 dropped)
- 0 failures
- Loop terminated early — all tasks pass

**Final state**:
- System prompt: 8,754 characters (up from ~2,000 in the default)
- Tool schemas: 15 tools with modifications
- Tool code: 7 tools with custom preprocessors
- Total: 2/2 failures fixed (100% fix rate on attempted tasks)

This demonstrates the full lifecycle: baseline evaluation → failure extraction → teacher diagnosis → patching → validation → merge → re-evaluation → convergence.

---

## 10. Relationship Between Code Modules

```
__main__.py
    │
    ├── [loop] ──→ parallel_loop.run_loop()
    │                 │
    │                 ├── evaluation/runner.run_baseline()
    │                 │       │
    │                 │       ├── agents/evolvable.EvolvableAgent (registered via registry)
    │                 │       │       └── PatchedTool (wraps tau2 Tool objects)
    │                 │       │
    │                 │       └── tau2.run.run_domain() ──→ tau2 orchestrator
    │                 │
    │                 ├── reflection/teacher.TeacherSession
    │                 │       │
    │                 │       ├── reflection/prompts (REFLECTION_PROMPT, RETRY_PROMPT)
    │                 │       ├── reflection/formatting (format_messages, format_tools, etc.)
    │                 │       ├── reflection/tools (PatchPrompt, PatchTool, etc.)
    │                 │       ├── reflection/patches (apply_one_patch, text_replace)
    │                 │       └── reflection/preprocessor (compile_preprocessor, sandbox)
    │                 │
    │                 ├── session_log (save_session, save_student_sessions)
    │                 └── models (LoopState, FixResult, Patch, etc.)
    │
    ├── [web]  ──→ web/app.py (FastAPI server)
    │                 │
    │                 ├── parallel_loop.run_loop() (in background thread)
    │                 ├── analysis/charts.py (Plotly figure generation)
    │                 ├── session_log (session listing and loading)
    │                 └── web/templates/ (Jinja2 HTML)
    │
    └── [ui]   ──→ ui/app.py (Textual TUI)
                      └── parallel_loop.run_loop() (in worker thread)
```

---

## 11. Key Design Decisions and Their Rationale

| Decision | Rationale |
|----------|-----------|
| **Subclass LLMAgent** instead of modifying tau2 | Keeps tau2 unmodified; all customization is in our code |
| **Pass custom params through `llm_args`** | tau2's `RunConfig` → agent constructor pipeline only passes `llm_args`; we piggyback on it and pop our params before `super().__init__()` |
| **Find-and-replace patching** instead of full rewrite | More controllable, less likely to break working parts, enables incremental changes |
| **Preprocessors as sandboxed Python** | More flexible than JSON schema constraints; allows runtime input coercion that static schema changes cannot |
| **Drop tasks after fix attempt (whether fixed or not)** | Prevents re-fixing already-fixed tasks (waste) and prevents infinite retrying of intractable tasks |
| **Validate each fix independently** then merge winners | Ensures only proven improvements enter the global state; prevents untested patches from degrading performance |
| **Stateful teacher conversation** with retries | Allows the teacher to learn from its own failed attempts within the same context window |
| **Single OpenRouter API key** for all models | Simplifies configuration; OpenRouter handles routing to different providers |
| **Thread-based parallelism** for teacher sessions | I/O-bound workload; threads are simpler and lighter than processes for API calls |
