# Story 6.4: Creature personalities

Status: review

## Story

As a developer,
I want expressive creature personalities,
so that the living-office feel is fully realized.

## Acceptance Criteria

1. **Given** the scene, **When** agents act, **Then** creatures show characterful
   idle/role animations that still encode real state (charm bounded by legibility).
2. **Given** any frame or role, **When** a creature renders, **Then** its status
   glyph is always present (state never hidden by flourish, UX-DR2).
3. **Given** reduced motion, **When** the scene renders, **Then** no animation timer
   runs (the static face still reads state).

## Tasks / Subtasks

- [x] Task 1: `tui/creatures.py` — pure `creature(agent, frame, *, ascii_only)`:
      `<status glyph><body bob><role tag>`. The status glyph is authoritative and
      always leads; the body bobs only while the agent is *active* (motion encodes
      busy) and is still otherwise; `role_tag` adds a per-role personality letter.
- [x] Task 2: Wire into the floor-plan — `render_scene(..., frame=0)` and
      `_creature` use the creature face; `SceneWidget` holds a `_frame` and
      `tick_animation()` advances it and re-renders.
- [x] Task 3: Animation cadence — `WcsApp.start_creature_animation` sets an interval
      that bobs the creatures; suppressed under `reduced_motion`. `LiveWatchApp`
      starts it too.
- [x] Task 4: Tests — status glyph present every frame; active status bobs across
      frames (2-frame cycle); calm/terminal statuses don't animate; failed is marked
      and stable; role tag personality; ascii-only stays ascii; `SceneWidget`
      tick advances the frame. Updated the scene ascii test for the new face.

## Dev Notes

The capstone charm story, held to the cardinal rule **charm never costs legibility
(UX-DR2)**. A creature is `status-glyph + body + role-tag`:

- **status glyph** — authoritative, always first, never animates, so the agent's
  real state is unambiguous at any frame/role.
- **body** — bobs between two frames *only while the agent is active*
  (reading/thinking/delegating/working); calm and terminal states are still, so
  motion itself reads as "busy" (legibility through motion, not noise).
- **role tag** — the role's initial, a stable personality flourish.

`creature` is a pure function of `(AgentState, frame)` — deterministic, so it stays
consistent with the single reducer and replay (NFR5); animation is just the frame
advancing. The apps drive an interval (`start_creature_animation`) that bumps the
`SceneWidget` frame; `reduced_motion` (UX-DR / accessibility) suppresses the timer
entirely and the static face still encodes state.

Animation is wired into the default floor-plan; the 6.1/6.2 view modes
(team/tree/focus/compact) stay static (they trade animation for density on purpose).

**Gotcha:** Textual's `App` reserves the attribute `_animate` (a `BoundAnimator`);
the interval callback is named `_tick_creatures` to avoid shadowing it.

### Project Structure Notes

- New: `src/well_corp_sw/tui/creatures.py`, `tests/tui/test_creatures.py`.
- Modified: `tui/scene.py` (creature face + frame + `tick_animation`), `tui/app.py`
  (`start_creature_animation` interval), `tui/live.py` (start it),
  `tests/tui/test_scene.py` (ascii face assertion).
- Pure presentation in `tui/`; no core-side import of tui (NFR17 KEPT).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.4] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] — living-office creatures; UX-DR2 (meaning never by colour/charm alone).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Completion Notes List

- Pure `creature()` = status-glyph (authoritative, always shown) + active-only body
  bob + role personality tag — charm bounded by legibility (UX-DR2).
- Wired into the floor-plan with a frame; `SceneWidget.tick_animation` + an app
  interval drive it; `reduced_motion` suppresses the timer.
- Renamed the interval callback to `_tick_creatures` (Textual reserves `_animate`).
- **Closes Epic 6 (Scale & Vision) and the full story backlog (all 6 epics).**

### File List

- src/well_corp_sw/tui/creatures.py (new)
- tests/tui/test_creatures.py (new)
- src/well_corp_sw/tui/scene.py (modified — creature face + frame + tick_animation)
- src/well_corp_sw/tui/app.py (modified — start_creature_animation interval)
- src/well_corp_sw/tui/live.py (modified — start animation)
- tests/tui/test_scene.py (modified — ascii face assertion)

### Change Log

- 2026-06-10: Implemented story 6.4 — `creatures.py` personality faces (status-led,
  active-only bob, role tag) wired into the scene with a reduced-motion-aware
  animation interval. Closes Epic 6 and the backlog. Status → review.
