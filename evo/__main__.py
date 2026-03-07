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
    loop_p = sub.add_parser("loop", help="Run the parallel evolution loop")
    loop_p.add_argument("--domain", default=cfg.DEFAULT_DOMAIN)
    loop_p.add_argument("--num-tasks", type=int, default=cfg.DEFAULT_NUM_TASKS)
    loop_p.add_argument("--max-iterations", type=int, default=cfg.DEFAULT_MAX_ITERATIONS)
    loop_p.add_argument("--max-retries", type=int, default=cfg.DEFAULT_MAX_RETRIES)
    loop_p.add_argument("--max-workers", type=int, default=4, help="Max parallel teachers")
    loop_p.add_argument("--seed", type=int, default=cfg.DEFAULT_SEED)
    loop_p.add_argument("--task-ids", nargs="+", help="Run only these task IDs")

    # ── ui ────────────────────────────────────────────────────────────────
    sub.add_parser("ui", help="Launch the Textual dashboard")

    # ── web ───────────────────────────────────────────────────────────────
    web_p = sub.add_parser("web", help="Launch the web dashboard")
    web_p.add_argument("--port", type=int, default=8080)
    web_p.add_argument("--reload", action="store_true", help="Enable auto-reload for dev")

    args = parser.parse_args()

    if args.command == "loop":
        _quiet_deps()
        from evo.parallel_loop import run_loop

        state = run_loop(
            domain=args.domain,
            num_tasks=args.num_tasks,
            max_iterations=args.max_iterations,
            max_retries=args.max_retries,
            max_workers=args.max_workers,
            seed=args.seed,
            task_ids=args.task_ids,
            on_status=lambda msg: console.print(msg),
        )
        total_fixed = sum(r.num_fixed for r in state.history)
        total_failures = sum(r.num_failures for r in state.history)
        console.print(f"\n[bold]Done.[/bold] {total_fixed}/{total_failures} total fixes.")

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
