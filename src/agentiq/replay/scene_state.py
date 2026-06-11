"""Scene state — the projection both replay and the live scene render.

A ``SceneState`` is the spatial snapshot at a given ``seq``: where each agent is
(zone), what it is doing (status), the delegation paths between agents, the run
status, and a one-line caption for the current event. It is produced solely by the
reducer (see ``reducer.py``); there is exactly one reducer so live and replay can
never diverge.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class Zone:
    FLOOR = "floor"
    LIBRARY = "library"
    DESK = "desk"
    SUBAGENTS = "subagents"
    PATH = "path"


class Status:
    IDLE = "idle"
    READING = "reading"
    THINKING = "thinking"
    DELEGATING = "delegating"
    WORKING = "working"
    FAILED = "failed"
    DONE = "done"


@dataclass
class AgentState:
    agent_id: str
    role: str | None = None
    parent_id: str | None = None
    status: str = Status.IDLE
    zone: str = Zone.FLOOR
    team: str | None = None


@dataclass
class SceneState:
    current_seq: int = -1
    run_status: str = "pending"
    caption: str = ""
    agents: dict[str, AgentState] = field(default_factory=dict)
    paths: list[tuple[str, str]] = field(default_factory=list)

    @property
    def teams(self) -> dict[str, list[str]]:
        """Named-team grouping (FR6): team name -> sorted member agent ids."""
        out: dict[str, list[str]] = {}
        for agent in self.agents.values():
            if agent.team:
                out.setdefault(agent.team, []).append(agent.agent_id)
        for members in out.values():
            members.sort()
        return dict(sorted(out.items()))  # deterministic team ordering


def initial_state() -> SceneState:
    """The empty scene before any event is applied."""
    return SceneState()
