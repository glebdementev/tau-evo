# Plan: Teacher "Decompose" Mode

## Goal

A second, independent teacher mode that creates subagents by:
1. Grouping related tools under a new subagent with its own prompt
2. Removing those tools + related instructions from the main agent
3. Adding a `delegate_to_<name>` tool to the main agent

The output is a standard diff (patches + subagent defs) that merges through the existing merge pipeline. No loop changes.

---

## What a Subagent Is

```python
@dataclass
class SubAgentDef:
    name: str                # e.g. "refund_handler"
    description: str         # shown to main agent in delegate tool
    system_prompt: str       # subagent's own prompt
    tool_names: list[str]    # tools moved from main agent
```

At runtime, `delegate_to_refund_handler(task: str) → str` spawns a mini LLM conversation with the subagent's prompt + assigned tools, returns the result as a tool output to the main agent.

---

## Output Format

The decomposer produces a `DecomposeResult`:

```python
@dataclass
class DecomposeResult:
    subagents: list[SubAgentDef]
    patches: list[Patch]       # prompt patches (remove tool instructions, add delegation guidance)
    diagnosis: str
```

These patches are plain `Patch` objects — identical to what the existing teacher produces. They merge through the existing `merge_fixes` pipeline with no special handling.

---

## New Files

### 1. `evo/agents/subagent.py`

**`SubAgentDef`** dataclass (as above).

**`make_delegate_tool(subagent_def, sub_tools, llm, llm_args) → Tool`**
- Creates a tau2-compatible `Tool` named `delegate_to_{name}`
- Schema: `{ task: str }` — description from `subagent_def.description`
- Implementation: runs a small LLM agent loop
  - System prompt = `subagent_def.system_prompt`
  - Tools = the actual tool objects from `sub_tools`
  - Input = the `task` string
  - Runs until the LLM stops calling tools (or max rounds)
  - Returns final text as tool result
- Uses same LLM + llm_args as the main agent (no extra config)

### 2. `evo/reflection/decompose_tools.py`

Pydantic models for the decomposer's tool calls:

| Tool | Fields | Purpose |
|---|---|---|
| `CreateSubAgent` | `name`, `description`, `system_prompt`, `tool_names: list[str]` | Register a subagent + assign tools in one call |
| `PatchSubAgentPrompt` | `agent_name`, `old_text`, `new_text` | Edit a subagent's prompt after creation |
| `PatchPrompt` | `old_text`, `new_text` | Edit main agent prompt (reuse existing model) |
| `ListTools` | — | Show available tools so teacher knows what can be assigned |

Exported as `DECOMPOSE_TOOLS` list (OpenAI function format).

### 3. `evo/reflection/decomposer.py`

**`DecomposerSession`** — parallel to `TeacherSession`, shares no code with it.

Constructor args:
- `system_prompt` — current main agent prompt
- `tools` — list of tool objects (for listing)
- `tool_schemas` — current schemas
- `failures` — list of failing sim runs (all at once, not per-failure)
- `model` — teacher model

**Prompt** shows the teacher:
- Current main agent prompt
- All available tools (names + descriptions)
- All failure traces (summarized)
- Instructions: identify tool groups that form a logical sub-task, create a subagent for them, edit the main prompt to delegate

**`decompose() → DecomposeResult`**:
- Runs tool-calling loop (same pattern as `TeacherSession.reflect`)
- Tracks created `SubAgentDef`s in internal state
- Tracks prompt patches in internal state
- Returns `DecomposeResult`

Internal state management:
- `_subagents: dict[str, SubAgentDef]` — created subagents
- Applies prompt patches to a working copy (like teacher does)
- `PatchSubAgentPrompt` edits the subagent's prompt in `_subagents`
- `ListTools` returns formatted tool list

---

## Modified Files

### 4. `evo/models.py`

- Import `SubAgentDef` from `evo.agents.subagent`
- Add `subagents: Optional[dict[str, SubAgentDef]]` to `LoopState`
- Handle serialization/deserialization in `save()`/`load()`

### 5. `evo/agents/evolvable.py`

In `__init__`, extract `subagents` from `llm_args` (same pattern as `tool_schemas`).

In `_apply_patches()`, after existing tool patching:
```
for each subagent_def in self.subagents:
    sub_tools = [tool for tool in self.tools if tool.name in subagent_def.tool_names]
    self.tools = [tool for tool in self.tools if tool.name not in subagent_def.tool_names]
    delegate = make_delegate_tool(subagent_def, sub_tools, self.llm, self.llm_args)
    self.tools.append(delegate)
```

### 6. `evo/evaluation/runner.py`

Pass `subagents` through `llm_args_agent` alongside existing fields (one line).

### 7. `evo/config.py`

```python
DECOMPOSE_ENABLED = False
```

Single boolean flag. No other config needed (uses same teacher model, same LLM).

### 8. `evo/parallel_loop.py`

In the fix phase, after collecting `FixResult`s:
- If `DECOMPOSE_ENABLED` and there are still failures, run `DecomposerSession`
- Wrap result as a `FixResult` with the prompt patches
- Append to the fix list → flows into existing merge automatically
- Store `subagent_defs` on `LoopState`

This is ~15 lines of code. The decomposer output is just another `FixResult` from merge's perspective.

---

## Merge Integration (automatic)

The decomposer's `patches` (prompt edits) are plain `Patch` objects. They enter `merge_fixes` alongside regular teacher patches. The merger LLM sees them as "remove these tool-specific instructions, add delegation guidance" — no special handling.

The `subagent_defs` bypass merge (they don't conflict — they're additive). They're stored directly on `LoopState`.

---

## Runtime Flow

```
Agent constructed with subagents in llm_args
    ↓
_apply_patches():
    1. Apply tool schema patches (existing)
    2. Apply tool code patches (existing)
    3. For each subagent:
       - Collect assigned tool objects
       - Remove them from main tool list
       - Create delegate_to_X tool
       - Add to main tool list
    ↓
Main agent runs:
    - Sees delegate_to_refund_handler(task: str) as a normal tool
    - Calls it with a task description
    - Under the hood: mini LLM loop with subagent prompt + tools
    - Gets back result string
```

---

## Implementation Order

1. `SubAgentDef` + `make_delegate_tool()` in `evo/agents/subagent.py`
2. Decompose tools in `evo/reflection/decompose_tools.py`
3. `DecomposerSession` in `evo/reflection/decomposer.py`
4. Wire into `evolvable.py` (extract subagents, apply in `_apply_patches`)
5. Wire into `runner.py` (pass subagents through llm_args)
6. Wire into `parallel_loop.py` (~15 lines: run decomposer, wrap as FixResult)
7. Wire into `models.py` (LoopState serialization)
8. Config flag in `config.py`
