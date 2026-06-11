"""Tests for the in-process async event bus (story 1.3)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from agentiq.events.bus import EventBus, resync_from_log
from agentiq.events.models import Event
from agentiq.events.writer import JsonlEventWriter


def _event(seq: int) -> Event:
    return Event.model_validate(
        {
            "seq": seq,
            "ts": "2026-06-09T12:00:00.000000Z",
            "run_id": "r",
            "type": "vault.read",
            "payload": {"ref": "x"},
        }
    )


async def test_publish_non_blocking_sets_overflow() -> None:
    bus = EventBus()
    sub = bus.subscribe(maxsize=1)
    for i in range(3):
        bus.publish(_event(i))  # must return immediately, no exception
    assert sub.overflowed is True
    first = await asyncio.wait_for(sub.get(), timeout=1)
    assert first.seq == 0


async def test_slow_consumer_does_not_block_producer() -> None:
    bus = EventBus()
    sub = bus.subscribe(maxsize=2)
    # Nothing consumes; producer publishes far past the queue capacity.
    for i in range(5):
        bus.publish(_event(i))
    # Reaching here means publish never blocked; overflow is flagged.
    assert sub.overflowed is True


async def test_independent_in_order_delivery() -> None:
    bus = EventBus()
    s1 = bus.subscribe(maxsize=10)
    s2 = bus.subscribe(maxsize=10)
    for i in range(3):
        bus.publish(_event(i))
    got1 = [(await s1.get()).seq for _ in range(3)]
    got2 = [(await s2.get()).seq for _ in range(3)]
    assert got1 == [0, 1, 2]
    assert got2 == [0, 1, 2]
    assert s1.last_seq == 2
    assert s2.last_seq == 2


async def test_resync_from_log_recovers_missed_events(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    with JsonlEventWriter(log) as w:
        w.write("run.started", {"goal": "g", "project": "."}, run_id="r")  # seq 0
        w.write("vault.read", {"ref": "x"}, run_id="r")  # seq 1
        w.write("run.completed", {"status": "completed"}, run_id="r")  # seq 2
    bus = EventBus()
    sub = bus.subscribe(maxsize=1)
    # Subscriber received seq 0 live, then overflowed and missed 1 & 2.
    sub.last_seq = 0
    sub.overflowed = True

    missed = list(resync_from_log(sub, log))

    assert [e.seq for e in missed] == [1, 2]
    assert sub.last_seq == 2
    assert sub.overflowed is False
