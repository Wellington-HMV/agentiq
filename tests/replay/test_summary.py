"""Tests for run summary projection (story 1.8)."""

from __future__ import annotations

import json
from pathlib import Path

from agentiq.events.reader import read_events
from agentiq.events.writer import JsonlEventWriter
from agentiq.replay.summary import build_summary, write_summary


def _write_completed_run(log: Path) -> None:
    with JsonlEventWriter(log) as w:
        w.write("run.started", {"goal": "ship it", "project": "."}, run_id="R")
        w.write("agent.spawned", {"role": "parent"}, run_id="R", agent_id="parent")
        w.write("agent.spawned", {"role": "analyze"}, run_id="R", agent_id="a1")
        w.write(
            "task.delegated",
            {"task": "t", "to_agent": "a1"},
            run_id="R",
            agent_id="parent",
        )
        w.write("run.completed", {"status": "completed"}, run_id="R")


def test_summary_projects_from_log(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    _write_completed_run(log)
    s = build_summary(read_events(log))
    assert s.run_id == "R"
    assert s.goal == "ship it"
    assert s.status == "completed"
    assert s.event_count == 5
    assert s.agents_spawned == 2
    assert s.tasks_delegated == 1
    assert s.failures == 0
    assert s.cost_usd == 0.0
    assert s.duration_seconds is not None and s.duration_seconds >= 0


def test_aborted_run_summarizes(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    with JsonlEventWriter(log) as w:
        w.write("run.started", {"goal": "g", "project": "."}, run_id="R")
        w.write("agent.failed", {"cause": "boom"}, run_id="R", agent_id="a1")
        w.write("run.aborted", {"reason": "boom"}, run_id="R")
    s = build_summary(read_events(log))
    assert s.status == "aborted"
    assert s.failures == 1


def test_write_summary_creates_json(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    _write_completed_run(log)
    out = tmp_path / "summary.json"
    write_summary(log, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["status"] == "completed"
    assert data["goal"] == "ship it"
    assert data["agents_spawned"] == 2
