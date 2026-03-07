"""CLI entry point: python -m tau_evo"""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console

import tau_evo.config as cfg

cfg.ensure_dirs()
console = Console()


def _quiet_litellm():
    """Suppress litellm's noisy provider-list spam."""
    logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
    logging.getLogger("LiteLLM Router").setLevel(logging.CRITICAL)
    logging.getLogger("LiteLLM Proxy").setLevel(logging.CRITICAL)
    import litellm
    litellm.suppress_debug_info = True


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

    args = parser.parse_args()
    _quiet_litellm()

    if args.command == "loop":
        from tau_evo.loop import run_loop

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
        from tau_evo.ui.app import EvolutionApp

        app = EvolutionApp()
        app.run()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
