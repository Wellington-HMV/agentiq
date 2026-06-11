"""Tests for the plain textual timeline (story 2.2)."""

from __future__ import annotations

from pathlib import Path

from agentiq.events.reader import read_events
from agentiq.events.writer import JsonlEventWriter
from agentiq.replay.timeline import iter_timeline_lines


def _write_run(log: Path) -> int:
    with JsonlEventWriter(log) as w:
        w.write("run.started", {"goal": "g", "project": "."}, run_id="R")
        w.write("agent.spawned", {"role": "a"}, run_id="R", agent_id="a1")
        w.write("decision.pending", {"prompt": "pick"}, run_id="R", agent_id="a1")
        w.write("agent.failed", {"cause": "boom"}, run_id="R", agent_id="a1")
        w.write("run.completed", {"status": "completed"}, run_id="R")
    return 5


def test_one_line_per_event_in_order(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    n = _write_run(log)
    lines = list(iter_timeline_lines(read_events(log)))
    assert len(lines) == n
    # Lines start with their seq in order.
    assert [int(line.split()[0]) for line in lines] == list(range(n))
    assert "run.started" in lines[0]


def test_decision_and_failure_markers(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    _write_run(log)
    lines = list(iter_timeline_lines(read_events(log)))
    # marker is the 2nd whitespace-separated column.
    markers = [line.split()[1] for line in lines]
    assert markers[2] == "D"  # decision.pending
    assert markers[3] == "F"  # agent.failed
    assert markers[0] == "."  # run.started

    # ASCII only (pipeable everywhere).
    assert all(line.isascii() for line in lines)
