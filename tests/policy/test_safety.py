"""Tests for action scoping + confirm-before-irreversible (story 4.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.agent.adapter import AgentAdapter
from agentiq.core.decision import DecisionRequest
from agentiq.events.bus import EventBus
from agentiq.events.reader import read_events
from agentiq.events.writer import JsonlEventWriter
from agentiq.policy.safety import (
    AgentAction,
    SafetyDenied,
    SafetyGuard,
    authorize,
)


def _guard(tmp_path: Path) -> SafetyGuard:
    project = tmp_path / "proj"
    vault = tmp_path / "vault"
    project.mkdir()
    vault.mkdir()
    return SafetyGuard(project, [vault], denied_ops=["network"])


def test_in_scope(tmp_path: Path) -> None:
    g = _guard(tmp_path)
    assert g.in_scope(tmp_path / "proj" / "a.py")
    assert g.in_scope(tmp_path / "vault" / "n.md")
    assert not g.in_scope(tmp_path / "elsewhere" / "x")


def test_evaluate_verdicts(tmp_path: Path) -> None:
    g = _guard(tmp_path)
    assert g.evaluate(AgentAction("read", path=str(tmp_path / "proj" / "a"))) == "allow"
    assert g.evaluate(AgentAction("read", path=str(tmp_path / "outside"))) == "deny"
    assert g.evaluate(AgentAction("network")) == "deny"  # denied op kind
    assert g.evaluate(AgentAction("delete", irreversible=True)) == "confirm"
    assert g.evaluate(AgentAction("post", outward=True)) == "confirm"


def _adapter(tmp_path: Path) -> tuple[AgentAdapter, JsonlEventWriter, Path]:
    log = tmp_path / "events.jsonl"
    writer = JsonlEventWriter(log)
    return AgentAdapter("R", writer, EventBus(), secrets=set()), writer, log


class _Choose:
    def __init__(self, value: str) -> None:
        self._value = value

    async def resolve(self, request: DecisionRequest) -> tuple[str, str]:
        return self._value, "human"


async def test_authorize_allow(tmp_path: Path) -> None:
    g = _guard(tmp_path)
    adapter, writer, _log = _adapter(tmp_path)
    ok = await authorize(
        g,
        AgentAction("read", path=str(tmp_path / "proj" / "a")),
        adapter=adapter,
        resolver=_Choose("proceed"),
        agent_id="a1",
    )
    writer.close()
    assert ok is True


async def test_authorize_deny_raises(tmp_path: Path) -> None:
    g = _guard(tmp_path)
    adapter, writer, _log = _adapter(tmp_path)
    with pytest.raises(SafetyDenied):
        await authorize(
            g,
            AgentAction("read", path=str(tmp_path / "outside")),
            adapter=adapter,
            resolver=_Choose("proceed"),
            agent_id="a1",
        )
    writer.close()


async def test_authorize_confirm_proceed_and_cancel(tmp_path: Path) -> None:
    g = _guard(tmp_path)
    adapter, writer, log = _adapter(tmp_path)
    action = AgentAction("delete", irreversible=True)
    assert await authorize(
        g, action, adapter=adapter, resolver=_Choose("proceed"), agent_id="a1"
    )
    assert not await authorize(
        g, action, adapter=adapter, resolver=_Choose("cancel"), agent_id="a1"
    )
    writer.close()
    types = [e.type for e in read_events(log)]
    assert types.count("decision.pending") == 2
    assert types.count("decision.resolved") == 2
