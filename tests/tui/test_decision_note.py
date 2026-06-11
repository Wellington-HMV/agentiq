"""Tests for on-screen decision notes (story 5.2)."""

from __future__ import annotations

from pathlib import Path

from textual.app import App

from agentiq.agent.adapter import AgentAdapter
from agentiq.core.decision import DecisionRequest, request_decision
from agentiq.events.bus import EventBus
from agentiq.events.reader import read_events
from agentiq.events.writer import JsonlEventWriter
from agentiq.tui.decision_note import DecisionNote, TuiDecisionResolver

_REQ = DecisionRequest(
    agent_id="parent",
    prompt="Deploy to prod?",
    options=["yes", "no"],
    default="no",
    kind="deploy",
)


class _NoteHost(App[object]):
    """Pushes a DecisionNote on mount and records its dismiss result."""

    def __init__(self, request: DecisionRequest) -> None:
        super().__init__()
        self._request = request
        self.result: str | None = None

    def on_mount(self) -> None:
        self.run_worker(self._go())

    async def _go(self) -> None:
        self.result = await self.push_screen_wait(DecisionNote(self._request))


async def test_note_renders_prompt_options_and_default() -> None:
    host = _NoteHost(_REQ)
    async with host.run_test() as pilot:
        await pilot.pause()
        note = host.screen
        assert isinstance(note, DecisionNote)
        text = note.text
        assert "Deploy to prod?" in text
        assert "1. yes" in text
        assert "2. no" in text
        assert "(default)" in text


async def test_digit_picks_the_option() -> None:
    host = _NoteHost(_REQ)
    async with host.run_test() as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        assert host.result == "yes"
        assert not isinstance(host.screen, DecisionNote)


async def test_enter_picks_the_default() -> None:
    host = _NoteHost(_REQ)
    async with host.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert host.result == "no"
        assert not isinstance(host.screen, DecisionNote)


async def test_invalid_digit_keeps_note_open() -> None:
    host = _NoteHost(_REQ)
    async with host.run_test() as pilot:
        await pilot.pause()
        await pilot.press("9")  # out of range — no resolution
        await pilot.pause()
        assert host.result is None
        assert isinstance(host.screen, DecisionNote)


class _ResolverHost(App[object]):
    """Runs `request_decision` through the TUI resolver in a worker."""

    def __init__(self, request: DecisionRequest, adapter: AgentAdapter) -> None:
        super().__init__()
        self._request = request
        self._adapter = adapter
        self.choice: str | None = None

    def on_mount(self) -> None:
        self.run_worker(self._go())

    async def _go(self) -> None:
        self.choice = await request_decision(
            self._adapter, self._request, TuiDecisionResolver(self)
        )


async def test_resolver_settles_request_decision_end_to_end(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    writer = JsonlEventWriter(log)
    adapter = AgentAdapter("R", writer, EventBus(), secrets=set())
    host = _ResolverHost(_REQ, adapter)
    async with host.run_test() as pilot:
        await pilot.pause()
        # decision.pending emitted; note up; the worker blocks (scene paused).
        assert isinstance(host.screen, DecisionNote)
        assert host.choice is None
        await pilot.press("1")  # pick "yes" -> world resumes
        await pilot.pause()
    writer.close()

    assert host.choice == "yes"
    events = list(read_events(log))
    types = [e.type for e in events]
    assert "decision.pending" in types
    resolved = [e for e in events if e.type == "decision.resolved"]
    assert len(resolved) == 1
    assert resolved[0].payload["choice"] == "yes"
    assert resolved[0].payload["resolved_by"] == "human"
