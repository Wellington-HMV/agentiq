"""Event marker classification, shared by the timeline (2.2) and transport (2.4).

Keeping these predicates in one place ensures the textual ``D``/``F`` markers and
the jump-to-marker targets never drift apart.
"""

from __future__ import annotations


def is_decision(event_type: str) -> bool:
    """A decision marker (◆): any ``decision.*`` event."""
    return event_type.startswith("decision.")


def is_failure(event_type: str) -> bool:
    """A failure marker (✕): an agent failure or an aborted run."""
    return event_type in ("agent.failed", "run.aborted")
