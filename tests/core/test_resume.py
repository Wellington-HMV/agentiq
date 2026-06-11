"""Tests for the resume primitive (story 4.6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.core.run import RunError, resume_run, start_run
from agentiq.events.reader import read_events


def _blocked_run(tmp_path: Path) -> tuple[str, Path]:
    runs_root = tmp_path / "runs"
    run = start_run("g", tmp_path, runs_root=runs_root, run_id="X")
    run.writer.write(
        "decision.pending",
        {"prompt": "?", "options": ["y", "n"], "default": None},
        run_id="X",
        agent_id="a1",
    )
    run.writer.close()  # leave non-terminal (meta status stays "running")
    return run.run_id, runs_root


def test_resume_reopens_and_continues_seq(tmp_path: Path) -> None:
    run_id, runs_root = _blocked_run(tmp_path)
    run = resume_run(run_id, runs_root=runs_root)
    # next event continues the seq (0 started, 1 pending → 2 next)
    e = run.writer.write("run.completed", {"status": "completed"}, run_id=run_id)
    run.writer.close()
    assert e.seq == 2
    seqs = [ev.seq for ev in read_events(run.events_path)]
    assert seqs == [0, 1, 2]  # strictly increasing, append-only preserved


def test_resume_finished_run_raises(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    run = start_run("g", tmp_path, runs_root=runs_root, run_id="Y")
    run.complete()
    with pytest.raises(RunError, match="already finished"):
        resume_run("Y", runs_root=runs_root)


def test_resume_unknown_run_raises(tmp_path: Path) -> None:
    with pytest.raises(RunError, match="no run found"):
        resume_run("NOPE", runs_root=tmp_path / "runs")


def test_resume_empty_log_raises(tmp_path: Path) -> None:
    # Non-terminal meta + empty log = crashed before run.started; refuse to resume
    # (resuming would assign seq 0 to the wrong event type).
    runs = tmp_path / "runs"
    run_dir = runs / "Z"
    run_dir.mkdir(parents=True)
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    (run_dir / "meta.json").write_text(
        '{"run_id": "Z", "goal": "g", "project": ".", "status": "running"}',
        encoding="utf-8",
    )
    with pytest.raises(RunError, match="empty log"):
        resume_run("Z", runs_root=runs)
