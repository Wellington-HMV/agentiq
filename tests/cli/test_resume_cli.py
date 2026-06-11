"""Tests for the ``agentiq resume`` command (story 4.6)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from agentiq.cli.resume import resume_command
from agentiq.core.run import start_run
from agentiq.events.reader import read_events


def test_resume_finalizes_blocked_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runs_root = tmp_path / "runs"
    run = start_run("g", tmp_path, runs_root=runs_root, run_id="X")
    run.writer.write(
        "decision.pending",
        {"prompt": "?", "options": ["y"], "default": None},
        run_id="X",
        agent_id="a1",
    )
    run.writer.close()  # blocked: started + pending, no terminal

    rc = resume_command(argparse.Namespace(run_id="X", runs_root=runs_root))
    assert rc == 0
    assert "completed" in capsys.readouterr().out
    types = [e.type for e in read_events(run.events_path)]
    assert types[-1] == "run.completed"
    assert (run.root_dir / "summary.json").exists()


def test_resume_unknown_run_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = resume_command(argparse.Namespace(run_id="NOPE", runs_root=tmp_path / "runs"))
    assert rc != 0
    assert "no run found" in capsys.readouterr().err
