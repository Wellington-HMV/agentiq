"""Tests for marker predicates and jump navigation (story 2.4)."""

from __future__ import annotations

from agentiq.events.models import Event
from agentiq.replay.markers import is_decision, is_failure
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


def test_predicates() -> None:
    assert is_decision("decision.pending")
    assert is_decision("decision.resolved")
    assert not is_decision("agent.spawned")
    assert is_failure("agent.failed")
    assert is_failure("run.aborted")
    assert not is_failure("run.completed")


def _events() -> list[Event]:
    return [
        _evt(0, "run.started", {"goal": "g", "project": "."}),  # 0
        _evt(1, "agent.spawned", {"role": "a"}, "a1"),  # 1
        _evt(2, "decision.pending", {"prompt": "x"}, "a1"),  # 2 decision
        _evt(3, "agent.failed", {"cause": "boom", "last_good_seq": 1}, "a1"),  # 3 fail
        _evt(
            4, "decision.resolved", {"choice": "y", "resolved_by": "human"}, "a1"
        ),  # 4
        _evt(5, "run.completed", {"status": "completed"}),  # 5
    ]


def test_next_and_prev_decision() -> None:
    c = ReplayController(_events())  # pos 0
    assert c.next_decision() is True
    assert c.position == 2
    assert c.next_decision() is True
    assert c.position == 4
    assert c.next_decision() is False  # none after
    assert c.prev_decision() is True
    assert c.position == 2


def test_next_failure_exposes_cause_and_last_good() -> None:
    c = ReplayController(_events())
    assert c.next_failure() is True
    assert c.position == 3
    assert c.current_event is not None
    assert c.current_event.payload["cause"] == "boom"
    assert c.last_good_index == 2  # state just before the failure
    assert c.next_failure() is False


def test_jump_returns_false_when_no_markers() -> None:
    c = ReplayController(
        [
            _evt(0, "run.started", {"goal": "g", "project": "."}),
            _evt(1, "run.completed", {"status": "completed"}),
        ]
    )
    assert c.next_decision() is False
    assert c.next_failure() is False
