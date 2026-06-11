"""Cost metering and hard ceiling.

`CostMeter` is a pure aggregator (per-agent + per-run totals, ceiling check).
`apply_usage` is the enforcement point: it logs `agent.usage`, records the cost,
emits a single `budget.exceeded` on the crossing, and returns whether the ceiling
is now exceeded so the caller halts new fan-out (FR32 / NFR12). The deterministic
strategy emits no usage; the real Claude-SDK strategy reports it through this path.
"""

from __future__ import annotations

from agentiq.agent.adapter import AgentAdapter


class CostMeter:
    """Aggregates token cost per agent and per run, with a hard ceiling."""

    def __init__(self, ceiling_usd: float | None = None) -> None:
        self.ceiling_usd = ceiling_usd
        self.total = 0.0
        self._per_agent: dict[str, float] = {}
        self._breach_emitted = False

    @property
    def exceeded(self) -> bool:
        return self.ceiling_usd is not None and self.total >= self.ceiling_usd

    def per_agent(self, agent_id: str) -> float:
        return self._per_agent.get(agent_id, 0.0)

    def record(self, agent_id: str, cost_usd: float) -> None:
        self.total += cost_usd
        self._per_agent[agent_id] = self._per_agent.get(agent_id, 0.0) + cost_usd

    def take(self, agent_id: str, cost_usd: float) -> bool:
        """Record cost; True only on the record that first crosses the ceiling."""
        was = self.exceeded
        self.record(agent_id, cost_usd)
        return self.exceeded and not was


def apply_usage(
    meter: CostMeter,
    adapter: AgentAdapter,
    agent_id: str,
    cost_usd: float,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> bool:
    """Log usage, meter it, emit `budget.exceeded` once on the crossing.

    Returns ``meter.exceeded`` so the caller can halt new fan-out.
    """
    adapter.record_usage(
        agent_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
    )
    crossed = meter.take(agent_id, cost_usd)
    if crossed and not meter._breach_emitted:
        adapter.emit(
            "budget.exceeded",
            {"spent_usd": meter.total, "ceiling_usd": meter.ceiling_usd},
        )
        meter._breach_emitted = True
    return meter.exceeded
