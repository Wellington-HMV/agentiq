"""Tests for the append-only JSONL writer (story 1.2)."""

from __future__ import annotations

from pathlib import Path

import agentiq.events.writer as writer_mod
from agentiq.events.reader import read_events
from agentiq.events.writer import JsonlEventWriter


def test_seq_is_monotonic_from_zero(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    with JsonlEventWriter(log) as w:
        e0 = w.write("run.started", {"goal": "g", "project": "."}, run_id="r")
        e1 = w.write("vault.read", {"ref": "x"}, run_id="r", agent_id="a1")
    assert e0.seq == 0
    assert e1.seq == 1


def test_one_json_object_per_line(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    with JsonlEventWriter(log) as w:
        w.write("run.started", {"goal": "g", "project": "."}, run_id="r")
        w.write("run.completed", {"status": "completed"}, run_id="r")
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_fsync_called_per_write(tmp_path: Path, monkeypatch) -> None:
    calls = {"n": 0}
    real_fsync = writer_mod.os.fsync

    def spy(fd: int) -> None:
        calls["n"] += 1
        real_fsync(fd)

    monkeypatch.setattr(writer_mod.os, "fsync", spy)
    log = tmp_path / "events.jsonl"
    with JsonlEventWriter(log) as w:
        w.write("run.started", {"goal": "g", "project": "."}, run_id="r")
        w.write("run.completed", {"status": "completed"}, run_id="r")
    # 2 writes (+ at least the close fsync).
    assert calls["n"] >= 2


def test_appending_continues_seq(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    with JsonlEventWriter(log) as w:
        w.write("run.started", {"goal": "g", "project": "."}, run_id="r")
        w.write("vault.read", {"ref": "x"}, run_id="r")
    # New writer on the same path resumes seq.
    with JsonlEventWriter(log) as w2:
        assert w2.next_seq == 2
        e = w2.write("run.completed", {"status": "completed"}, run_id="r")
    assert e.seq == 2
    seqs = [ev.seq for ev in read_events(log)]
    assert seqs == [0, 1, 2]
