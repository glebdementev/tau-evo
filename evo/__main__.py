"""CLI entry point: python -m evo"""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console

import evo.config as cfg

cfg.ensure_dirs()
console = Console()


def _quiet_deps():
    """Suppress noisy logs from litellm and tau2."""
    logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
    logging.getLogger("LiteLLM Router").setLevel(logging.CRITICAL)
    logging.getLogger("LiteLLM Proxy").setLevel(logging.CRITICAL)
    import litellm
    litellm.suppress_debug_info = True
    # Suppress tau2's loguru error-level noise (cost lookup failures, git hash, etc.)
    from loguru import logger
    logger.disable("tau2")


def main():
    parser = argparse.ArgumentParser(description="tau-evo: self-evolving LLM agents")
    sub = parser.add_subparsers(dest="command")

    # ── loop ──────────────────────────────────────────────────────────────
    loop_p = sub.add_parser("loop", help="Run the full evolution loop")
    loop_p.add_argument("--domain", default=cfg.DEFAULT_DOMAIN)
    loop_p.add_argument("--num-tasks", type=int, default=cfg.DEFAULT_NUM_TASKS)
    loop_p.add_argument("--max-iterations", type=int, default=cfg.DEFAULT_MAX_ITERATIONS)
    loop_p.add_argument("--seed", type=int, default=cfg.DEFAULT_SEED)
    loop_p.add_argument("--task-ids", nargs="+", help="Run only these task IDs (skip baseline)")

    # ── ui ────────────────────────────────────────────────────────────────
    sub.add_parser("ui", help="Launch the Textual dashboard")

    # ── web ───────────────────────────────────────────────────────────────
    web_p = sub.add_parser("web", help="Launch the NiceGUI web dashboard")
    web_p.add_argument("--port", type=int, default=8080)
    web_p.add_argument("--reload", action="store_true", help="Enable auto-reload for dev")

    args = parser.parse_args()

    if args.command == "loop":
        _quiet_deps()
        from evo.loop import run_loop

        state = run_loop(
            domain=args.domain,
            num_tasks=args.num_tasks,
            max_iterations=args.max_iterations,
            seed=args.seed,
            task_ids=args.task_ids,
            on_status=lambda msg: console.print(msg),
        )
        fixed = sum(1 for r in state.history if r.fixed)
        console.print(f"\n[bold]Done.[/bold] {fixed}/{len(state.history)} failures fixed.")

    elif args.command == "ui":
        from evo.ui.app import EvolutionApp

        app = EvolutionApp()
        app.run()

    elif args.command == "web":
        _quiet_deps()
        from evo.web.app import start

        start(port=args.port, reload=args.reload)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
