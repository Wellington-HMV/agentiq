"""Tests for creature personalities (story 6.4)."""

from __future__ import annotations

from agentiq.replay.scene_state import AgentState, Status
from agentiq.tui.app import WcsApp
from agentiq.tui.creatures import creature, status_glyph
from agentiq.tui.scene import SceneWidget


def _agent(status: str, role: str | None = "analyze") -> AgentState:
    return AgentState("a1", role=role, status=status)


def test_status_glyph_always_present_every_frame() -> None:
    # Charm never hides state: the status glyph leads the face at any frame.
    g = status_glyph(Status.WORKING)
    assert creature(_agent(Status.WORKING), 0).startswith(g)
    assert creature(_agent(Status.WORKING), 1).startswith(g)


def test_active_status_bobs_across_frames() -> None:
    a = _agent(Status.WORKING)
    assert creature(a, 0) != creature(a, 1)  # motion = busy
    assert creature(a, 0) == creature(a, 2)  # 2-frame cycle


def test_calm_status_does_not_animate() -> None:
    a = _agent(Status.IDLE)
    assert creature(a, 0) == creature(a, 1)  # still when nothing happening


def test_failed_is_stable_and_marked() -> None:
    a = _agent(Status.FAILED)
    assert status_glyph(Status.FAILED) in creature(a, 0)
    assert creature(a, 0) == creature(a, 1)  # terminal: no motion


def test_role_gives_personality_tag() -> None:
    assert creature(_agent(Status.WORKING, role="analyze"), 0).endswith("a")
    assert creature(_agent(Status.WORKING, role="verify"), 0).endswith("v")
    assert creature(_agent(Status.WORKING, role=None), 0).endswith("?")


def test_ascii_only_stays_ascii() -> None:
    for status in (Status.WORKING, Status.IDLE, Status.FAILED, Status.READING):
        for frame in (0, 1):
            assert creature(_agent(status), frame, ascii_only=True).isascii()


async def test_scene_widget_tick_advances_frame() -> None:
    app = WcsApp(state=None, reduced_motion=True)  # no auto interval; drive manually
    async with app.run_test():
        widget = app.query_one(SceneWidget)
        assert widget._frame == 0
        widget.tick_animation()
        assert widget._frame == 1
