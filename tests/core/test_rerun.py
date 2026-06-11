"""Tests for re-running from a sane state (story 5.6 / FR29)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.agent.adapter import AgentAdapter
from agentiq.core.orchestrator import continue_run
from agentiq.core.run import RunError, rerun_from, start_run
from agentiq.events.reader import read_events


def _failed_run(runs_root: Path, rid: str = "SRC") -> None:
    """A run that spawned an agent, failed, and aborted."""
    run = start_run("ship it", ".", runs_root=runs_root, run_id=rid)
    w = run.writer
    w.write(
        "agent.spawned",
        {"role": "analyze", "parent_id": "parent"},
        run_id=rid,
        agent_id="a1",
    )
    w.write("agent.failed", {"cause": "boom"}, run_id=rid, agent_id="a1")
    run.abort("a1 failed")  # events: started, spawned, failed, aborted


def test_rerun_default_cuts_before_failure(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    _failed_run(runs)
    new = rerun_from("SRC", runs_root=runs)
    assert new.run_id != "SRC"
    new.complete()

    events = list(read_events(new.events_path))
    types = [e.type for e in events]
    assert types[:2] == ["run.started", "agent.spawned"]  # last-good prefix seeded
    assert "agent.failed" not in types  # the failure is dropped
    assert types[-1] == "run.completed"
    assert [e.seq for e in events] == list(range(len(events)))  # seq contiguous
    # The new run carries forward the good work — it did not restart at seq 0 only.
    assert len(events) == 3  # started, spawned, completed

    # Source run is untouched.
    src = list(read_events(runs / "SRC" / "events.jsonl"))
    assert [e.type for e in src][-1] == "run.aborted"


def test_rerun_at_seq_pins_checkpoint(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    _failed_run(runs)
    new = rerun_from("SRC", at_seq=0, runs_root=runs)  # only run.started
    new.complete()
    types = [e.type for e in read_events(new.events_path)]
    assert types == ["run.started", "run.completed"]


def test_rerun_without_failure_raises(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    run = start_run("g", ".", runs_root=runs, run_id="OK")
    run.complete()  # no failure
    with pytest.raises(RunError):
        rerun_from("OK", runs_root=runs)
    # ...but an explicit checkpoint still works.
    new = rerun_from("OK", at_seq=0, runs_root=runs)
    new.complete()
    assert new.run_id != "OK"


def test_rerun_unknown_run_raises(tmp_path: Path) -> None:
    with pytest.raises(RunError):
        rerun_from("NOPE", runs_root=tmp_path / "runs")


class _OneStep:
    """A strategy that appends one spawn then completes (no parent re-spawn)."""

    async def run(
        self,
        goal: str,
        project: Path,
        adapter: AgentAdapter,
        vault: object | None = None,
        resolver: object | None = None,
    ) -> str:
        adapter.spawn("redo", role="redo", parent_id="parent")
        return "completed"


async def test_continue_run_reexecutes_from_checkpoint(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    _failed_run(runs)
    forked = rerun_from("SRC", runs_root=runs)  # seeded prefix, writer open
    run = await continue_run(forked, strategy=_OneStep())

    assert run.status == "completed"
    events = list(read_events(run.events_path))  # raises if seq not increasing
    types = [e.type for e in events]
    assert types[-1] == "run.completed"  # actually finalized
    assert "redo" in [e.agent_id for e in events if e.type == "agent.spawned"]
    # The seeded prefix is preserved before the continuation.
    assert types[0] == "run.started"
    assert "agent.failed" not in types  # the failure was cut by the fork


def test_rerun_does_not_touch_source(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    _failed_run(runs)
    before = (runs / "SRC" / "events.jsonl").read_text(encoding="utf-8")
    rerun_from("SRC", runs_root=runs).complete()
    after = (runs / "SRC" / "events.jsonl").read_text(encoding="utf-8")
    assert before == after  # forking never mutates the original run
