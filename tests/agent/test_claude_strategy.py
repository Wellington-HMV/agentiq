"""Tests for the Claude SDK strategy translation (no network).

Uses a fake `query_fn` yielding objects whose class names + attributes mimic the
SDK message schema, so the translation is exercised without an API key.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.agent.adapter import AgentAdapter
from agentiq.agent.claude_strategy import ClaudeStrategy
from agentiq.events.bus import EventBus
from agentiq.events.reader import read_events
from agentiq.events.writer import JsonlEventWriter


class ToolUseBlock:
    def __init__(self, id: str, name: str, input: dict) -> None:
        self.id = id
        self.name = name
        self.input = input


class TextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class AssistantMessage:
    def __init__(self, content, usage=None, parent_tool_use_id=None) -> None:
        self.content = content
        self.usage = usage
        self.parent_tool_use_id = parent_tool_use_id


class ResultMessage:
    def __init__(self, total_cost_usd=0.0, is_error=False) -> None:
        self.total_cost_usd = total_cost_usd
        self.is_error = is_error


def _adapter(tmp_path: Path) -> tuple[AgentAdapter, JsonlEventWriter, Path]:
    log = tmp_path / "events.jsonl"
    writer = JsonlEventWriter(log)
    return AgentAdapter("R", writer, EventBus(), secrets=set()), writer, log


async def test_translates_task_tooluse_and_usage_and_cost(tmp_path: Path) -> None:
    async def fake_query(*, prompt, options):  # noqa: ARG001
        yield AssistantMessage(
            content=[
                TextBlock("planning"),
                ToolUseBlock(
                    "tu1", "Task", {"subagent_type": "analyze", "prompt": "do x"}
                ),
            ],
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        yield ResultMessage(total_cost_usd=0.42, is_error=False)

    adapter, writer, log = _adapter(tmp_path)
    status = await ClaudeStrategy(query_fn=fake_query).run("goal", Path("."), adapter)
    writer.close()

    assert status == "completed"
    events = list(read_events(log))
    types = [e.type for e in events]
    assert "agent.spawned" in types  # subagent from the Task tool use
    assert "task.delegated" in types
    assert "agent.usage" in types
    spawned = next(e for e in events if e.type == "agent.spawned")
    assert spawned.payload["role"] == "analyze"
    # final cost recorded from the ResultMessage
    costs = [e.payload["cost_usd"] for e in events if e.type == "agent.usage"]
    assert 0.42 in costs


async def test_result_error_yields_failed_status(tmp_path: Path) -> None:
    async def fake_query(*, prompt, options):  # noqa: ARG001
        yield ResultMessage(total_cost_usd=0.0, is_error=True)

    adapter, writer, _log = _adapter(tmp_path)
    status = await ClaudeStrategy(query_fn=fake_query).run("g", Path("."), adapter)
    writer.close()
    assert status == "failed"


async def test_trailing_sdk_error_after_result_is_tolerated(tmp_path: Path) -> None:
    # Observed live: the SDK raises while tearing down the stream AFTER delivering
    # a terminal ResultMessage. A result we already have must not be lost.
    async def fake_query(*, prompt, options):  # noqa: ARG001
        yield ResultMessage(total_cost_usd=0.0, is_error=False)
        raise RuntimeError("stream teardown noise")

    adapter, writer, _log = _adapter(tmp_path)
    status = await ClaudeStrategy(query_fn=fake_query).run("g", Path("."), adapter)
    writer.close()
    assert status == "completed"  # kept the result despite the trailing raise


async def test_error_before_any_result_propagates(tmp_path: Path) -> None:
    # A failure before any ResultMessage is a real abort -> propagate so the
    # orchestration turns it into run.aborted (never silently "completed").
    async def fake_query(*, prompt, options):  # noqa: ARG001
        raise RuntimeError("connection failed")
        yield  # pragma: no cover - makes this an async generator

    adapter, writer, _log = _adapter(tmp_path)
    with pytest.raises(RuntimeError):
        await ClaudeStrategy(query_fn=fake_query).run("g", Path("."), adapter)
    writer.close()


async def test_subagent_tagged_with_team(tmp_path: Path) -> None:
    async def fake_query(*, prompt, options):  # noqa: ARG001
        yield AssistantMessage(
            content=[ToolUseBlock("tu1", "Task", {"subagent_type": "analyze"})]
        )
        yield ResultMessage()

    adapter, writer, log = _adapter(tmp_path)
    await ClaudeStrategy(query_fn=fake_query).run("g", Path("."), adapter)
    writer.close()
    spawned = next(e for e in read_events(log) if e.type == "agent.spawned")
    # Subagents are grouped under the delegating lead (the parent here) — FR6.
    assert spawned.payload["team"] == "parent"


# --- guards wired into the SDK translation (cost / safety / decision) -------

from agentiq.core.decision import DecisionRequest  # noqa: E402
from agentiq.policy.safety import SafetyGuard  # noqa: E402


class _Proceed:
    async def resolve(self, request: DecisionRequest) -> tuple[str, str]:
        return "proceed", "human"


async def test_cost_breach_emits_budget_exceeded(tmp_path: Path) -> None:
    async def fake_query(*, prompt, options):  # noqa: ARG001
        yield ResultMessage(total_cost_usd=1.5, is_error=False)

    adapter, writer, log = _adapter(tmp_path)
    await ClaudeStrategy(query_fn=fake_query, cost_ceiling_usd=1.0).run(
        "g", tmp_path, adapter
    )
    writer.close()
    types = [e.type for e in read_events(log)]
    assert "agent.usage" in types
    assert types.count("budget.exceeded") == 1


async def test_halts_fanout_after_budget(tmp_path: Path) -> None:
    async def fake_query(*, prompt, options):  # noqa: ARG001
        yield ResultMessage(total_cost_usd=2.0)  # breach first
        yield AssistantMessage(
            content=[ToolUseBlock("t1", "Task", {"subagent_type": "x"})]
        )

    adapter, writer, log = _adapter(tmp_path)
    await ClaudeStrategy(query_fn=fake_query, cost_ceiling_usd=1.0).run(
        "g", tmp_path, adapter
    )
    writer.close()
    spawned = [e for e in read_events(log) if e.type == "agent.spawned"]
    assert spawned == []  # fan-out halted after the budget breach (NFR12)


# --- real tool prevention via the SDK can_use_tool callback -----------------

from types import SimpleNamespace  # noqa: E402

from claude_agent_sdk import (  # noqa: E402
    PermissionResultAllow,
    PermissionResultDeny,
)


class _Cancel:
    async def resolve(self, request) -> tuple[str, str]:  # noqa: ANN001
        return "cancel", "human"


def _cb(tmp_path: Path, resolver, adapter):  # noqa: ANN001
    strat = ClaudeStrategy(safety=SafetyGuard(tmp_path))
    return strat._permission_cb(adapter, resolver)


async def test_permission_allows_in_scope_readonly_tool(tmp_path: Path) -> None:
    adapter, writer, _log = _adapter(tmp_path)
    cb = _cb(tmp_path, _Proceed(), adapter)
    res = await cb(
        "Read", {"file_path": str(tmp_path / "f.txt")}, SimpleNamespace(agent_id="p")
    )
    writer.close()
    assert isinstance(res, PermissionResultAllow)  # read in scope -> proceeds


async def test_permission_denies_out_of_scope(tmp_path: Path) -> None:
    adapter, writer, _log = _adapter(tmp_path)
    cb = _cb(tmp_path, _Proceed(), adapter)
    res = await cb(
        "Write",
        {"file_path": str(tmp_path.parent / "outside.txt")},
        SimpleNamespace(agent_id="p"),
    )
    writer.close()
    assert isinstance(res, PermissionResultDeny)  # SDK never runs it (NFR10)


async def test_permission_confirms_irreversible_proceed(tmp_path: Path) -> None:
    adapter, writer, log = _adapter(tmp_path)
    cb = _cb(tmp_path, _Proceed(), adapter)
    res = await cb(
        "Write", {"file_path": str(tmp_path / "x.txt")}, SimpleNamespace(agent_id="a1")
    )
    writer.close()
    assert isinstance(res, PermissionResultAllow)  # confirmed -> allowed (FR34)
    types = [e.type for e in read_events(log)]
    assert "decision.pending" in types and "decision.resolved" in types


async def test_permission_denies_on_cancel(tmp_path: Path) -> None:
    adapter, writer, _log = _adapter(tmp_path)
    cb = _cb(tmp_path, _Cancel(), adapter)
    res = await cb("Bash", {"command": "rm -rf /"}, SimpleNamespace(agent_id="p"))
    writer.close()
    assert isinstance(res, PermissionResultDeny)  # cancelled confirm -> blocked


async def test_permission_denies_when_unresolvable(tmp_path: Path) -> None:
    # No human + no default => DefaultResolver raises => deny (never silently allow).
    adapter, writer, _log = _adapter(tmp_path)
    cb = _cb(tmp_path, None, adapter)  # resolver None -> DefaultResolver
    res = await cb(
        "Edit", {"file_path": str(tmp_path / "x.txt")}, SimpleNamespace(agent_id="p")
    )
    writer.close()
    assert isinstance(res, PermissionResultDeny)


def test_build_options_sets_budget_and_callback(tmp_path: Path) -> None:
    strat = ClaudeStrategy(cost_ceiling_usd=2.0, safety=SafetyGuard(tmp_path))
    adapter, writer, _log = _adapter(tmp_path)
    opts = strat._build_options(strat._permission_cb(adapter, _Proceed()))
    writer.close()
    assert opts.max_budget_usd == 2.0  # in-flight spend cap handed to the SDK
    assert opts.can_use_tool is not None  # pre-execution tool gate wired


def test_build_options_hard_blocks_denied_ops(tmp_path: Path) -> None:
    # denied_ops -> disallowed_tools: the CLI hard-blocks these regardless of
    # whether it consults can_use_tool (authoritative prevention).
    strat = ClaudeStrategy(safety=SafetyGuard(tmp_path, denied_ops=["Bash", "Write"]))
    opts = strat._build_options(None)
    assert opts.disallowed_tools == ["Bash", "Write"]
