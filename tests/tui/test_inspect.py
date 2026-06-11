"""Tests for the inspect overlay (story 2.8)."""

from __future__ import annotations

from agentiq.events.models import Event
from agentiq.replay.transport import ReplayController
from agentiq.tui.app import WcsApp
from agentiq.tui.inspect import InspectOverlay, render_inspect


def _evt(seq: int, type: str, payload: dict, agent_id: str | None = None) -> Event:
    return Event.model_validate(
        {
            "seq": seq,
            "ts": "2026-06-09T12:00:00.000000Z",
            "run_id": "R",
            "agent_id": agent_id,
            "type": type,
            "payload": payload,
        }
    )


def _controller() -> ReplayController:
    return ReplayController(
        [
            _evt(0, "run.started", {"goal": "g", "project": "."}),
            _evt(1, "agent.spawned", {"role": "analyze"}, "a1"),
            _evt(2, "vault.read", {"ref": "api-design"}, "a1"),
        ]
    )


def test_render_inspect_shows_event_and_agents() -> None:
    c = _controller()
    c.to_end()  # sit on the vault.read event
    out = render_inspect(c)
    assert "vault.read" in out
    assert "api-design" in out  # payload value
    assert "--- agents ---" in out
    assert "a1" in out
    assert "status=reading" in out


async def test_enter_opens_and_escape_closes_overlay() -> None:
    app = WcsApp(controller=_controller())
    async with app.run_test() as pilot:
        await pilot.press("enter")
        assert isinstance(app.screen, InspectOverlay)
        await pilot.press("escape")
        assert not isinstance(app.screen, InspectOverlay)
