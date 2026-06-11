"""Runs browser screen — pick a past run to open its replay.

A reusable `Screen[str | None]`: selecting a row dismisses with that run's id (the
caller opens the scene); quitting dismisses with None. With no runs it shows the
exact `agentiq run` command (UX-DR11), never a blank table. The non-interactive
`agentiq runs` (story 1.9) remains the scriptable table.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from agentiq.core.run import RunInfo, list_runs

_EMPTY_HINT = 'No runs yet. Start one with:  agentiq run "<goal>" --project <path>'


def _fmt_cost(cost: float | None) -> str:
    return f"${cost:.2f}" if cost is not None else "-"


def _fmt_duration(seconds: float | None) -> str:
    return f"{seconds:.1f}s" if seconds is not None else "-"


class RunsBrowserScreen(Screen[str | None]):
    """Lists runs in a DataTable; dismisses with the selected run id."""

    BINDINGS = [
        Binding("enter", "open", "Open"),
        Binding("escape", "cancel", "Back"),
        Binding("q", "cancel", "Quit"),
    ]

    def __init__(self, runs_root: str | Path | None = None) -> None:
        super().__init__()
        self._runs_root = runs_root
        self._runs: list[RunInfo] = []
        self._run_ids: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        self._runs = list_runs(self._runs_root)
        self._run_ids = [r.run_id for r in self._runs]
        if self._runs:
            yield DataTable(id="runs-table")
        else:
            yield Static(_EMPTY_HINT, id="runs-empty")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "runs"
        if not self._runs:
            return
        table = self.query_one("#runs-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("RUN ID", "STATUS", "COST", "DURATION", "GOAL")
        for run in self._runs:
            table.add_row(
                run.run_id,
                run.status,
                _fmt_cost(run.cost_usd),
                _fmt_duration(run.duration_seconds),
                run.goal,
                key=run.run_id,
            )
        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        run_id = event.row_key.value
        if run_id is not None:
            self.dismiss(run_id)

    def action_open(self) -> None:
        if not self._run_ids:
            return
        table = self.query_one("#runs-table", DataTable)
        row = table.cursor_row
        if 0 <= row < len(self._run_ids):
            self.dismiss(self._run_ids[row])

    def action_cancel(self) -> None:
        self.dismiss(None)
