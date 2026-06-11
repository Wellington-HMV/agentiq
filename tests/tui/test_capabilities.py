"""Tests for terminal capability detection (story 2.10)."""

from __future__ import annotations

from agentiq.events.models import Event
from agentiq.replay.transport import ReplayController
from agentiq.tui.app import WcsApp
from agentiq.tui.capabilities import (
    Capabilities,
    choose_representation,
    detect,
)
from agentiq.tui.scene import SceneWidget


def test_representation_breakpoints() -> None:
    assert choose_representation(120, 40) == "full"
    assert choose_representation(200, 60) == "full"
    assert choose_representation(80, 24) == "compact"
    assert choose_representation(119, 39) == "compact"
    assert choose_representation(79, 23) == "minimal"
    assert choose_representation(40, 10) == "minimal"


def test_detect_ascii_and_motion() -> None:
    caps = detect(100, 30, unicode_ok=True)
    assert isinstance(caps, Capabilities)
    assert caps.ascii_only is False
    assert caps.representation == "compact"

    assert detect(100, 30, unicode_ok=False).ascii_only is True
    assert detect(100, 30, ascii_only=True).ascii_only is True
    assert detect(100, 30, reduced_motion=True).reduced_motion is True


def _controller() -> ReplayController:
    def e(seq: int, type: str, payload: dict, agent_id: str | None = None) -> Event:
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

    return ReplayController(
        [
            e(0, "run.started", {"goal": "g", "project": "."}),
            e(1, "agent.spawned", {"role": "a"}, "a1"),
            e(2, "run.completed", {"status": "completed"}),
        ]
    )


async def test_app_passes_ascii_to_scene() -> None:
    app = WcsApp(controller=_controller(), ascii_only=True)
    async with app.run_test():
        scene = app.query_one(SceneWidget)
        assert scene._ascii_only is True


async def test_reduced_motion_steps_instead_of_playing() -> None:
    c = _controller()
    app = WcsApp(controller=c, reduced_motion=True)
    async with app.run_test() as pilot:
        assert c.position == 0
        await pilot.press("space")
        assert c.position == 1  # advanced one step
        assert c.playing is False  # no timer-driven playback
