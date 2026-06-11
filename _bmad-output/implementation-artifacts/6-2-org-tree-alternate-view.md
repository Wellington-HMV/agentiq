# Story 6.2: Org-tree alternate view

Status: review

## Story

As a developer,
I want an alternate hierarchical org-tree view,
so that I can read structure densely when preferred.

## Acceptance Criteria

1. **Given** a run, **When** I switch view, **Then** a parent→subagent tree with
   per-node state renders from the same reducer state.
2. **Given** an agent whose parent isn't present, **When** the tree renders, **Then**
   it appears as a root (orphans aren't dropped).
3. **Given** the tree key, **When** I press it again, **Then** it toggles back to the
   floor-plan.

## Tasks / Subtasks

- [x] Task 1: `ViewState` gains `mode == "tree"` + `toggle_tree()`; `render_view`
      dispatches to `_render_tree`.
- [x] Task 2: `_render_tree` builds the parent→children hierarchy from
      `AgentState.parent_id`, renders roots (no parent, or parent absent) and walks
      depth-first with indentation, showing per-node state via the shared
      `_agent_line`. A `seen` set guards against any parent cycle. Deterministic
      (children + roots sorted).
- [x] Task 3: Key `t` toggles the tree view in `WcsApp` (replay) and `LiveWatchApp`
      (live).
- [x] Task 4: Tests — tree renders the hierarchy with correct indentation and
      per-node state; an orphan (missing parent) is a root; `toggle_tree` flips mode;
      the `t` key drives it.

## Dev Notes

A second pure view mode on the same `SceneState` (no new data) — the AC's "from the
same reducer state" is satisfied by construction: `render_view` is pure over the
single reducer's projection, so the tree matches the floor-plan/timeline for the
same seq (NFR5).

`_render_tree` is a depth-first walk over `parent_id` adjacency. Roots are agents
with no parent or whose parent isn't in the state (so a re-run-seeded or partial
state never hides an agent). The `seen` set makes the walk total even if the data
ever contained a cycle. Reuses `_agent_line` so node rendering (glyph + status +
zone) matches the other views exactly.

Sits alongside 6.1's zoom/team/focus as another `mode`; the modes are mutually
exclusive (one `mode` field), and `t` toggles tree↔floor like `g` does team.

### Project Structure Notes

- Modified: `tui/scene_view.py` (`tree` mode + `_render_tree`), `tui/app.py`
  (`t` binding + `action_tree`), `tui/live.py` (`t` binding).
- Tests appended to `tests/tui/test_scene_view.py`.
- Pure presentation in `tui/`; no core-side import of tui (NFR17 KEPT).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.2] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] — alternate dense hierarchy view; per-node state.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Completion Notes List

- `tree` view = depth-first walk over `parent_id`, roots = no/absent parent, cycle-
  guarded, deterministic; reuses `_agent_line` for per-node state.
- Pure over the one reducer state (matches floor-plan/timeline for the same seq).
- `t` toggles tree↔floor in both replay and live.

### File List

- src/well_corp_sw/tui/scene_view.py (modified — tree mode + _render_tree)
- src/well_corp_sw/tui/app.py (modified — t binding + action_tree)
- src/well_corp_sw/tui/live.py (modified — t binding)
- tests/tui/test_scene_view.py (modified — org-tree tests)

### Change Log

- 2026-06-10: Implemented story 6.2 — org-tree alternate view (`mode="tree"`,
  `_render_tree`) over the reducer state, toggled with `t`. Status → review.
