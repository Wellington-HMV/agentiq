"""Tests for legibility-at-scale view modes (story 6.1 / FR21, NFR14)."""

from __future__ import annotations

from agentiq.events.models import Event
from agentiq.replay.scene_state import AgentState, SceneState, Status, Zone
from agentiq.replay.transport import ReplayController
from agentiq.tui.app import WcsApp
from agentiq.tui.scene_view import CROWD_THRESHOLD, ViewState, render_view


def _state(n: int, *, teamed: bool = False) -> SceneState:
    agents: dict[str, AgentState] = {
        "parent": AgentState("parent", status=Status.DELEGATING, zone=Zone.FLOOR)
    }
    for i in range(n):
        aid = f"a{i}"
        agents[aid] = AgentState(
            aid,
            role="r",
            parent_id="parent",
            status=Status.WORKING,
            zone=Zone.DESK,
            team=(f"t{i % 2}" if teamed else None),
        )
    return SceneState(current_seq=0, run_status="running", caption="c", agents=agents)


# --- zoom / density ---------------------------------------------------------


def test_auto_compacts_when_crowded() -> None:
    out = render_view(_state(CROWD_THRESHOLD + 2), ViewState())
    assert f"agents: {CROWD_THRESHOLD + 3}" in out  # +parent
    assert "zones:" in out and "status:" in out  # compact counts, not full plan


def test_auto_full_when_small() -> None:
    out = render_view(_state(3), ViewState())
    assert "DESKS" in out  # full floor-plan labels from render_scene


def test_density_full_forces_detail_even_crowded() -> None:
    out = render_view(_state(CROWD_THRESHOLD + 5), ViewState(density="full"))
    assert "DESKS" in out


def test_density_compact_forces_counts_even_small() -> None:
    out = render_view(_state(2), ViewState(density="compact"))
    assert "agents: 3" in out and "zones:" in out


def test_cycle_zoom_rotates() -> None:
    v = ViewState()
    assert v.density == "auto"
    assert v.cycle_zoom().density == "full"
    assert v.cycle_zoom().cycle_zoom().density == "compact"
    assert v.cycle_zoom().cycle_zoom().cycle_zoom().density == "auto"


# --- group by team ----------------------------------------------------------


def test_team_view_groups_by_team() -> None:
    out = render_view(_state(4, teamed=True), ViewState(mode="team"))
    assert "[t0]" in out and "[t1]" in out
    assert "(no team)" in out  # parent has no team


def test_toggle_team_flips_mode() -> None:
    assert ViewState().toggle_team().mode == "team"
    assert ViewState(mode="team").toggle_team().mode == "floor"


# --- org-tree (6.2) ---------------------------------------------------------


def test_tree_renders_hierarchy_with_per_node_state() -> None:
    out = render_view(_lineage(), ViewState(mode="tree"))
    lines = out.splitlines()
    # parent at depth 0, its children indented under it
    parent_idx = next(i for i, ln in enumerate(lines) if "parent(" in ln)
    a1_idx = next(i for i, ln in enumerate(lines) if "a1(" in ln)
    a2_idx = next(i for i, ln in enumerate(lines) if "a2(" in ln)
    assert not lines[parent_idx].startswith(" ")  # root, no indent
    assert lines[a1_idx].startswith("  ")  # child of parent, indented one level
    assert lines[a2_idx].startswith("    ")  # grandchild, indented two levels
    assert "(working)" in out and "(reading)" in out  # per-node state shown


def test_tree_orphan_is_a_root() -> None:
    state = SceneState(
        current_seq=0,
        run_status="running",
        agents={
            "x": AgentState(
                "x", parent_id="ghost", status=Status.WORKING, zone=Zone.DESK
            ),
        },
    )
    out = render_view(state, ViewState(mode="tree"))
    # parent "ghost" isn't in state -> x is treated as a root (rendered, no indent)
    x_line = next(ln for ln in out.splitlines() if "x(" in ln)
    assert not x_line.startswith(" ")


def test_toggle_tree_flips_mode() -> None:
    assert ViewState().toggle_tree().mode == "tree"
    assert ViewState(mode="tree").toggle_tree().mode == "floor"


# --- focus-follow -----------------------------------------------------------


def _lineage() -> SceneState:
    return SceneState(
        current_seq=0,
        run_status="running",
        agents={
            "parent": AgentState("parent", status=Status.DELEGATING, zone=Zone.FLOOR),
            "a1": AgentState(
                "a1", parent_id="parent", status=Status.WORKING, zone=Zone.DESK
            ),
            "a2": AgentState(
                "a2", parent_id="a1", status=Status.READING, zone=Zone.LIBRARY
            ),
            "b1": AgentState(
                "b1", parent_id="parent", status=Status.WORKING, zone=Zone.DESK
            ),
        },
    )


def test_focus_shows_only_the_lineage() -> None:
    out = render_view(_lineage(), ViewState(mode="focus", focus="a1"))
    assert "focus: a1" in out
    assert "parent: " in out and "parent(" in out  # its parent
    assert "child: " in out and "a2(" in out  # its child
    assert "b1" not in out  # an unrelated sibling is hidden


def test_focus_unknown_agent_is_graceful() -> None:
    out = render_view(_lineage(), ViewState(mode="focus", focus="zzz"))
    assert "no agent 'zzz'" in out


def test_focus_on_toggles_off_when_repeated() -> None:
    v = ViewState().focus_on("a1")
    assert v.mode == "focus" and v.focus == "a1"
    assert v.focus_on("a1").mode == "floor"
    assert ViewState().focus_on(None).mode == "floor"


# --- app wiring -------------------------------------------------------------


def _evt(seq: int, type: str, payload: dict, agent_id: str | None = None) -> Event:
    return Event.model_validate(
        {
            "seq": seq,
            "ts": "2026-06-10T00:00:00.000000Z",
            "run_id": "R",
            "agent_id": agent_id,
            "type": type,
            "payload": payload,
        }
    )


async def test_app_keys_drive_view_modes() -> None:
    ctrl = ReplayController(
        [
            _evt(0, "run.started", {"goal": "g", "project": "."}),
            _evt(1, "agent.spawned", {"role": "analyze"}, "a1"),
        ]
    )
    app = WcsApp(controller=ctrl)
    async with app.run_test() as pilot:
        await pilot.press("g")
        assert app._view.mode == "team"
        await pilot.press("g")
        assert app._view.mode == "floor"
        await pilot.press("t")
        assert app._view.mode == "tree"
        await pilot.press("t")
        assert app._view.mode == "floor"
        await pilot.press("z")
        assert app._view.density == "full"
        await pilot.press("end")  # current event now has agent_id a1
        await pilot.press("o")
        assert app._view.mode == "focus" and app._view.focus == "a1"
