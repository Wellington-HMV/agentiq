"""Tests for deterministic exit codes (story 1.8)."""

from __future__ import annotations

import json
from pathlib import Path

from agentiq.core.exit_codes import ExitCode, status_to_exit_code
from agentiq.core.orchestrator import DeterministicStrategy, run_orchestration


def test_status_mapping() -> None:
    assert status_to_exit_code("completed") == ExitCode.SUCCESS
    assert status_to_exit_code("aborted") == ExitCode.FAILED
    assert status_to_exit_code("blocked") == ExitCode.BLOCKED
    assert status_to_exit_code("budget_exceeded") == ExitCode.BUDGET_EXCEEDED
    assert status_to_exit_code("weird") == ExitCode.FAILED


async def test_orchestration_writes_summary_matching_log(tmp_path: Path) -> None:
    run = await run_orchestration(
        "build", tmp_path, strategy=DeterministicStrategy(), runs_root=tmp_path / "runs"
    )
    summary_path = run.root_dir / "summary.json"
    assert summary_path.exists()
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert data["status"] == "completed"
    assert data["run_id"] == run.run_id
    # parent + 3 subtasks = 4 spawns; 3 delegations
    assert data["agents_spawned"] == 4
    assert data["tasks_delegated"] == 3
    assert status_to_exit_code(run.status) == ExitCode.SUCCESS
