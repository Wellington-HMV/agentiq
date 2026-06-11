"""Autonomy policy wired into the headless run path (story 5.4 / FR25)."""

from __future__ import annotations

from pathlib import Path

from agentiq.agent.adapter import AgentAdapter
from agentiq.config.settings import AutonomyRule, AutonomySection
from agentiq.core.decision import DecisionRequest, Resolver, request_decision
from agentiq.core.orchestrator import run_orchestration
from agentiq.events.reader import read_events
from agentiq.policy.policy import PolicyResolver

_REQ = DecisionRequest(
    "parent", "deploy?", options=["yes", "no"], default="yes", kind="deploy"
)


class _DecideStrategy:
    """A strategy that asks one decision through the injected resolver."""

    async def run(
        self,
        goal: str,
        project: Path,
        adapter: AgentAdapter,
        vault: object | None = None,
        resolver: Resolver | None = None,
    ) -> str:
        assert resolver is not None
        await request_decision(adapter, _REQ, resolver)
        return "completed"


async def _run(autonomy: AutonomySection, tmp_path: Path) -> Path:
    run = await run_orchestration(
        "g",
        tmp_path,
        strategy=_DecideStrategy(),
        runs_root=tmp_path / "runs",
        resolver=PolicyResolver(autonomy),
    )
    return run.events_path


async def test_headless_allow_auto_resolves(tmp_path: Path) -> None:
    path = await _run(AutonomySection(default="allow"), tmp_path)
    resolved = [e for e in read_events(path) if e.type == "decision.resolved"]
    assert len(resolved) == 1
    assert resolved[0].payload == {"choice": "yes", "resolved_by": "policy"}


async def test_headless_ask_aborts_never_hangs(tmp_path: Path) -> None:
    # No human in headless: PolicyResolver raises -> run aborts (NFR8).
    run = await run_orchestration(
        "g",
        tmp_path,
        strategy=_DecideStrategy(),
        runs_root=tmp_path / "runs",
        resolver=PolicyResolver(AutonomySection(default="ask")),
    )
    assert run.status == "aborted"
    types = [e.type for e in read_events(run.events_path)]
    assert "decision.pending" in types and "decision.resolved" not in types


async def test_headless_rule_beats_default(tmp_path: Path) -> None:
    autonomy = AutonomySection(
        default="allow", rules=[AutonomyRule(kind="deploy", action="deny")]
    )
    path = await _run(autonomy, tmp_path)
    resolved = [e for e in read_events(path) if e.type == "decision.resolved"]
    assert resolved[0].payload == {"choice": "deny", "resolved_by": "policy"}
