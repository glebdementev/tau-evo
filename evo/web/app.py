"""FastAPI + Jinja2 + HTMX web dashboard for tau-evo experiments."""

from __future__ import annotations

import asyncio
import json
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

import evo.config as cfg
import evo.session_log as slog
from evo.analysis.charts import all_charts_from_state
from evo.models import (
    LoopState, Patch, RunMeta,
    FIX_TIER_PROMPT, FIX_TIER_CODE,
    RUN_RUNNING, RUN_FINISHED, RUN_STOPPED, RUN_ERROR,
)

# SSE event sentinels.
_EVT_DONE = "[DONE]"
_EVT_CHARTS = "[CHARTS]"
_EVT_SAVE = "[SAVE]"
_EVT_LIVE = "[LIVE]"
_EVT_PHASE_PREFIX = "[PHASE:"
_EVT_SESSION_PREFIX = "[SESSION:"

cfg.ensure_dirs()
cfg.quiet_deps()

app = FastAPI(title="tau-evo")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# ---------------------------------------------------------------------------
# In-memory state (single-user, single-run)
# ---------------------------------------------------------------------------
_running = False


class EventBuffer:
    """Thread-safe ring buffer of SSE events with monotonic sequence IDs.

    Supports replay from a given sequence ID so reconnecting clients
    can recover missed events via the browser's native Last-Event-ID header.
    """

    def __init__(self, maxlen: int = 2000):
        self._lock = threading.Lock()
        self._buf: deque[tuple[int, str]] = deque(maxlen=maxlen)
        self._seq = 0

    def put(self, msg: str) -> int:
        with self._lock:
            self._seq += 1
            self._buf.append((self._seq, msg))
            return self._seq

    def get_after(self, after_seq: int) -> list[tuple[int, str]]:
        with self._lock:
            return [(s, m) for s, m in self._buf if s > after_seq]

    @property
    def latest_seq(self) -> int:
        with self._lock:
            return self._seq

    def clear(self) -> None:
        with self._lock:
            self._buf.clear()
            # Don't reset _seq — clients holding old IDs should get
            # an empty replay rather than duplicate events.


_events = EventBuffer()

# Route orchestrator logs (agent/user/env messages) to the SSE log queue.
# Only forward when a run is active to avoid stale messages between runs.
from loguru import logger as _loguru

def _loguru_sink(message):
    """Forward loguru INFO records from tau2.orchestrator to the web SSE queue.

    Message content is logged at DEBUG and filtered out by level="INFO".
    Only step-transition lines (e.g. "Step 6: agent -> user") reach here.
    """
    if not _running:
        return
    text = str(message).rstrip()
    if " - " in text:
        text = text.split(" - ", 1)[1]
    _events.put(text)

_loguru.add(_loguru_sink, filter="tau2.orchestrator", level="INFO")

# Active run (written by the loop thread)
_active_run_id: Optional[str] = None
_active_state: Optional[LoopState] = None
_live_fixes: dict[str, dict] = {}  # task_id -> {patches, diagnosis, attempt, status}
_stop_event: Optional[threading.Event] = None  # set to request graceful stop

# Viewed run (what the dashboard displays — may differ from active)
_viewed_run_id: Optional[str] = None
_viewed_state: Optional[LoopState] = None

# Session IDs belonging to the currently *executing* run.
_run_session_ids: set[str] = set()
_run_session_ids_lock = threading.Lock()

# In-memory teacher sessions — only for live-polling active sessions.
# Cleared when a run finishes so stale entries don't pollute the session list.
_teacher_sessions: dict = {}
_teacher_sessions_lock = threading.Lock()


def _viewing_active() -> bool:
    return _active_run_id is not None and _viewed_run_id == _active_run_id


def _get_viewed_state() -> Optional[LoopState]:
    """Return the LoopState for the currently viewed run."""
    if _viewing_active():
        return _active_state
    return _viewed_state


def _get_viewed_session_ids() -> set[str]:
    """Return session IDs for the currently viewed run."""
    if _viewing_active():
        with _run_session_ids_lock:
            return set(_run_session_ids)
    state = _viewed_state
    return set(state.session_ids) if state else set()


# ---------------------------------------------------------------------------
# Run persistence helpers
# ---------------------------------------------------------------------------
def _save_run(state: LoopState) -> None:
    if state.meta is None:
        return
    state.meta.total_fixes = state.total_fixed
    state.meta.total_failures = state.total_failures
    with _run_session_ids_lock:
        state.session_ids = sorted(_run_session_ids)
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
def _register_session(session_id: str) -> bool:
    """Add session_id to current run's set. Returns True if new."""
    with _run_session_ids_lock:
        is_new = session_id not in _run_session_ids
        _run_session_ids.add(session_id)
    return is_new


def _on_teacher_message(session, message) -> None:
    """Callback from TeacherSession — runs in the teacher's thread."""
    is_new = _register_session(session.session_id)
    with _teacher_sessions_lock:
        _teacher_sessions[session.session_id] = session
    payload = json.dumps({
        "session_id": session.session_id,
        "session_type": "teacher",
        "task_id": session.task_id,
        "status": session.status,
        "message_count": len(session._messages),
        "is_new": is_new,
    })
    _events.put(f"{_EVT_SESSION_PREFIX}{payload}]")


def _on_student_session(session_id: str, data: slog.SessionData) -> None:
    """Callback when a student session is saved to disk."""
    _register_session(session_id)
    payload = json.dumps({
        "session_id": session_id,
        "session_type": "student",
        "task_id": data.task_id,
        "status": "done",
        "message_count": len(data.messages),
        "is_new": True,
        "reward": data.reward,
        "context": data.context or "",
    })
    _events.put(f"{_EVT_SESSION_PREFIX}{payload}]")


# ---------------------------------------------------------------------------
# Shared loop thread helpers
# ---------------------------------------------------------------------------
def _on_iteration_cb(meta: RunMeta):
    """Create an on_iteration callback bound to a RunMeta."""
    def _on_iteration(state: LoopState):
        global _active_state
        state.meta = meta
        _active_state = state
        _live_fixes.clear()
        _save_run(state)
        _events.put(_EVT_SAVE)
    return _on_iteration


def _make_phase_cb(max_sweeps: int, has_test: bool = False):
    """Return an on_phase callback that includes max_sweeps in the event."""
    def _on_phase(sweep: int, phase_name: str, phase_status: str):
        payload = json.dumps({
            "sweep": sweep, "phase": phase_name,
            "status": phase_status, "max_sweeps": max_sweeps,
            "has_test": has_test,
        })
        _events.put(f"{_EVT_PHASE_PREFIX}{payload}]")
    return _on_phase


def _on_fix_attempt_cb(task_id: str, attempt: int, patches: list[Patch],
                       diagnosis: str, status: str):
    _live_fixes[task_id] = {
        "task_id": task_id,
        "attempt": attempt + 1,
        "patches": [{"old_text": p.old_text, "new_text": p.new_text,
                     "tool_name": p.tool_name} for p in patches],
        "diagnosis": diagnosis or "",
        "status": status,
    }
    _events.put(_EVT_LIVE)


def _finish_loop_thread(meta: RunMeta, state: LoopState) -> None:
    """Post-run bookkeeping shared by run and resume threads."""
    global _active_state
    was_stopped = _stop_event is not None and _stop_event.is_set()
    meta.status = RUN_STOPPED if was_stopped else RUN_FINISHED
    state.meta = meta
    _active_state = state
    _live_fixes.clear()
    _save_run(state)
    _events.put(f"\nDone. {state.total_fixed}/{state.total_failures} total fixes.")
    _events.put(_EVT_CHARTS)


def _teardown_loop_thread() -> None:
    """Clean up global state after any loop thread exits."""
    global _running, _active_run_id, _active_state, _viewed_state
    if _viewed_run_id == _active_run_id and _active_state:
        with _run_session_ids_lock:
            _active_state.session_ids = sorted(_run_session_ids)
        _viewed_state = _active_state
    _running = False
    _active_run_id = None
    _active_state = None
    _live_fixes.clear()
    with _teacher_sessions_lock:
        _teacher_sessions.clear()
    _events.put(_EVT_DONE)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    _try_load_latest_run()
    state = _get_viewed_state()
    ctx = _build_stats_context(state)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "domains": cfg.DOMAINS,
        "student_models": cfg.STUDENT_MODELS,
        "defaults": {
            "domain": cfg.DEFAULT_DOMAIN,
            "student_model": cfg.STUDENT_MODEL,
            "num_tasks": cfg.DEFAULT_NUM_TASKS,
            "max_sweeps": cfg.DEFAULT_MAX_SWEEPS,
            "parallelism": cfg.DEFAULT_PARALLELISM,
            "seed": cfg.DEFAULT_SEED,
        },
        "domain_train_tasks": cfg.DOMAIN_TRAIN_TASKS,
        "results": _build_results(),
        "running": _running,
        "runs": _list_runs(),
        "active_run_id": _active_run_id,
        "viewed_run_id": _viewed_run_id,
        **ctx,
    })


@app.post("/run", response_class=HTMLResponse)
async def run(request: Request):
    global _running, _active_run_id, _active_state, _viewed_run_id, _viewed_state, _stop_event

    if _running:
        return HTMLResponse('<div id="status" class="text-yellow-400">Already running.</div>')

    form = await request.form()
    domain = form.get("domain", cfg.DEFAULT_DOMAIN)
    student_model = form.get("student_model", cfg.STUDENT_MODEL)
    if student_model not in cfg.STUDENT_MODELS:
        student_model = cfg.STUDENT_MODEL
    max_sweeps = int(form.get("max_sweeps", cfg.DEFAULT_MAX_SWEEPS))
    parallelism = int(form.get("parallelism", cfg.DEFAULT_PARALLELISM))
    seed = int(form.get("seed", cfg.DEFAULT_SEED))
    use_task_ids = form.get("use_task_ids") == "on"
    task_ids_raw = form.get("task_ids", "")
    num_tasks = int(form.get("num_tasks", cfg.DEFAULT_NUM_TASKS))

    max_for_domain = cfg.DOMAIN_TRAIN_TASKS.get(domain, cfg.DOMAIN_NUM_TASKS.get(domain, 100))
    if num_tasks > max_for_domain:
        num_tasks = max_for_domain

    task_ids = None
    if use_task_ids and task_ids_raw.strip():
        task_ids = [t.strip() for t in task_ids_raw.split(",") if t.strip()]

    run_id = RunMeta.make_id(domain)
    _running = True
    _active_run_id = run_id
    _viewed_run_id = run_id
    _viewed_state = None  # viewed == active, so _get_viewed_state() returns _active_state
    _stop_event = threading.Event()
    with _teacher_sessions_lock:
        _teacher_sessions.clear()
    with _run_session_ids_lock:
        _run_session_ids.clear()
    _drain_queue()

    # Save the run immediately so it appears in history while running.
    meta = RunMeta(
        run_id=run_id,
        domain=domain,
        started_at=datetime.now().isoformat(),
        status=RUN_RUNNING,
        num_tasks=num_tasks,
    )
    _active_state = LoopState(meta=meta)
    _save_run(_active_state)

    def _run_in_thread():
        try:
            from evo.parallel_loop import run_loop
            state = run_loop(
                domain=domain,
                num_tasks=num_tasks,
                max_sweeps=max_sweeps,
                parallelism=parallelism,
                seed=seed,
                task_ids=task_ids,
                student_model=student_model,
                on_status=lambda msg: _events.put(msg),
                on_iteration=_on_iteration_cb(meta),
                on_phase=_make_phase_cb(max_sweeps, has_test=(task_ids is None)),
                on_fix_attempt=_on_fix_attempt_cb,
                on_teacher_message=_on_teacher_message,
                on_session=_on_student_session,
                stop_event=_stop_event,
            )
            _finish_loop_thread(meta, state)
        except Exception as e:
            meta.status = RUN_ERROR
            if _active_state:
                _active_state.meta = meta
                _save_run(_active_state)
            _events.put(f"\nERROR: {e}")
        finally:
            _teardown_loop_thread()

    threading.Thread(target=_run_in_thread, daemon=True).start()

    return HTMLResponse(
        '<div id="status" class="text-green-400">Started.</div>'
        '<script>startSSE(true)</script>'
    )


@app.get("/logs")
async def logs(request: Request):
    """SSE endpoint streaming log messages with replay support.

    Clients can reconnect with Last-Event-ID to recover missed events.
    Terminates only on the [DONE] sentinel.
    """
    # Determine replay point from Last-Event-ID header.
    last_id = request.headers.get("last-event-id")
    cursor = int(last_id) if last_id and last_id.isdigit() else _events.latest_seq

    def _parse_event(msg: str) -> dict:
        if msg == _EVT_DONE:
            return {"event": "done", "data": ""}
        if msg == _EVT_CHARTS:
            return {"event": "charts", "data": "update"}
        if msg == _EVT_SAVE:
            return {"event": "save", "data": "update"}
        if msg == _EVT_LIVE:
            return {"event": "live", "data": "update"}
        if msg.startswith(_EVT_PHASE_PREFIX):
            return {"event": "phase", "data": msg[len(_EVT_PHASE_PREFIX):-1]}
        if msg.startswith(_EVT_SESSION_PREFIX):
            return {"event": "session", "data": msg[len(_EVT_SESSION_PREFIX):-1]}
        return {"event": "log", "data": msg}

    async def event_generator():
        nonlocal cursor

        while True:
            new = _events.get_after(cursor)
            for seq, msg in new:
                ev = _parse_event(msg)
                ev["id"] = str(seq)
                cursor = seq
                if ev["event"] == "done":
                    yield ev
                    return
                yield ev

            await asyncio.sleep(0.2)

    return EventSourceResponse(event_generator())


def _build_resume_context(state: Optional[LoopState]) -> dict:
    """Build can_resume / run_status / resume_iteration for templates."""
    can_resume = (
        _viewed_run_id is not None
        and not _running
        and state is not None
        and state.meta is not None
        and state.meta.status in (RUN_STOPPED, RUN_ERROR)
    )
    return {
        "can_resume": can_resume,
        "run_status": state.meta.status if state and state.meta else "",
        "resume_sweep": len(state.history) + 1 if state else 1,
    }


@app.get("/results", response_class=HTMLResponse)
async def results(request: Request):
    state = _get_viewed_state()
    ctx = _build_stats_context(state)
    return templates.TemplateResponse("_results.html", {
        "request": request,
        "results": _build_results(),
        **ctx,
        **_build_resume_context(state),
        "viewed_run_id": _viewed_run_id,
    })


@app.get("/summary", response_class=HTMLResponse)
async def summary(request: Request):
    state = _get_viewed_state()
    return templates.TemplateResponse("_summary.html", {
        "request": request,
        **_build_stats_context(state),
    })


@app.get("/api/live-fixes")
async def api_live_fixes():
    if not _viewing_active():
        return JSONResponse([])
    return JSONResponse(list(_live_fixes.values()))


@app.get("/api/state")
async def api_state():
    return JSONResponse({
        "running": _running,
        "active_run_id": _active_run_id,
        "viewed_run_id": _viewed_run_id,
    })


@app.get("/api/charts")
async def api_charts():
    state = _get_viewed_state()
    if state is None:
        return JSONResponse(all_charts_from_state(LoopState()))
    return JSONResponse(all_charts_from_state(state))


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
    """List sessions belonging to the viewed run. Optional ?type=teacher or ?type=student."""
    allowed = _get_viewed_session_ids()
    if not allowed:
        return JSONResponse([])

    # Only include live teacher sessions when viewing the active run.
    active: dict[str, slog.SessionSummary] = {}
    if _viewing_active():
        with _teacher_sessions_lock:
            for sid, s in _teacher_sessions.items():
                if sid in allowed:
                    try:
                        active[sid] = s.get_log_snapshot()
                    except Exception:
                        pass

    disk = slog.list_sessions(session_type=type, only_ids=allowed)

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
    if session_id not in _get_viewed_session_ids():
        return JSONResponse({"error": "Session not found"}, status_code=404)
    data = _get_session_data(session_id)
    if data is None:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    result = data.model_dump(**_DUMP)
    result["duration_s"] = slog._calc_duration(data)
    return JSONResponse(result)


@app.get("/api/sessions/{session_id}/messages")
async def api_session_messages(session_id: str, after: int = 0):
    """Incremental message fetch for live polling."""
    if session_id not in _get_viewed_session_ids():
        return JSONResponse({"error": "Session not found"}, status_code=404)
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


@app.get("/api/sessions/teacher-summary")
async def api_teacher_summary():
    """Download all teacher session summaries for the viewed run as JSON."""
    from fastapi.responses import Response

    allowed = _get_viewed_session_ids()
    if not allowed:
        return JSONResponse([])

    active: dict[str, slog.SessionSummary] = {}
    if _viewing_active():
        with _teacher_sessions_lock:
            for sid, s in _teacher_sessions.items():
                if sid in allowed:
                    try:
                        active[sid] = s.get_log_snapshot()
                    except Exception:
                        pass

    disk = slog.list_sessions(session_type="teacher", only_ids=allowed)

    merged: dict[str, slog.SessionSummary] = {}
    for s in disk:
        merged[s.session_id] = s
    for sid, s in active.items():
        merged[sid] = s

    result = sorted(merged.values(), key=lambda s: s.started_at, reverse=True)
    data = [s.model_dump(**_DUMP) for s in result]

    run_id = _viewed_run_id or _active_run_id or "unknown"
    filename = f"teacher_sessions_{run_id}.json"

    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Run history endpoints
# ---------------------------------------------------------------------------
@app.get("/runs", response_class=HTMLResponse)
async def runs_list(request: Request):
    return templates.TemplateResponse("_history.html", {
        "request": request,
        "runs": _list_runs(),
        "active_run_id": _active_run_id,
        "viewed_run_id": _viewed_run_id,
    })


@app.get("/runs/{run_id}", response_class=HTMLResponse)
async def load_run_endpoint(run_id: str, request: Request):
    global _viewed_run_id, _viewed_state
    if run_id == _active_run_id:
        # Switch view back to the active run
        _viewed_run_id = run_id
        _viewed_state = None
        state = _active_state
    else:
        state = _load_run(run_id)
        if state is None:
            return HTMLResponse('<p class="text-red-400 text-sm">Run not found.</p>')
        _viewed_run_id = run_id
        _viewed_state = state
    ctx = _build_stats_context(state)
    return templates.TemplateResponse("_results.html", {
        "request": request,
        "results": _build_results(),
        **ctx,
        **_build_resume_context(state),
        "viewed_run_id": _viewed_run_id,
    })


@app.delete("/runs/{run_id}")
async def delete_run(run_id: str):
    global _viewed_run_id, _viewed_state
    if _running and run_id == _active_run_id:
        return HTMLResponse('<p class="text-yellow-400 text-sm">Cannot delete the active run.</p>', status_code=409)
    path = _safe_run_path(run_id)
    if path is not None and path.exists():
        path.unlink()
    if _viewed_run_id == run_id:
        _viewed_run_id = None
        _viewed_state = None
    return HTMLResponse("")


@app.post("/runs/{run_id}/stop", response_class=HTMLResponse)
async def stop_run(run_id: str):
    """Request graceful stop of the active run."""
    global _stop_event
    if not _running or run_id != _active_run_id:
        return HTMLResponse('<div id="status" class="text-yellow-400">No active run to stop.</div>')
    if _stop_event is not None:
        _stop_event.set()
        _events.put("\n>>> Stop requested. Finishing in-flight work...")
    return HTMLResponse(
        '<div id="status" class="text-amber-400">Stopping... (finishing in-flight requests)</div>'
    )


@app.post("/runs/{run_id}/resume", response_class=HTMLResponse)
async def resume_run(run_id: str, request: Request):
    """Resume a stopped run from its last checkpoint."""
    global _running, _active_run_id, _active_state, _viewed_run_id, _viewed_state, _stop_event

    if _running:
        return HTMLResponse('<div id="status" class="text-yellow-400">Already running.</div>')

    prev_state = _load_run(run_id)
    if prev_state is None:
        return HTMLResponse('<div id="status" class="text-red-400">Run not found.</div>')
    if prev_state.meta is None:
        return HTMLResponse('<div id="status" class="text-red-400">Run has no metadata.</div>')
    if prev_state.meta.status not in ("stopped", "error"):
        return HTMLResponse('<div id="status" class="text-yellow-400">Only stopped or errored runs can be resumed.</div>')

    form = await request.form()
    max_sweeps = int(form.get("max_sweeps", cfg.DEFAULT_MAX_SWEEPS))
    parallelism = int(form.get("parallelism", cfg.DEFAULT_PARALLELISM))

    domain = prev_state.meta.domain
    student_model = form.get("student_model")
    if student_model and student_model not in cfg.STUDENT_MODELS:
        student_model = None

    # Reuse same run_id so history is continuous.
    _running = True
    _active_run_id = run_id
    _viewed_run_id = run_id
    _viewed_state = None
    _stop_event = threading.Event()
    with _teacher_sessions_lock:
        _teacher_sessions.clear()
    with _run_session_ids_lock:
        # Preserve previous session IDs.
        _run_session_ids.clear()
        _run_session_ids.update(prev_state.session_ids)
    _drain_queue()

    meta = prev_state.meta
    meta.status = RUN_RUNNING
    _active_state = prev_state
    _save_run(_active_state)

    def _resume_in_thread():
        try:
            from evo.parallel_loop import run_loop
            state = run_loop(
                domain=domain,
                num_tasks=prev_state.meta.num_tasks,
                max_sweeps=max_sweeps,
                parallelism=parallelism,
                seed=cfg.DEFAULT_SEED,
                student_model=student_model,
                on_status=lambda msg: _events.put(msg),
                on_iteration=_on_iteration_cb(meta),
                on_fix_attempt=_on_fix_attempt_cb,
                on_teacher_message=_on_teacher_message,
                on_session=_on_student_session,
                on_phase=_make_phase_cb(max_sweeps, has_test=bool(prev_state.test_task_ids)),
                stop_event=_stop_event,
                resume_state=prev_state,
            )
            _finish_loop_thread(meta, state)
        except Exception as e:
            meta.status = RUN_ERROR
            if _active_state:
                _active_state.meta = meta
                _save_run(_active_state)
            _events.put(f"\nERROR: {e}")
        finally:
            _teardown_loop_thread()

    threading.Thread(target=_resume_in_thread, daemon=True).start()

    return HTMLResponse(
        '<div id="status" class="text-green-400">Resumed.</div>'
        '<script>startSSE(false)</script>'
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fmt_duration(secs: float) -> str:
    if not secs:
        return ""
    m, s = divmod(int(secs), 60)
    return f"{m}m {s}s" if m else f"{s}s"


def _build_results() -> list[dict]:
    state = _get_viewed_state()
    if state is None:
        return []
    rows = []
    for r in state.history:
        for fix in r.fixes:
            rows.append({
                "sweep": r.sweep,
                "task": fix.task_id,
                "baseline": "Pass" if fix.baseline_reward >= 1.0 else "Fail",
                "patched": "Pass" if fix.patched_reward >= 1.0 else "Fail",
                "delta": "0→1" if fix.delta > 0 else "1→0" if fix.delta < 0 else ("1→1" if fix.baseline_reward >= 1.0 else "0→0"),
                "retries": fix.retries,
                "status": "FIXED" if fix.fixed else "NOT FIXED",
                "fix_tier": fix.fix_tier,
                "teacher_msgs": fix.teacher_msgs,
                "teacher_tool_calls": fix.teacher_tool_calls,
                "teacher_duration": _fmt_duration(fix.teacher_duration_s),
                "fixed_at_try": fix.retries + 1 if fix.fixed else None,
                "patches": fix.patches,
            })
    return rows


def _build_stats_context(state: Optional[LoopState]) -> dict:
    """Build the shared template context for fix/eval/test stats."""
    fixes = state.flat_fixes() if state else []
    total = len(fixes)
    fixed = sum(1 for f in fixes if f.fixed)
    fixed_prompt = sum(1 for f in fixes if f.fix_tier == FIX_TIER_PROMPT)
    fixed_code = sum(1 for f in fixes if f.fix_tier == FIX_TIER_CODE)

    sweep_total = 0
    sweep_passed = 0
    if state and not fixes:
        for h in state.history:
            sweep_total += len(h.sweep_rewards)
            sweep_passed += sum(1 for r in h.sweep_rewards.values() if r >= 1.0)

    tr = state.test_results if state else None
    return {
        "total": total,
        "fixed": fixed,
        "fixed_prompt": fixed_prompt,
        "fixed_code": fixed_code,
        "not_fixed": total - fixed,
        "rate": int(fixed / total * 100) if total else (
            int(sweep_passed / sweep_total * 100) if sweep_total else 0
        ),
        "sweep_total": sweep_total,
        "sweep_passed": sweep_passed,
        "test_results": tr is not None,
        "test_baseline_rate": int(tr.baseline_pass_rate * 100) if tr else 0,
        "test_evolved_rate": int(tr.evolved_pass_rate * 100) if tr and tr.evolved_rewards else None,
        "test_prompt_only_rate": int(tr.prompt_only_pass_rate * 100) if tr and tr.prompt_only_rewards else None,
    }


def _drain_queue() -> None:
    """Clear the event buffer between runs."""
    _events.clear()


def _try_load_latest_run() -> None:
    global _viewed_run_id, _viewed_state
    if _viewed_run_id is not None:
        return
    runs = _list_runs()
    if not runs:
        path = cfg.PATCHES_DIR / "loop_state.json"
        if path.exists():
            try:
                _viewed_state = LoopState.load(path)
            except Exception:
                pass
        return
    latest = runs[0]
    state = _load_run(latest.run_id)
    if state:
        _viewed_state = state
        _viewed_run_id = latest.run_id


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
