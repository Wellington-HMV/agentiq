"""Action safety — scope confinement + confirm-before-irreversible.

The guard is the enforcement point an agent's tool actions pass through. File/
shell actions are confined to the bound project + vault paths (NFR10); a denied
operation kind is refused; irreversible or outward-facing actions require an
explicit decision (FR34/NFR11) reusing the decision mechanism (a `confirm` becomes
a `decision.pending`/`resolved` pair).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from agentiq.agent.adapter import AgentAdapter
from agentiq.core.decision import DecisionRequest, Resolver, request_decision


class SafetyDenied(Exception):
    """Raised when an action is refused (out of scope or a denied operation)."""


@dataclass(frozen=True)
class AgentAction:
    kind: str
    path: str | None = None
    irreversible: bool = False
    outward: bool = False


class SafetyGuard:
    """Confines actions to allowed roots and flags irreversible/outward ones."""

    def __init__(
        self,
        project_root: str | Path,
        vault_paths: Iterable[str | Path] = (),
        denied_ops: Iterable[str] = (),
    ) -> None:
        self._roots = [Path(project_root).resolve()] + [
            Path(p).resolve() for p in vault_paths
        ]
        self._denied_ops = set(denied_ops)

    @property
    def denied_ops(self) -> set[str]:
        """Operation kinds refused outright (a hard, always-enforced block)."""
        return set(self._denied_ops)

    def in_scope(self, path: str | Path) -> bool:
        resolved = Path(path).resolve()
        return any(resolved.is_relative_to(root) for root in self._roots)

    def evaluate(self, action: AgentAction) -> str:
        if action.kind in self._denied_ops:
            return "deny"
        if action.path is not None and not self.in_scope(action.path):
            return "deny"
        if action.irreversible or action.outward:
            return "confirm"
        return "allow"


async def authorize(
    guard: SafetyGuard,
    action: AgentAction,
    *,
    adapter: AgentAdapter,
    resolver: Resolver,
    agent_id: str,
) -> bool:
    """Return whether the action may proceed; raise SafetyDenied if refused."""
    verdict = guard.evaluate(action)
    if verdict == "allow":
        return True
    if verdict == "deny":
        raise SafetyDenied(f"{action.kind} {action.path or ''}".strip())
    # confirm: block pending an explicit decision.
    target = f"{action.kind} {action.path or ''}".strip()
    request = DecisionRequest(
        agent_id=agent_id,
        prompt=f"confirm irreversible action: {target}",
        options=["proceed", "cancel"],
        default=None,
        kind="irreversible",
    )
    return await request_decision(adapter, request, resolver) == "proceed"
