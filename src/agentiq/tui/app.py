"""The Textual app shell for agentiq.

Renders the spatial scene (2.6) and, when given a `ReplayController`, an
interactive transport bar (2.7): the key bindings drive the controller and the
widgets re-render. The TUI holds no orchestration logic — it only calls
controller methods and renders `SceneState` (NFR17).
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from agentiq.replay.scene_state import SceneState
from agentiq.replay.transport import ReplayController
from agentiq.tui.inspect import InspectOverlay, render_inspect
from agentiq.tui.scene import SceneWidget
from agentiq.tui.scene_view import ViewState
from agentiq.tui.transport_bar import TransportBar

_TICK_SECONDS = 0.3
_ANIM_SECONDS = 0.5  # creature idle/active animation cadence (6.4)


class WcsApp(App[None]):
    """The root agentiq TUI application."""

    CSS_PATH = "scene.tcss"
    BINDINGS = [
        Binding("space", "toggle_play", "Play/Pause"),
        Binding("right", "step_forward", "Step"),
        Binding("left", "step_back", "Back"),
        Binding("n", "next_decision", "Next decision"),
        Binding("p", "prev_decision", "Prev decision"),
        Binding("f", "next_failure", "Failure"),
        Binding("home", "to_start", "Start"),
        Binding("end", "to_end", "End"),
        Binding("enter", "inspect", "Inspect"),
        Binding("i", "inspect", "Inspect"),
        Binding("z", "zoom", "Zoom"),
        Binding("g", "group", "Team view"),
        Binding("t", "tree", "Org-tree"),
        Binding("o", "focus_agent", "Focus"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        controller: ReplayController | None = None,
        state: SceneState | None = None,
        app_title: str = "AGENTIQ",
        *,
        ascii_only: bool = False,
        reduced_motion: bool = False,
    ) -> None:
        super().__init__()
        self._app_title = app_title
        self._controller = controller
        self._state = state or (
            controller.current_state if controller is not None else None
        )
        self._ascii_only = ascii_only
        self._reduced_motion = reduced_motion
        self._view = ViewState()
        self._scene: SceneWidget | None = None
        self._bar: TransportBar | None = None
        self._timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        self._scene = SceneWidget(
            self._state, ascii_only=self._ascii_only, view=self._view
        )
        yield self._scene
        if self._controller is not None:
            self._bar = TransportBar(ascii_only=self._ascii_only)
            yield self._bar
        yield Footer()

    def on_mount(self) -> None:
        self.title = self._app_title
        if self._controller is not None:
            self._refresh()
        self.start_creature_animation()

    def start_creature_animation(self) -> None:
        """Bob the creatures on an interval (6.4); silent under reduced motion."""
        if self._reduced_motion:
            return
        self.set_interval(_ANIM_SECONDS, self._tick_creatures)

    def _tick_creatures(self) -> None:
        if self._scene is not None:
            self._scene.tick_animation()

    # --- refresh ------------------------------------------------------------
    def _refresh(self) -> None:
        if self._controller is None:
            return
        if self._scene is not None:
            self._scene.update_scene(self._controller.current_state)
        if self._bar is not None:
            self._bar.update_bar(self._controller)

    # --- transport actions (no-ops without a controller) --------------------
    def action_step_forward(self) -> None:
        if self._controller:
            self._controller.step_forward()
            self._refresh()

    def action_step_back(self) -> None:
        if self._controller:
            self._controller.step_backward()
            self._refresh()

    def action_next_decision(self) -> None:
        if self._controller:
            self._controller.next_decision()
            self._refresh()

    def action_prev_decision(self) -> None:
        if self._controller:
            self._controller.prev_decision()
            self._refresh()

    def action_next_failure(self) -> None:
        if self._controller:
            self._controller.next_failure()
            self._refresh()

    def action_to_start(self) -> None:
        if self._controller:
            self._controller.to_start()
            self._refresh()

    def action_to_end(self) -> None:
        if self._controller:
            self._controller.to_end()
            self._refresh()

    def action_inspect(self) -> None:
        if self._controller:
            self.push_screen(InspectOverlay(render_inspect(self._controller)))

    # --- view modes (6.1: zoom / group-by-team / focus-follow) --------------
    def _current_scene_state(self) -> SceneState | None:
        if self._controller is not None:
            return self._controller.current_state
        return self._scene.state if self._scene is not None else None

    def _focus_target(self) -> str | None:
        """The agent to focus-follow: the current event's, else an active one."""
        if self._controller is not None and self._controller.current_event is not None:
            if self._controller.current_event.agent_id:
                return self._controller.current_event.agent_id
        state = self._current_scene_state()
        if state is None or not state.agents:
            return None
        active = [a for a in state.agents.values() if a.status not in ("idle", "done")]
        pool = active or list(state.agents.values())
        return sorted(a.agent_id for a in pool)[0]

    def _apply_view(self) -> None:
        if self._scene is not None:
            self._scene.set_view(self._view)

    def action_zoom(self) -> None:
        self._view = self._view.cycle_zoom()
        self._apply_view()

    def action_group(self) -> None:
        self._view = self._view.toggle_team()
        self._apply_view()

    def action_tree(self) -> None:
        self._view = self._view.toggle_tree()
        self._apply_view()

    def action_focus_agent(self) -> None:
        self._view = self._view.focus_on(self._focus_target())
        self._apply_view()

    def action_toggle_play(self) -> None:
        if not self._controller:
            return
        if self._reduced_motion:
            # No timer-driven animation; advance a single step instead.
            self._controller.step_forward()
            self._refresh()
            return
        self._controller.toggle_play()
        if self._controller.playing:
            self._timer = self.set_interval(_TICK_SECONDS, self._tick)
        elif self._timer is not None:
            self._timer.stop()
            self._timer = None

    def _tick(self) -> None:
        if not self._controller:
            return
        self._controller.step_forward()
        self._refresh()
        if self._controller.at_end:
            self._controller.pause()
            if self._timer is not None:
                self._timer.stop()
                self._timer = None
