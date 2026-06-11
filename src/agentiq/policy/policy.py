"""Autonomy policy engine — a `Resolver` that maps a decision to an action.

Plugs into `request_decision` (story 4.1) unchanged: it resolves the action for a
decision's `kind` from config rules (first match, else the default action).
`allow`/`deny` auto-resolve (`resolved_by="policy"`); `ask` routes to an injected
human resolver, or raises `DecisionUnresolved` in headless (NFR8 — the run aborts,
never hangs).
"""

from __future__ import annotations

from agentiq.config.settings import AutonomySection
from agentiq.core.decision import DecisionRequest, DecisionUnresolved, Resolver


class PolicyResolver:
    """Resolves decisions from declarative autonomy rules."""

    def __init__(
        self, autonomy: AutonomySection, ask_resolver: Resolver | None = None
    ) -> None:
        self._autonomy = autonomy
        self._ask_resolver = ask_resolver

    def _action_for(self, kind: str) -> str:
        for rule in self._autonomy.rules:
            if rule.kind == kind:
                return rule.action
        return self._autonomy.default

    async def resolve(self, request: DecisionRequest) -> tuple[str, str]:
        action = self._action_for(request.kind)
        if action == "allow":
            choice = request.default or (
                request.options[0] if request.options else "allow"
            )
            return choice, "policy"
        if action == "deny":
            return "deny", "policy"
        # action == "ask": a human must decide.
        if self._ask_resolver is not None:
            return await self._ask_resolver.resolve(request)
        raise DecisionUnresolved(request.prompt)
