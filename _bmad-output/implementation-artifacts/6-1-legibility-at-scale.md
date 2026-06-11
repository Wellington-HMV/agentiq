# Story 6.1: Legibility at scale

Status: review

## Story

As a developer,
I want zoom / group-by-team / focus-follow,
so that the scene stays readable with many agents.

## Acceptance Criteria

1. **Given** a run with 10+ agents, **When** the scene would crowd, **Then** I can
   zoom, group by team, or focus-follow one agent and stay legible (FR21, NFR14).
2. **Given** zoom, **When** I cycle density, **Then** `auto` compacts to counts once
   crowded (>= 10 agents), `full` forces detail, `compact` forces counts.
3. **Given** focus-follow, **When** I focus an agent, **Then** only that agent plus
   its parent and children render; re-focusing the same agent toggles back to floor.

## Tasks / Subtasks

- [x] Task 1: `tui/scene_view.py` — `ViewState` (immutable: `mode`
      floor/team/focus, `density` auto/full/compact, `focus`) + pure
      `render_view(state, view)` dispatching to: full floor-plan (reuses
      `render_scene`), compact per-zone/per-status counts, team grouping, or a
      single-lineage focus view. `CROWD_THRESHOLD = 10` drives `auto` compaction.
- [x] Task 2: `SceneWidget` holds a `ViewState` and renders via `render_view`
      (`set_view` re-renders the current state); falls back to the plain plan when
      no view is set.
- [x] Task 3: Keys in `WcsApp` (replay) and `LiveWatchApp` (live) — `z` cycle zoom,
      `g` toggle team view, `o` focus-follow (target = current event's agent, else
      an active agent). Renamed the action to `focus_agent` to avoid colliding with
      Textual's built-in `App.action_focus`.
- [x] Task 4: Tests — auto compacts when crowded / stays full when small; `full`/
      `compact` overrides; zoom cycle; team grouping (+ loose agents under
      `(no team)`); focus shows only the lineage and hides unrelated siblings;
      unknown focus is graceful; focus toggles off; app keys drive the modes.

## Dev Notes

The scene crowds as a run fans out. 6.1 adds a **view layer** on top of the one
reducer's `SceneState` — purely presentational, so the spatial picture still
matches the timeline/replay for the same seq (NFR5).

- **Zoom** is a tri-state `density`: `auto` (full until `>= CROWD_THRESHOLD`
  agents, then per-zone/per-status counts), `full`, `compact`. `auto` is the safe
  default — legibility degrades gracefully without any keypress (NFR14).
- **Group-by-team** buckets agents under their team (5.3's `SceneState.teams`),
  loose agents under `(no team)`.
- **Focus-follow** renders one lineage — the focused agent, its parent, its
  children — hiding the rest.

`render_view` is pure and reuses `render_scene` for the full plan, so there's one
source of truth for the detailed layout. `SceneWidget` keeps the `ViewState` and
re-renders on `set_view`; the apps own the `ViewState` and mutate it via immutable
`ViewState` helpers (`cycle_zoom`/`toggle_team`/`focus_on`).

**LSP note:** Textual's `App` already defines `action_focus(widget_id)`; binding
`o` to a method named `action_focus` would override it incompatibly (ty flags it),
so the action is `action_focus_agent`.

The view layer lives in `tui/` (it needs `glyph`); `SceneWidget` imports
`scene_view` lazily inside `update_scene` to avoid an import-order cycle with
`scene`. No core-side module imports tui (NFR17 KEPT).

### Project Structure Notes

- New: `src/well_corp_sw/tui/scene_view.py`, `tests/tui/test_scene_view.py`.
- Modified: `tui/scene.py` (`SceneWidget` holds a view + `set_view`),
  `tui/app.py` (view state + z/g/o bindings + actions), `tui/live.py` (same
  bindings + pass the view to its scene widget).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.1] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR21 (zoom/group/focus), NFR14 (legible at scale).
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] — stable mental map; meaning by zone/status/glyph (UX-DR1/UX-DR2).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Completion Notes List

- Pure `render_view` view layer over the single reducer's `SceneState`: tri-state
  zoom (auto compacts at 10+), team grouping, single-lineage focus.
- `auto` density means crowded scenes stay legible with no keypress (NFR14).
- Keys `z`/`g`/`o` in both replay and live apps; action named `focus_agent` to
  avoid overriding Textual's `App.action_focus` (LSP).

### File List

- src/well_corp_sw/tui/scene_view.py (new)
- tests/tui/test_scene_view.py (new)
- src/well_corp_sw/tui/scene.py (modified — SceneWidget holds a ViewState)
- src/well_corp_sw/tui/app.py (modified — view state + z/g/o bindings/actions)
- src/well_corp_sw/tui/live.py (modified — z/g/o bindings + pass view)

### Change Log

- 2026-06-10: Implemented story 6.1 — `scene_view.py` view layer (zoom /
  group-by-team / focus-follow) over the reducer state, wired into replay + live
  via `z`/`g`/`o`. Opens Epic 6 (Vision). Status → review.
