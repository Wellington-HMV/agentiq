"""Autonomy policy wired into the live watch path (story 5.4 / FR25)."""

from __future__ import annotations

from pathlib import Path

from agentiq.agent.adapter import AgentAdapter
from agentiq.config.settings import AutonomySection
from agentiq.core.decision import DecisionRequest, Resolver, request_decision
from agentiq.tui.decision_note import DecisionNote
from agentiq.tui.live import LiveWatchApp

_REQ = DecisionRequest(
    "parent", "deploy?", options=["yes", "no"], default="yes", kind="deploy"
)


class _DecideStrategy:
    async def run(
        self,
        goal: str,
        project: Path,
        adapter: AgentAdapter,
        vault: object | None = None,
        resolver: Resolver | None = None,
    ) -> str:
        assert resolver is not None
        await request_decision(adapter, _REQ, resolver)
        return "completed"


async def test_live_ask_surfaces_note_and_resumes(tmp_path: Path) -> None:
    app = LiveWatchApp(
        "g",
        tmp_path,
        strategy=_DecideStrategy(),
        runs_root=tmp_path / "runs",
        autonomy=AutonomySection(default="ask"),
    )
    async with app.run_test() as pilot:
        for _ in range(30):
            await pilot.pause()
            if isinstance(app.screen, DecisionNote):
                break
        assert isinstance(app.screen, DecisionNote)  # paused, awaiting human
        await pilot.press("1")  # pick "yes" -> world resumes
        for _ in range(30):
            await pilot.pause()
            if app._live_state.run_status in ("completed", "aborted"):
                break
    assert app._live_state.run_status == "completed"


async def test_live_allow_auto_resolves_without_note(tmp_path: Path) -> None:
    app = LiveWatchApp(
        "g",
        tmp_path,
        strategy=_DecideStrategy(),
        runs_root=tmp_path / "runs",
        autonomy=AutonomySection(default="allow"),
    )
    async with app.run_test() as pilot:
        for _ in range(30):
            await pilot.pause()
            if app._live_state.run_status in ("completed", "aborted"):
                break
        # Auto-resolved by policy: never had to surface a note.
        assert not isinstance(app.screen, DecisionNote)
    assert app._live_state.run_status == "completed"
