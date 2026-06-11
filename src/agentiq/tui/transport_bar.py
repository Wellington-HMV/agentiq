"""The transport bar — playhead, markers, and position counter (UX-DR3).

`render_transport` is a pure function of a `ReplayController`; `TransportBar` is a
dumb Static that renders it. Key bindings (in the app) drive the controller; this
widget only shows where the playhead is and where the decisions/failures lie.
"""

from __future__ import annotations

from textual.widgets import Static

from agentiq.replay.transport import ReplayController
from agentiq.tui.tokens import glyph


def render_transport(controller: ReplayController, *, ascii_only: bool = False) -> str:
    """Render a one-line transport track with markers + playhead + counter."""
    total = controller.event_count
    if total == 0:
        return "[ ] 0/0"

    decisions = set(controller.decision_indices)
    failures = set(controller.failure_indices)
    pos = controller.position
    head = glyph("playhead", ascii_only=ascii_only)
    dec = glyph("decision", ascii_only=ascii_only)
    fail = glyph("failure", ascii_only=ascii_only)

    cells: list[str] = []
    for i in range(total):
        if i == pos:
            cells.append(head)
        elif i in failures:
            cells.append(fail)
        elif i in decisions:
            cells.append(dec)
        else:
            cells.append(".")
    track = "".join(cells)
    caption = controller.current_state.caption
    return f"[{track}] {pos + 1}/{total}  {caption}"


class TransportBar(Static):
    """Renders the replay transport track for the current controller position."""

    def __init__(self, *, ascii_only: bool = False) -> None:
        super().__init__(id="transport")
        self._ascii_only = ascii_only

    def update_bar(self, controller: ReplayController) -> None:
        self.update(render_transport(controller, ascii_only=self._ascii_only))
