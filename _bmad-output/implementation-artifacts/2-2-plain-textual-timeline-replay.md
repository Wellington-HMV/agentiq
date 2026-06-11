# Story 2.2: Plain textual timeline replay

Status: review

## Story

As a developer,
I want to replay a run as a plain text timeline,
so that I always have a complete, pipeable, fallback view of any run.

## Acceptance Criteria

1. **Given** a run's event log, **When** I run `wcs replay <run-id> --timeline`,
   **Then** I see one line per event (seq, ts, agent, type, summary) in order.
2. **Given** the timeline, **When** decision and failure events appear, **Then**
   they are marked inline.
3. **Given** no TTY, **When** I run the command, **Then** it works and is pipeable
   (FR14, NFR7) — plain ASCII, deterministic order by seq.

## Tasks / Subtasks

- [x] Task 1: `replay/timeline.py` — `iter_timeline_lines` folds through the
      shared reducer, emits one ASCII line/event with `D`/`F`/`.` marker.
- [x] Task 2: `core/run.find_run_dir(run_id, runs_root=None)`.
- [x] Task 3: `cli/replay.py` `replay_command` (unknown id → stderr + FAILED;
      `--scene` → stderr note + timeline fallback; default timeline) + wired
      `replay` subparser/dispatch, removed from stub list.
- [x] Task 4: Tests (5) — timeline one-line-per-event in seq order; D/F markers +
      ASCII-only; `wcs replay` prints timeline; unknown id fails with stderr;
      `--scene` falls back to timeline with a note.

## Dev Notes

Builds on 2.1 (reducer/SceneState), 1.2 (reader), 1.4 (run dir). This is the
universal fallback view (NFR7): a complete textual replay that always works, with
no TTY, pipeable. The animated spatial scene (`--scene`) is story 2.6; here
`--scene` prints a note and falls back to the timeline so the command is never a
dead end.

**Reuse the shared reducer (2.1):** fold events through `reduce` and emit the
per-step `caption` so the timeline's wording matches the scene's — one projection,
consistent everywhere. Ordering is by `seq` (the reader already enforces strictly
increasing seq).

**ASCII only:** the timeline must be safe in any terminal / redirected file, so
use ASCII markers (`D`/`F`/`.`), not the `◆`/`✕` glyphs reserved for the TUI
transport bar.

**Run lookup:** `find_run_dir` resolves `<runs_root>/<run_id>/` and checks for
`events.jsonl`. For tests, `runs_root` is injectable; the CLI defaults to
`~/.well-corp-sw/runs`.

**Patterns:** `replay/` imports only `events/` + its own modules (no tui).
`cli/replay.py` wires it. Pipeable: print plain lines to stdout, exit 0.

### Project Structure Notes

- New: `src/well_corp_sw/replay/timeline.py`, `src/well_corp_sw/cli/replay.py`.
- Modified: `core/run.py` (find_run_dir), `cli/app.py` (wire `replay`).
- Tests: `tests/replay/test_timeline.py`, `tests/cli/test_replay.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Rendering (Frontend Architecture, adapted)] — timeline fallback always available; shared reducer.
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Component Strategy] — `TimelineView` = plain textual replay, the universal fallback.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR14 (plain timeline); NFR7 (always degrades to timeline).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 68 passed; ty clean; lint-imports KEPT. Ruff flagged a long help
  string in app.py → shortened; format clean after.
- **Real smoke:** `wcs run "demo replay"` then `wcs replay <id>` printed a 9-line
  timeline (run.started → spawns/delegations → run.completed) in seq order.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- First visible replay output — a complete, pipeable textual timeline (NFR7),
  reusing the single shared reducer (2.1) so its wording matches the future scene.
- ASCII-only markers (`D`/`F`/`.`) — safe in any terminal / redirect; the `◆`/`✕`
  glyphs are reserved for the TUI transport bar (story 2.7).
- `--scene` is a graceful fallback to the timeline now (a note on stderr); the real
  animated scene is story 2.6 — `wcs replay` is never a dead end.
- `replay/` and `cli/replay.py` import no `tui` (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/replay/timeline.py (new)
- src/well_corp_sw/cli/replay.py (new)
- src/well_corp_sw/core/run.py (modified — find_run_dir)
- src/well_corp_sw/cli/app.py (modified — wire `replay`)
- tests/replay/test_timeline.py (new)
- tests/cli/test_replay.py (new)
- tests/cli/test_app.py (modified — stub test uses `vault`)

### Change Log

- 2026-06-09: Implemented story 2.2 — plain textual timeline replay
  (`wcs replay <id> [--timeline]`) over the shared reducer; ASCII, pipeable,
  with decision/failure markers and a graceful `--scene` fallback. 5 tests.
  Status → review.
