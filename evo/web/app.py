"""FastAPI + Jinja2 + HTMX web dashboard for tau-evo experiments."""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

import evo.config as cfg
from evo.analysis.charts import all_charts_from_history

cfg.ensure_dirs()

logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("LiteLLM Router").setLevel(logging.CRITICAL)
logging.getLogger("LiteLLM Proxy").setLevel(logging.CRITICAL)

DOMAINS = ["airline", "retail", "telecom"]

app = FastAPI(title="tau-evo")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# ---------------------------------------------------------------------------
# In-memory state (single-user, single-run)
# ---------------------------------------------------------------------------
_running = False
_log_queue: queue.Queue[str] = queue.Queue()
_loop_state: Optional[object] = None  # LoopState once finished


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    saved = _load_saved_state()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "domains": DOMAINS,
        "defaults": {
            "domain": cfg.DEFAULT_DOMAIN,
            "num_tasks": cfg.DEFAULT_NUM_TASKS,
            "max_iterations": cfg.DEFAULT_MAX_ITERATIONS,
            "seed": cfg.DEFAULT_SEED,
        },
        "results": saved.get("results", []),
        "patches": saved.get("patches", "{}"),
        "running": _running,
    })


@app.post("/run", response_class=HTMLResponse)
async def run(request: Request):
    global _running, _loop_state

    if _running:
        return HTMLResponse('<div id="status" class="text-yellow-400">Already running.</div>')

    form = await request.form()
    domain = form.get("domain", cfg.DEFAULT_DOMAIN)
    max_iter = int(form.get("max_iterations", cfg.DEFAULT_MAX_ITERATIONS))
    seed = int(form.get("seed", cfg.DEFAULT_SEED))
    use_task_ids = form.get("use_task_ids") == "on"
    task_ids_raw = form.get("task_ids", "")
    num_tasks = int(form.get("num_tasks", cfg.DEFAULT_NUM_TASKS))

    task_ids = None
    if use_task_ids and task_ids_raw.strip():
        task_ids = [t.strip() for t in task_ids_raw.split(",") if t.strip()]

    _running = True
    # Clear old logs
    while not _log_queue.empty():
        try:
            _log_queue.get_nowait()
        except queue.Empty:
            break

    def _run_in_thread():
        global _running, _loop_state
        try:
            from evo.parallel_loop import run_loop

            state = run_loop(
                domain=domain,
                num_tasks=num_tasks,
                max_iterations=max_iter,
                seed=seed,
                task_ids=task_ids,
                on_status=lambda msg: _log_queue.put(msg),
            )
            _loop_state = state
            total_fixed = sum(r.num_fixed for r in state.history)
            total_failures = sum(r.num_failures for r in state.history)
            _log_queue.put(f"\nDone. {total_fixed}/{total_failures} total fixes.")
            _log_queue.put("[CHARTS]")
        except Exception as e:
            _log_queue.put(f"\nERROR: {e}")
        finally:
            _running = False
            _log_queue.put("[DONE]")

    threading.Thread(target=_run_in_thread, daemon=True).start()

    return HTMLResponse(
        '<div id="status" class="text-green-400">Started.</div>'
        '<script>startSSE()</script>'
    )


@app.get("/logs")
async def logs():
    """SSE endpoint streaming log messages."""
    async def event_generator():
        while True:
            try:
                msg = _log_queue.get_nowait()
            except queue.Empty:
                if not _running and _log_queue.empty():
                    # Check once more — race between _running flip and last msg
                    await asyncio.sleep(0.1)
                    if _log_queue.empty():
                        yield {"event": "done", "data": ""}
                        return
                await asyncio.sleep(0.2)
                continue

            if msg == "[DONE]":
                yield {"event": "done", "data": ""}
                return
            if msg == "[CHARTS]":
                yield {"event": "charts", "data": "update"}
                continue
            yield {"event": "log", "data": msg}

    return EventSourceResponse(event_generator())


@app.get("/results", response_class=HTMLResponse)
async def results(request: Request):
    """Return the results table fragment."""
    rows = _build_results()
    return templates.TemplateResponse("_results.html", {
        "request": request,
        "results": rows,
        "patches": _build_patches_json(),
    })


@app.get("/api/charts")
async def api_charts():
    """Return Plotly figure dicts for all charts."""
    history = _build_history_dicts()
    charts = all_charts_from_history(history)
    return JSONResponse(charts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_results() -> list[dict]:
    if _loop_state is None:
        return []
    rows = []
    for r in _loop_state.history:
        for fix in r.fixes:
            rows.append({
                "iter": r.iteration,
                "task": fix.task_id,
                "baseline": f"{fix.baseline_reward:.2f}",
                "patched": f"{fix.patched_reward:.2f}",
                "delta": f"{fix.patched_reward - fix.baseline_reward:+.2f}",
                "retries": fix.retries,
                "status": "FIXED" if fix.fixed else "NOT FIXED",
                "diagnosis": (fix.diagnosis or "")[:120],
            })
    return rows


def _build_history_dicts() -> list[dict]:
    """Flatten history into per-fix dicts for charts compatibility."""
    if _loop_state is None:
        return []
    rows = []
    for r in _loop_state.history:
        for fix in r.fixes:
            rows.append({
                "iteration": r.iteration,
                "task_id": fix.task_id,
                "baseline_reward": fix.baseline_reward,
                "patched_reward": fix.patched_reward,
                "fixed": fix.fixed,
                "diagnosis": fix.diagnosis,
                "retries": fix.retries,
            })
    return rows


def _build_patches_json() -> str:
    if _loop_state is None:
        return "{}"
    data = {
        "prompt_instruction": _loop_state.prompt_instruction,
        "tool_schemas": _loop_state.tool_schemas,
    }
    return json.dumps(data, indent=2)


def _load_saved_state() -> dict:
    path = cfg.PATCHES_DIR / "loop_state.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
        from evo.parallel_loop import LoopState, IterationResult, FixResult
        global _loop_state
        history = []
        for h in raw.get("history", []):
            fixes = [FixResult(**f) for f in h.get("fixes", [])]
            history.append(IterationResult(
                iteration=h["iteration"],
                num_evaluated=h["num_evaluated"],
                num_failures=h["num_failures"],
                fixes=fixes,
                num_fixed=h["num_fixed"],
            ))
        ls = LoopState(
            prompt_instruction=raw.get("prompt_instruction"),
            tool_schemas=raw.get("tool_schemas"),
            history=history,
        )
        _loop_state = ls
        return {"results": _build_results(), "patches": _build_patches_json()}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def start(port: int = 8080, reload: bool = False):
    import uvicorn
    uvicorn.run(
        "evo.web.app:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
        reload_dirs=[str(Path(__file__).resolve().parents[1])] if reload else None,
    )
