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
NO_THINK_ARGS: dict = {"extra_body": {"reasoning": {"effort": "none"}}}

# ── Domains ──────────────────────────────────────────────────────────────
DOMAINS = ["airline", "retail", "telecom"]
DOMAIN_NUM_TASKS: dict[str, int] = {"airline": 50, "retail": 114, "telecom": 114}

# ── Defaults ─────────────────────────────────────────────────────────────
DEFAULT_DOMAIN = "airline"
DEFAULT_NUM_TASKS = 5
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_MAX_RETRIES = 2
DEFAULT_PARALLELISM = 4
DEFAULT_SEED = 42


def quiet_deps() -> None:
    """Suppress noisy logs from litellm, loguru, and tau2."""
    import logging
    logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
    logging.getLogger("LiteLLM Router").setLevel(logging.CRITICAL)
    logging.getLogger("LiteLLM Proxy").setLevel(logging.CRITICAL)
    import litellm
    litellm.suppress_debug_info = True
    from loguru import logger
    logger.disable("tau2")
    logger.enable("tau2.orchestrator")  # keep message-level logs visible
