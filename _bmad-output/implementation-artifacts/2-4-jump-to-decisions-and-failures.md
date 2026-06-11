# Story 2.4: Jump to decisions and failures

Status: review

## Story

As a developer,
I want to jump straight to decisions and failures,
so that I can answer "why?" and "where did it break?" in one keypress.

## Acceptance Criteria

1. **Given** a replay with decision and failure events, **When** I jump to the
   next/previous decision, **Then** the replay lands on it (or reports none).
2. **Given** a replay with failures, **When** I jump to the next/previous failure,
   **Then** the replay lands on it.
3. **Given** landing on a failure, **When** I inspect the current event, **Then**
   its cause is available and the last-good state (the state just before) is
   reachable (FR17).

## Tasks / Subtasks

- [x] Task 1: `replay/markers.py` — `is_decision`/`is_failure`; `timeline._marker`
      refactored to use them (DRY).
- [x] Task 2: Marker navigation on `ReplayController` — precomputed
      `_decision_indices`/`_failure_indices`; `next_/prev_decision`,
      `next_/prev_failure` (return bool, False if none); `last_good_index`.
- [x] Task 3: Tests (4 in test_markers.py) — predicates; next/prev decision land +
      end returns False; next_failure lands, exposes cause, last_good_index = before;
      no-markers returns False.

## Dev Notes

Builds on 2.3 (ReplayController). Adds marker navigation to the engine — still no
Textual; the key bindings (`n`/`p`/`f`) live in the transport bar widget (2.7),
which will call these methods. Marker glyphs (◆/✕) are also a 2.7 concern; this
story only computes positions.

**Marker classification (DRY):** decisions = any `decision.*`; failures =
`agent.failed` or `run.aborted`. Put the predicates in `replay/markers.py` and
have both the timeline (2.2) and the transport use them so the textual `D`/`F`
markers and the jump targets never drift apart.

**FR17 (jump to failure shows cause + last-good):** landing puts `position` on the
failure event, so `current_event.payload["cause"]` is available; `last_good_index`
returns `position - 1` (clamped) so the UI can show the state immediately before
the break. No new state computation — reuse the precomputed states from 2.3.

**Direction semantics:** `next_*` finds the nearest marker with index >
`position`; `prev_*` the nearest with index < `position`. Returns False (no move)
when none exists in that direction.

**Patterns:** `replay/` only imports `events/` + `replay/`; no tui (import-linter).

### Project Structure Notes

- New: `src/well_corp_sw/replay/markers.py`. Modified: `replay/transport.py`
  (marker navigation), `replay/timeline.py` (use shared predicates).
- Tests: `tests/replay/test_markers.py`, extend `tests/replay/test_transport.py`.

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#2.5 Experience Mechanics] — n/p next/prev decision; f next failure.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR17 (jump to failure; cause + last-good state).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 77 passed; ty clean; lint-imports KEPT. Initial test had a
  `decision.resolved` payload missing the required `resolved_by` field (model
  rejected it) → fixed the test; ruff autofix + reformat; all green.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Marker predicates centralized in `replay/markers.py`; both the timeline (D/F)
  and the transport jumps use them, so textual markers and jump targets never drift.
- Navigation is engine-only (no key bindings — those land on the transport bar
  widget, story 2.7, which will call these methods).
- FR17: `next_failure` lands on the failure (cause in `current_event.payload`);
  `last_good_index` gives the state just before it. No recomputation (reuses 2.3 states).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/replay/markers.py (new)
- src/well_corp_sw/replay/transport.py (modified — marker navigation)
- src/well_corp_sw/replay/timeline.py (modified — use shared predicates)
- tests/replay/test_markers.py (new)

### Change Log

- 2026-06-09: Implemented story 2.4 — shared marker predicates + jump-to-decision/
  failure navigation on ReplayController (with last_good_index for FR17). 4 tests.
  Status → review.
