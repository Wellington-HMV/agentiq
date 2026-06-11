"""Tests for human decision resolution (story 4.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.agent.adapter import AgentAdapter
from agentiq.config.settings import AutonomySection
from agentiq.core.decision import (
    DecisionRequest,
    DecisionUnresolved,
    PromptResolver,
    format_decision_prompt,
    parse_choice,
    request_decision,
)
from agentiq.events.bus import EventBus
from agentiq.events.reader import read_events
from agentiq.events.writer import JsonlEventWriter
from agentiq.policy.policy import PolicyResolver
from agentiq.replay.markers import is_decision


def _req(default: str | None = "yes") -> DecisionRequest:
    return DecisionRequest("a1", "proceed?", options=["yes", "no"], default=default)


def test_format_marks_default() -> None:
    out = format_decision_prompt(_req())
    assert "1. yes  (default)" in out
    assert "2. no" in out


def test_parse_choice_variants() -> None:
    req = _req()
    assert parse_choice(req, "") == "yes"  # Enter → default
    assert parse_choice(req, "2") == "no"  # number → option
    assert parse_choice(req, "yes") == "yes"  # exact text
    with pytest.raises(DecisionUnresolved):
        parse_choice(req, "9")  # out of range
    with pytest.raises(DecisionUnresolved):
        parse_choice(_req(default=None), "")  # empty, no default


async def test_prompt_resolver_picks_option() -> None:
    resolver = PromptResolver(input_fn=lambda _prompt: "2")
    choice, by = await resolver.resolve(_req())
    assert (choice, by) == ("no", "human")


async def test_resolution_persists_in_log(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    writer = JsonlEventWriter(log)
    adapter = AgentAdapter("R", writer, EventBus(), secrets=set())
    resolver = PromptResolver(input_fn=lambda _prompt: "")  # Enter → default
    choice = await request_decision(adapter, _req(), resolver)
    writer.close()
    assert choice == "yes"
    resolved = next(e for e in read_events(log) if e.type == "decision.resolved")
    assert resolved.payload == {"choice": "yes", "resolved_by": "human"}
    assert is_decision(resolved.type)  # shows as a ◆ marker in replay


async def test_policy_ask_routes_to_prompt() -> None:
    autonomy = AutonomySection(default="ask")
    resolver = PolicyResolver(autonomy, ask_resolver=PromptResolver(lambda _p: "1"))
    choice, by = await resolver.resolve(_req())
    assert (choice, by) == ("yes", "human")
