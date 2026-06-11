"""On-screen decision notes (live) — story 5.2.

A pending human decision surfaces as a `DecisionNote` modal over the live scene.
Because the orchestration runs in a Textual worker that `await`s the resolver, the
scene pauses for free while the note is open and resumes when it dismisses (FR26).

`DecisionNote` and `TuiDecisionResolver` reuse `format_decision_prompt`/
`parse_choice` from `core.decision`, so the live overlay and the headless prompt
share one render/parse. The resolver plugs into the same `Resolver` seam as
`PromptResolver`/`DefaultResolver` (FR22).
"""

from __future__ import annotations

from typing import Any

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static

from agentiq.core.decision import (
    DecisionRequest,
    DecisionUnresolved,
    format_decision_prompt,
    parse_choice,
)


class DecisionNote(ModalScreen[str]):
    """Modal note for a pending decision. Digit picks an option, Enter the default."""

    BINDINGS = [Binding("enter", "accept_default", "Default")]

    def __init__(self, request: DecisionRequest) -> None:
        super().__init__()
        self._request = request
        self.text = format_decision_prompt(request)  # rendered prompt + options

    def compose(self) -> ComposeResult:
        yield Static(self.text, id="decision-note")

    def on_key(self, event: events.Key) -> None:
        if event.key.isdigit():
            event.stop()
            try:
                self.dismiss(parse_choice(self._request, event.key))
            except DecisionUnresolved:
                pass  # out-of-range digit — keep the note open (AC #3)

    def action_accept_default(self) -> None:
        try:
            self.dismiss(parse_choice(self._request, ""))
        except DecisionUnresolved:
            pass  # no default — Enter does nothing, note stays open (AC #3)


class TuiDecisionResolver:
    """`Resolver` that shows a `DecisionNote` and awaits the user's pick."""

    def __init__(self, app: App[Any]) -> None:
        self._app = app

    async def resolve(self, request: DecisionRequest) -> tuple[str, str]:
        choice = await self._app.push_screen_wait(DecisionNote(request))
        return choice, "human"
