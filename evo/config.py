"""Centralised configuration: API keys, model IDs, paths."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
PROMPTS_DIR = ROOT / "prompts"
EVOLVED_DIR = PROMPTS_DIR / "evolved"
PATCHES_DIR = ROOT / "patches"


def ensure_dirs() -> None:
    """Create output directories. Call once at startup, not on import."""
    for d in (RESULTS_DIR, EVOLVED_DIR, PATCHES_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ── API ──────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# ── Models ────────────────────────────────────────────────────────────────
# Bare model IDs (no litellm prefix). Callers add "openrouter/" when needed.
STUDENT_MODEL = "qwen/qwen3.5-35b-a3b"
TEACHER_MODEL = "moonshotai/kimi-k2.5"
USER_SIM_MODEL = "qwen/qwen3.5-35b-a3b"

# Disable reasoning/thinking tokens for Qwen3.5 via OpenRouter.
NO_THINK_ARGS: dict = {"extra_body": {"reasoning": {"effort": "none"}}}

# ── Defaults ─────────────────────────────────────────────────────────────
DEFAULT_DOMAIN = "airline"
DEFAULT_NUM_TASKS = 5
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_MAX_RETRIES = 2
DEFAULT_SEED = 42
