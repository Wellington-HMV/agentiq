"""Compare two runs (story 6.3 / FR30).

A pure projection that pulls the comparable facts out of each run's event log —
outcome (status), cost, fan-out, and the ordered decisions — and renders them side
by side, flagging the differences. Like every projection here it is derived purely
from events (the single source of truth); nothing is read from mutable metadata.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from agentiq.events.models import Event
from agentiq.replay.summary import build_summary


@dataclass(frozen=True)
class DecisionRecord:
    prompt: str
    choice: str
    resolved_by: str


@dataclass(frozen=True)
class RunFacts:
    """The comparable facts of one run, projected from its log."""

    run_id: str | None
    status: str
    cost_usd: float
    agents_spawned: int
    decisions: list[DecisionRecord] = field(default_factory=list)


@dataclass(frozen=True)
class RunComparison:
    a: RunFacts
    b: RunFacts


def facts(events: Iterable[Event]) -> RunFacts:
    """Project the comparable facts (reuses the summary for the aggregates)."""
    events = list(events)
    summary = build_summary(events)
    pending: list[str] = []
    decisions: list[DecisionRecord] = []
    for event in events:
        if event.type == "decision.pending":
            pending.append(str(event.payload.get("prompt", "")))
        elif event.type == "decision.resolved":
            prompt = pending.pop(0) if pending else ""  # pair pending->resolved FIFO
            decisions.append(
                DecisionRecord(
                    prompt=prompt,
                    choice=str(event.payload.get("choice", "")),
                    resolved_by=str(event.payload.get("resolved_by", "")),
                )
            )
    return RunFacts(
        run_id=summary.run_id,
        status=summary.status,
        cost_usd=summary.cost_usd,
        agents_spawned=summary.agents_spawned,
        decisions=decisions,
    )


_COL = 24
_DIFF = "  != "  # ascii-safe difference marker
_SAME = ""


def _row(label: str, va: object, vb: object, *, differ: bool) -> str:
    mark = _DIFF if differ else _SAME
    return f"{label:<12}{str(va):<{_COL}}{str(vb):<{_COL}}{mark}"


def render_comparison(
    comp: RunComparison, *, label_a: str = "A", label_b: str = "B"
) -> str:
    """Render a side-by-side comparison, flagging differing fields with `!=`."""
    a, b = comp.a, comp.b
    lines = [
        _row(
            "",
            f"{label_a}: {a.run_id or '?'}",
            f"{label_b}: {b.run_id or '?'}",
            differ=False,
        ),
        "-" * (12 + _COL * 2),
        _row("status", a.status, b.status, differ=a.status != b.status),
        _row(
            "cost_usd",
            f"{a.cost_usd:.4f}",
            f"{b.cost_usd:.4f}",
            differ=abs(a.cost_usd - b.cost_usd) > 1e-9,
        ),
        _row(
            "agents",
            a.agents_spawned,
            b.agents_spawned,
            differ=a.agents_spawned != b.agents_spawned,
        ),
        _row(
            "decisions",
            len(a.decisions),
            len(b.decisions),
            differ=len(a.decisions) != len(b.decisions),
        ),
        "",
        "decisions:",
    ]
    n = max(len(a.decisions), len(b.decisions))
    if n == 0:
        lines.append("  (none)")
    for i in range(n):
        da = a.decisions[i] if i < len(a.decisions) else None
        db = b.decisions[i] if i < len(b.decisions) else None
        ca = f"{da.choice}({da.resolved_by})" if da else "—"
        cb = f"{db.choice}({db.resolved_by})" if db else "—"
        present = da if da is not None else db
        prompt = (present.prompt if present is not None else "")[:18]
        mark = _DIFF if ca != cb else _SAME
        lines.append(f"  {i + 1}. {prompt:<20}{ca:<{_COL}}{cb:<{_COL}}{mark}")
    return "\n".join(lines)
