"""Tests for the ``agentiq replay`` command (story 2.2)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from agentiq.cli.replay import replay_command
from agentiq.core.run import start_run


def _make_run(tmp_path: Path) -> tuple[str, Path]:
    runs_root = tmp_path / "runs"
    run = start_run("ship it", tmp_path, runs_root=runs_root, run_id="A")
    run.complete()
    return run.run_id, runs_root


def test_replay_prints_timeline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_id, runs_root = _make_run(tmp_path)
    rc = replay_command(
        argparse.Namespace(run_id=run_id, runs_root=runs_root, scene=False)
    )
    assert rc == 0
    out = capsys.readouterr().out.splitlines()
    assert any("run.started" in line for line in out)
    assert any("run.completed" in line for line in out)


def test_replay_unknown_run_id_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = replay_command(
        argparse.Namespace(run_id="NOPE", runs_root=tmp_path / "runs", scene=False)
    )
    assert rc != 0
    assert "no run found" in capsys.readouterr().err


def test_replay_scene_falls_back_to_timeline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_id, runs_root = _make_run(tmp_path)
    rc = replay_command(
        argparse.Namespace(run_id=run_id, runs_root=runs_root, scene=True)
    )
    assert rc == 0
    captured = capsys.readouterr()
    # Under pytest stdout is not a TTY → falls back to the timeline.
    assert "needs a TTY" in captured.err
    assert any("run.started" in line for line in captured.out.splitlines())
