"""Run summary — a projection of the event log.

``summary.json`` is derived purely by replaying ``events.jsonl``; it is never
written field-by-field during a run (that would risk drifting from the log). It
is computed once a run has a terminal event.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from agentiq.events.models import Event
from agentiq.events.reader import read_events

_TS_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
_TERMINAL_TYPES = {"run.completed", "run.aborted"}


class RunSummary(BaseModel):
    """Human- and machine-readable projection of a run."""

    run_id: str | None = None
    goal: str | None = None
    status: str = "incomplete"
    started_ts: str | None = None
    ended_ts: str | None = None
    duration_seconds: float | None = None
    event_count: int = 0
    agents_spawned: int = 0
    tasks_delegated: int = 0
    decisions_made: int = 0
    failures: int = 0
    cost_usd: float = 0.0  # filled by the Epic 4 cost meter; 0.0 until then


def _duration(started: str | None, ended: str | None) -> float | None:
    if not started or not ended:
        return None
    fmt = _TS_FORMAT
    delta = datetime.strptime(ended, fmt) - datetime.strptime(started, fmt)
    return delta.total_seconds()


def build_summary(events: Iterable[Event]) -> RunSummary:
    """Project a RunSummary purely from an event sequence."""
    s = RunSummary()
    for event in events:
        s.event_count += 1
        if s.run_id is None:
            s.run_id = event.run_id
        match event.type:
            case "run.started":
                s.goal = event.payload.get("goal")
                s.started_ts = event.ts
            case "run.completed":
                s.status = event.payload.get("status", "completed")
                s.ended_ts = event.ts
            case "run.aborted":
                s.status = "aborted"
                s.ended_ts = event.ts
            case "agent.spawned":
                s.agents_spawned += 1
            case "task.delegated":
                s.tasks_delegated += 1
            case "decision.resolved":
                s.decisions_made += 1
            case "agent.failed":
                s.failures += 1
            case "agent.usage":
                s.cost_usd += float(event.payload.get("cost_usd", 0.0))
    s.duration_seconds = _duration(s.started_ts, s.ended_ts)
    return s


def write_summary(
    events_path: str | os.PathLike[str], out_path: str | os.PathLike[str]
) -> RunSummary:
    """Build the summary from a log file and write it as pretty JSON."""
    summary = build_summary(read_events(events_path))
    Path(out_path).write_text(
        json.dumps(summary.model_dump(), indent=2), encoding="utf-8"
    )
    return summary
