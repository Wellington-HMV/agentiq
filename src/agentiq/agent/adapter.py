"""The single Claude Agent SDK seam.

This is the ONLY module that imports ``claude_agent_sdk``. It translates agent
lifecycle into domain events (the rest of the system depends on our event
vocabulary, never on SDK types) and scrubs secrets at the boundary before any
event is logged or published. The real SDK client wiring is done by orchestration
(story 1.7); here we provide the translation layer, the spawn/reuse registry, and
the scrubbed ``emit`` path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import ModuleType
from typing import Any

import claude_agent_sdk

from agentiq.agent.scrub import collect_secrets, scrub
from agentiq.core.isolation import Isolation
from agentiq.events.bus import EventBus
from agentiq.events.models import Event
from agentiq.events.writer import JsonlEventWriter


def sdk_module() -> ModuleType:
    """Return the Claude Agent SDK module (kept behind this seam)."""
    return claude_agent_sdk


@dataclass
class AgentContext:
    """One agent's identity and isolated context (its own context window)."""

    agent_id: str
    role: str | None = None
    parent_id: str | None = None
    team: str | None = None
    memory: dict[str, Any] = field(default_factory=dict)


class AgentAdapter:
    """Translates agent lifecycle into scrubbed domain events on log + bus."""

    def __init__(
        self,
        run_id: str,
        writer: JsonlEventWriter,
        bus: EventBus,
        secrets: set[str] | None = None,
        isolation: Isolation | None = None,
    ) -> None:
        self.run_id = run_id
        self._writer = writer
        self._bus = bus
        self._secrets = secrets if secrets is not None else collect_secrets()
        self._agents: dict[str, AgentContext] = {}
        # Per-agent workspace isolation (5.5); a writing strategy acquires a
        # workspace via `adapter.isolation`. None = writes go straight to project.
        self.isolation = isolation

    def emit(
        self,
        type: str,
        payload: dict[str, Any] | None = None,
        *,
        agent_id: str | None = None,
    ) -> Event:
        """Scrub, durably log (source of truth), then publish one event."""
        scrubbed = scrub(dict(payload or {}), self._secrets)
        event = self._writer.write(
            type, scrubbed, run_id=self.run_id, agent_id=agent_id
        )
        self._bus.publish(event)
        return event

    def spawn(
        self,
        agent_id: str,
        role: str | None = None,
        parent_id: str | None = None,
        team: str | None = None,
    ) -> AgentContext:
        """Register a new agent (emitting agent.spawned) or reuse an existing one."""
        existing = self._agents.get(agent_id)
        if existing is not None:
            return existing
        ctx = AgentContext(agent_id=agent_id, role=role, parent_id=parent_id, team=team)
        self._agents[agent_id] = ctx
        self.emit(
            "agent.spawned",
            {"role": role, "parent_id": parent_id, "team": team},
            agent_id=agent_id,
        )
        return ctx

    def get(self, agent_id: str) -> AgentContext | None:
        return self._agents.get(agent_id)

    def delegate(self, agent_id: str, task: str, to_agent: str) -> Event:
        return self.emit(
            "task.delegated", {"task": task, "to_agent": to_agent}, agent_id=agent_id
        )

    def vault_read(self, agent_id: str, ref: str) -> Event:
        return self.emit("vault.read", {"ref": ref}, agent_id=agent_id)

    def fail(
        self, agent_id: str, cause: str, last_good_seq: int | None = None
    ) -> Event:
        return self.emit(
            "agent.failed",
            {"cause": cause, "last_good_seq": last_good_seq},
            agent_id=agent_id,
        )

    def record_usage(
        self,
        agent_id: str,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> Event:
        return self.emit(
            "agent.usage",
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
            },
            agent_id=agent_id,
        )
