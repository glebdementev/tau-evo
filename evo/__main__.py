"""CLI entry point: python -m evo"""

from __future__ import annotations

import argparse
import sys

import evo.config as cfg

cfg.ensure_dirs()


def main():
    parser = argparse.ArgumentParser(description="tau-evo: self-evolving LLM agents")
    sub = parser.add_subparsers(dest="command")

    # ── web ───────────────────────────────────────────────────────────────
    web_p = sub.add_parser("web", help="Launch the web dashboard")
    web_p.add_argument("--port", type=int, default=8080)
    web_p.add_argument("--reload", action="store_true", help="Enable auto-reload for dev")

    args = parser.parse_args()

    if args.command == "web":
        cfg.quiet_deps()
        from evo.web.app import start

        start(port=args.port, reload=args.reload)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
