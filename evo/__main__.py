"""CLI entry point: python -m evo"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

import evo.config as cfg

cfg.ensure_dirs()
console = Console()


def main():
    parser = argparse.ArgumentParser(description="tau-evo: self-evolving LLM agents")
    sub = parser.add_subparsers(dest="command")

    # ── loop ──────────────────────────────────────────────────────────────
    loop_p = sub.add_parser("loop", help="Run the parallel evolution loop")
    loop_p.add_argument("--domain", default=cfg.DEFAULT_DOMAIN)
    _domain_hints = ", ".join(f"{d}={n}" for d, n in cfg.DOMAIN_NUM_TASKS.items())
    loop_p.add_argument("--num-tasks", type=int, default=cfg.DEFAULT_NUM_TASKS,
                        help=f"Number of tasks to evaluate ({_domain_hints})")
    loop_p.add_argument("--max-iterations", type=int, default=cfg.DEFAULT_MAX_ITERATIONS)
    loop_p.add_argument("--max-retries", type=int, default=cfg.DEFAULT_MAX_RETRIES)
    loop_p.add_argument("--parallelism", type=int, default=cfg.DEFAULT_PARALLELISM, help="Max parallel workers (teachers & tau2 evals)")
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
        max_for_domain = cfg.DOMAIN_NUM_TASKS.get(args.domain, args.num_tasks)
        if args.num_tasks > max_for_domain:
            console.print(f"[yellow]Warning:[/yellow] {args.domain} has only {max_for_domain} tasks, clamping num_tasks.")
            args.num_tasks = max_for_domain

        cfg.quiet_deps()
        from evo.parallel_loop import run_loop

        state = run_loop(
            domain=args.domain,
            num_tasks=args.num_tasks,
            max_iterations=args.max_iterations,
            max_retries=args.max_retries,
            parallelism=args.parallelism,
            seed=args.seed,
            task_ids=args.task_ids,
            on_status=lambda msg: console.print(msg),
        )
        console.print(f"\n[bold]Done.[/bold] {state.total_fixed}/{state.total_failures} total fixes.")

    elif args.command == "ui":
        from evo.ui.app import EvolutionApp

        app = EvolutionApp()
        app.run()

    elif args.command == "web":
        cfg.quiet_deps()
        from evo.web.app import start

        start(port=args.port, reload=args.reload)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
