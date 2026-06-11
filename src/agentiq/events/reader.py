"""JSONL event log reader/validator.

Reads a run's log line by line, validating each into a typed ``Event``. Fails
fast with a precise ``EventLogError`` on a corrupt or schema-incompatible line
(NFR6 crash-safety: everything before a bad trailing line still reads). Ordering
is enforced by strictly increasing ``seq`` — never wall-clock (NFR5).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from agentiq.events.models import Event


class EventLogError(Exception):
    """Raised when an event log line is corrupt or schema-incompatible."""


def read_events(path: str | os.PathLike[str]) -> Iterator[Event]:
    """Yield validated events in file order, asserting strictly increasing seq."""
    p = Path(path)
    prev_seq: int | None = None
    with open(p, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                event = Event.model_validate_json(line)
            except ValidationError as e:
                raise EventLogError(f"line {lineno}: invalid event: {e}") from e
            except ValueError as e:  # malformed JSON
                raise EventLogError(f"line {lineno}: malformed JSON: {e}") from e

            if prev_seq is not None and event.seq <= prev_seq:
                raise EventLogError(
                    f"line {lineno}: seq {event.seq} not strictly increasing "
                    f"(previous {prev_seq})"
                )
            prev_seq = event.seq
            yield event
