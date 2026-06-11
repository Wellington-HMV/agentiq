"""Tests for the run store and lifecycle (story 1.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentiq.core.run import start_run
from agentiq.events.reader import read_events


def test_start_run_creates_dir_with_files(tmp_path: Path) -> None:
    run = start_run("do x", tmp_path, runs_root=tmp_path / "runs")
    run.complete()
    assert run.root_dir.is_dir()
    assert (run.root_dir / "events.jsonl").exists()
    assert (run.root_dir / "meta.json").exists()
    assert run.root_dir.name == run.run_id


def test_first_event_is_run_started(tmp_path: Path) -> None:
    run = start_run("build feature", tmp_path, runs_root=tmp_path / "runs")
    run.complete()
    events = list(read_events(run.events_path))
    assert events[0].seq == 0
    assert events[0].type == "run.started"
    assert events[0].payload["goal"] == "build feature"
    assert events[0].payload["project"] == str(tmp_path.resolve())


def test_complete_appends_run_completed(tmp_path: Path) -> None:
    run = start_run("g", tmp_path, runs_root=tmp_path / "runs")
    run.complete()
    types = [e.type for e in read_events(run.events_path)]
    assert types == ["run.started", "run.completed"]
    meta = json.loads(run.meta_path.read_text(encoding="utf-8"))
    assert meta["status"] == "completed"


def test_abort_appends_run_aborted(tmp_path: Path) -> None:
    run = start_run("g", tmp_path, runs_root=tmp_path / "runs")
    run.abort("vault missing")
    events = list(read_events(run.events_path))
    assert events[-1].type == "run.aborted"
    assert events[-1].payload["reason"] == "vault missing"
    meta = json.loads(run.meta_path.read_text(encoding="utf-8"))
    assert meta["status"] == "aborted"


def test_meta_round_trips(tmp_path: Path) -> None:
    run = start_run("g", tmp_path, runs_root=tmp_path / "runs", run_id="01TESTULID")
    run.complete()
    meta = json.loads(run.meta_path.read_text(encoding="utf-8"))
    assert meta["run_id"] == "01TESTULID"
    assert meta["goal"] == "g"
    assert meta["project"] == str(tmp_path.resolve())
    assert "created_ts" in meta


def test_context_manager_aborts_on_exception(tmp_path: Path) -> None:
    run = start_run("g", tmp_path, runs_root=tmp_path / "runs")
    with pytest.raises(RuntimeError):
        with run:
            raise RuntimeError("boom")
    events = list(read_events(run.events_path))
    assert events[-1].type == "run.aborted"
    assert "boom" in events[-1].payload["reason"]
