"""FastAPI + Jinja2 + HTMX web dashboard for tau-evo experiments."""

from __future__ import annotations

import asyncio
import json
import queue
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

import evo.config as cfg
import evo.session_log as slog
from evo.analysis.charts import all_charts, all_charts_from_state
from evo.models import LoopState, Patch, RunMeta

cfg.ensure_dirs()
cfg.quiet_deps()

app = FastAPI(title="tau-evo")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# ---------------------------------------------------------------------------
# In-memory state (single-user, single-run)
# ---------------------------------------------------------------------------
_running = False
_log_queue: queue.Queue[str] = queue.Queue()

# Route orchestrator logs (agent/user/env messages) to the SSE log queue.
from loguru import logger as _loguru

def _loguru_sink(message):
    """Forward loguru records from tau2.orchestrator to the web SSE queue."""
    text = str(message).rstrip()
    if " - " in text:
        text = text.split(" - ", 1)[1]
    _log_queue.put(text)

_loguru.add(_loguru_sink, filter="tau2.orchestrator", level="INFO")
_loop_state: Optional[LoopState] = None
_current_run_id: Optional[str] = None
_live_fixes: dict[str, dict] = {}  # task_id -> {patches, diagnosis, attempt, status}

# In-memory teacher sessions (students are disk-only since they complete instantly).
_teacher_sessions: dict = {}
_teacher_sessions_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Run persistence helpers
# ---------------------------------------------------------------------------
def _save_run(state: LoopState) -> None:
    if state.meta is None:
        return
    state.meta.total_fixes = state.total_fixed
    state.meta.total_failures = state.total_failures
    path = cfg.RUNS_DIR / f"{state.meta.run_id}.json"
    state.save(path)


def _list_runs() -> list[RunMeta]:
    runs = []
    for p in cfg.RUNS_DIR.glob("*.json"):
        try:
            raw = json.loads(p.read_text())
            meta_raw = raw.get("meta")
            if meta_raw:
                runs.append(RunMeta(**meta_raw))
        except Exception:
            continue
    runs.sort(key=lambda r: r.started_at, reverse=True)
    return runs


def _safe_run_path(run_id: str) -> Optional[Path]:
    """Return the run file path if run_id is safe, else None."""
    path = (cfg.RUNS_DIR / f"{run_id}.json").resolve()
    if path.parent != cfg.RUNS_DIR.resolve():
        return None
    return path


def _load_run(run_id: str) -> Optional[LoopState]:
    path = _safe_run_path(run_id)
    if path is None or not path.exists():
        return None
    try:
        return LoopState.load(path)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Session callbacks (teacher + student)
# ---------------------------------------------------------------------------
def _on_teacher_message(session, message) -> None:
    """Callback from TeacherSession — runs in the teacher's thread."""
    is_new = False
    with _teacher_sessions_lock:
        if session.session_id not in _teacher_sessions:
            is_new = True
        _teacher_sessions[session.session_id] = session
    payload = json.dumps({
        "session_id": session.session_id,
        "session_type": "teacher",
        "task_id": session.task_id,
        "status": session.status,
        "message_count": len(session._messages),
        "is_new": is_new,
    })
    _log_queue.put(f"[SESSION:{payload}]")


def _on_student_session(session_id: str, data: slog.SessionData) -> None:
    """Callback when a student session is saved to disk."""
    payload = json.dumps({
        "session_id": session_id,
        "session_type": "student",
        "task_id": data.task_id,
        "status": "done",
        "message_count": len(data.messages),
        "is_new": True,
        "reward": data.reward,
    })
    _log_queue.put(f"[SESSION:{payload}]")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    _try_load_latest_run()
    fixes = _loop_state.flat_fixes() if _loop_state else []
    total = len(fixes)
    fixed = sum(1 for f in fixes if f.fixed)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "domains": cfg.DOMAINS,
        "student_models": cfg.STUDENT_MODELS,
        "defaults": {
            "domain": cfg.DEFAULT_DOMAIN,
            "student_model": cfg.STUDENT_MODEL,
            "num_tasks": cfg.DEFAULT_NUM_TASKS,
            "max_iterations": cfg.DEFAULT_MAX_ITERATIONS,
            "parallelism": cfg.DEFAULT_PARALLELISM,
            "seed": cfg.DEFAULT_SEED,
        },
        "results": _build_results(),
        "running": _running,
        "runs": _list_runs(),
        "active_run_id": _current_run_id,
        "total": total,
        "fixed": fixed,
        "not_fixed": total - fixed,
        "rate": int(fixed / total * 100) if total else 0,
    })


@app.post("/run", response_class=HTMLResponse)
async def run(request: Request):
    global _running, _loop_state, _current_run_id

    if _running:
        return HTMLResponse('<div id="status" class="text-yellow-400">Already running.</div>')

    form = await request.form()
    domain = form.get("domain", cfg.DEFAULT_DOMAIN)
    student_model = form.get("student_model", cfg.STUDENT_MODEL)
    if student_model not in cfg.STUDENT_MODELS:
        student_model = cfg.STUDENT_MODEL
    max_iter = int(form.get("max_iterations", cfg.DEFAULT_MAX_ITERATIONS))
    parallelism = int(form.get("parallelism", cfg.DEFAULT_PARALLELISM))
    seed = int(form.get("seed", cfg.DEFAULT_SEED))
    use_task_ids = form.get("use_task_ids") == "on"
    task_ids_raw = form.get("task_ids", "")
    num_tasks = int(form.get("num_tasks", cfg.DEFAULT_NUM_TASKS))

    task_ids = None
    if use_task_ids and task_ids_raw.strip():
        task_ids = [t.strip() for t in task_ids_raw.split(",") if t.strip()]

    run_id = RunMeta.make_id(domain)
    _current_run_id = run_id
    _running = True
    _loop_state = None
    with _teacher_sessions_lock:
        _teacher_sessions.clear()
    while not _log_queue.empty():
        try:
            _log_queue.get_nowait()
        except queue.Empty:
            break

    def _run_in_thread():
        global _running, _loop_state
        try:
            from evo.parallel_loop import run_loop

            meta = RunMeta(
                run_id=run_id,
                domain=domain,
                started_at=datetime.now().isoformat(),
                status="running",
                num_tasks=num_tasks,
            )

            def _on_iteration(state: LoopState):
                global _loop_state
                state.meta = meta
                _loop_state = state
                _live_fixes.clear()
                _save_run(state)
                _log_queue.put("[SAVE]")

            def _on_fix_attempt(task_id: str, attempt: int, patches: list[Patch],
                                diagnosis: str, status: str):
                _live_fixes[task_id] = {
                    "task_id": task_id,
                    "attempt": attempt + 1,
                    "patches": [{"old_text": p.old_text, "new_text": p.new_text,
                                 "tool_name": p.tool_name} for p in patches],
                    "diagnosis": diagnosis or "",
                    "status": status,
                }
                _log_queue.put("[LIVE]")

            state = run_loop(
                domain=domain,
                num_tasks=num_tasks,
                max_iterations=max_iter,
                parallelism=parallelism,
                seed=seed,
                task_ids=task_ids,
                student_model=student_model,
                on_status=lambda msg: _log_queue.put(msg),
                on_iteration=_on_iteration,
                on_fix_attempt=_on_fix_attempt,
                on_teacher_message=_on_teacher_message,
                on_session=_on_student_session,
            )
            meta.status = "finished"
            state.meta = meta
            _loop_state = state
            _live_fixes.clear()
            _save_run(state)
            _log_queue.put(f"\nDone. {state.total_fixed}/{state.total_failures} total fixes.")
            _log_queue.put("[CHARTS]")
        except Exception as e:
            meta.status = "error"
            if _loop_state:
                _loop_state.meta = meta
                _save_run(_loop_state)
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
            if msg == "[SAVE]":
                yield {"event": "save", "data": "update"}
                continue
            if msg == "[LIVE]":
                yield {"event": "live", "data": "update"}
                continue
            if msg.startswith("[SESSION:"):
                payload = msg[len("[SESSION:"):-1]
                yield {"event": "session", "data": payload}
                continue
            yield {"event": "log", "data": msg}

    return EventSourceResponse(event_generator())


@app.get("/results", response_class=HTMLResponse)
async def results(request: Request):
    fixes = _loop_state.flat_fixes() if _loop_state else []
    total = len(fixes)
    fixed = sum(1 for f in fixes if f.fixed)
    return templates.TemplateResponse("_results.html", {
        "request": request,
        "results": _build_results(),
        "total": total,
        "fixed": fixed,
        "not_fixed": total - fixed,
        "rate": int(fixed / total * 100) if total else 0,
    })


@app.get("/summary", response_class=HTMLResponse)
async def summary(request: Request):
    fixes = _loop_state.flat_fixes() if _loop_state else []
    total = len(fixes)
    fixed = sum(1 for f in fixes if f.fixed)

    # If no fixes but we have eval data, show eval-based pass rate
    eval_total = 0
    eval_passed = 0
    if _loop_state and not fixes:
        for h in _loop_state.history:
            eval_total += len(h.eval_rewards)
            eval_passed += sum(1 for r in h.eval_rewards.values() if r >= 1.0)

    return templates.TemplateResponse("_summary.html", {
        "request": request,
        "total": total,
        "fixed": fixed,
        "not_fixed": total - fixed,
        "rate": int(fixed / total * 100) if total else (
            int(eval_passed / eval_total * 100) if eval_total else 0
        ),
        "eval_total": eval_total,
        "eval_passed": eval_passed,
    })


@app.get("/api/live-fixes")
async def api_live_fixes():
    return JSONResponse(list(_live_fixes.values()))


@app.get("/api/charts")
async def api_charts():
    if _loop_state is None:
        return JSONResponse(all_charts([]))
    return JSONResponse(all_charts_from_state(_loop_state))


# ---------------------------------------------------------------------------
# Unified session API (teacher + student)
# ---------------------------------------------------------------------------
def _get_session_data(session_id: str) -> Optional[slog.SessionData]:
    """Resolve a session: in-memory teacher first, then disk."""
    with _teacher_sessions_lock:
        ts = _teacher_sessions.get(session_id)
    if ts:
        return ts._as_session_data()
    return slog.load_session(session_id)


_DUMP = dict(exclude_none=True)


@app.get("/api/sessions")
async def api_sessions(type: Optional[str] = None):
    """List all sessions. Optional ?type=teacher or ?type=student."""
    with _teacher_sessions_lock:
        active: dict[str, slog.SessionSummary] = {
            sid: s.get_log_snapshot() for sid, s in _teacher_sessions.items()
        }

    disk = slog.list_sessions(session_type=type)

    merged: dict[str, slog.SessionSummary] = {}
    for s in disk:
        merged[s.session_id] = s
    if type is None or type == "teacher":
        for sid, s in active.items():
            merged[sid] = s

    result = sorted(merged.values(), key=lambda s: s.started_at, reverse=True)
    return JSONResponse([s.model_dump(**_DUMP) for s in result])


@app.get("/api/sessions/{session_id}")
async def api_session(session_id: str):
    """Full session data (messages, errors, etc)."""
    data = _get_session_data(session_id)
    if data is None:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return JSONResponse(data.model_dump(**_DUMP))


@app.get("/api/sessions/{session_id}/messages")
async def api_session_messages(session_id: str, after: int = 0):
    """Incremental message fetch for live polling."""
    data = _get_session_data(session_id)
    if data is None:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    msgs = data.messages[after:]
    return JSONResponse({
        "messages": [m.model_dump(**_DUMP) for m in msgs],
        "total": len(data.messages),
        "status": data.status,
        "session_type": data.session_type,
        "reward": data.reward,
    })


# ---------------------------------------------------------------------------
# Run history endpoints
# ---------------------------------------------------------------------------
@app.get("/runs", response_class=HTMLResponse)
async def runs_list(request: Request):
    return templates.TemplateResponse("_history.html", {
        "request": request,
        "runs": _list_runs(),
        "active_run_id": _current_run_id,
    })


@app.get("/runs/{run_id}", response_class=HTMLResponse)
async def load_run_endpoint(run_id: str, request: Request):
    global _loop_state, _current_run_id
    state = _load_run(run_id)
    if state is None:
        return HTMLResponse('<p class="text-red-400 text-sm">Run not found.</p>')
    _loop_state = state
    _current_run_id = run_id
    fixes = state.flat_fixes()
    total = len(fixes)
    fixed = sum(1 for f in fixes if f.fixed)
    return templates.TemplateResponse("_results.html", {
        "request": request,
        "results": _build_results(),
        "total": total,
        "fixed": fixed,
        "not_fixed": total - fixed,
        "rate": int(fixed / total * 100) if total else 0,
    })


@app.delete("/runs/{run_id}")
async def delete_run(run_id: str):
    global _loop_state, _current_run_id
    path = _safe_run_path(run_id)
    if path is not None and path.exists():
        path.unlink()
    if _current_run_id == run_id:
        _loop_state = None
        _current_run_id = None
    return HTMLResponse("")


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
                "delta": f"{fix.delta:+.2f}",
                "retries": fix.retries,
                "status": "FIXED" if fix.fixed else "NOT FIXED",
                "diagnosis": (fix.diagnosis or "")[:120],
                "patches": fix.patches,
            })
    return rows


def _try_load_latest_run() -> None:
    global _loop_state, _current_run_id
    if _loop_state is not None:
        return
    runs = _list_runs()
    if not runs:
        path = cfg.PATCHES_DIR / "loop_state.json"
        if path.exists():
            try:
                _loop_state = LoopState.load(path)
            except Exception:
                pass
        return
    latest = runs[0]
    state = _load_run(latest.run_id)
    if state:
        _loop_state = state
        _current_run_id = latest.run_id


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
