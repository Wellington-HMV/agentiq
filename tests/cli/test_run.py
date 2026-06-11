"""Tests for the ``agentiq run`` command (story 1.7)."""

from __future__ import annotations

from pathlib import Path

import pytest

import agentiq.core.orchestrator as orch
from agentiq.cli.app import main


def test_run_command_exits_zero_and_creates_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runs_root = tmp_path / "runs"
    real_start = orch.start_run

    def fake_start(goal, project, *, runs_root=None, run_id=None, bus=None):  # noqa: ARG001
        # Force the run store into a temp dir (don't touch the real home).
        return real_start(
            goal, project, runs_root=runs_root_dir, run_id=run_id, bus=bus
        )

    runs_root_dir = runs_root
    monkeypatch.setattr(orch, "start_run", fake_start)

    rc = main(["run", "do something", "--project", str(tmp_path)])

    assert rc == 0
    assert "completed" in capsys.readouterr().out
    logs = list(runs_root.glob("*/events.jsonl"))
    assert len(logs) == 1
