# Story 2.9: Runs browser screen

Status: review

## Story

As a developer,
I want a runs list screen with clear empty/loading/idle states,
so that picking a run to read is effortless.

## Acceptance Criteria

1. **Given** runs exist, **When** the runs browser is shown, **Then** a DataTable
   lists them (id, status, cost, duration, goal), newest first, and selecting a
   row yields that run's id (to open its replay).
2. **Given** no runs, **When** the browser is shown, **Then** an empty state shows
   the exact `wcs run "<goal>" --project <path>` command (UX-DR11), not a blank table.

## Tasks / Subtasks

- [x] Task 1: `tui/runs_browser.py` `RunsBrowserScreen(Screen[str | None])` —
      `list_runs` → DataTable (RUN ID/STATUS/COST/DURATION/GOAL, newest first,
      rows keyed by run_id) or `#runs-empty` Static hint; `RowSelected`/enter →
      `dismiss(run_id)`; `q`/`escape` → `dismiss(None)`; Header + Footer.
- [x] Task 2: Tests (3) — table has a row per run + enter dismisses with the
      newest (row 0 = "B"); empty store shows the `wcs run` hint; `q` cancels → None.

## Dev Notes

Builds on 1.9 (`list_runs`) + 2.5 (app/tokens). Delivers the browser SCREEN as a
reusable component that returns a selected run id via `dismiss(run_id)` — the
caller (a future top-level interactive `wcs` shell) decides to open the scene with
that id. Wiring the browser → scene into a single top-level command is a thin
follow-on; this story delivers and tests the screen + selection contract. The
non-interactive `wcs runs` (story 1.9) stays as the scriptable table.

**Empty state (UX-DR11):** never a blank table — show the exact `wcs run` command.
A real async "loading…" state is unnecessary here (`list_runs` is a fast local
glob); note it and keep the empty/has-rows split.

**Selection contract:** the screen is `Screen[str | None]`. Selecting a row
`dismiss(run_id)`; quitting `dismiss(None)`. Tested by pushing the screen from a
tiny host app in `run_test` and reading the dismiss result via the push_screen
callback.

**DataTable:** keep a parallel `run_ids` list in row order so `cursor_row` (int)
maps to a run id. Rows are newest-first (list_runs already sorts).

**Patterns:** `tui/` imports `core.run.list_runs` + Textual; pure presentation, no
orchestration; core-side never imports tui (import-linter).

### Project Structure Notes

- New: `src/well_corp_sw/tui/runs_browser.py`. Tests: `tests/tui/test_runs_browser.py`.

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Component Strategy] — runs browser DataTable + empty/loading/idle states.
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#UX Consistency Patterns] — empty state shows the exact `wcs run` command.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.9] — acceptance criteria.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 90 passed (3 browser); ruff/ty/format clean; lint-imports KEPT.
- Headless testing fixes: query `app.screen.query_one(...)` (the pushed screen,
  not the App's default) after `await pilot.pause()`. `Static` has no `.renderable`
  in this Textual version → asserted the hint constant instead.
- Selection bug: `DataTable.add_row` without an explicit `key` yields a row key
  whose `.value` is None, so the key→id map collapsed to the last run. Fixed by
  passing `key=run.run_id` and reading `event.row_key.value` in
  `on_data_table_row_selected` (DataTable consumes Enter and emits RowSelected, so
  the screen's Enter binding alone never fired).

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Reusable `Screen[str | None]`: returns the selected run id via `dismiss`, so a
  future top-level interactive `wcs` shell can open the scene with it. Non-interactive
  `wcs runs` (1.9) stays the scriptable table.
- Empty state shows the exact `wcs run` command (UX-DR11), never a blank table.
  `list_runs` is a fast local glob, so no async loading state was needed.
- `tui/` imports `core.run.list_runs` + Textual; core-side never imports tui (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/tui/runs_browser.py (new)
- tests/tui/test_runs_browser.py (new)

### Change Log

- 2026-06-09: Implemented story 2.9 — runs browser screen (DataTable of runs,
  newest-first, select → dismiss(run_id); empty-state hint). 3 tests. Status → review.
