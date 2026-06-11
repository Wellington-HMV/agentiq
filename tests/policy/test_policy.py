"""Tests for the autonomy policy engine (story 4.2)."""

from __future__ import annotations

import pytest

from agentiq.config.settings import AutonomyRule, AutonomySection
from agentiq.core.decision import DecisionRequest, DecisionUnresolved
from agentiq.policy.policy import PolicyResolver


def _req(kind: str = "general", default: str | None = None) -> DecisionRequest:
    return DecisionRequest(
        "a1", "proceed?", options=["yes", "no"], default=default, kind=kind
    )


async def test_allow_rule_auto_resolves() -> None:
    autonomy = AutonomySection(rules=[AutonomyRule(kind="spawn", action="allow")])
    choice, by = await PolicyResolver(autonomy).resolve(_req("spawn", default="yes"))
    assert (choice, by) == ("yes", "policy")


async def test_allow_without_default_uses_first_option() -> None:
    autonomy = AutonomySection(rules=[AutonomyRule(kind="spawn", action="allow")])
    choice, by = await PolicyResolver(autonomy).resolve(_req("spawn"))
    assert (choice, by) == ("yes", "policy")  # first option


async def test_deny_rule() -> None:
    autonomy = AutonomySection(rules=[AutonomyRule(kind="rm", action="deny")])
    choice, by = await PolicyResolver(autonomy).resolve(_req("rm"))
    assert (choice, by) == ("deny", "policy")


async def test_ask_without_resolver_raises() -> None:
    autonomy = AutonomySection(default="ask")
    with pytest.raises(DecisionUnresolved):
        await PolicyResolver(autonomy).resolve(_req("anything"))


async def test_ask_delegates_to_human_resolver() -> None:
    class _Human:
        async def resolve(self, request: DecisionRequest) -> tuple[str, str]:
            return "no", "human"

    autonomy = AutonomySection(default="ask")
    choice, by = await PolicyResolver(autonomy, ask_resolver=_Human()).resolve(_req())
    assert (choice, by) == ("no", "human")


async def test_no_matching_rule_falls_to_default_action() -> None:
    autonomy = AutonomySection(
        default="allow", rules=[AutonomyRule(kind="rm", action="deny")]
    )
    # kind "other" has no rule → default "allow"
    choice, by = await PolicyResolver(autonomy).resolve(_req("other", default="yes"))
    assert (choice, by) == ("yes", "policy")
