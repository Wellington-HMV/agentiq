"""Tests for the ``agentiq rerun`` command (story 5.6)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from agentiq.cli.rerun import rerun_command
from agentiq.core.run import start_run
from agentiq.events.reader import read_events


def _failed_run(runs_root: Path, rid: str = "SRC") -> None:
    run = start_run("g", ".", runs_root=runs_root, run_id=rid)
    run.writer.write("agent.failed", {"cause": "boom"}, run_id=rid, agent_id="a1")
    run.abort("failed")


def test_rerun_forks_and_finalizes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runs_root = tmp_path / "runs"
    _failed_run(runs_root)

    rc = rerun_command(
        argparse.Namespace(run_id="SRC", at_seq=None, runs_root=runs_root)
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "re-run" in out and "from SRC" in out

    # A new run dir exists (not SRC) holding a finalized, sane-prefix log.
    new_dirs = [d for d in runs_root.iterdir() if d.name != "SRC"]
    assert len(new_dirs) == 1
    types = [e.type for e in read_events(new_dirs[0] / "events.jsonl")]
    assert types[0] == "run.started" and types[-1] == "run.completed"
    assert "agent.failed" not in types
    assert (new_dirs[0] / "summary.json").exists()


def test_rerun_unknown_run_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = rerun_command(
        argparse.Namespace(run_id="NOPE", at_seq=None, runs_root=tmp_path / "runs")
    )
    assert rc != 0
    assert "no run found" in capsys.readouterr().err
