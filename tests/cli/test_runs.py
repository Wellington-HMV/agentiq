"""Tests for the ``agentiq runs`` command (story 1.9)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

import agentiq.cli.runs as runs_mod
from agentiq.cli.runs import runs_command
from agentiq.core.run import start_run


def test_runs_empty_prints_hint(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = runs_command(argparse.Namespace(runs_root=tmp_path / "runs"))
    assert rc == 0
    assert "agentiq run" in capsys.readouterr().out


def test_runs_lists_each_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runs_root = tmp_path / "runs"
    for rid, goal in (("A", "first"), ("B", "second")):
        r = start_run(goal, tmp_path, runs_root=runs_root, run_id=rid)
        r.complete()
    rc = runs_command(argparse.Namespace(runs_root=runs_root))
    assert rc == 0
    out = capsys.readouterr().out
    assert "A" in out
    assert "B" in out
    assert "second" in out


def test_runs_default_root_used_when_arg_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # No runs_root attribute → falls back to list_runs(None) → default root.
    monkeypatch.setattr(runs_mod, "list_runs", lambda root: [])
    rc = runs_command(argparse.Namespace())
    assert rc == 0
    assert "agentiq run" in capsys.readouterr().out
