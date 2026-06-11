# Story 2.3: Replay transport and seeking

Status: review

## Story

As a developer,
I want to play, pause, step, and seek through a run,
so that I can move to any moment instantly.

## Acceptance Criteria

1. **Given** a replay is open, **When** I step or jump (forward/back/start/end),
   **Then** the current position and scene state update accordingly.
2. **Given** any target position, **When** I seek to it, **Then** it is immediate
   (O(1)) — the scene state at any seq is available without recomputation lag (FR16).
3. **Given** the transport, **When** I toggle play/pause or change speed, **Then**
   the playing flag and speed multiplier update (clamped to a sane range).

## Tasks / Subtasks

- [x] Task 1: `replay/transport.py` — `ReplayController(events)` precomputes one
      `SceneState` per index (O(1) seek). Position API (position/current_event/
      current_state/step_forward/step_backward/to_start/to_end/seek/seek_to_seq,
      all clamped), playback API (playing, play/pause/toggle_play, speed +
      faster/slower clamped [0.25, 8]), at_start/at_end.
- [x] Task 2: Tests (5) — opens at 0 (state == prefix fold); step/jump clamp at
      ends; seek_to_seq matches prefix fold + unknown seq False; play toggle +
      speed clamp; empty log → pos -1, initial state, no-op steps.

## Dev Notes

Builds on 2.1 (reducer/SceneState). This is the transport ENGINE (model) only —
the visual transport bar widget + key bindings are story 2.7, and jump-to-marker
(decisions/failures) is story 2.4. Keep it pure-Python, no Textual, no I/O beyond
the events handed in.

**O(1) seek (FR16):** precompute the cumulative `SceneState` list on construction
(`states[i] = reduce_all(events[:i+1])`), so `seek`/`step` are index moves with no
recomputation — "no perceptible lag" even on large runs. This is safe because the
reducer is pure (2.1): cached states never mutate.

**Position semantics:** `position` is the index of the currently-shown event
(0-based). A freshly opened replay sits at position 0 (the `run.started` event
applied). An empty event list yields position -1 and `current_state ==
initial_state()`.

**Playback:** `playing`/`speed` are just state the UI clock (2.7) reads to decide
when to call `step_forward`; the engine itself does not run a timer. `speed`
clamps to [0.25, 8]; `faster`/`slower` double/halve within the clamp.

**Patterns:** `replay/transport.py` imports only `events/` + `replay/` (reducer,
scene_state); never `tui` (import-linter). Dataclass/class `PascalCase`.

### Project Structure Notes

- New: `src/well_corp_sw/replay/transport.py`. Tests: `tests/replay/test_transport.py`.

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#2.5 Experience Mechanics] — transport: play/pause, step, jump to start/end, speed.
- [Source: _bmad-output/planning-artifacts/architecture.md#Rendering (Frontend Architecture, adapted)] — scene state via the shared reducer; replay seeks the reduced states.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR16 (scrub to any point; immediate).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates clean on first run: pytest 73 passed; ruff check + format clean; ty clean;
  lint-imports KEPT.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Transport ENGINE only — no Textual, no key bindings (story 2.7), no marker jumps
  (story 2.4). Pure model over the shared reducer.
- O(1) seek via precomputed cumulative states (safe because the reducer is pure);
  `seek_to_seq` correctness verified against `reduce_all(prefix)`.
- Engine holds `playing`/`speed` only; it runs no timer — the UI clock (2.7) reads
  them to decide when to `step_forward`.
- `replay/transport.py` imports only `events/` + `replay/`; no tui (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/replay/transport.py (new)
- tests/replay/test_transport.py (new)

### Change Log

- 2026-06-09: Implemented story 2.3 — `ReplayController` transport engine with
  O(1) precomputed seek, step/jump, and play/speed state. 5 tests. Status → review.
