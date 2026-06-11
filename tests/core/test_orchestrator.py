"""Tests for the headless orchestration loop (story 1.7)."""

from __future__ import annotations

from pathlib import Path

from agentiq.agent.adapter import AgentAdapter
from agentiq.core.orchestrator import (
    DeterministicStrategy,
    run_orchestration,
)
from agentiq.events.reader import read_events


def _seq_signature(events_path: Path) -> list[tuple[str, dict]]:
    """The (type, payload) sequence, excluding volatile run_id/ts."""
    return [(e.type, e.payload) for e in read_events(events_path)]


async def test_orchestration_emits_expected_sequence(tmp_path: Path) -> None:
    run = await run_orchestration(
        "build feature",
        tmp_path,
        strategy=DeterministicStrategy(subtasks=("analyze", "implement")),
        runs_root=tmp_path / "runs",
    )
    assert run.status == "completed"
    types = [e.type for e in read_events(run.events_path)]
    assert types == [
        "run.started",
        "agent.spawned",  # parent
        "agent.spawned",  # a1
        "task.delegated",
        "agent.spawned",  # a2
        "task.delegated",
        "run.completed",
    ]


async def test_orchestration_is_deterministic(tmp_path: Path) -> None:
    s = DeterministicStrategy()
    run_a = await run_orchestration(
        "same goal", tmp_path, strategy=s, runs_root=tmp_path / "runs", run_id="A"
    )
    run_b = await run_orchestration(
        "same goal", tmp_path, strategy=s, runs_root=tmp_path / "runs", run_id="B"
    )
    assert run_a.run_id != run_b.run_id
    assert _seq_signature(run_a.events_path) == _seq_signature(run_b.events_path)


async def test_replay_reproduces_written_sequence(tmp_path: Path) -> None:
    run = await run_orchestration(
        "g", tmp_path, strategy=DeterministicStrategy(), runs_root=tmp_path / "runs"
    )
    events = list(read_events(run.events_path))
    seqs = [e.seq for e in events]
    assert seqs == list(range(len(events)))  # contiguous, ordered (FR18)
    assert events[0].type == "run.started"
    assert events[-1].type == "run.completed"


class _FailingStrategy:
    async def run(
        self,
        goal: str,
        project: Path,
        adapter: AgentAdapter,
        vault: object | None = None,
        resolver: object | None = None,
    ) -> str:
        raise RuntimeError("boom")


async def test_failing_strategy_aborts_without_raising(tmp_path: Path) -> None:
    run = await run_orchestration(
        "g", tmp_path, strategy=_FailingStrategy(), runs_root=tmp_path / "runs"
    )
    assert run.status == "aborted"
    last = list(read_events(run.events_path))[-1]
    assert last.type == "run.aborted"
    assert "boom" in last.payload["reason"]
