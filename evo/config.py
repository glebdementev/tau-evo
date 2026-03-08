"""Centralised configuration: API keys, model IDs, paths."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
RUNS_DIR = RESULTS_DIR / "runs"
PROMPTS_DIR = ROOT / "prompts"
EVOLVED_DIR = PROMPTS_DIR / "evolved"
PATCHES_DIR = ROOT / "patches"
SESSION_LOGS_DIR = RESULTS_DIR / "session_logs"
TEACHER_LOGS_DIR = SESSION_LOGS_DIR  # back-compat alias


def ensure_dirs() -> None:
    """Create output directories. Call once at startup, not on import."""
    for d in (RESULTS_DIR, RUNS_DIR, EVOLVED_DIR, PATCHES_DIR, SESSION_LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ── API ──────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# ── Models ────────────────────────────────────────────────────────────────
# Bare model IDs (no litellm prefix). Callers add "openrouter/" when needed.
STUDENT_MODELS: dict[str, str] = {
    "qwen/qwen3-30b-a3b": "Qwen3 30B-A3B",
    "qwen/qwen3.5-flash-02-23": "Qwen3.5 Flash",
    "z-ai/glm-4.7-flash-20260119": "GLM 4.7 Flash",
}
STUDENT_MODEL = "qwen/qwen3-30b-a3b"
TEACHER_MODEL = "moonshotai/kimi-k2.5"
USER_SIM_MODEL = "qwen/qwen3-30b-a3b"

# Disable reasoning/thinking tokens via OpenRouter.
NO_THINK_ARGS: dict = {"extra_body": {"reasoning": {"effort": "none"}}, "timeout": 60}

# ── Domains ──────────────────────────────────────────────────────────────
DOMAINS = ["airline", "retail", "telecom"]
DOMAIN_NUM_TASKS: dict[str, int] = {"airline": 50, "retail": 114, "telecom": 114}
DOMAIN_TRAIN_TASKS: dict[str, int] = {"airline": 30, "retail": 74, "telecom": 74}

# ── Defaults ─────────────────────────────────────────────────────────────
DEFAULT_DOMAIN = "airline"
DEFAULT_NUM_TASKS = 5
DEFAULT_MAX_SWEEPS = 3
DEFAULT_MAX_RETRIES = 2
DEFAULT_PARALLELISM = 13
DEFAULT_SEED = 42
DEFAULT_NUM_TRIALS = 3
MAX_ERRORS_PER_TASK = 3
VERIFY_RETRIES = 3
VERIFY_BACKOFF = 2.0
API_RETRIES = 3
API_BACKOFF = 2.0
API_RATE_LIMIT_RETRIES = 8
API_RATE_LIMIT_BACKOFF = 5.0


def rate_limit_delay(exc: Exception, hit_count: int, base_backoff: float = API_RATE_LIMIT_BACKOFF) -> float:
    """Compute retry delay for a 429 error.

    Respects Retry-After header if present, otherwise exponential backoff capped at 120s.
    """
    retry_after = None
    if hasattr(exc, "response") and exc.response is not None:
        headers = getattr(exc.response, "headers", None)
        if headers:
            header = headers.get("retry-after") or headers.get("Retry-After")
            if header:
                try:
                    retry_after = float(header)
                except (ValueError, TypeError):
                    pass
    if retry_after is not None and retry_after > 0:
        return retry_after
    return min(base_backoff * (2 ** (hit_count - 1)), 120.0)


def quiet_deps() -> None:
    """Suppress noisy logs from litellm, loguru, and tau2.

    Also bridges Python logging → loguru so all evo.* messages appear in
    the same loguru stream as tau2 orchestrator output.
    """
    import logging
    logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
    logging.getLogger("LiteLLM Router").setLevel(logging.CRITICAL)
    logging.getLogger("LiteLLM Proxy").setLevel(logging.CRITICAL)
    import litellm
    litellm.suppress_debug_info = True
    from loguru import logger
    logger.disable("tau2")
    logger.enable("tau2.orchestrator")  # step-level logs (INFO) visible

    # Bridge evo.* Python logging → loguru so teacher/merger/loop messages
    # appear in the same terminal stream as tau2 orchestrator output.
    class _LoguruHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            logger.opt(depth=6, exception=record.exc_info).log(
                level, record.getMessage(),
            )

    evo_logger = logging.getLogger("evo")
    if not any(isinstance(h, _LoguruHandler) for h in evo_logger.handlers):
        evo_logger.addHandler(_LoguruHandler())
        evo_logger.setLevel(logging.INFO)
