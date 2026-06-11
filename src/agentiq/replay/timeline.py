"""Plain textual timeline replay — the universal, pipeable fallback view.

Folds a run's events through the shared reducer (story 2.1) and emits one ASCII
line per event, so any run can be read with no TTY and piped anywhere (NFR7).
Decision and failure events are marked inline.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from agentiq.events.models import Event
from agentiq.replay.markers import is_decision, is_failure
from agentiq.replay.reducer import reduce
from agentiq.replay.scene_state import initial_state


def _marker(event_type: str) -> str:
    if is_decision(event_type):
        return "D"
    if is_failure(event_type):
        return "F"
    return "."


def iter_timeline_lines(events: Iterable[Event]) -> Iterator[str]:
    """Yield one ASCII timeline line per event, in seq order."""
    state = initial_state()
    for event in events:
        state = reduce(state, event)
        agent = event.agent_id or "-"
        yield (
            f"{event.seq:>4} {_marker(event.type)} {event.ts} "
            f"{agent:<8} {event.type:<16} {state.caption}"
        )
