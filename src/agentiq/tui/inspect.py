"""Inspect overlay — drill into the current event/agent without leaving the scene.

`render_inspect` is a pure function of the controller's current state; the
`InspectOverlay` modal just shows it and dims the scene beneath (context
preserved). No data fetching, no orchestration logic (NFR17).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static

from agentiq.replay.transport import ReplayController


def render_inspect(controller: ReplayController) -> str:
    """Detail view of the current event plus an agents summary."""
    event = controller.current_event
    lines: list[str] = []
    if event is None:
        lines.append("(no event)")
    else:
        lines.append(f"Event #{event.seq}  {event.type}")
        lines.append(f"agent: {event.agent_id or '-'}    ts: {event.ts}")
        lines.append("")
        lines.append("payload:")
        if event.payload:
            for key, value in event.payload.items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append("  (empty)")

    state = controller.current_state
    lines.append("")
    lines.append("--- agents ---")
    if state.agents:
        for agent in sorted(state.agents.values(), key=lambda a: a.agent_id):
            role = agent.role or "-"
            lines.append(
                f"  {agent.agent_id}  role={role}  status={agent.status}  "
                f"zone={agent.zone}"
            )
    else:
        lines.append("  (none)")
    return "\n".join(lines)


class InspectOverlay(ModalScreen[None]):
    """Modal drill-in for the focused event/agent. Esc closes."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("i", "dismiss", "Close"),
    ]

    def __init__(self, text: str) -> None:
        super().__init__()
        self._text = text

    def compose(self) -> ComposeResult:
        yield Static(self._text, id="inspect")
