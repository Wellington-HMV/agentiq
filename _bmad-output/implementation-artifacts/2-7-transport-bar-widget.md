# Story 2.7: Transport bar widget

Status: review

## Story

As a developer,
I want a visual transport bar with markers and a caption,
so that I always know where I am and what's happening.

## Acceptance Criteria

1. **Given** the scene replay, **When** it renders, **Then** a transport bar shows
   a playhead, decision (◆) and failure (✕) markers, and a seq/total counter (UX-DR3).
2. **Given** the replay, **When** I press the transport keys (space, ←/→, n/p, f,
   home/end), **Then** the controller moves and the scene + bar update accordingly.
3. **Given** a one-line caption, **When** the position changes, **Then** the bar's
   caption names the current event.

## Tasks / Subtasks

- [x] Task 0: `ReplayController` public `event_count`/`decision_indices`/`failure_indices`.
- [x] Task 1: `tui/transport_bar.py` — `render_transport` (track sized to
      event_count, ◆/✕ markers, playhead wins, `pos+1/total` + caption) + `TransportBar(Static)`.
- [x] Task 2: `WcsApp(controller=None, state=None)` — controller path mounts
      SceneWidget + TransportBar; transport BINDINGS (space/←→/n/p/f/home/end);
      action handlers call controller + `_refresh()`; play uses a `set_interval`
      timer pausing at end. No-controller path unchanged + actions are no-ops.
- [x] Task 3: `wcs replay --scene` builds a `ReplayController` and passes it to WcsApp.
- [x] Task 4: Tests (3) — render_transport counter/markers/playhead; keys drive
      controller (right→advance, f→failure, home→0, space→playing) in headless
      run_test; empty controller renders `[ ] 0/0`.

## Dev Notes

Builds on 2.3 (ReplayController), 2.4 (markers), 2.5 (app/tokens), 2.6 (scene).
This story makes the scene INTERACTIVE — the bindings drive the controller and the
widgets re-render. The engine already exists (2.3/2.4); the widget/bindings are the
thin Textual layer (NFR17: no logic in the TUI — it only calls controller methods
and renders state).

**Transport bar visual (UX-DR3):** a single-line track sized to `event_count`;
mark ◆ decisions and ✕ failures; the playhead glyph (▶) shows the current position
and takes precedence over a marker at the same spot. Use the token glyphs (ASCII
fallback honoured; auto tier-detect is 2.10).

**Playback:** `space` toggles `controller.playing`; while playing, a Textual
`set_interval` timer calls `step_forward` and `_refresh`, stopping at `at_end`.
Keep the interval simple (fixed) for the MVP — `speed`-driven timing can refine
later. The engine holds no timer; the app owns it (the UI clock).

**Refresh:** one `_refresh()` updates both `SceneWidget.update_scene(...)` and
`TransportBar.update_bar(...)` from the controller's current state — single code
path, scene and bar never drift.

**Compatibility:** `WcsApp(state=...)` (2.6 static path) still works; only the
controller path adds the bar + bindings. Action handlers are no-ops without a
controller (so the bindings are safe even on the static path).

**Dependency rule:** `tui/` imports `replay/` (controller/scene) + Textual; no
core-side package imports `tui` (import-linter).

### Project Structure Notes

- New: `src/well_corp_sw/tui/transport_bar.py`. Modified: `replay/transport.py`
  (introspection props), `tui/app.py` (controller wiring + bindings),
  `cli/replay.py` (pass a controller).
- Tests: `tests/tui/test_transport_bar.py`.

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Component Strategy] — TransportBar: playhead + ◆/✕ markers + seq/total + caption.
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#2.5 Experience Mechanics] — transport keys space/←→/n-p/f/home-end.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.7] — acceptance criteria.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates clean first run: pytest 85 passed (3 transport-bar); ruff/ty/format clean;
  lint-imports KEPT. Headless `run_test` confirms key presses drive the controller.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- The scene is now INTERACTIVE: bindings → controller methods → `_refresh()` updates
  both SceneWidget and TransportBar from one path (they never drift).
- TUI stays logic-free (NFR17): the engine (2.3/2.4) does the work; the app only
  calls methods and renders. Action handlers are safe no-ops without a controller.
- Playback timer (`set_interval`, fixed tick) lives in the app (the UI clock), not
  the engine; pauses at `at_end`. Speed-driven timing can refine later.
- `wcs replay --scene` now scrubs interactively (passes a ReplayController).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/tui/transport_bar.py (new)
- src/well_corp_sw/replay/transport.py (modified — public introspection props)
- src/well_corp_sw/tui/app.py (modified — controller wiring + transport bindings + timer)
- src/well_corp_sw/cli/replay.py (modified — pass a ReplayController)
- tests/tui/test_transport_bar.py (new)

### Change Log

- 2026-06-09: Implemented story 2.7 — transport bar widget + interactive key
  bindings driving the ReplayController; the spatial scene is now navigable
  (scrub/step/jump/play). 3 tests. Status → review.
