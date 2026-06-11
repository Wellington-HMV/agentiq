"""Legibility-at-scale view modes for the scene (story 6.1 / FR21, NFR14).

The scene crowds once a run fans out to many agents. `ViewState` is a small,
immutable view configuration the user drives from the keyboard, and `render_view`
is a PURE function `(SceneState, ViewState) -> str` that keeps the picture legible:

- **zoom** (``density``): ``auto`` shows the full floor-plan until the run crowds
  (>= ``CROWD_THRESHOLD`` agents), then compacts to per-zone/per-status counts;
  ``full`` forces detail; ``compact`` forces counts.
- **group by team** (``mode == "team"``): agents bucketed under their team name.
- **focus-follow** (``mode == "focus"``): only the focused agent plus its parent
  and children, so one lineage stays readable amid many.

All output is deterministic (sorted), matches the single reducer's `SceneState`,
and carries meaning by zone/status/glyph — never colour alone (UX-DR2).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from agentiq.replay.scene_state import SceneState
from agentiq.tui.scene import render_scene
from agentiq.tui.tokens import glyph

CROWD_THRESHOLD = 10  # NFR14: at/above this many agents, `auto` density compacts

_DENSITIES = ("auto", "full", "compact")


@dataclass(frozen=True)
class ViewState:
    """How the scene is currently being viewed (user-driven, immutable)."""

    mode: str = "floor"  # "floor" | "team" | "tree" | "focus"
    density: str = "auto"  # "auto" | "full" | "compact"
    focus: str | None = None

    def cycle_zoom(self) -> ViewState:
        nxt = _DENSITIES[(_DENSITIES.index(self.density) + 1) % len(_DENSITIES)]
        return replace(self, density=nxt)

    def toggle_team(self) -> ViewState:
        return replace(self, mode="floor" if self.mode == "team" else "team")

    def toggle_tree(self) -> ViewState:
        return replace(self, mode="floor" if self.mode == "tree" else "tree")

    def focus_on(self, agent_id: str | None) -> ViewState:
        # Toggle off if re-focusing the same agent or given nothing.
        if agent_id is None or (self.mode == "focus" and self.focus == agent_id):
            return replace(self, mode="floor", focus=None)
        return replace(self, mode="focus", focus=agent_id)


def _is_compact(state: SceneState, view: ViewState) -> bool:
    if view.density == "compact":
        return True
    if view.density == "full":
        return False
    return len(state.agents) >= CROWD_THRESHOLD  # auto


def _header(state: SceneState) -> list[str]:
    return [
        f"run: {state.run_status}",
        f"> {state.caption}" if state.caption else ">",
        "",
    ]


def render_view(
    state: SceneState, view: ViewState, *, ascii_only: bool = False, frame: int = 0
) -> str:
    """Render the scene under the active view mode/zoom (pure).

    ``frame`` drives the floor-plan creature animation (6.4); the dense view modes
    (team/tree/focus/compact) are intentionally static — they trade motion for
    density.
    """
    if view.mode == "team":
        return _render_team(state, ascii_only=ascii_only)
    if view.mode == "tree":
        return _render_tree(state, ascii_only=ascii_only)
    if view.mode == "focus" and view.focus is not None:
        return _render_focus(state, view.focus, ascii_only=ascii_only)
    if _is_compact(state, view):
        return _render_counts(state)
    return render_scene(state, ascii_only=ascii_only, frame=frame)


def _render_counts(state: SceneState) -> str:
    """Compact floor view: per-zone and per-status counts (legible at scale)."""
    lines = _header(state)
    lines.append(f"agents: {len(state.agents)}")
    by_zone: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for agent in state.agents.values():
        by_zone[agent.zone] = by_zone.get(agent.zone, 0) + 1
        by_status[agent.status] = by_status.get(agent.status, 0) + 1
    lines.append(
        "  zones:   " + ", ".join(f"{z}={by_zone[z]}" for z in sorted(by_zone))
    )
    lines.append(
        "  status:  " + ", ".join(f"{s}={by_status[s]}" for s in sorted(by_status))
    )
    if state.paths:
        lines.append(f"  paths:   {len(state.paths)}")
    return "\n".join(lines)


def _render_team(state: SceneState, *, ascii_only: bool) -> str:
    """Group agents under their team name; loose agents under (no team)."""
    lines = _header(state)
    teams = state.teams
    grouped = {aid for ids in teams.values() for aid in ids}
    for name in sorted(teams):
        lines.append(f"[{name}] ({len(teams[name])})")
        for aid in teams[name]:
            lines.append("  " + _agent_line(state, aid, ascii_only=ascii_only))
    loose = sorted(
        a.agent_id for a in state.agents.values() if a.agent_id not in grouped
    )
    if loose:
        lines.append("[(no team)]")
        for aid in loose:
            lines.append("  " + _agent_line(state, aid, ascii_only=ascii_only))
    return "\n".join(lines)


def _render_tree(state: SceneState, *, ascii_only: bool) -> str:
    """Dense hierarchical org-tree: parent -> subagents, per-node state (6.2)."""
    lines = _header(state)
    children: dict[str | None, list[str]] = {}
    for agent in state.agents.values():
        children.setdefault(agent.parent_id, []).append(agent.agent_id)
    for kids in children.values():
        kids.sort()
    # Roots = agents with no parent, or whose parent isn't in this state.
    roots = sorted(
        a.agent_id
        for a in state.agents.values()
        if a.parent_id is None or a.parent_id not in state.agents
    )
    seen: set[str] = set()

    def walk(agent_id: str, depth: int) -> None:
        if agent_id in seen:  # guard against any parent cycle
            return
        seen.add(agent_id)
        indent = "  " * depth
        lines.append(indent + _agent_line(state, agent_id, ascii_only=ascii_only))
        for child in children.get(agent_id, []):
            walk(child, depth + 1)

    for root in roots:
        walk(root, 0)
    return "\n".join(lines)


def _render_focus(state: SceneState, focus: str, *, ascii_only: bool) -> str:
    """Show one lineage: the focused agent plus its parent and children."""
    lines = [f"run: {state.run_status}", f"focus: {focus}", ""]
    target = state.agents.get(focus)
    if target is None:
        lines.append(f"(no agent {focus!r})")
        return "\n".join(lines)
    if target.parent_id:
        lines.append(
            "parent: " + _agent_line(state, target.parent_id, ascii_only=ascii_only)
        )
    lines.append(_agent_line(state, focus, ascii_only=ascii_only))
    children = sorted(a.agent_id for a in state.agents.values() if a.parent_id == focus)
    for child in children:
        lines.append("  child: " + _agent_line(state, child, ascii_only=ascii_only))
    return "\n".join(lines)


def _agent_line(state: SceneState, agent_id: str, *, ascii_only: bool) -> str:
    agent = state.agents.get(agent_id)
    if agent is None:
        return f"{agent_id}(?)"
    mark = glyph("agent", ascii_only=ascii_only)
    return f"{mark} {agent_id}({agent.status}) {agent.zone}"
