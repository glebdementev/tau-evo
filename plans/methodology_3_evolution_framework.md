# Methodology Document 3: The Evolution Framework

**Purpose**: Walk through the complete evolution pipeline in exhaustive detail — every step, every data flow, every decision point — grounded in the actual code.

---

## 1. High-Level Architecture

The evolution framework implements a **diagnose-patch-validate** loop. A weaker "student" model runs on benchmark tasks, fails on some, and a stronger "teacher" model analyzes each failure, proposes modifications to the student's prompt and tool configuration, and those modifications are validated by re-running the student. The process repeats over multiple iterations.

The architecture has two levels of iteration:

1. **Outer loop** (iterations): evaluate all tasks → collect failures → fix them → merge patches → repeat
2. **Inner loop** (per-failure fix attempts): teacher diagnoses → proposes patches → validate → if failed, teacher retries with feedback

```
OUTER LOOP (max_iterations times):
│
├─ EVALUATE: Run student on all tasks
│  └─ Produces: pass/fail + conversation traces for each task
│
├─ EXTRACT FAILURES: Filter tasks with reward < 1.0
│
├─ FIX FAILURES (in parallel):
│  │
│  └─ For each failure (up to 1 + max_retries attempts):
│     │
│     ├─ TEACHER SESSION: Teacher analyzes trace, calls patch tools
│     │  └─ Produces: patches to prompt, tool schemas, tool code
│     │
│     ├─ VALIDATE: Re-run student on this task with patches applied
│     │  └─ If improved → FIXED, break
│     │  └─ If not improved → feed result back to teacher, retry
│     │
│     └─ Result: FixResult (fixed/not-fixed, patches, diagnosis)
│
├─ MERGE: Apply winning patches to global state
│
├─ DROP: Remove all attempted tasks from future evaluation
│
└─ REPEAT with evolved prompt
```

---

## 2. The Outer Loop: `run_loop()`

Located in `evo/parallel_loop.py:141-333`. This is the main entry point.

### Initialization (lines 157-178)

1. Create an empty `LoopState` — the accumulator for all evolution state.
2. Load domain tools and policy once from tau2's registry:
   ```python
   env = tau2_registry.get_env_constructor(domain)()
   tools = env.get_tools()
   domain_policy = env.get_policy()
   ```
3. Construct the **initial system prompt** using tau2's template:
   ```python
   current_system_prompt = SYSTEM_PROMPT.format(
       domain_policy=domain_policy,
       agent_instruction=AGENT_INSTRUCTION,
   )
   ```
4. Snapshot the **initial tool schemas** as a dict of `{tool_name: openai_schema_dict}`:
   ```python
   current_tool_schemas = {t.name: deepcopy(t.openai_schema) for t in tools}
   ```
5. Initialize empty `current_tool_code` dict (no preprocessors initially).
6. Initialize empty `dropped_task_ids` set.

### Phase 1: Evaluation (lines 180-236)

For each iteration:

1. **Compute evaluation task set**: start with either explicit `task_ids` (if provided) or `num_tasks` random tasks. Exclude any `dropped_task_ids`.
2. **Run evaluation** via `run_baseline()`:
   - Passes `current_system_prompt`, `current_tool_schemas`, `current_tool_code` (the evolved state so far)
   - Results are saved to `results/eval_iter{N}.json`
3. **Lock task IDs** after the first evaluation: if no explicit task_ids were provided, the randomly-selected task IDs are captured and reused for all subsequent iterations. This ensures we always evaluate the same tasks.
4. **Extract failures**: filter for `reward < 1.0`.
5. **Record eval rewards**: `{task_id: reward}` for all tasks, used in iteration results.

**Early exit**: if no failures, record the iteration result and break.

### Phase 2: Parallel Fix (lines 251-299)

If there are failures:

1. **Spawn parallel workers**: `min(parallelism, len(failures))` threads via `ThreadPoolExecutor`.
2. **Each thread runs `_fix_single_failure()`** (detailed in Section 3 below) for one failed task.
3. **Collect results**: each thread returns a `FixResult`. If a thread crashes, a synthetic "unfixed" `FixResult` is created with the exception message.

### Phase 3: Merge and Drop (lines 301-326)

1. **Identify winners**: `FixResult` objects where `fixed == True`.
2. **Drop ALL attempted tasks** (both fixed and unfixed) from future iterations:
   ```python
   for f in fix_results:
       dropped_task_ids.add(f.task_id)
   ```
   **Why drop fixed tasks?** They were already validated during the fix phase — re-evaluating them would waste API calls. The patches that fixed them are already applied.

   **Why drop unfixed tasks?** The teacher couldn't fix them after `max_retries` attempts. Re-attempting in the next iteration with a slightly different global prompt is unlikely to help and risks the teacher proposing conflicting patches. These tasks are considered "intractable" for the current teacher/student pair.

3. **Merge winning patches** into the global state:
   ```python
   for fix in winners:
       current_system_prompt, current_tool_schemas, current_tool_code = apply_patches(
           current_system_prompt, current_tool_schemas, fix.patches, current_tool_code,
       )
   ```
   `apply_patches()` applies each patch sequentially using find-and-replace. Failed patches (e.g., `old_text` not found) are logged and skipped.

4. **Update LoopState**: save the current prompt, tool schemas, tool code, iteration results, and dropped task IDs.

5. **Save to disk**: `patches/loop_state.json` contains the full evolution state.

### Loop Termination

The loop terminates when:
- All tasks pass (no failures to fix), OR
- `max_iterations` is reached, OR
- All tasks have been dropped (nothing left to evaluate)

---

## 3. The Inner Loop: `_fix_single_failure()`

Located in `evo/parallel_loop.py:26-138`. This function handles one failed task.

### Input

- `sim`: the `SimulationRun` from tau2 — contains `task_id`, `messages` (conversation trace), `reward_info`
- `task`: the `Task` definition — contains `evaluation_criteria`, `user_scenario`
- The current global state: `base_system_prompt`, `base_tool_schemas`, `base_tool_code`
- `tools`: the domain's tool objects (for the teacher to inspect)

### Step 1: Create TeacherSession (lines 47-57)

A `TeacherSession` is instantiated with:
- The current system prompt (may already have patches from previous iterations)
- The conversation trace (messages from the failed run)
- The task definition and reward info
- Deep copies of tool schemas and tool code (so patches are local to this session)

The session generates a unique ID: `{task_id}_{timestamp}_{random_hex}`.

### Step 2: Reflect-Validate Loop (lines 65-128)

For up to `1 + max_retries` attempts:

1. **Teacher reflects**: `session.reflect()` (detailed in Section 4) — the teacher analyzes the failure and calls patch tools.
   - Returns: `(patches: list[Patch], diagnosis: str)`
   - If no patches returned, give up.

2. **Validate patches**: re-run the student on this specific task with the session's live-patched state:
   ```python
   val_results = run_baseline(
       domain=domain,
       task_ids=[task_id],
       seed=seed,
       system_prompt=session.current_prompt,
       tool_schemas=session.current_tool_schemas,
       tool_code=session.current_tool_code or None,
   )
   ```

3. **Check improvement**:
   ```python
   patched_reward = val_sim.reward_info.reward
   fixed = patched_reward > baseline_reward
   ```
   - If improved → **FIXED**, break out of retry loop.
   - If not improved and retries remain → **RETRY**.

4. **Feed failure back to teacher** (if retrying):
   ```python
   session.report_failure(
       baseline_reward=baseline_reward,
       patched_reward=patched_reward,
       new_sim=val_sim,  # the new conversation trace
   )
   ```
   This appends a retry prompt to the teacher's conversation history (see Section 4.5), letting it see what happened after its patches were applied and try again.

### Output

Returns a `FixResult`:
- `task_id`: which task
- `baseline_reward`: reward before any patches
- `patched_reward`: reward after the last attempt
- `diagnosis`: concatenated teacher diagnoses across attempts
- `patches`: list of all patches if fixed, empty list if not fixed
- `retries`: number of attempts
- `fixed`: boolean

**Critical design choice**: patches are only returned (and thus only merged globally) if the fix was validated. Failed patches are discarded entirely — they don't pollute the global state.

---

## 4. The Teacher Session: `TeacherSession`

Located in `evo/reflection/teacher.py:57-389`. This is the core intelligence of the framework.

### 4.1 Architecture: Stateful Conversation with Tool Calling

The teacher session maintains a **stateful conversation** with the teacher model (Kimi K2.5) using OpenAI's chat completions API with function calling. The teacher has four tools it can call:

1. **`patch_prompt`**: find-and-replace on the agent's system prompt
2. **`patch_tool`**: find-and-replace on a tool's schema JSON
3. **`read_tool_code`**: inspect a tool's parameter details, types, and current preprocessor
4. **`patch_tool_code`**: find-and-replace on a tool's input preprocessor source code

These tools are defined as Pydantic models in `evo/reflection/tools.py` and converted to OpenAI function-calling format using `pydantic_function_tool()`.

The conversation follows this pattern:
```
USER (initial prompt) → ASSISTANT (diagnosis + tool calls) → TOOL (results) →
ASSISTANT (more tool calls or done) → TOOL (results) → ...
```

### 4.2 The Initial Prompt

The teacher receives a single comprehensive user message constructed from the `REFLECTION_PROMPT` template (`evo/reflection/prompts.py:3-66`):

```
You are an expert at diagnosing failures in LLM-based customer service agents.

Below you will find:
1. The agent's current system prompt (with any previously applied patches already baked in).
2. The current tool schemas (with any previously applied patches already baked in).
3. A failed conversation trace between the agent and a user (simulated).
4. The task requirements that the agent was supposed to fulfil.
5. The reward breakdown showing exactly what went wrong.

Your job is to:
1. **Diagnose** the root cause of the failure in your message text. Classify it as one of:
   - TOOL_MISUSE: wrong tool, wrong parameters, missing tool call
   - POLICY_VIOLATION: skipped a validation step, broke a constraint
   - REASONING_ERROR: incorrect assumption, incomplete plan
   - COMMUNICATION_ERROR: confusing message, failed to guide user

2. **Fix** the issue by calling the provided tools:
   - `patch_prompt`: to edit the agent's system prompt
   - `patch_tool`: to edit a tool's schema JSON
   - `read_tool_code`: to inspect a tool's details and current preprocessor
   - `patch_tool_code`: to edit a tool's input preprocessor
   ...

---

## Agent System Prompt
{system_prompt}

## Tool Definitions
{tool_definitions}

## Failed Conversation Trace
{conversation_trace}

## Task Requirements
{task_requirements}

## Reward Breakdown
{reward_breakdown}
```

The five data sections are populated as follows:

- **`system_prompt`**: the current system prompt string (may already contain patches from previous iterations).
- **`tool_definitions`**: all tool schemas serialized to JSON via `format_tools()`, with consistent 2-space indent.
- **`conversation_trace`**: the full conversation formatted by `format_messages()` (`evo/reflection/formatting.py:11-46`), which:
  - Skips system messages (shown separately)
  - Labels each message by role: `[user]`, `[assistant]`, `[assistant -> tool_call]`, `[tool_result: tool_name]`
  - Preserves full tool call arguments as JSON
  - Preserves full tool results without truncation (verified by test: `tests/test_teacher_fidelity.py`)
  - Tracks tool_call_id → tool_name mapping so tool results show which tool produced them
- **`task_requirements`**: the task's `user_scenario` + `evaluation_criteria` serialized as JSON.
- **`reward_breakdown`**: the `reward_info` object serialized as JSON, showing exactly which criteria passed/failed.

### 4.3 The Reflect Loop

`TeacherSession.reflect()` (`teacher.py:202-289`) calls the teacher in a loop:

```
for round_idx in range(max_rounds):  # max_rounds=10
    msg, response = self._call_teacher()

    if msg.content:
        # Teacher wrote diagnostic text — save it
        diagnosis_parts.append(msg.content)

    if not msg.tool_calls:
        # Teacher is done — no more tools to call
        break

    for tc in msg.tool_calls:
        # Apply each tool call and give feedback
        result_text = self._apply_tool_call(tc, all_patches)
        # Feed result back to teacher
        self._history.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})
```

This allows the teacher to:
1. First diagnose the problem (text content)
2. Call one or more patch tools
3. Receive feedback on whether each patch was applied successfully
4. Call more tools if needed (e.g., read a tool's code, then patch it)
5. Stop when satisfied

The teacher can make up to 10 rounds of tool calls. In practice, most sessions complete in 2-4 rounds.

### 4.4 Tool Call Application

When the teacher calls a tool, `_apply_tool_call()` (`teacher.py:291-330`) processes it:

1. **Parse arguments**: validate against the Pydantic model for that tool.
2. **Dispatch by type**:

   - **`PatchPrompt`**: creates a `Patch(old_text=..., new_text=..., tool_name=None)` and applies it to the current prompt via `apply_one_patch()`.

   - **`PatchTool`**: creates a `Patch(old_text=..., new_text=..., tool_name=...)` and applies it to the named tool's schema JSON.

   - **`ReadToolCode`**: returns the tool's parameter details, types, exceptions, and current preprocessor source (read-only, no patch created).

   - **`PatchToolCode`**: creates a `Patch(old_text=..., new_text=..., tool_name=..., is_code=True)` and applies it to the tool's preprocessor source.

3. **Return feedback string**: either success message with context, or error message explaining what went wrong.

### 4.5 Retry Mechanism

When validation fails (the patched student still doesn't improve), `report_failure()` (`teacher.py:367-389`) appends a retry prompt to the conversation:

```
Your previous patches did NOT fix the issue. The agent was re-run on the same task.

- Baseline reward: {baseline_reward}
- Reward after your patches: {patched_reward}

Here is the new conversation trace after applying your patches:
{new_trace}

And the new reward breakdown:
{new_reward}

## Current Agent System Prompt (with your patches applied)
{current_prompt}

## Current Tool Schemas (with your patches applied)
{current_tools}

## Current Tool Preprocessors (with your patches applied)
{current_preprocessors}

Please analyse what went wrong with your previous patches and try again.
```

This gives the teacher:
- The new conversation trace (showing what happened with its patches)
- The new reward breakdown (what still failed)
- The current state of everything it modified (so it can write accurate `old_text` values)
- Context about its previous attempt

The teacher then re-enters the reflect loop, proposing new or revised patches.

---

## 5. The Three Patch Surfaces

### 5.1 Prompt Patches (`patch_prompt`)

**What**: find-and-replace edits to the agent's system prompt text.

**How they work**: `text_replace()` (`patches.py:22-43`) performs a literal string search for `old_text` within the prompt. If found, replaces the first occurrence with `new_text`. If `old_text` is empty, appends `new_text` to the end.

**What the teacher typically adds**:
- Specific behavioral rules ("ALWAYS verify the customer's identity before making account changes")
- Tool-use instructions ("When looking up a reservation, use the reservation_id field, not the flight number")
- Policy clarifications ("Free cancellation is only available within 24 hours of booking")
- Error recovery procedures ("If the tool returns an error, inform the user and suggest alternatives")

**Feedback to teacher**: on success, returns a snippet showing context around the replacement. On failure, returns the first 120 characters of the `old_text` that wasn't found, so the teacher can correct its match.

### 5.2 Tool Schema Patches (`patch_tool`)

**What**: find-and-replace edits to a tool's OpenAI function-calling schema JSON.

**How they work**: the tool's schema dict is serialized to JSON with 2-space indent (matching exactly what the teacher sees in the prompt). `text_replace()` performs the edit on the JSON string. The result is then parsed back to a dict — if the JSON is invalid, the patch is rejected.

**What the teacher typically changes**:
- Parameter descriptions ("reservation_id: The reservation ID, must start with '#'")
- Tool descriptions ("Use this tool to look up flight details. Requires the reservation ID, NOT the flight number.")
- Adding constraint notes to enum descriptions

**Validation**: the patched JSON string must parse as valid JSON. If the teacher's replacement breaks JSON syntax, the patch is rejected with an error message.

### 5.3 Tool Preprocessors (`patch_tool_code`)

**What**: Python functions that transform tool input arguments before the tool executes.

**Default state**: every tool starts with the identity preprocessor:
```python
def preprocess(kwargs):
    return kwargs
```

**How they work**: the teacher edits the preprocessor source code using find-and-replace. The new source is:
1. Checked for forbidden constructs (imports, eval, exec, file I/O, etc.) via regex
2. Compiled with `compile()` — syntax errors are caught
3. Executed in a sandboxed namespace with restricted builtins (no `__import__`, no `open`, etc.)
4. The `preprocess` function is extracted from the namespace

At runtime, `PatchedTool.__call__()` runs the preprocessor on kwargs before calling the original tool. If the preprocessor raises an exception, it's caught and the original kwargs are used as fallback.

**What the teacher typically adds**:
```python
def preprocess(kwargs):
    # Fix reservation ID format: add '#' prefix if missing
    if 'reservation_id' in kwargs:
        rid = str(kwargs['reservation_id'])
        if not rid.startswith('#'):
            kwargs['reservation_id'] = '#' + rid
    return kwargs
```

**Available builtins in preprocessors**: `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, `len`, `isinstance`, `type`, `max`, `min`, `abs`, `round`, `sorted`, `reversed`, `enumerate`, `zip`, `map`, `filter`, `any`, `all`, `range`, `repr`, `ValueError`, `TypeError`, `KeyError`, `re` (regex module).

**Forbidden**: imports, eval, exec, compile, globals, locals, getattr, setattr, delattr, open, print, and any dunder access.

**Strategy guidance** (from the teacher prompt): "Use `patch_prompt` and `patch_tool` to fix the agent's reasoning and understanding. Use `patch_tool_code` to add defensive input coercion that catches common LLM mistakes (wrong ID formats, type mismatches, missing prefixes, etc.) — these are guardrails that protect against mistakes the agent might still make even with better instructions."

---

## 6. Patch Application Mechanics

### `apply_one_patch()` (`patches.py:46-92`)

Dispatches based on patch type:

1. **Prompt patch** (`patch.is_prompt`): `text_replace()` on the prompt string.
2. **Tool code patch** (`patch.is_tool_code`): `text_replace()` on the preprocessor source, then `compile_preprocessor()` to validate.
3. **Tool schema patch** (`patch.is_tool`): serialize schema to JSON → `text_replace()` → parse back to dict. Rejects if tool name unknown or result is invalid JSON.

Returns: `(prompt, tool_schemas, tool_code, ok, message)`

### `apply_patches()` (`patches.py:95-110`)

Applies a list of patches sequentially. Failed patches are logged and skipped — they don't abort the entire batch.

### `text_replace()` (`patches.py:22-43`)

The core replacement function:
- If `old == ""`: append `new` to the end of the text (with a newline separator)
- If `old not in text`: return failure with the first 120 chars of `old_text` for debugging
- Otherwise: `text.replace(old, new, 1)` — replace first occurrence only

**Why first-occurrence-only**: prevents unintended cascading replacements when the same text appears multiple times.

---

## 7. Failure Taxonomy

The teacher is instructed to classify each failure into one of four categories:

| Category | Code | Description | Examples |
|----------|------|-------------|----------|
| Tool Misuse | `TOOL_MISUSE` | Wrong tool, wrong parameters, missing tool call | Using `get_flight_details` instead of `get_reservation_details`; passing flight number where reservation ID is expected |
| Policy Violation | `POLICY_VIOLATION` | Skipped a validation step, broke a constraint | Cancelling without checking refund eligibility; not verifying customer identity |
| Reasoning Error | `REASONING_ERROR` | Incorrect assumption, incomplete plan | Assuming a flight is direct when it has connections; not checking all required conditions |
| Communication Error | `COMMUNICATION_ERROR` | Confusing message, failed to guide user | Not explaining fees; giving contradictory information |

### How Classification Works

Classification is **automated by the teacher model** — there is no manual labeling step. The teacher includes the failure type in its diagnostic text as instructed by the prompt. The classification is extracted from the diagnosis text for analysis:

```python
# In chart_failure_types_from_fixes():
for ft in FAILURE_TYPES:
    if ft in diag_upper:
        before[ft] += 1
        break
if not matched:
    before["REASONING_ERROR"] += 1  # default
```

This is a simple string-matching extraction — if the teacher's diagnosis contains "TOOL_MISUSE", it's classified as such. If no type is found, it defaults to `REASONING_ERROR`.

**Limitation**: this is heuristic. The teacher might use different phrasing, or a failure might span multiple categories. The current implementation takes the first match.

---

## 8. Session Logging

Every teacher and student interaction is logged to disk as a JSON file in `results/session_logs/`.

### Teacher Sessions

Each `TeacherSession` writes to `{session_id}.json` after every message. The log contains:

- `session_id`: unique identifier
- `session_type`: `"teacher"`
- `task_id`: which task is being fixed
- `model`: teacher model ID
- `started_at`: ISO timestamp
- `status`: `"active"` → `"done"` or `"retrying"`
- `messages`: list of all messages (user prompts, assistant responses with tool calls, tool results)
- `errors`: list of error events (API failures, patch failures)

Each message includes:
- `ts`: ISO timestamp
- `role`: `"user"`, `"assistant"`, `"tool"`, `"system"`
- `content`: text content
- `tool_calls`: list of tool call info (name, arguments, ID)
- `meta`: response metadata (model, token usage)

### Student Sessions

After each evaluation run (baseline or validation), student sessions are saved via `save_student_sessions()`. Each task's conversation is saved as a separate `SessionData` with:
- `session_type`: `"student"`
- `context`: describes the evaluation context (e.g., `"eval_iter1"`, `"fix_0_a0"`)
- `reward`: the task's reward score
- `messages`: the full conversation converted from tau2 format to `SessionMessage` format

### Purpose

Session logs serve two functions:
1. **Debugging**: allows post-hoc inspection of exactly what the teacher saw, what it proposed, and why fixes succeeded or failed.
2. **Web dashboard**: the dashboard displays live and historical sessions, with incremental message polling for active teacher sessions.

---

## 9. Parallelism Architecture

The evolution framework uses parallelism at two levels:

### Level 1: Task Evaluation (tau2 concurrency)

tau2-bench evaluates multiple tasks concurrently using `max_concurrency` on `RunConfig`. This is controlled by the `--parallelism` CLI flag (default 4). Each task runs in a separate thread.

### Level 2: Parallel Teacher Sessions

During the fix phase, each failed task gets its own teacher session running in a separate thread:

```python
with ThreadPoolExecutor(max_workers=workers) as pool:
    for sim in failures:
        future = pool.submit(_fix_single_failure, ...)
```

Workers = `min(parallelism, len(failures))`. Each teacher session is fully independent — it has its own copy of the prompt, tool schemas, and tool code (deep-copied at creation time). There is no shared mutable state between teacher threads.

**Why ThreadPoolExecutor (not ProcessPoolExecutor)**: teacher sessions are I/O-bound (API calls), not CPU-bound. Threads avoid the overhead of inter-process communication and are simpler for sharing the logging infrastructure.

**Thread safety**: the OpenAI client is a singleton created with a lock. Session logging uses file I/O (each session writes to its own file). The web dashboard uses thread-safe queues for log messages and locks for shared state.

---

## 10. Data Flow Summary

```
[Domain Environment]
    │
    ├─ tools: list[Tool]          ──→ EvolvableAgent + teacher prompt
    ├─ policy: str                ──→ system prompt
    └─ tasks: list[Task]          ──→ evaluation

[run_baseline()]
    │
    ├─ RunConfig                  ──→ tau2's run_domain()
    │   ├─ llm_agent: "openrouter/qwen/qwen3-30b-a3b"
    │   ├─ llm_args_agent: {extra_body: {reasoning: {effort: "none"}},
    │   │                    system_prompt: ..., tool_schemas: ..., tool_code: ...}
    │   ├─ llm_user: "openrouter/qwen/qwen3-30b-a3b"
    │   └─ llm_args_user: {extra_body: {reasoning: {effort: "none"}}}
    │
    └─ Results                    ──→ extract_failures()
        ├─ simulations[].messages     ──→ teacher prompt (conversation trace)
        ├─ simulations[].reward_info  ──→ teacher prompt (reward breakdown)
        └─ simulations[].task_id      ──→ fix targeting

[TeacherSession]
    │
    ├─ Input: system_prompt + tools + trace + task + reward
    ├─ Conversation: teacher calls patch_prompt/patch_tool/read_tool_code/patch_tool_code
    ├─ Output: list[Patch] + diagnosis
    │
    └─ Each Patch:
        ├─ old_text: str        (what to find)
        ├─ new_text: str        (what to replace with)
        ├─ tool_name: str|None  (None = prompt patch; str = tool patch)
        └─ is_code: bool        (True = preprocessor patch)

[Validation]
    │
    ├─ run_baseline(task_ids=[failed_task], system_prompt=patched, ...)
    └─ patched_reward > baseline_reward → FIXED

[Merge]
    │
    └─ apply_patches(global_prompt, global_schemas, winning_patches, global_code)
        → updated global state for next iteration
```

---

## 11. State Persistence: `LoopState`

The complete evolution state is serialized to `patches/loop_state.json` and individual run files in `results/runs/`. The `LoopState` dataclass (`evo/models.py:85-148`) contains:

- `system_prompt`: the current (evolved) system prompt string
- `tool_schemas`: dict of `{tool_name: patched_schema_dict}`
- `tool_code`: dict of `{tool_name: preprocessor_source_string}`
- `history`: list of `IterationResult`, each containing:
  - `iteration`: iteration number
  - `num_evaluated`: total tasks evaluated
  - `num_failures`: tasks that failed
  - `num_fixed`: tasks that were fixed
  - `eval_rewards`: `{task_id: reward}` for all tasks
  - `fixes`: list of `FixResult` with full details
- `meta`: `RunMeta` with run ID, domain, timestamps, status
- `session_ids`: list of session IDs (teacher + student) created during the run
- `dropped_task_ids`: task IDs removed from future evaluation

This state is self-contained — it can be loaded and used to reconstruct the evolved agent configuration for any evaluation condition.
