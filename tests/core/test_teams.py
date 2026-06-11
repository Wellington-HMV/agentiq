"""Tests for named, concurrent teams (story 5.3)."""

from __future__ import annotations

from pathlib import Path

from agentiq.core.orchestrator import TeamStrategy, run_orchestration
from agentiq.events.reader import read_events
from agentiq.replay.reducer import reduce_all

_TEAMS = {
    "backend": ("api", "db"),
    "frontend": ("ui", "ux"),
}


async def test_teams_group_agents_and_log_stays_ordered(tmp_path: Path) -> None:
    run = await run_orchestration(
        "ship it",
        tmp_path,
        strategy=TeamStrategy(_TEAMS),
        runs_root=tmp_path / "runs",
    )
    # read_events enforces strictly-increasing seq; concurrent teams must not
    # corrupt ordering (FR7).
    events = list(read_events(run.events_path))
    assert [e.seq for e in events] == list(range(len(events)))  # contiguous, monotonic
    assert run.status == "completed"

    state = reduce_all(events)
    # Both teams present with members grouped (FR6).
    assert set(state.teams) == {"backend", "frontend"}
    assert state.teams["backend"] == ["backend-1", "backend-2", "backend-lead"]
    assert state.teams["frontend"] == ["frontend-1", "frontend-2", "frontend-lead"]
    assert state.agents["parent"].team is None  # parent belongs to no team


async def test_all_team_events_present(tmp_path: Path) -> None:
    run = await run_orchestration(
        "goal",
        tmp_path,
        strategy=TeamStrategy({"t": ("x",)}),
        runs_root=tmp_path / "runs",
    )
    events = list(read_events(run.events_path))
    spawned = {e.agent_id for e in events if e.type == "agent.spawned"}
    assert {"parent", "t-lead", "t-1"} <= spawned
    delegated = [e.payload["to_agent"] for e in events if e.type == "task.delegated"]
    assert "t-lead" in delegated and "t-1" in delegated


async def test_many_teams_concurrent_no_corruption(tmp_path: Path) -> None:
    teams = {f"team{i}": ("a", "b", "c") for i in range(8)}
    run = await run_orchestration(
        "big goal",
        tmp_path,
        strategy=TeamStrategy(teams),
        runs_root=tmp_path / "runs",
    )
    events = list(read_events(run.events_path))  # raises if seq not strictly increasing
    assert [e.seq for e in events] == list(range(len(events)))
    state = reduce_all(events)
    assert len(state.teams) == 8
    for members in state.teams.values():
        assert len(members) == 4  # lead + 3 members
