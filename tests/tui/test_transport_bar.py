"""Tests for the transport bar widget + interactive bindings (story 2.7)."""

from __future__ import annotations

from agentiq.events.models import Event
from agentiq.replay.transport import ReplayController
from agentiq.tui.app import WcsApp
from agentiq.tui.transport_bar import render_transport


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


def _events() -> list[Event]:
    return [
        _evt(0, "run.started", {"goal": "g", "project": "."}),  # 0
        _evt(1, "agent.spawned", {"role": "a"}, "a1"),  # 1
        _evt(2, "decision.pending", {"prompt": "x"}, "a1"),  # 2 ◆
        _evt(3, "agent.failed", {"cause": "boom"}, "a1"),  # 3 ✕
        _evt(4, "run.completed", {"status": "completed"}),  # 4
    ]


def test_render_transport_counter_and_markers() -> None:
    c = ReplayController(_events())
    out = render_transport(c, ascii_only=True)
    assert "1/5" in out  # 1-based position / total
    # playhead at index 0; decision at 2 -> D; failure at 3 -> X
    track = out[out.index("[") + 1 : out.index("]")]
    assert track[0] == ">"  # playhead
    assert track[2] == "D"
    assert track[3] == "X"


async def test_keys_drive_controller_and_scene() -> None:
    c = ReplayController(_events())
    app = WcsApp(controller=c)
    async with app.run_test() as pilot:
        assert c.position == 0
        await pilot.press("right")
        assert c.position == 1
        await pilot.press("f")
        assert c.current_event is not None
        assert c.current_event.type == "agent.failed"
        await pilot.press("home")
        assert c.position == 0
        await pilot.press("space")
        assert c.playing is True


async def test_empty_controller_renders_safely() -> None:
    c = ReplayController([])
    assert render_transport(c) == "[ ] 0/0"
