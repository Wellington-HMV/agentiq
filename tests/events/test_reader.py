"""Tests for the JSONL reader/validator (story 1.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.events.reader import EventLogError, read_events
from agentiq.events.writer import JsonlEventWriter


def test_round_trip_equality(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    with JsonlEventWriter(log) as w:
        written = [
            w.write("run.started", {"goal": "g", "project": "."}, run_id="r"),
            w.write("vault.read", {"ref": "x"}, run_id="r", agent_id="a1"),
            w.write("run.completed", {"status": "completed"}, run_id="r"),
        ]
    assert list(read_events(log)) == written


def test_corrupt_line_fails_fast_with_lineno(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    with JsonlEventWriter(log) as w:
        w.write("run.started", {"goal": "g", "project": "."}, run_id="r")
    # Append a corrupt second line.
    with open(log, "a", encoding="utf-8") as f:
        f.write("{not valid json\n")
    gen = read_events(log)
    assert next(gen).seq == 0  # first event reads fine
    with pytest.raises(EventLogError, match="line 2"):
        next(gen)


def test_non_increasing_seq_rejected(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    # Hand-write two events with seq going backwards.
    lines = [
        '{"seq":5,"ts":"2026-06-09T12:00:00.000000Z","run_id":"r","agent_id":null,'
        '"type":"run.started","payload":{"goal":"g","project":"."}}',
        '{"seq":3,"ts":"2026-06-09T12:00:01.000000Z","run_id":"r","agent_id":null,'
        '"type":"run.completed","payload":{"status":"completed"}}',
    ]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    gen = read_events(log)
    assert next(gen).seq == 5
    with pytest.raises(EventLogError, match="not strictly increasing"):
        next(gen)


def test_partial_trailing_line_reads_prefix_then_fails(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    with JsonlEventWriter(log) as w:
        w.write("run.started", {"goal": "g", "project": "."}, run_id="r")
    # Simulate a crash mid-write: a truncated second line with no newline.
    with open(log, "a", encoding="utf-8") as f:
        f.write('{"seq":1,"ts":"2026-06-09T12:00:01.00')
    gen = read_events(log)
    assert next(gen).seq == 0
    with pytest.raises(EventLogError):
        next(gen)
