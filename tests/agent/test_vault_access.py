"""Tests for the vault access bridge (story 3.3)."""

from __future__ import annotations

from pathlib import Path

from agentiq.agent.adapter import AgentAdapter
from agentiq.agent.vault_access import VaultReader
from agentiq.events.bus import EventBus
from agentiq.events.reader import read_events
from agentiq.events.writer import JsonlEventWriter
from agentiq.vault.harness import HarnessVaultProvider

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "vault"


def _reader(tmp_path: Path) -> tuple[VaultReader, JsonlEventWriter, Path]:
    log = tmp_path / "events.jsonl"
    writer = JsonlEventWriter(log)
    adapter = AgentAdapter("R", writer, EventBus(), secrets=set())
    reader = VaultReader(HarnessVaultProvider(_FIXTURE), adapter)
    return reader, writer, log


def test_read_returns_doc_and_emits_event(tmp_path: Path) -> None:
    reader, writer, log = _reader(tmp_path)
    doc = reader.read("a1", "api-design")
    writer.close()
    assert "API Design" in doc.body
    events = [e for e in read_events(log) if e.type == "vault.read"]
    assert len(events) == 1
    assert events[0].payload["ref"] == "api-design"
    assert events[0].agent_id == "a1"


def test_search_delegates_to_provider(tmp_path: Path) -> None:
    reader, writer, _log = _reader(tmp_path)
    writer.close()
    assert [e.id for e in reader.search(tags=["api"])] == ["api-design"]


def test_vault_reuse_is_identical(tmp_path: Path) -> None:
    a = [e.id for e in HarnessVaultProvider(_FIXTURE).entries()]
    b = [e.id for e in HarnessVaultProvider(_FIXTURE).entries()]
    assert a == b  # FR12 — same vault, same index across providers
