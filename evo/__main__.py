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
    loop_p.add_argument("--max-sweeps", type=int, default=cfg.DEFAULT_MAX_SWEEPS)
    loop_p.add_argument("--max-retries", type=int, default=cfg.DEFAULT_MAX_RETRIES)
    loop_p.add_argument("--parallelism", type=int, default=cfg.DEFAULT_PARALLELISM, help="Max parallel workers (teachers & task runs)")
    loop_p.add_argument("--seed", type=int, default=cfg.DEFAULT_SEED)
    loop_p.add_argument("--task-ids", nargs="+", help="Run only these task IDs")
    loop_p.add_argument("--split", action=argparse.BooleanOptionalAction, default=True,
                        help="Use canonical train/test split (default: on)")
    loop_p.add_argument("--test-only", type=str, default=None, metavar="STATE_FILE",
                        help="Run test evaluation on an existing LoopState (skip evolution)")

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

        if args.test_only:
            # Re-run test evaluation on an existing state file.
            from pathlib import Path
            from evo.models import LoopState
            from evo.parallel_loop import _run_test_evaluation
            from tau2.run import load_task_splits

            state = LoopState.load(Path(args.test_only))
            splits = load_task_splits(args.domain)
            if not splits:
                console.print("[red]No canonical splits for this domain.[/red]")
                sys.exit(1)
            test_ids = splits["test"]
            console.print(f"Running test evaluation on {len(test_ids)} held-out tasks...")
            state.test_results = _run_test_evaluation(
                domain=args.domain, test_ids=test_ids, seed=args.seed,
                evolved_prompt=state.system_prompt, evolved_schemas=state.tool_schemas,
                evolved_code=state.tool_code, student_model=None,
                parallelism=args.parallelism,
                on_status=lambda msg: console.print(msg),
            )
            state.test_task_ids = test_ids
            state.save(Path(args.test_only))
            console.print("[bold]Done.[/bold] Test results saved.")
        else:
            from evo.parallel_loop import run_loop

            state = run_loop(
                domain=args.domain,
                num_tasks=args.num_tasks,
                max_sweeps=args.max_sweeps,
                max_retries=args.max_retries,
                parallelism=args.parallelism,
                seed=args.seed,
                task_ids=args.task_ids,
                use_split=args.split,
                on_status=lambda msg: console.print(msg),
            )
            console.print(f"\n[bold]Done.[/bold] {state.total_fixed}/{state.total_failures} total fixes.")
            if state.test_results:
                tr = state.test_results
                console.print(f"[bold]Test results:[/bold] baseline={tr.baseline_pass_rate:.0%} "
                              f"evolved={tr.evolved_pass_rate:.0%} prompt-only={tr.prompt_only_pass_rate:.0%}")

    elif args.command == "web":
        cfg.quiet_deps()
        from evo.web.app import start

        start(port=args.port, reload=args.reload)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
