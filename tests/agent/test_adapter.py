"""Tests for the agent runtime adapter (story 1.6)."""

from __future__ import annotations

from pathlib import Path

from agentiq.agent.adapter import AgentAdapter
from agentiq.events.bus import EventBus
from agentiq.events.reader import read_events
from agentiq.events.writer import JsonlEventWriter


def _adapter(tmp_path: Path, secrets: set[str] | None = None):
    log = tmp_path / "events.jsonl"
    writer = JsonlEventWriter(log)
    bus = EventBus()
    adapter = AgentAdapter("run1", writer, bus, secrets=secrets or set())
    return adapter, writer, bus, log


def test_spawn_emits_once_then_reuses(tmp_path: Path) -> None:
    adapter, writer, _bus, log = _adapter(tmp_path)
    c1 = adapter.spawn("a1", role="builder")
    c2 = adapter.spawn("a1", role="builder")  # reuse
    writer.close()
    assert c1 is c2
    spawned = [e for e in read_events(log) if e.type == "agent.spawned"]
    assert len(spawned) == 1


def test_lifecycle_events_reach_log_and_bus(tmp_path: Path) -> None:
    adapter, writer, bus, log = _adapter(tmp_path)
    sub = bus.subscribe()
    adapter.spawn("a1")
    adapter.delegate("a1", task="do x", to_agent="a2")
    adapter.vault_read("a2", ref="api-design")
    adapter.fail("a2", cause="missing dep", last_good_seq=1)
    writer.close()

    log_types = [e.type for e in read_events(log)]
    assert log_types == [
        "agent.spawned",
        "task.delegated",
        "vault.read",
        "agent.failed",
    ]
    # Bus received the same events.
    bus_types = []
    while not sub._queue.empty():
        bus_types.append(sub._queue.get_nowait().type)
    assert bus_types == log_types


def test_credential_never_leaks_to_log_or_bus(tmp_path: Path) -> None:
    secret = "sk-ant-DEADBEEF_secret"
    adapter, writer, bus, log = _adapter(tmp_path, secrets={secret})
    sub = bus.subscribe()
    event = adapter.emit("vault.read", {"ref": f"leaked {secret} here"}, agent_id="a1")
    writer.close()

    # Not in the published event.
    assert secret not in event.to_json_line()
    assert "***" in event.payload["ref"]
    # Not on disk.
    raw = log.read_text(encoding="utf-8")
    assert secret not in raw
    # Not on the bus.
    delivered = sub._queue.get_nowait()
    assert secret not in delivered.to_json_line()
