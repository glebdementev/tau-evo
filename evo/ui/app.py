"""Minimal Textual dashboard for monitoring the evolution loop."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, DataTable, Log

from evo.config import DEFAULT_DOMAIN, DEFAULT_NUM_TASKS, DEFAULT_MAX_ITERATIONS, DEFAULT_SEED


class StatusPanel(Static):
    DEFAULT_CSS = """
    StatusPanel {
        height: 3;
        padding: 0 1;
        background: $surface;
        border: solid $primary;
    }
    """

    def on_mount(self) -> None:
        self.update("[bold]Status:[/bold] Ready. Press [green]Start[/green] to begin.")


class EvolutionApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    #main {
        height: 1fr;
    }
    #results-table {
        width: 1fr;
        height: 1fr;
    }
    #log-panel {
        width: 1fr;
        height: 1fr;
        border: solid $accent;
    }
    #controls {
        height: auto;
        padding: 1;
        layout: horizontal;
    }
    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "start_loop", "Start"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield StatusPanel(id="status")
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield DataTable(id="results-table")
            with Vertical(id="right"):
                yield Log(id="log-panel", highlight=True)
        with Horizontal(id="controls"):
            yield Button("Start Loop", id="start-btn", variant="success")
            yield Button("Quit", id="quit-btn", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns("Iter", "Task ID", "Before", "After", "Retries", "Status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            self.action_start_loop()
        elif event.button.id == "quit-btn":
            self.exit()

    def action_start_loop(self) -> None:
        btn = self.query_one("#start-btn", Button)
        btn.disabled = True
        self.run_worker(self._run_loop, thread=True)

    def _update_ui(self, msg: str) -> None:
        """Update both the log and status panel (runs on main thread)."""
        self.query_one("#log-panel", Log).write_line(msg)
        self.query_one("#status", StatusPanel).update(f"[bold]Status:[/bold] {msg.strip().split(chr(10))[-1]}")

    def _enable_start_btn(self) -> None:
        self.query_one("#start-btn", Button).disabled = False

    def _run_loop(self) -> None:
        """Worker thread that runs the evolution loop."""
        from evo.parallel_loop import run_loop

        state = run_loop(
            domain=DEFAULT_DOMAIN,
            num_tasks=DEFAULT_NUM_TASKS,
            max_iterations=DEFAULT_MAX_ITERATIONS,
            seed=DEFAULT_SEED,
            on_status=lambda msg: self.call_from_thread(self._update_ui, msg),
        )

        table = self.query_one("#results-table", DataTable)
        for r in state.history:
            for fix in r.fixes:
                status = "[green]FIXED[/green]" if fix.fixed else "[red]FAILED[/red]"
                self.call_from_thread(
                    table.add_row,
                    str(r.iteration),
                    fix.task_id,
                    f"{fix.baseline_reward:.2f}",
                    f"{fix.patched_reward:.2f}",
                    str(fix.retries),
                    status,
                )

        total_fixed = sum(r.num_fixed for r in state.history)
        total_failures = sum(r.num_failures for r in state.history)
        self.call_from_thread(
            self._update_ui,
            f"Done. {total_fixed}/{total_failures} total fixes.",
        )
        self.call_from_thread(self._enable_start_btn)
