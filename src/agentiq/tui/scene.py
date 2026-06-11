"""The spatial scene — the visible heart of agentiq.

`render_scene` is a PURE function of a `SceneState` (which comes from the single
shared reducer), so the scene always matches the timeline/replay for the same seq
(NFR5). `SceneWidget` is a dumb renderer that holds no orchestration logic
(NFR17). Meaning is carried by zone + status + glyph, never colour alone (UX-DR2).
Rich motion/animation is Growth; this MVP slice is a clear static snapshot.
"""

from __future__ import annotations

from textual.widgets import Static

from agentiq.replay.scene_state import AgentState, SceneState, Zone
from agentiq.tui.creatures import creature

# Fixed zones, always shown (the stable mental map / UX-DR1).
_ZONES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("LIBRARY", (Zone.LIBRARY,)),
    ("DESKS", (Zone.DESK, Zone.FLOOR)),
    ("SUBAGENTS", (Zone.PATH, Zone.SUBAGENTS)),
)


def _creature(agent: AgentState, *, ascii_only: bool, frame: int) -> str:
    # Personality face (6.4) leads with the status glyph, then the agent id +
    # status text — charm never hides real state (UX-DR2).
    face = creature(agent, frame, ascii_only=ascii_only)
    return f"{face} {agent.agent_id}({agent.status})"


def render_scene(state: SceneState, *, ascii_only: bool = False, frame: int = 0) -> str:
    """Render a SceneState as a deterministic multi-line floor-plan.

    ``frame`` advances the creatures' idle/active animation (6.4); the same state
    at the same frame always renders identically (deterministic).
    """
    lines: list[str] = [
        f"run: {state.run_status}",
        f"> {state.caption}" if state.caption else ">",
        "",
    ]
    for label, zones in _ZONES:
        in_zone = [a for a in state.agents.values() if a.zone in zones]
        in_zone.sort(key=lambda a: a.agent_id)
        creatures = "  ".join(
            _creature(a, ascii_only=ascii_only, frame=frame) for a in in_zone
        )
        lines.append(f"{label:<10} {creatures}")
    if state.paths:
        edges = ", ".join(f"{src}->{dst}" for src, dst in state.paths)
        lines.append(f"{'PATHS':<10} {edges}")
    return "\n".join(lines)


class SceneWidget(Static):
    """Renders the current SceneState as the spatial office floor-plan."""

    def __init__(
        self,
        state: SceneState | None = None,
        *,
        ascii_only: bool = False,
        view: object | None = None,
    ) -> None:
        super().__init__(id="scene")
        self._state = state
        self._ascii_only = ascii_only
        self._frame = 0  # creature animation frame (6.4)
        # ViewState (6.1) — kept as object to avoid a tui->tui import cycle at
        # module load; set/None means the plain floor-plan.
        self._view = view

    @property
    def state(self) -> SceneState | None:
        return self._state

    def on_mount(self) -> None:
        if self._state is not None:
            self.update_scene(self._state)

    def set_view(self, view: object) -> None:
        """Switch view mode/zoom (6.1) and re-render the current state."""
        self._view = view
        if self._state is not None:
            self.update_scene(self._state)

    def tick_animation(self) -> None:
        """Advance the creature animation frame (6.4) and re-render."""
        self._frame += 1
        if self._state is not None:
            self.update_scene(self._state)

    def update_scene(self, state: SceneState) -> None:
        self._state = state
        if self._view is None:
            self.update(
                render_scene(state, ascii_only=self._ascii_only, frame=self._frame)
            )
            return
        from agentiq.tui.scene_view import ViewState, render_view

        assert isinstance(self._view, ViewState)
        self.update(
            render_view(
                state, self._view, ascii_only=self._ascii_only, frame=self._frame
            )
        )
