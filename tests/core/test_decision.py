"""Tests for decision points (story 4.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.agent.adapter import AgentAdapter
from agentiq.core.decision import (
    DecisionRequest,
    DecisionUnresolved,
    DefaultResolver,
    Resolver,
    request_decision,
)
from agentiq.events.bus import EventBus
from agentiq.events.reader import read_events
from agentiq.events.writer import JsonlEventWriter


def _adapter(tmp_path: Path) -> tuple[AgentAdapter, JsonlEventWriter, Path]:
    log = tmp_path / "events.jsonl"
    writer = JsonlEventWriter(log)
    return AgentAdapter("R", writer, EventBus(), secrets=set()), writer, log


async def test_default_resolves_and_emits_both_events(tmp_path: Path) -> None:
    adapter, writer, log = _adapter(tmp_path)
    req = DecisionRequest("a1", "proceed?", options=["yes", "no"], default="yes")
    choice = await request_decision(adapter, req, DefaultResolver())
    writer.close()
    assert choice == "yes"
    types = [e.type for e in read_events(log)]
    assert types == ["decision.pending", "decision.resolved"]
    resolved = next(e for e in read_events(log) if e.type == "decision.resolved")
    assert resolved.payload == {"choice": "yes", "resolved_by": "default"}


async def test_no_default_raises_after_pending_no_resolved(tmp_path: Path) -> None:
    adapter, writer, log = _adapter(tmp_path)
    req = DecisionRequest("a1", "proceed?", options=["yes", "no"], default=None)
    with pytest.raises(DecisionUnresolved):
        await request_decision(adapter, req, DefaultResolver())
    writer.close()
    types = [e.type for e in read_events(log)]
    assert types == ["decision.pending"]  # pending emitted, no resolved, no hang


class _PickFirst:
    async def resolve(self, request: DecisionRequest) -> tuple[str, str]:
        return request.options[0], "policy"


async def test_custom_resolver_picks_option(tmp_path: Path) -> None:
    adapter, writer, log = _adapter(tmp_path)
    resolver: Resolver = _PickFirst()
    req = DecisionRequest("a1", "pick", options=["alpha", "beta"])
    choice = await request_decision(adapter, req, resolver)
    writer.close()
    assert choice == "alpha"
    resolved = next(e for e in read_events(log) if e.type == "decision.resolved")
    assert resolved.payload == {"choice": "alpha", "resolved_by": "policy"}
