"""Tests for run comparison (story 6.3 / FR30)."""

from __future__ import annotations

from agentiq.events.models import Event
from agentiq.replay.compare import (
    DecisionRecord,
    RunComparison,
    facts,
    render_comparison,
)


def _evt(
    seq: int, type: str, payload: dict, run_id: str, agent_id: str | None = None
) -> Event:
    return Event.model_validate(
        {
            "seq": seq,
            "ts": "2026-06-10T00:00:00.000000Z",
            "run_id": run_id,
            "agent_id": agent_id,
            "type": type,
            "payload": payload,
        }
    )


def _events(
    run_id: str,
    *,
    status: str = "completed",
    usage: float = 0.0,
    decisions: tuple[tuple[str, str], ...] = (),
) -> list[Event]:
    evs = [_evt(0, "run.started", {"goal": "g", "project": "."}, run_id)]
    seq = 1
    for choice, by in decisions:
        evs.append(
            _evt(
                seq,
                "decision.pending",
                {"prompt": "ship?", "options": ["yes", "no"], "default": None},
                run_id,
                "a1",
            )
        )
        seq += 1
        evs.append(
            _evt(
                seq,
                "decision.resolved",
                {"choice": choice, "resolved_by": by},
                run_id,
                "a1",
            )
        )
        seq += 1
    if usage:
        evs.append(_evt(seq, "agent.usage", {"cost_usd": usage}, run_id, "a1"))
        seq += 1
    evs.append(_evt(seq, "agent.spawned", {"role": "x"}, run_id, "a1"))
    seq += 1
    if status == "aborted":
        evs.append(_evt(seq, "run.aborted", {"reason": "boom"}, run_id))
    else:
        evs.append(_evt(seq, "run.completed", {"status": status}, run_id))
    return evs


def test_facts_projects_outcome_cost_and_decisions() -> None:
    f = facts(
        _events(
            "R",
            status="completed",
            usage=0.5,
            decisions=(("yes", "human"), ("no", "policy")),
        )
    )
    assert f.run_id == "R"
    assert f.status == "completed"
    assert f.cost_usd == 0.5
    assert f.agents_spawned == 1
    assert f.decisions == [
        DecisionRecord("ship?", "yes", "human"),
        DecisionRecord("ship?", "no", "policy"),
    ]


def test_render_flags_differences() -> None:
    a = facts(
        _events("AAA", status="completed", usage=0.1, decisions=(("yes", "policy"),))
    )
    b = facts(_events("BBB", status="aborted", usage=0.3, decisions=(("no", "human"),)))
    out = render_comparison(RunComparison(a, b))
    assert "AAA" in out and "BBB" in out
    assert "!=" in out  # status/cost/decision differ -> flagged
    assert "yes(policy)" in out and "no(human)" in out


def test_render_handles_uneven_decision_counts() -> None:
    a = facts(_events("A", decisions=(("yes", "policy"),)))
    b = facts(_events("B", decisions=()))
    out = render_comparison(RunComparison(a, b))
    assert "—" in out  # B has no matching decision -> placeholder
    assert "yes(policy)" in out


def test_render_no_decisions() -> None:
    a = facts(_events("A"))
    b = facts(_events("B"))
    out = render_comparison(RunComparison(a, b))
    assert "(none)" in out
