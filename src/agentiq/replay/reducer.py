"""The single pure reducer: events → SceneState.

`reduce(state, event)` returns a NEW state and never mutates the input, so the
transport (story 2.3) can cache and step states freely. Both replay and the live
scene fold events through this one function, guaranteeing identical output for
identical input (NFR5).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from agentiq.events.models import Event
from agentiq.replay.scene_state import (
    AgentState,
    SceneState,
    Status,
    Zone,
    initial_state,
)


def reduce(state: SceneState, event: Event) -> SceneState:
    """Fold one event into the scene, returning a new (never-mutated) state."""
    agents = {aid: replace(a) for aid, a in state.agents.items()}
    paths = list(state.paths)
    run_status = state.run_status
    caption = state.caption
    aid = event.agent_id
    p = event.payload

    match event.type:
        case "run.started":
            run_status = "running"
            caption = f"run started: {p.get('goal', '')}"
        case "run.completed":
            run_status = p.get("status", "completed")
            caption = f"run {run_status}"
        case "run.aborted":
            run_status = "aborted"
            caption = f"run aborted: {p.get('reason', '')}"
        case "agent.spawned":
            key = aid or ""
            parent_id = p.get("parent_id")
            agents[key] = AgentState(
                agent_id=key,
                role=p.get("role"),
                parent_id=parent_id,
                status=Status.IDLE,
                zone=Zone.DESK if parent_id else Zone.FLOOR,
                team=p.get("team"),
            )
            caption = f"spawned {key}" + (f" ({p['role']})" if p.get("role") else "")
        case "task.delegated":
            to_agent = p.get("to_agent", "")
            paths.append((aid or "", to_agent))
            if aid in agents:
                agents[aid].status = Status.DELEGATING
                agents[aid].zone = Zone.PATH
            if to_agent in agents:
                agents[to_agent].status = Status.WORKING
            caption = f"{aid} -> {to_agent}: {p.get('task', '')}"
        case "vault.read":
            if aid in agents:
                agents[aid].zone = Zone.LIBRARY
                agents[aid].status = Status.READING
            caption = f"{aid} reads vault: {p.get('ref', '')}"
        case "decision.pending":
            caption = f"decision pending: {p.get('prompt', '')}"
        case "decision.resolved":
            caption = f"decision resolved: {p.get('choice', '')}"
        case "agent.failed":
            if aid in agents:
                agents[aid].status = Status.FAILED
            caption = f"{aid} failed: {p.get('cause', '')}"
        case _:
            # Valid but unhandled event type: advance without crashing (forward-compat).
            caption = event.type

    return SceneState(
        current_seq=event.seq,
        run_status=run_status,
        caption=caption,
        agents=agents,
        paths=paths,
    )


def reduce_all(
    events: Iterable[Event], initial: SceneState | None = None
) -> SceneState:
    """Fold a whole event sequence into a final SceneState."""
    state = initial if initial is not None else initial_state()
    for event in events:
        state = reduce(state, event)
    return state
