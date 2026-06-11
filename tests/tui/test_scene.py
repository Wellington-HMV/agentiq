"""Tests for the spatial scene rendering (story 2.6)."""

from __future__ import annotations

from agentiq.events.models import Event
from agentiq.replay.reducer import reduce_all
from agentiq.tui.app import WcsApp
from agentiq.tui.scene import SceneWidget, render_scene


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


def _state():
    events = [
        _evt(0, "run.started", {"goal": "g", "project": "."}),
        _evt(1, "agent.spawned", {"role": "parent"}, "parent"),
        _evt(2, "agent.spawned", {"role": "analyze", "parent_id": "parent"}, "a1"),
        _evt(3, "task.delegated", {"task": "t", "to_agent": "a1"}, "parent"),
        _evt(4, "vault.read", {"ref": "api-design"}, "a1"),
    ]
    return reduce_all(events)


def test_render_scene_shows_zones_and_agents() -> None:
    out = render_scene(_state())
    # Fixed zones present (the stable mental map).
    assert "LIBRARY" in out
    assert "DESKS" in out
    assert "SUBAGENTS" in out
    # Parent anchored + a1 present; a1 is in the library (read the vault).
    assert "parent" in out
    library_line = next(line for line in out.splitlines() if line.startswith("LIBRARY"))
    assert "a1(reading)" in library_line
    assert "run: running" in out


def test_render_scene_ascii_only() -> None:
    out = render_scene(_state(), ascii_only=True)
    assert "a1(reading)" in out  # agent labelled with its state
    assert out.isascii()  # creature face stays ASCII in ascii-only mode


async def test_scene_widget_mounts_with_state() -> None:
    app = WcsApp(state=_state())
    async with app.run_test():
        widget = app.query_one(SceneWidget)
        rendered = render_scene(_state())
        assert "a1(reading)" in rendered
        assert widget is not None
