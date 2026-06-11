"""Tests for the runs browser screen (story 2.9)."""

from __future__ import annotations

from pathlib import Path

from textual.app import App
from textual.widgets import DataTable, Static

from agentiq.core.run import start_run
from agentiq.tui.runs_browser import _EMPTY_HINT, RunsBrowserScreen


class _Host(App[None]):
    def __init__(self, runs_root: Path) -> None:
        super().__init__()
        self._runs_root = runs_root
        self.result: str | None = "UNSET"

    def on_mount(self) -> None:
        self.push_screen(RunsBrowserScreen(self._runs_root), self._got)

    def _got(self, run_id: str | None) -> None:
        self.result = run_id


def _make_runs(tmp_path: Path) -> Path:
    runs_root = tmp_path / "runs"
    for rid, goal in (("A", "first"), ("B", "second")):
        r = start_run(goal, tmp_path, runs_root=runs_root, run_id=rid)
        r.complete()
    return runs_root


async def test_browser_lists_and_selects_newest_first(tmp_path: Path) -> None:
    runs_root = _make_runs(tmp_path)
    app = _Host(runs_root)
    async with app.run_test() as pilot:
        await pilot.pause()  # let the pushed screen mount
        table = app.screen.query_one("#runs-table", DataTable)
        assert table.row_count == 2
        await pilot.press("enter")  # select cursor (row 0 = newest = "B")
    assert app.result == "B"


async def test_browser_empty_shows_hint(tmp_path: Path) -> None:
    app = _Host(tmp_path / "empty")
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.query_one("#runs-empty", Static) is not None
    assert "agentiq run" in _EMPTY_HINT


async def test_browser_cancel_returns_none(tmp_path: Path) -> None:
    runs_root = _make_runs(tmp_path)
    app = _Host(runs_root)
    async with app.run_test() as pilot:
        await pilot.press("q")
    assert app.result is None
