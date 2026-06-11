# Story 2.6: Spatial scene rendering

Status: review

## Story

As a developer,
I want the top-down office floor-plan with creatures,
so that I can read agent activity spatially at a glance.

## Acceptance Criteria

1. **Given** a `SceneState`, **When** the scene renders, **Then** the fixed zones
   (LIBRARY / DESKS / SUBAGENTS) and the anchored parent are shown (UX-DR1).
2. **Given** a `SceneState`, **When** it renders, **Then** each agent's
   position/posture is encoded by zone + status + glyph (not colour alone) (UX-DR2).
3. **Given** a run, **When** `wcs replay <id> --scene` is run in a TTY, **Then**
   the scene renders matching the reducer state; with no TTY it falls back to the
   timeline (NFR7).

## Tasks / Subtasks

- [x] Task 1: `tui/scene.py` `render_scene(state, *, ascii_only=False)` — pure,
      deterministic floor-plan: `run:` header + caption + fixed zones
      LIBRARY/DESKS/SUBAGENTS (agents as `<glyph> <id>(<status>)`, sorted) + PATHS
      edges. Zone placement from `AgentState.zone`; token glyphs w/ ASCII fallback.
- [x] Task 2: `SceneWidget(Static)` with `update_scene(state)`.
- [x] Task 3: `WcsApp(state=None, ...)` renders `SceneWidget`; replaced the placeholder.
- [x] Task 4: `wcs replay --scene` → TTY launches `WcsApp(state=reduce_all(...))`;
      non-TTY falls back to the timeline (NFR7); Textual imported lazily.
- [x] Task 5: Tests (3 scene + updated replay/app) — render shows zones + parent +
      a1 reading in LIBRARY + run status; ASCII-only mode; SceneWidget mounts in
      `run_test`; `--scene` non-TTY falls back to timeline.

## Dev Notes

Builds on 2.1 (SceneState/reducer), 2.5 (app shell, tokens). THE visible heart of
the product. Keep the rendering a PURE function of `SceneState` (UX/architecture:
the TUI is a dumb renderer of reducer state; no orchestration logic, NFR17). Rich
animation/motion is Growth — for the MVP slice this is a clear static spatial
snapshot of the current state. Interactive stepping (transport bar + keys) is
story 2.7; here `--scene` shows the run's final state.

**Determinism / parity (NFR5):** `render_scene` derives only from `SceneState`,
which comes from the single shared reducer — so the scene always matches the
timeline/replay for the same seq.

**No-colour / ASCII (UX-DR2, UX-DR10):** meaning is carried by zone + status text
+ glyph, never colour alone; `ascii_only` swaps glyphs to ASCII fallbacks so the
scene reads in any terminal. (Full responsive tier selection is story 2.10.)

**`--scene` + TTY (NFR7):** launching a Textual app requires a TTY. Guard with
`sys.stdout.isatty()`: TTY → run `WcsApp`; otherwise fall back to the plain
timeline so piping/headless never breaks. Import Textual lazily inside the scene
branch (don't pay the import when piping).

**Dependency rule:** `tui/` imports `replay/` (reducer) + Textual — fine.
`cli/replay.py` imports `tui` lazily — `cli/` is not forbidden from importing
`tui`; only core-side packages are (import-linter).

### Project Structure Notes

- New: `src/well_corp_sw/tui/scene.py`. Modified: `tui/app.py` (mount SceneWidget),
  `cli/replay.py` (launch scene on TTY).
- Tests: `tests/tui/test_scene.py`, extend `tests/cli/test_replay.py`.

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Design Direction Decision] — office floor-plan (zones, anchored parent, delegation paths).
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Component Strategy] — SceneWidget + Creature; state→tokens mapping; never colour-only.
- [Source: _bmad-output/planning-artifacts/architecture.md#Rendering (Frontend Architecture, adapted)] — TUI is a dumb renderer of SceneState.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.6] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR15 (replay as spatial scene); NFR5/NFR7.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 82 passed (3 scene); ruff/ty clean; format reflowed 1 file;
  lint-imports KEPT.
- Demo render (ascii_only) shows zones + creatures matching reducer state:
  `LIBRARY o a1(reading)`, `SUBAGENTS o parent(delegating)`, `PATHS parent->a1`.
- Note: raw `print()` of the unicode scene fails on the Windows cp1252 console —
  not a product bug (Textual manages its own encoding; ASCII fallback exists; auto
  capability-tier selection is story 2.10).

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- The visible heart: `render_scene` is a pure function of `SceneState`, so the
  scene always matches the timeline for the same seq (NFR5). `SceneWidget` is a
  dumb renderer (NFR17).
- MVP slice = a clear static spatial snapshot; rich motion/animation is Growth.
  Parent is shown but follows its last action's zone (e.g. `delegating` →
  in-transit) — faithful to reducer state; richer anchoring is a later refinement.
- `wcs replay --scene` launches the Textual app on a TTY, else falls back to the
  timeline (NFR7); Textual imported lazily so piping never pays the import.
- `tui/` imports `replay/` + Textual; `cli/replay.py` imports `tui` lazily; no
  core-side package imports `tui` (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/tui/scene.py (new)
- src/well_corp_sw/tui/app.py (modified — mount SceneWidget, accept state)
- src/well_corp_sw/tui/scene.tcss (modified — #scene)
- src/well_corp_sw/cli/replay.py (modified — launch scene on TTY)
- tests/tui/test_scene.py (new)
- tests/tui/test_app.py (modified — query SceneWidget)
- tests/cli/test_replay.py (modified — scene non-TTY fallback message)

### Change Log

- 2026-06-09: Implemented story 2.6 — spatial scene rendering (`render_scene` +
  `SceneWidget`), mounted in `WcsApp`, with `wcs replay --scene` launching the TUI
  on a TTY (timeline fallback otherwise). The product's visible scene. 3 tests.
  Status → review.
