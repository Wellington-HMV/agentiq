"""Tests for the scene reducer (story 2.1)."""

from __future__ import annotations

from agentiq.events.models import Event
from agentiq.replay.reducer import reduce, reduce_all
from agentiq.replay.scene_state import Status, Zone, initial_state


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


def _run_events() -> list[Event]:
    return [
        _evt(0, "run.started", {"goal": "ship", "project": "."}),
        _evt(1, "agent.spawned", {"role": "parent"}, agent_id="parent"),
        _evt(2, "agent.spawned", {"role": "analyze", "parent_id": "parent"}, "a1"),
        _evt(3, "task.delegated", {"task": "t", "to_agent": "a1"}, "parent"),
        _evt(4, "vault.read", {"ref": "api-design"}, "a1"),
        _evt(5, "run.completed", {"status": "completed"}),
    ]


def test_fold_full_run() -> None:
    state = reduce_all(_run_events())
    assert state.current_seq == 5
    assert state.run_status == "completed"
    assert set(state.agents) == {"parent", "a1"}
    assert state.agents["a1"].zone == Zone.LIBRARY
    assert state.agents["a1"].status == Status.READING
    assert ("parent", "a1") in state.paths


def test_determinism() -> None:
    assert reduce_all(_run_events()) == reduce_all(_run_events())


def test_reduce_is_pure() -> None:
    s0 = initial_state()
    spawn = _evt(0, "agent.spawned", {"role": "parent"}, agent_id="parent")
    s1 = reduce(s0, spawn)
    # Input untouched.
    assert s0.agents == {}
    assert s0.current_seq == -1
    # Output advanced.
    assert "parent" in s1.agents
    assert s1.current_seq == 0


def test_unhandled_event_advances_without_error() -> None:
    s0 = reduce_all(_run_events()[:3])  # up to a delegation
    before_agents = dict(s0.agents)
    s1 = reduce(s0, _evt(3, "budget.exceeded", {"spent_usd": 9, "ceiling_usd": 5}))
    assert s1.current_seq == 3
    assert s1.agents.keys() == before_agents.keys()  # unchanged set
    assert s1.caption == "budget.exceeded"
