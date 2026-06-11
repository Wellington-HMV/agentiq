"""Tests for the replay transport engine (story 2.3)."""

from __future__ import annotations

from agentiq.events.models import Event
from agentiq.replay.reducer import reduce_all
from agentiq.replay.scene_state import initial_state
from agentiq.replay.transport import ReplayController


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
        _evt(0, "run.started", {"goal": "g", "project": "."}),
        _evt(1, "agent.spawned", {"role": "parent"}, "parent"),
        _evt(2, "agent.spawned", {"role": "a"}, "a1"),
        _evt(3, "vault.read", {"ref": "x"}, "a1"),
        _evt(4, "run.completed", {"status": "completed"}),
    ]


def test_opens_at_start() -> None:
    c = ReplayController(_events())
    assert c.position == 0
    assert c.current_state == reduce_all(_events()[:1])
    assert c.at_start


def test_step_clamps_at_ends() -> None:
    c = ReplayController(_events())
    c.step_backward()
    assert c.position == 0  # clamped
    c.to_end()
    assert c.position == 4
    assert c.at_end
    c.step_forward()
    assert c.position == 4  # clamped


def test_seek_to_seq_matches_prefix_fold() -> None:
    evs = _events()
    c = ReplayController(evs)
    assert c.seek_to_seq(3) is True
    assert c.position == 3
    assert c.current_state == reduce_all(evs[:4])  # instant precomputed seek
    assert c.seek_to_seq(99) is False


def test_play_and_speed_clamp() -> None:
    c = ReplayController(_events())
    assert c.playing is False
    c.toggle_play()
    assert c.playing is True
    for _ in range(10):
        c.faster()
    assert c.speed == 8.0
    for _ in range(10):
        c.slower()
    assert c.speed == 0.25


def test_empty_events() -> None:
    c = ReplayController([])
    assert c.position == -1
    assert c.current_state == initial_state()
    assert c.current_event is None
    c.step_forward()
    assert c.position == -1  # no-op
