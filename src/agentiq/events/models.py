"""Event model — the single contract every component couples to (event sourcing).

A run's event log IS the database. Each event is one JSON line with a small
envelope (`seq`, `ts`, `run_id`, `agent_id`, `type`, `payload`). `seq` is the only
ordering authority (NFR5); `ts` is informational. Payloads are typed per event
`type` via the ``EVENT_PAYLOADS`` registry — the single place new event types are
added. The contract is additive-only: payload models ignore unknown keys on read
so older code survives newer logs.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class _Payload(BaseModel):
    """Base for all event payloads. Tolerates unknown keys on read (forward-compat)."""

    model_config = ConfigDict(extra="ignore")


# --- Payload models (one per event type) ------------------------------------
# Keep fields minimal and additive; later stories extend these without breaking
# old logs.


class RunStartedPayload(_Payload):
    goal: str
    project: str


class RunCompletedPayload(_Payload):
    status: str  # e.g. "completed"


class RunAbortedPayload(_Payload):
    reason: str


class AgentSpawnedPayload(_Payload):
    role: str | None = None
    parent_id: str | None = None
    team: str | None = None  # named team this agent belongs to (FR6)


class TaskDelegatedPayload(_Payload):
    task: str
    to_agent: str


class VaultReadPayload(_Payload):
    ref: str


class DecisionPendingPayload(_Payload):
    prompt: str
    options: list[str] = []
    default: str | None = None


class DecisionResolvedPayload(_Payload):
    choice: str
    resolved_by: str  # "policy" | "human" | "default"


class AgentFailedPayload(_Payload):
    cause: str
    last_good_seq: int | None = None


class BudgetExceededPayload(_Payload):
    spent_usd: float
    ceiling_usd: float


class AgentUsagePayload(_Payload):
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


# --- Registry: the single place event types are declared ---------------------
# Type strings are lower.dotted: <entity>.<past-tense> for facts, <entity>.pending
# for an awaited request.
EVENT_PAYLOADS: dict[str, type[_Payload]] = {
    "run.started": RunStartedPayload,
    "run.completed": RunCompletedPayload,
    "run.aborted": RunAbortedPayload,
    "agent.spawned": AgentSpawnedPayload,
    "task.delegated": TaskDelegatedPayload,
    "vault.read": VaultReadPayload,
    "decision.pending": DecisionPendingPayload,
    "decision.resolved": DecisionResolvedPayload,
    "agent.failed": AgentFailedPayload,
    "agent.usage": AgentUsagePayload,
    "budget.exceeded": BudgetExceededPayload,
}


class Event(BaseModel):
    """One orchestration event — one line in the JSONL log."""

    model_config = ConfigDict(extra="forbid")

    seq: int
    ts: str  # ISO-8601 UTC, informational only
    run_id: str
    agent_id: str | None = None
    type: str  # lower.dotted; must be a key in EVENT_PAYLOADS
    payload: dict[str, Any] = {}

    @model_validator(mode="after")
    def _validate_type_and_payload(self) -> Event:
        payload_model = EVENT_PAYLOADS.get(self.type)
        if payload_model is None:
            raise ValueError(f"unknown event type: {self.type!r}")
        # Validate payload against its typed model (extra keys ignored).
        # We keep payload as a dict for clean, lossless JSON round-trips.
        payload_model.model_validate(self.payload)
        return self

    def to_json_line(self) -> str:
        """Serialize to a single-line JSON string (no trailing newline)."""
        return self.model_dump_json()
