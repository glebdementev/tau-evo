"""NiceGUI web dashboard for tau-evo experiments."""

from __future__ import annotations

import asyncio
import json
import logging
from functools import partial
from typing import Optional

from nicegui import ui

import evo.config as cfg

cfg.ensure_dirs()

# Suppress noisy loggers before anything imports litellm.
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("LiteLLM Router").setLevel(logging.CRITICAL)
logging.getLogger("LiteLLM Proxy").setLevel(logging.CRITICAL)


# ---------------------------------------------------------------------------
# State shared across the UI
# ---------------------------------------------------------------------------
class RunState:
    running: bool = False
    loop_state: Optional[object] = None  # LoopState once finished
    log_element: Optional[ui.log] = None
    results_table: Optional[ui.table] = None
    patches_editor: Optional[ui.textarea] = None


state = RunState()


# ---------------------------------------------------------------------------
# Background loop execution
# ---------------------------------------------------------------------------
async def _run_loop_async(domain: str, num_tasks: int, max_iter: int, seed: int, task_ids_raw: str):
    """Run the evolution loop in a thread, streaming status to the log widget."""
    if state.running:
        ui.notify("Already running!", type="warning")
        return

    state.running = True
    log = state.log_element
    log.clear()
    log.push("Starting evolution loop...")

    # Parse optional task IDs.
    task_ids = None
    if task_ids_raw.strip():
        task_ids = [t.strip() for t in task_ids_raw.split(",") if t.strip()]

    def on_status(msg: str):
        log.push(msg)

    try:
        # Import lazily so the web UI starts fast.
        from evo.loop import run_loop

        loop_state = await asyncio.get_event_loop().run_in_executor(
            None,
            partial(
                run_loop,
                domain=domain,
                num_tasks=num_tasks,
                max_iterations=max_iter,
                seed=seed,
                task_ids=task_ids,
                on_status=on_status,
            ),
        )
        state.loop_state = loop_state
        _refresh_results(loop_state)
        _refresh_patches(loop_state)
        fixed = sum(1 for r in loop_state.history if r.fixed)
        log.push(f"\nDone. {fixed}/{len(loop_state.history)} failures fixed.")
        ui.notify(f"Loop complete: {fixed}/{len(loop_state.history)} fixed", type="positive")
    except Exception as e:
        log.push(f"\nERROR: {e}")
        ui.notify(str(e), type="negative")
    finally:
        state.running = False


# ---------------------------------------------------------------------------
# Refresh helpers
# ---------------------------------------------------------------------------
def _refresh_results(loop_state):
    if state.results_table is None or loop_state is None:
        return
    rows = []
    for r in loop_state.history:
        rows.append({
            "iter": r.iteration,
            "task": r.task_id,
            "baseline": f"{r.baseline_reward:.2f}",
            "patched": f"{r.patched_reward:.2f}",
            "delta": f"{r.patched_reward - r.baseline_reward:+.2f}",
            "status": "FIXED" if r.fixed else "NOT FIXED",
            "type": r.diagnosis.get("failure_type", ""),
            "explanation": r.diagnosis.get("explanation", "")[:120],
        })
    state.results_table.rows = rows
    state.results_table.update()


def _refresh_patches(loop_state):
    if state.patches_editor is None or loop_state is None:
        return
    data = {
        "prompt_patch": loop_state.prompt_patch,
        "tool_patches": loop_state.tool_patches,
    }
    state.patches_editor.set_value(json.dumps(data, indent=2))


def _load_saved_state():
    """Load loop_state.json if it exists from a previous run."""
    path = cfg.PATCHES_DIR / "loop_state.json"
    if not path.exists():
        return
    try:
        raw = json.loads(path.read_text())
        _load_state_dict(raw)
    except Exception:
        pass


def _load_state_dict(raw: dict):
    """Populate the UI from a saved state dict."""
    from evo.loop import LoopState, IterationResult

    ls = LoopState(
        prompt_patch=raw.get("prompt_patch"),
        tool_patches=raw.get("tool_patches"),
        history=[IterationResult(**h) for h in raw.get("history", [])],
    )
    state.loop_state = ls
    _refresh_results(ls)
    _refresh_patches(ls)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
@ui.page("/")
def index():
    ui.dark_mode().enable()

    with ui.header().classes("items-center justify-between"):
        ui.label("tau-evo").classes("text-xl font-bold")
        ui.label("self-evolving LLM agents").classes("text-sm opacity-70")

    with ui.splitter(value=35).classes("w-full h-full") as splitter:
        # ── Left panel: controls + log ─────────────────────────────
        with splitter.before:
            with ui.card().classes("w-full"):
                ui.label("Experiment Config").classes("text-lg font-semibold")

                domain = ui.input("Domain", value=cfg.DEFAULT_DOMAIN).classes("w-full")
                with ui.row().classes("w-full gap-2"):
                    num_tasks = ui.number("Tasks", value=cfg.DEFAULT_NUM_TASKS, min=1, max=100)
                    max_iter = ui.number("Max iterations", value=cfg.DEFAULT_MAX_ITERATIONS, min=1, max=50)
                    seed = ui.number("Seed", value=cfg.DEFAULT_SEED)
                task_ids = ui.input("Task IDs (comma-sep, optional)").classes("w-full")

                ui.button(
                    "Run Evolution Loop",
                    on_click=lambda: _run_loop_async(
                        domain.value, int(num_tasks.value), int(max_iter.value),
                        int(seed.value), task_ids.value,
                    ),
                    icon="play_arrow",
                ).classes("w-full mt-2").props("color=primary")

            with ui.card().classes("w-full mt-4"):
                ui.label("Log").classes("text-lg font-semibold")
                state.log_element = ui.log(max_lines=500).classes("w-full h-96")

        # ── Right panel: results + patches ─────────────────────────
        with splitter.after:
            with ui.card().classes("w-full"):
                ui.label("Iteration Results").classes("text-lg font-semibold")
                columns = [
                    {"name": "iter", "label": "#", "field": "iter", "sortable": True},
                    {"name": "task", "label": "Task", "field": "task", "sortable": True},
                    {"name": "baseline", "label": "Baseline", "field": "baseline"},
                    {"name": "patched", "label": "Patched", "field": "patched"},
                    {"name": "delta", "label": "Delta", "field": "delta"},
                    {"name": "status", "label": "Status", "field": "status"},
                    {"name": "type", "label": "Failure Type", "field": "type"},
                    {"name": "explanation", "label": "Explanation", "field": "explanation"},
                ]
                state.results_table = ui.table(
                    columns=columns, rows=[], row_key="iter",
                ).classes("w-full")

            with ui.card().classes("w-full mt-4"):
                ui.label("Accumulated Patches").classes("text-lg font-semibold")
                state.patches_editor = ui.textarea(
                    value="{}",
                ).classes("w-full").props("type=textarea rows=12 outlined")

    # Load previous results if available.
    _load_saved_state()


def start(port: int = 8080, reload: bool = False):
    """Entry point for the web UI."""
    ui.run(title="tau-evo", port=port, reload=reload, show=False)
