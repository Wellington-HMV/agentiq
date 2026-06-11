"""Append-only, fsync-per-write JSONL event writer.

One run = one log file. The writer assigns the monotonic ``seq`` (the sole
ordering authority) and fsyncs after every line so an interrupted run leaves a
valid log up to the last completed event (NFR6). Synchronous by design — the
async EventBus (story 1.3) wraps/offloads the I/O later.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

from agentiq.events.models import Event
from agentiq.events.reader import read_events


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class JsonlEventWriter:
    """Writes events as JSON lines to an append-only log file."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Continue seq from an existing log, else start at 0.
        self._next_seq = self._resume_seq()
        self._file = open(self._path, "a", encoding="utf-8", newline="\n")

    def _resume_seq(self) -> int:
        if not self._path.exists() or self._path.stat().st_size == 0:
            return 0
        last_seq = -1
        for event in read_events(self._path):
            last_seq = event.seq
        return last_seq + 1

    def write(
        self,
        type: str,
        payload: dict[str, object] | None = None,
        *,
        run_id: str,
        agent_id: str | None = None,
        ts: str | None = None,
    ) -> Event:
        """Build, durably append, and return one event with its assigned seq."""
        event = Event(
            seq=self._next_seq,
            ts=ts or _utc_now_iso(),
            run_id=run_id,
            agent_id=agent_id,
            type=type,
            payload=dict(payload or {}),
        )
        self._file.write(event.to_json_line() + "\n")
        self._file.flush()
        os.fsync(self._file.fileno())
        self._next_seq += 1
        return event

    @property
    def next_seq(self) -> int:
        return self._next_seq

    def close(self) -> None:
        if not self._file.closed:
            self._file.flush()
            os.fsync(self._file.fileno())
            self._file.close()

    def __enter__(self) -> JsonlEventWriter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
