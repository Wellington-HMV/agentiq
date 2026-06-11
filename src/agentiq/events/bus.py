"""In-process async pub/sub event bus.

The core is the sole producer; subscribers (cost meter, TUI, replay) consume
independently via bounded queues. ``publish`` is a plain synchronous method and
never awaits a consumer (NFR2): on a full queue it flags the subscriber as
overflowed instead of blocking or dropping silently. The JSONL log (story 1.2)
is the source of truth, so an overflowed subscriber recovers missed events with
``resync_from_log`` rather than losing them.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator

from agentiq.events.models import Event
from agentiq.events.reader import read_events

DEFAULT_MAXSIZE = 1024


class Subscription:
    """One independent consumer's view of the event stream."""

    def __init__(self, maxsize: int = DEFAULT_MAXSIZE) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)
        self.overflowed: bool = False
        self.last_seq: int = -1

    def _deliver(self, event: Event) -> None:
        """Non-blocking delivery; flags overflow instead of back-pressuring."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self.overflowed = True

    async def get(self) -> Event:
        """Await the next queued event, advancing ``last_seq``."""
        event = await self._queue.get()
        self.last_seq = event.seq
        return event

    def __aiter__(self) -> Subscription:
        return self

    async def __anext__(self) -> Event:
        return await self.get()


class EventBus:
    """Fan-out bus. One producer, many independent subscribers."""

    def __init__(self) -> None:
        self._subscriptions: list[Subscription] = []

    def subscribe(self, maxsize: int = DEFAULT_MAXSIZE) -> Subscription:
        sub = Subscription(maxsize=maxsize)
        self._subscriptions.append(sub)
        return sub

    def unsubscribe(self, sub: Subscription) -> None:
        if sub in self._subscriptions:
            self._subscriptions.remove(sub)

    def publish(self, event: Event) -> None:
        """Fan out an event to all subscribers. Never blocks, never awaits."""
        for sub in self._subscriptions:
            sub._deliver(event)


def resync_from_log(
    sub: Subscription, log_path: str | os.PathLike[str]
) -> Iterator[Event]:
    """Yield events the subscriber missed (seq > last_seq) from the JSONL log.

    Catches an overflowed subscriber back up from the source of truth, advancing
    ``last_seq`` and clearing the ``overflowed`` flag.
    """
    for event in read_events(log_path):
        if event.seq > sub.last_seq:
            sub.last_seq = event.seq
            yield event
    sub.overflowed = False
