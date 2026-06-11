"""Tests for vault-aware orchestration (story 3.5)."""

from __future__ import annotations

from pathlib import Path

from agentiq.core.orchestrator import DeterministicStrategy, run_orchestration
from agentiq.events.reader import read_events
from agentiq.vault.harness import HarnessVaultProvider

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "vault"


async def test_run_with_vault_emits_reads_and_verifies(tmp_path: Path) -> None:
    run = await run_orchestration(
        "build",
        tmp_path,
        strategy=DeterministicStrategy(subtasks=("analyze",)),
        vault=HarnessVaultProvider(_FIXTURE),
        runs_root=tmp_path / "runs",
    )
    assert run.status == "completed"
    reads = [e for e in read_events(run.events_path) if e.type == "vault.read"]
    # one subagent read + one parent verification read for the single subtask
    agents = sorted(e.agent_id for e in reads)
    assert agents == ["a1", "parent"]
    assert all(e.payload["ref"] == "api-design" for e in reads)


async def test_run_without_vault_has_no_reads(tmp_path: Path) -> None:
    run = await run_orchestration(
        "build",
        tmp_path,
        strategy=DeterministicStrategy(subtasks=("analyze",)),
        runs_root=tmp_path / "runs",
    )
    assert run.status == "completed"
    assert not [e for e in read_events(run.events_path) if e.type == "vault.read"]


async def test_invalid_vault_aborts_run(tmp_path: Path) -> None:
    bad = tmp_path / "bad-vault"  # no .harness/manifest.toml
    bad.mkdir()
    run = await run_orchestration(
        "build",
        tmp_path,
        strategy=DeterministicStrategy(),
        vault=HarnessVaultProvider(bad),
        runs_root=tmp_path / "runs",
    )
    assert run.status == "aborted"
    last = list(read_events(run.events_path))[-1]
    assert last.type == "run.aborted"
    assert "vault invalid" in last.payload["reason"]
