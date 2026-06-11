"""Tests for live watch mode (story 5.1)."""

from __future__ import annotations

from pathlib import Path

from agentiq.core.orchestrator import DeterministicStrategy
from agentiq.tui.live import LiveWatchApp


async def test_live_watch_folds_events_into_scene(tmp_path: Path) -> None:
    app = LiveWatchApp(
        "ship it",
        tmp_path,
        strategy=DeterministicStrategy(subtasks=("analyze", "implement")),
        runs_root=tmp_path / "runs",
    )
    async with app.run_test() as pilot:
        # Let the orchestration + consume workers run to completion.
        for _ in range(30):
            await pilot.pause()
            if app._live_state.run_status in ("completed", "aborted"):
                break
    state = app._live_state
    assert state.run_status == "completed"
    assert "parent" in state.agents
    assert "a1" in state.agents and "a2" in state.agents
