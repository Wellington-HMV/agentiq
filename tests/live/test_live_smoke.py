"""Live smoke tests for the Claude SDK strategy.

Opt-in only: spends real tokens, so it is skipped unless BOTH ``ANTHROPIC_API_KEY``
and ``AGENTIQ_LIVE=1`` are set. Run with:

    AGENTIQ_LIVE=1 python -m uv run pytest tests/live -q     # (set the key too)

These assert the run reaches a terminal state through the real API; the exact
event shape is calibrated separately (see docs/live-calibration.md).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_LIVE = bool(os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("AGENTIQ_LIVE"))
pytestmark = pytest.mark.skipif(
    not _LIVE, reason="live API test; set ANTHROPIC_API_KEY and AGENTIQ_LIVE=1 to run"
)


async def test_live_run_reaches_terminal_state(tmp_path: Path) -> None:
    from agentiq.agent.claude_strategy import ClaudeStrategy
    from agentiq.core.orchestrator import run_orchestration
    from agentiq.events.reader import read_events

    run = await run_orchestration(
        "Say hello, then stop. Do not delegate.",
        tmp_path,
        strategy=ClaudeStrategy(cost_ceiling_usd=0.50),  # cap spend
        runs_root=tmp_path / "runs",
    )
    events = list(read_events(run.events_path))  # raises if seq corrupt
    assert events[0].type == "run.started"
    assert run.status in ("completed", "aborted")
    assert events[-1].type in ("run.completed", "run.aborted")


async def test_live_delegating_goal_spawns_subagents(tmp_path: Path) -> None:
    from agentiq.agent.claude_strategy import ClaudeStrategy
    from agentiq.core.orchestrator import run_orchestration
    from agentiq.events.reader import read_events

    run = await run_orchestration(
        "Break this into two subtasks and delegate each to a subagent.",
        tmp_path,
        strategy=ClaudeStrategy(cost_ceiling_usd=1.0),
        runs_root=tmp_path / "runs",
    )
    types = [e.type for e in read_events(run.events_path)]
    # If the model delegated, the translation must have produced spawn/delegate.
    # (Not asserted hard — model behaviour varies; this documents the expectation.)
    assert "run.started" in types
    if "task.delegated" in types:
        assert "agent.spawned" in types
