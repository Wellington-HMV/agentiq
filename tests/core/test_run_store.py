"""Tests for listing the run store (story 1.9)."""

from __future__ import annotations

import json
from pathlib import Path

from agentiq.core.run import list_runs, start_run


def test_list_runs_empty(tmp_path: Path) -> None:
    assert list_runs(tmp_path / "does-not-exist") == []
    (tmp_path / "runs").mkdir()
    assert list_runs(tmp_path / "runs") == []


def test_list_runs_newest_first(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    a = start_run("first", tmp_path, runs_root=runs_root, run_id="A")
    a.complete()
    b = start_run("second", tmp_path, runs_root=runs_root, run_id="B")
    b.complete()

    infos = list_runs(runs_root)
    assert [i.run_id for i in infos] == ["B", "A"]  # newest (greater ULID) first
    assert infos[0].goal == "second"
    assert infos[0].status == "completed"


def test_list_runs_reads_summary(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    run = start_run("g", tmp_path, runs_root=runs_root, run_id="A")
    run.complete()
    # Write a summary.json with cost/duration as the orchestrator would.
    (run.root_dir / "summary.json").write_text(
        json.dumps({"cost_usd": 1.25, "duration_seconds": 3.5}), encoding="utf-8"
    )
    info = list_runs(runs_root)[0]
    assert info.cost_usd == 1.25
    assert info.duration_seconds == 3.5
