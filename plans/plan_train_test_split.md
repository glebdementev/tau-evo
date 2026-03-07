# Plan: Train/Test Split and Transfer Rate Evaluation

**Status**: DRAFT — awaiting approval before implementation

---

## 1. Problem

Currently, the evolution loop evolves on all tasks and reports improvement on those same tasks. This is fitting, not science. GPT 5.4 correctly identified this as the critical gap. We also have no data on whether fixes (prompt or guardrail) generalize to unseen tasks.

## 2. Key Discovery

tau2-bench already ships canonical train/test splits with zero overlap:

| Domain   | Train | Test | Total |
|----------|-------|------|-------|
| airline  | 30    | 20   | 50    |
| retail   | 74    | 40   | 114   |
| telecom  | 74    | 40   | 114   |

These are loaded via `load_task_splits(domain)` and can be passed to `RunConfig.task_split_name`. We should use these rather than inventing our own.

## 3. Design

### 3.1 Execution Flow

```
Phase 1: EVOLVE (train split)
  run_loop(task_ids=train_ids)  # existing code, unchanged
  -> produces LoopState with evolved prompt, tool_schemas, tool_code
  -> each fix tagged with fix_tier: "prompt" | "code" | "none"

Phase 2: EVALUATE (test split) — NEW
  For each condition, run_baseline(task_ids=test_ids):

  a) Baseline:     default prompt, no patches, test tasks
  b) Evolved:      evolved prompt + schemas + code, test tasks
  c) Prompt-only:  evolved prompt + schemas (NO code patches), test tasks
  d) Frontier:     teacher model as student, default prompt, test tasks

  Store all four result sets in LoopState.
```

### 3.2 Why Four Conditions on Test

| Condition | What it proves |
|-----------|---------------|
| **Baseline** | Floor — how the unmodified student performs on held-out tasks |
| **Evolved** | Ceiling of our method — full evolved system on unseen tasks |
| **Prompt-only** | Transfer of teaching alone — strips guardrails, shows what the agent actually *learned* |
| **Frontier** | Upper bound — what the teacher model achieves natively |

The comparison between **Evolved** and **Prompt-only** on test tasks is the key thesis result:
- If Prompt-only matches Evolved: guardrails were unnecessary, teaching worked
- If Evolved >> Prompt-only: guardrails carry significant value, the agent couldn't learn some things
- Combined with fix_tier data from Phase 1: we know *which specific failures* needed guardrails

### 3.3 Transfer Rate Metrics

```
train_fix_rate     = fixes_on_train / failures_on_train
test_improvement   = (evolved_test_pass - baseline_test_pass) / baseline_test_tasks
transfer_rate      = test_improvement / train_fix_rate  (normalized)

# Per-tier transfer:
prompt_transfer    = (prompt_only_test_pass - baseline_test_pass) / prompt_fixes_on_train
guardrail_transfer = (evolved_test_pass - prompt_only_test_pass) / code_fixes_on_train
```

These tell us:
- Does fixing 10 train tasks improve 5 test tasks? (transfer_rate ~ 0.5)
- Do prompt fixes transfer differently than guardrail fixes?
- Are guardrail fixes more universal (they should be — `#` prefix is universal)?

### 3.4 Parameter Changes

#### CLI (`__main__.py`)

```
--split / --no-split    Enable train/test split mode (default: --split)
--test-only             Run test evaluation on an existing LoopState (skip evolution)
--conditions            Which test conditions to run: all|evolved|prompt-only
                        (default: all)
```

When `--split` is active (default):
- Evolution uses `train` split task IDs automatically
- After evolution completes, runs all test conditions
- `--num-tasks` clamps to train split size (not total)

When `--no-split`:
- Legacy mode, evolve on all tasks (for debugging / quick iteration)
- No test evaluation phase

`--test-only` allows re-running test evaluation on a saved LoopState without re-evolving. Useful for running additional conditions or with different seeds.

#### Web Dashboard

- Run form gets a "Train/Test Split" toggle (default on)
- "Test Only" button appears when viewing a completed run (re-evaluate on test split)

### 3.5 Data Model Changes

#### `LoopState` — new fields

```python
@dataclass
class TestResults:
    """Results of evaluating the evolved system on held-out test tasks."""
    baseline_rewards: dict[str, float]      # task_id -> reward
    evolved_rewards: dict[str, float]       # task_id -> reward
    prompt_only_rewards: dict[str, float]   # task_id -> reward (no code patches)
    frontier_rewards: dict[str, float]      # task_id -> reward (teacher as student)

    # Derived (computed properties)
    @property
    def baseline_pass_rate(self) -> float: ...
    @property
    def evolved_pass_rate(self) -> float: ...
    @property
    def prompt_only_pass_rate(self) -> float: ...
    @property
    def frontier_pass_rate(self) -> float: ...
    @property
    def gap_closure(self) -> float:
        """(evolved - baseline) / (frontier - baseline)"""
    @property
    def prompt_only_gap_closure(self) -> float:
        """(prompt_only - baseline) / (frontier - baseline)"""

@dataclass
class LoopState:
    # ... existing fields ...
    train_task_ids: list[str] = field(default_factory=list)  # NEW
    test_task_ids: list[str] = field(default_factory=list)   # NEW
    test_results: Optional[TestResults] = None               # NEW
```

Backward compatible: old state files load with empty lists and `None`.

### 3.6 Implementation in `parallel_loop.py`

```python
def run_loop(..., use_split: bool = True) -> LoopState:
    # Load splits if enabled
    if use_split and task_ids is None:
        from tau2.run import load_task_splits
        splits = load_task_splits(domain)
        train_ids = splits["train"]
        test_ids = splits["test"]
        task_ids = train_ids  # evolve only on train
    else:
        train_ids = task_ids
        test_ids = []

    # ... existing evolution loop (unchanged) ...

    # Phase 2: Test evaluation
    if test_ids:
        state.test_results = _run_test_evaluation(
            domain, test_ids, seed,
            state.system_prompt, state.tool_schemas, state.tool_code,
            student_model, parallelism, on_status,
        )
    state.train_task_ids = train_ids or []
    state.test_task_ids = test_ids
    return state
```

```python
def _run_test_evaluation(
    domain, test_ids, seed,
    evolved_prompt, evolved_schemas, evolved_code,
    student_model, parallelism, on_status,
) -> TestResults:
    """Run all four conditions on the held-out test split."""

    status("=== TEST EVALUATION (held-out) ===")

    # a) Baseline: default prompt, no patches
    baseline = run_baseline(domain=domain, task_ids=test_ids, seed=seed,
                            save_name="test_baseline", ...)

    # b) Evolved: full evolved system
    evolved = run_baseline(domain=domain, task_ids=test_ids, seed=seed,
                           system_prompt=evolved_prompt,
                           tool_schemas=evolved_schemas,
                           tool_code=evolved_code,
                           save_name="test_evolved", ...)

    # c) Prompt-only: evolved prompt + schemas, NO code patches
    prompt_only = run_baseline(domain=domain, task_ids=test_ids, seed=seed,
                               system_prompt=evolved_prompt,
                               tool_schemas=evolved_schemas,
                               tool_code=None,  # strip guardrails
                               save_name="test_prompt_only", ...)

    # d) Frontier: teacher model as student, default prompt
    frontier = run_baseline(domain=domain, task_ids=test_ids, seed=seed,
                            student_model=TEACHER_MODEL,
                            save_name="test_frontier", ...)

    return TestResults(
        baseline_rewards={s.task_id: s.reward_info.reward for s in baseline.simulations},
        evolved_rewards={s.task_id: s.reward_info.reward for s in evolved.simulations},
        prompt_only_rewards={s.task_id: s.reward_info.reward for s in prompt_only.simulations},
        frontier_rewards={s.task_id: s.reward_info.reward for s in frontier.simulations},
    )
```

### 3.7 Charts — New/Updated

#### New: "Test Results" comparison bar chart

Four grouped bars: Baseline / Prompt-Only / Evolved / Frontier pass rates on test split.
This is the **hero chart** of the thesis.

```
chart_test_comparison(test_results: TestResults) -> dict
```

#### New: "Transfer Rate" chart

Shows per-task pass/fail across conditions as a heatmap:
rows = test tasks, columns = [Baseline, Prompt-Only, Evolved, Frontier]

```
chart_test_heatmap(test_results: TestResults) -> dict
```

#### Updated: "Fix Tiers" donut (already implemented)

No change needed — already shows prompt vs guardrail vs unfixed from train phase.

#### Updated: Comparison bar

Currently shows baseline vs evolved from train data. Update to show test data when available, with train data as secondary.

### 3.8 Summary Stats — Updated

When test results exist, the summary header shows:

```
| Train Fix Rate | Test Baseline | Test Evolved | Test Prompt-Only | Gap Closure |
|     73%        |    40%        |    65%       |      55%         |    62%      |
```

### 3.9 Web Dashboard Changes

1. **Summary row**: adds test pass rates when available
2. **Results table**: keep as-is (shows train fix details with tier)
3. **Charts area**: adds test comparison bar + test heatmap
4. **Run form**: "Train/Test Split" checkbox (default on)
5. **Completed run view**: "Run Test Evaluation" button for `--test-only`

### 3.10 Cost Impact

Per domain, the test evaluation adds 4 full evaluation runs on the test split:

| Domain   | Test tasks | Runs | Extra eval calls |
|----------|-----------|------|-----------------|
| airline  | 20        | 4    | 80              |
| retail   | 40        | 4    | 160             |
| telecom  | 40        | 4    | 160             |

The frontier condition uses the teacher model (Kimi K2.5) which is more expensive, but only for one run on the test split. Estimated additional cost per domain: ~$5-15.

## 4. What This Proves (Thesis Claims)

With this design, we can make these claims with evidence:

**H1**: Teacher-generated prompt patches improve student pass rate on held-out tasks.
- Evidence: `prompt_only_test_pass > baseline_test_pass`

**H2**: Guardrail (code) patches provide additional improvement beyond teaching.
- Evidence: `evolved_test_pass > prompt_only_test_pass`

**H3**: The combined system closes a meaningful fraction of the student-frontier gap.
- Evidence: `gap_closure = (evolved - baseline) / (frontier - baseline)`

**H4**: Guardrail fixes transfer more reliably than prompt fixes.
- Evidence: compare per-tier transfer rates
- Hypothesis: guardrails are format-level (universal), prompt fixes are reasoning-level (may be task-specific)

**Anti-reward-hacking defense**:
- All claims are on held-out test tasks, never seen during evolution
- Prompt-only condition isolates "what the agent learned" from "what the tools compensate for"
- Using tau2-bench's own canonical splits (not our invention)

## 5. Implementation Order

1. `TestResults` dataclass + `LoopState` fields + serialization
2. `_run_test_evaluation()` function in `parallel_loop.py`
3. Wire into `run_loop()` with `use_split` parameter
4. CLI flags: `--split/--no-split`, `--test-only`
5. Two new charts: `chart_test_comparison`, `chart_test_heatmap`
6. Updated summary stats in `_summary.html`
7. Web form toggle + "Run Test Evaluation" button
8. Update methodology docs

## 6. What I Will NOT Do

- Custom train/test splits (use tau2's canonical ones)
- Cross-domain transfer (each domain evolved independently — this is a clear thesis scope boundary)
- Multiple seeds / statistical significance testing (single seed, single trial — acknowledged as limitation)
- Prompt pruning / prompt length optimization (out of scope, noted as future work)
