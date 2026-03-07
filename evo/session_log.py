"""Unified session logging for teacher and student conversations.

All session data flows through typed Pydantic schemas — no loose dicts.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from pydantic import BaseModel, ConfigDict, Field

from evo.config import SESSION_LOGS_DIR

log = logging.getLogger(__name__)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# -- Schemas -------------------------------------------------------------------

class ToolCallFunction(BaseModel):
    name: str = ""
    arguments: str = ""


class ToolCallInfo(BaseModel):
    id: str = ""
    type: str = "function"
    function: ToolCallFunction


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ResponseMeta(BaseModel):
    response_model: Optional[str] = None
    usage: Optional[UsageInfo] = None


class SessionMessage(BaseModel):
    """A single message in a session log (OpenAI chat format + metadata)."""
    model_config = ConfigDict(populate_by_name=True)

    ts: str = ""
    role: str = ""
    content: str = ""
    tool_calls: Optional[list[ToolCallInfo]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    meta: Optional[ResponseMeta] = Field(None, alias="_meta")
    error: Optional[str] = None
    context: Optional[str] = None


class ErrorRecord(BaseModel):
    ts: str = ""
    error: str = ""
    context: str = ""


class SessionData(BaseModel):
    """Full session log — the unit of persistence."""
    session_id: str
    session_type: str = "teacher"
    task_id: str = ""
    model: str = ""
    started_at: str = ""
    status: str = "active"
    context: str = ""
    reward: Optional[float] = None
    messages: list[SessionMessage] = []
    errors: list[ErrorRecord] = []


class SessionSummary(BaseModel):
    """Lightweight summary for list endpoints (no messages)."""
    session_id: str
    session_type: str = "teacher"
    task_id: str = ""
    model: str = ""
    started_at: str = ""
    status: str = "unknown"
    message_count: int = 0
    error_count: int = 0
    reward: Optional[float] = None
    context: str = ""

    @classmethod
    def from_data(cls, data: SessionData) -> SessionSummary:
        return cls(
            session_id=data.session_id,
            session_type=data.session_type,
            task_id=data.task_id,
            model=data.model,
            started_at=data.started_at,
            status=data.status,
            message_count=len(data.messages),
            error_count=len(data.errors),
            reward=data.reward,
            context=data.context,
        )


# -- Persistence ---------------------------------------------------------------

def save_session(data: SessionData) -> Path:
    """Save/update a session log to disk."""
    path = SESSION_LOGS_DIR / f"{data.session_id}.json"
    try:
        path.write_text(data.model_dump_json(indent=2, exclude_none=True))
    except Exception as e:
        log.warning("Failed to save session %s: %s", data.session_id, e)
    return path


def load_session(session_id: str) -> Optional[SessionData]:
    """Load full session data from disk."""
    path = safe_path(session_id)
    if path is None or not path.exists():
        return None
    try:
        return SessionData.model_validate_json(path.read_text())
    except Exception:
        return None


def list_sessions(session_type: Optional[str] = None) -> list[SessionSummary]:
    """List session summaries from disk, newest first."""
    sessions: list[SessionSummary] = []
    for p in SESSION_LOGS_DIR.glob("*.json"):
        try:
            raw = json.loads(p.read_text())
            if session_type and raw.get("session_type") != session_type:
                continue
            sessions.append(SessionSummary(
                session_id=raw["session_id"],
                session_type=raw.get("session_type", "teacher"),
                task_id=raw.get("task_id", ""),
                model=raw.get("model", ""),
                started_at=raw.get("started_at", ""),
                status=raw.get("status", "unknown"),
                message_count=len(raw.get("messages", [])),
                error_count=len(raw.get("errors", [])),
                reward=raw.get("reward"),
                context=raw.get("context", ""),
            ))
        except Exception:
            continue
    sessions.sort(key=lambda s: s.started_at, reverse=True)
    return sessions


def safe_path(session_id: str) -> Optional[Path]:
    """Return session file path if session_id is safe, else None."""
    path = (SESSION_LOGS_DIR / f"{session_id}.json").resolve()
    if path.parent != SESSION_LOGS_DIR.resolve():
        return None
    return path


# -- Tau2 message conversion ---------------------------------------------------

def format_tau2_messages(messages: list) -> list[SessionMessage]:
    """Convert tau2 message objects to SessionMessage list."""
    ts = now_iso()
    result: list[SessionMessage] = []
    for msg in messages:
        role = msg.role if hasattr(msg, "role") else "unknown"
        content = getattr(msg, "content", None) or ""

        tool_calls = None
        raw_tc = getattr(msg, "tool_calls", None)
        if raw_tc:
            tool_calls = [
                ToolCallInfo(
                    id=getattr(tc, "id", ""),
                    function=ToolCallFunction(
                        name=tc.name,
                        arguments=(
                            json.dumps(tc.arguments)
                            if isinstance(tc.arguments, dict)
                            else tc.arguments
                        ),
                    ),
                )
                for tc in raw_tc
            ]

        result.append(SessionMessage(
            ts=ts,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=getattr(msg, "tool_call_id", None) if role == "tool" else None,
            name=getattr(msg, "name", None) if role == "tool" else None,
        ))
    return result


# -- Student session helpers ---------------------------------------------------

def save_student_sessions(
    results,
    context: str = "",
    model: str = "",
    on_session: Optional[Callable] = None,
) -> list[str]:
    """Save each simulation in a tau2 Results as a student SessionData.

    Returns the list of session IDs created.
    """
    session_ids: list[str] = []
    ts = now_iso()
    for sim in results.simulations:
        task_id = sim.task_id
        reward = sim.reward_info.reward if sim.reward_info else None
        sid = f"student_{task_id}_{uuid.uuid4().hex[:6]}"
        data = SessionData(
            session_id=sid,
            session_type="student",
            task_id=task_id,
            model=model,
            started_at=ts,
            status="done",
            context=context,
            reward=reward,
            messages=format_tau2_messages(sim.messages),
        )
        save_session(data)
        session_ids.append(sid)
        if on_session:
            try:
                on_session(sid, data)
            except Exception:
                pass
    return session_ids
