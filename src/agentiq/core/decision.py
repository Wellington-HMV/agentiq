"""Decision points: pending -> await resolver -> resolved.

The decision is an awaitable (FR22): `request_decision` emits the pending event,
awaits a `Resolver`, then emits the resolution. A resolver that can't decide
raises `DecisionUnresolved`, which the orchestrator turns into a terminal abort —
so headless runs never hang (NFR8). The full policy engine (4.2) and interactive
option/default resolution (4.3) are resolvers that plug into this same shape.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from agentiq.agent.adapter import AgentAdapter


class DecisionUnresolved(Exception):
    """Raised when a decision cannot be resolved (no policy, no default, no input)."""


@dataclass(frozen=True)
class DecisionRequest:
    agent_id: str
    prompt: str
    options: list[str] = field(default_factory=list)
    default: str | None = None
    kind: str = "general"  # category a policy rule matches on


class Resolver(Protocol):
    """Resolves a decision request into (choice, resolved_by) or raises."""

    async def resolve(self, request: DecisionRequest) -> tuple[str, str]: ...


class DefaultResolver:
    """Headless default-or-fail resolver: the default, else DecisionUnresolved."""

    async def resolve(self, request: DecisionRequest) -> tuple[str, str]:
        if request.default is not None:
            return request.default, "default"
        raise DecisionUnresolved(request.prompt)


async def request_decision(
    adapter: AgentAdapter, request: DecisionRequest, resolver: Resolver
) -> str:
    """Emit pending, await the resolver, emit resolved; return the chosen value."""
    adapter.emit(
        "decision.pending",
        {
            "prompt": request.prompt,
            "options": list(request.options),
            "default": request.default,
        },
        agent_id=request.agent_id,
    )
    choice, resolved_by = await resolver.resolve(request)
    adapter.emit(
        "decision.resolved",
        {"choice": choice, "resolved_by": resolved_by},
        agent_id=request.agent_id,
    )
    return choice


# --- human resolution (story 4.3) ------------------------------------------


def format_decision_prompt(request: DecisionRequest) -> str:
    """Render the prompt with numbered options and the default marked."""
    lines = [request.prompt]
    for i, option in enumerate(request.options, start=1):
        mark = "  (default)" if option == request.default else ""
        lines.append(f"  {i}. {option}{mark}")
    if request.default and request.default not in request.options:
        lines.append(f"  [default: {request.default}]")
    lines.append("> ")
    return "\n".join(lines)


def parse_choice(request: DecisionRequest, raw: str) -> str:
    """Resolve a raw input line to a chosen option (Enter = default)."""
    raw = raw.strip()
    if raw == "":
        if request.default is not None:
            return request.default
        raise DecisionUnresolved(f"no input and no default for: {request.prompt}")
    if raw.isdigit():
        index = int(raw) - 1
        if 0 <= index < len(request.options):
            return request.options[index]
        raise DecisionUnresolved(f"option {raw} out of range")
    if raw in request.options:
        return raw
    raise DecisionUnresolved(f"invalid choice {raw!r}")


class PromptResolver:
    """Human resolver: prompts (numbered options + default) and reads one line."""

    def __init__(self, input_fn: Callable[[str], str] = input) -> None:
        self._input = input_fn

    async def resolve(self, request: DecisionRequest) -> tuple[str, str]:
        raw = self._input(format_decision_prompt(request))
        return parse_choice(request, raw), "human"
