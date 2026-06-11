"""Tests for cost metering and the hard ceiling (story 4.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.agent.adapter import AgentAdapter
from agentiq.cost.meter import CostMeter, apply_usage
from agentiq.events.bus import EventBus
from agentiq.events.reader import read_events
from agentiq.events.writer import JsonlEventWriter
from agentiq.replay.summary import build_summary


def test_meter_aggregates_and_exceeds() -> None:
    m = CostMeter(ceiling_usd=1.0)
    m.record("a1", 0.3)
    m.record("a2", 0.4)
    m.record("a1", 0.2)
    assert m.total == pytest.approx(0.9)
    assert m.per_agent("a1") == pytest.approx(0.5)
    assert m.exceeded is False
    m.record("a2", 0.2)
    assert m.exceeded is True  # total 1.1 >= 1.0


def test_take_flags_only_the_crossing() -> None:
    m = CostMeter(ceiling_usd=1.0)
    assert m.take("a", 0.6) is False
    assert m.take("a", 0.5) is True  # crosses 1.0
    assert m.take("a", 0.5) is False  # already over, not a new crossing


def _adapter(tmp_path: Path) -> tuple[AgentAdapter, JsonlEventWriter, Path]:
    log = tmp_path / "events.jsonl"
    writer = JsonlEventWriter(log)
    return AgentAdapter("R", writer, EventBus(), secrets=set()), writer, log


def test_apply_usage_emits_usage_and_single_budget_exceeded(tmp_path: Path) -> None:
    adapter, writer, log = _adapter(tmp_path)
    meter = CostMeter(ceiling_usd=1.0)
    assert apply_usage(meter, adapter, "a1", 0.6) is False
    assert apply_usage(meter, adapter, "a1", 0.5) is True  # crosses
    assert apply_usage(meter, adapter, "a1", 0.5) is True  # still over
    writer.close()
    types = [e.type for e in read_events(log)]
    assert types.count("agent.usage") == 3
    assert types.count("budget.exceeded") == 1  # emitted once


def test_summary_cost_from_usage(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    with JsonlEventWriter(log) as w:
        w.write("run.started", {"goal": "g", "project": "."}, run_id="R")
        w.write("agent.usage", {"cost_usd": 0.25}, run_id="R", agent_id="a1")
        w.write("agent.usage", {"cost_usd": 0.75}, run_id="R", agent_id="a2")
        w.write("run.completed", {"status": "completed"}, run_id="R")
    summary = build_summary(read_events(log))
    assert summary.cost_usd == 1.0
