"""Live watch mode — render the scene as a run executes (Growth, story 5.1).

The headless core publishes to a shared `EventBus` (unchanged); this app is a pure
subscriber that folds the same events through the single reducer (2.1) and
refreshes the scene. The render never back-pressures the core — publish is
non-blocking (1.3 / NFR2).
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from agentiq.config.settings import AutonomySection
from agentiq.core.orchestrator import (
    DeterministicStrategy,
    OrchestrationStrategy,
    run_orchestration,
)
from agentiq.events.bus import EventBus, Subscription
from agentiq.policy.policy import PolicyResolver
from agentiq.replay.reducer import reduce
from agentiq.replay.scene_state import initial_state
from agentiq.tui.app import WcsApp  # reuse the shell base
from agentiq.tui.decision_note import TuiDecisionResolver
from agentiq.tui.scene import SceneWidget

_TERMINAL = {"run.completed", "run.aborted"}


class LiveWatchApp(WcsApp):
    """Runs an orchestration and renders its events live."""

    BINDINGS = [
        Binding("z", "zoom", "Zoom"),
        Binding("g", "group", "Team view"),
        Binding("t", "tree", "Org-tree"),
        Binding("o", "focus_agent", "Focus"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        goal: str,
        project: str | Path,
        *,
        strategy: OrchestrationStrategy | None = None,
        runs_root: str | Path | None = None,
        autonomy: AutonomySection | None = None,
        ascii_only: bool = False,
        app_title: str = "AGENTIQ (live)",
    ) -> None:
        super().__init__(app_title=app_title, ascii_only=ascii_only)
        self._goal = goal
        self._project = project
        self._strategy = strategy or DeterministicStrategy()
        self._runs_root = runs_root
        self._autonomy = autonomy if autonomy is not None else AutonomySection()
        self._bus = EventBus()
        self._sub: Subscription | None = None
        self._live_state = initial_state()

    def compose(self) -> ComposeResult:
        yield Header()
        self._scene = SceneWidget(
            self._live_state, ascii_only=self._ascii_only, view=self._view
        )
        yield self._scene
        yield Footer()

    def on_mount(self) -> None:
        self.title = self._app_title
        self._sub = self._bus.subscribe()  # subscribe before publishing starts
        self.run_worker(self._consume(), exclusive=False)
        self.run_worker(self._orchestrate(), exclusive=False)
        self.start_creature_animation()  # 6.4 idle/active bob

    async def _orchestrate(self) -> None:
        # The autonomy policy applies to live decisions (FR25): allow/deny
        # auto-resolve; `ask` falls through to a DecisionNote, which blocks this
        # worker so the scene pauses until the user answers (FR26).
        resolver = PolicyResolver(self._autonomy, TuiDecisionResolver(self))
        await run_orchestration(
            self._goal,
            self._project,
            strategy=self._strategy,
            runs_root=self._runs_root,
            bus=self._bus,
            resolver=resolver,
        )

    async def _consume(self) -> None:
        assert self._sub is not None
        while True:
            event = await self._sub.get()
            self._live_state = reduce(self._live_state, event)
            if self._scene is not None:
                self._scene.update_scene(self._live_state)
            if event.type in _TERMINAL:
                break
