"""Tests for the ``agentiq compare`` command (story 6.3)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from agentiq.cli.compare import compare_command
from agentiq.core.run import start_run


def _make(runs_root: Path, rid: str, *, status: str = "completed") -> None:
    run = start_run("g", ".", runs_root=runs_root, run_id=rid)
    run.writer.write("agent.spawned", {"role": "x"}, run_id=rid, agent_id="a1")
    if status == "aborted":
        run.abort("boom")
    else:
        run.complete()


def test_compare_prints_side_by_side(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runs = tmp_path / "runs"
    _make(runs, "AAA", status="completed")
    _make(runs, "BBB", status="aborted")
    rc = compare_command(argparse.Namespace(run_a="AAA", run_b="BBB", runs_root=runs))
    assert rc == 0
    out = capsys.readouterr().out
    assert "AAA" in out and "BBB" in out
    assert "status" in out and "!=" in out  # outcomes differ


def test_compare_unknown_run_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runs = tmp_path / "runs"
    _make(runs, "AAA")
    rc = compare_command(argparse.Namespace(run_a="AAA", run_b="NOPE", runs_root=runs))
    assert rc != 0
    assert "no run found" in capsys.readouterr().err
