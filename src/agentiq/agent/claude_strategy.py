"""Real Claude Agent SDK orchestration strategy.

Drives the live Claude Agent SDK (`query`) as the parent agent and translates its
message stream into our domain events via the adapter — the same
`OrchestrationStrategy` seam the `DeterministicStrategy` uses, so the loop, log,
and replay are unchanged. SDK usage is confined to the `agent/` package
(`adapter.py` + this module).

Requires `ANTHROPIC_API_KEY` + network to run live. `query_fn` is injectable so the
translation can be tested with a fake message stream (no network). The translation
is best-effort against the SDK message schema and reads fields defensively.

Guards wired into the translation:
- **cost** — the ceiling is handed to the SDK as ``max_budget_usd`` so spend is
  capped **in-flight** (the SDK halts when crossed), and the final cost is metered
  through ``apply_usage`` so a ``budget.exceeded`` is logged + fan-out halted too.
- **safety + decision (real prevention)** — a ``can_use_tool`` callback is given to
  the SDK, which calls it **before executing each tool**. It routes the action
  through the ``SafetyGuard`` (scope, denied ops); out-of-scope/denied → the tool is
  refused (the SDK never runs it), irreversible/outward → a human decision via the
  injected ``resolver`` decides. This is genuine prevention, not observe-only.
"""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

import claude_agent_sdk
from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

from agentiq.agent.adapter import AgentAdapter
from agentiq.agent.vault_access import VaultReader
from agentiq.core.decision import (
    DecisionUnresolved,
    DefaultResolver,
    Resolver,
)
from agentiq.cost.meter import CostMeter, apply_usage
from agentiq.policy.safety import AgentAction, SafetyDenied, SafetyGuard, authorize

_PermissionResult = PermissionResultAllow | PermissionResultDeny

_PARENT_ID = "parent"
_SUBAGENT_TOOLS = {"Task", "Agent"}
# Tools whose effects are hard to undo or reach outside the box — gated.
_IRREVERSIBLE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"}
_OUTWARD_TOOLS = {"WebFetch", "WebSearch"}

_SYSTEM_PROMPT = (
    "You are the parent orchestrator. Decompose the goal into tasks and delegate "
    "them to subagents. Consult the knowledge vault when relevant."
)

QueryFn = Callable[..., AsyncIterator[Any]]


async def _prompt_stream(goal: str) -> AsyncIterator[dict[str, Any]]:
    """Yield the goal as a streaming-input user message (required by can_use_tool)."""
    yield {
        "type": "user",
        "message": {"role": "user", "content": goal},
        "parent_tool_use_id": None,
        "session_id": "default",
    }


def _action_for_tool(name: str, inp: dict[str, Any]) -> AgentAction:
    path = inp.get("file_path") or inp.get("path") or inp.get("notebook_path")
    return AgentAction(
        kind=name,
        path=str(path) if path else None,
        irreversible=name in _IRREVERSIBLE_TOOLS,
        outward=name in _OUTWARD_TOOLS,
    )


class ClaudeStrategy:
    """Orchestrates a goal with the live Claude Agent SDK."""

    def __init__(
        self,
        query_fn: QueryFn | None = None,
        *,
        cost_ceiling_usd: float | None = None,
        safety: SafetyGuard | None = None,
    ) -> None:
        self._query = query_fn or claude_agent_sdk.query
        self._meter = CostMeter(cost_ceiling_usd)
        self._safety = safety
        self._halted = False

    def _build_options(self, can_use_tool: Any | None) -> Any:
        kwargs: dict[str, Any] = {"system_prompt": _SYSTEM_PROMPT}
        if can_use_tool is not None:
            # Scope + decision gate. Best-effort: the CLI only consults it when it
            # would otherwise prompt, so a session with pre-approved tools may skip
            # it — `disallowed_tools` below is the hard, always-enforced block.
            kwargs["can_use_tool"] = can_use_tool
        if self._safety is not None and self._safety.denied_ops:
            kwargs["disallowed_tools"] = sorted(self._safety.denied_ops)
        if self._meter.ceiling_usd is not None:
            kwargs["max_budget_usd"] = self._meter.ceiling_usd  # in-flight spend cap
        return claude_agent_sdk.ClaudeAgentOptions(**kwargs)

    def _permission_cb(
        self, adapter: AgentAdapter, resolver: Resolver | None
    ) -> Callable[[str, dict[str, Any], Any], Awaitable[_PermissionResult]]:
        """Build the SDK ``can_use_tool`` callback that enforces the SafetyGuard.

        Called by the SDK before each tool runs: allow -> tool proceeds; deny ->
        the SDK never executes it; irreversible/outward -> a decision via the
        resolver. A resolver that can't settle (no human, no default) denies.
        """
        guard = self._safety
        res = resolver if resolver is not None else DefaultResolver()

        async def can_use_tool(
            tool_name: str, tool_input: dict[str, Any], context: Any
        ) -> _PermissionResult:
            if guard is None:
                return PermissionResultAllow()
            action = _action_for_tool(tool_name, tool_input or {})
            agent_id = getattr(context, "agent_id", None) or _PARENT_ID
            result: _PermissionResult
            try:
                ok = await authorize(
                    guard, action, adapter=adapter, resolver=res, agent_id=agent_id
                )
                if ok:
                    result = PermissionResultAllow()
                else:
                    result = PermissionResultDeny(message=f"cancelled: {tool_name}")
            except (SafetyDenied, DecisionUnresolved):
                result = PermissionResultDeny(message=f"blocked by policy: {tool_name}")
            if os.environ.get("AGENTIQ_DEBUG_PERMS"):
                print(f"[perm] {tool_name} -> {result.behavior}", file=sys.stderr)
            return result

        return can_use_tool

    async def run(
        self,
        goal: str,
        project: Path,
        adapter: AgentAdapter,
        vault: VaultReader | None = None,
        resolver: Resolver | None = None,
    ) -> str:
        status = "completed"
        saw_result = False
        cb = self._permission_cb(adapter, resolver) if self._safety else None
        # The SDK requires streaming-input mode (prompt as an AsyncIterable) when a
        # can_use_tool callback is set; a plain string is fine otherwise.
        prompt: Any = _prompt_stream(goal) if cb is not None else goal
        try:
            stream = self._query(prompt=prompt, options=self._build_options(cb))
            async for message in stream:
                result = await self._handle(message, adapter)
                if result is not None:
                    status = result
                    saw_result = True
        except Exception:
            # The SDK can raise while tearing down the stream *after* it already
            # delivered a terminal ResultMessage (observed live: "returned an error
            # result: success"). If we got a result, keep it; only a failure before
            # any result is a real abort (re-raised -> run_orchestration aborts).
            if not saw_result:
                raise
        return status

    async def _handle(self, message: Any, adapter: AgentAdapter) -> str | None:
        """Translate one SDK message into events; return terminal status or None."""
        name = type(message).__name__
        if name == "AssistantMessage":
            await self._handle_assistant(message, adapter)
            return None
        if name == "ResultMessage":
            cost = getattr(message, "total_cost_usd", None)
            if cost is not None:
                # Meter the cost (emits agent.usage + a one-shot budget.exceeded);
                # halt further fan-out if the ceiling is crossed (NFR12).
                if apply_usage(self._meter, adapter, _PARENT_ID, float(cost)):
                    self._halted = True
            return "failed" if getattr(message, "is_error", False) else "completed"
        return None

    async def _handle_assistant(self, message: Any, adapter: AgentAdapter) -> None:
        agent_id = getattr(message, "parent_tool_use_id", None) or _PARENT_ID
        for block in getattr(message, "content", None) or []:
            if type(block).__name__ != "ToolUseBlock":
                continue
            name = getattr(block, "name", "")
            inp: dict[str, Any] = getattr(block, "input", None) or {}
            if name in _SUBAGENT_TOOLS:
                if self._halted:
                    continue  # budget exceeded — no new fan-out
                await self._spawn_subagent(block, inp, agent_id, adapter)
            # Other tools are gated PRE-execution by the can_use_tool callback
            # (see _permission_cb); here we only translate subagent fan-out.
        usage = getattr(message, "usage", None)
        if isinstance(usage, dict):
            adapter.record_usage(
                agent_id,
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
            )

    async def _spawn_subagent(
        self, block: Any, inp: dict[str, Any], agent_id: str, adapter: AgentAdapter
    ) -> None:
        sub_id = getattr(block, "id", None) or "sub"
        role = inp.get("subagent_type") or inp.get("description") or "subagent"
        task = inp.get("prompt") or inp.get("description") or ""
        # Subagents spawned by the same lead form a named team (5.3 / FR6): the team
        # is the delegating agent's id, so team grouping mirrors the delegation tree.
        adapter.spawn(sub_id, role=str(role), parent_id=agent_id, team=agent_id)
        adapter.delegate(agent_id, task=str(task), to_agent=sub_id)
