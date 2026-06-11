# Story 1.9: List past runs

Status: review

## Story

As a developer,
I want to list previous runs,
so that I can find a run to replay or resume.

## Acceptance Criteria

1. **Given** one or more runs exist in the run store, **When** I run `wcs runs`,
   **Then** I see id, goal, status, cost, and duration for each, newest first.
2. **Given** no runs, **When** I run `wcs runs`, **Then** I see a one-line hint
   showing the exact `wcs run` command.

## Tasks / Subtasks

- [x] Task 1: `core/run.py` — `RunInfo` dataclass + `list_runs(runs_root=None)`
      (scan `*/meta.json`, pull cost/duration from `summary.json` when present,
      newest-first by run_id, empty/absent root → `[]`).
- [x] Task 2: `cli/runs.py` `runs_command` (empty → `wcs run` hint; else table id/
      status/cost/duration/goal newest-first) + wired `runs` subparser/dispatch,
      removed from stub list.
- [x] Task 3: Tests (6) — `list_runs` empty/absent; newest-first; reads summary;
      `wcs runs` empty→hint; lists each run; default-root fallback. Also a real
      smoke: two `wcs run` then `wcs runs` prints both newest-first.

## Dev Notes

Builds on 1.4 (run store/meta.json) and 1.8 (summary.json). Closes Epic 1's
MVP-core. Read-only listing — no orchestration. Resume (`wcs resume`) is story 4.6;
replay UI is Epic 2 — not here.

**Run store layout (from 1.4/1.8):** `<runs_root>/<ulid>/{meta.json, events.jsonl,
summary.json}`. `meta.json` has run_id/goal/status; `summary.json` (if the run
finished through the orchestrator) has cost_usd/duration_seconds. A run dir without
a summary (e.g. interrupted) still lists from meta, with cost/duration shown as
`-`.

**Newest-first:** run_ids are sortable ULIDs, so sort by run_id descending — no
timestamps needed.

**No-TTY / scriptable:** `wcs runs` prints plain text and returns 0; it must not
require a TTY (NFR15). The empty-state hint is the only output when there are no
runs (UX-DR11: never a blank table).

**Patterns:** `core/` listing imports only stdlib + `events`-adjacent; `cli/runs.py`
wires it. No `tui` import (import-linter).

### Project Structure Notes

- Modified: `core/run.py` (add `RunInfo` + `list_runs`), `cli/app.py` (wire `runs`).
- New: `src/well_corp_sw/cli/runs.py`.
- Tests: `tests/core/test_run_store.py`, `tests/cli/test_runs.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Event Architecture (Data Architecture, adapted)] — run store dir, `wcs runs` globs the dir (no DB).
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#UX Consistency Patterns] — empty state shows the exact `wcs run` command (UX-DR11).
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.9] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR27 (list runs).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 59 passed; ruff clean; ty clean (after switching tests to real
  `argparse.Namespace`); lint-imports KEPT.
- Real smoke: two `wcs run` then `wcs runs` → table, newest-first, cost/duration
  from summary.json; empty store → `wcs run` hint.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Read-only listing over the run store (globs `*/meta.json`, enriches from
  `summary.json`). Newest-first via ULID sort — no timestamps needed.
- Empty state prints the exact `wcs run` command (UX-DR11), never a blank table.
- A run dir without summary.json still lists (cost/duration shown as `-`).
- `core/run.list_runs` + `cli/runs.py`; no tui import (import-linter KEPT).
- **Closes Epic 1 (MVP-core): all 9 stories implemented.** ACs satisfied; status → review.

### File List

- src/well_corp_sw/core/run.py (modified — RunInfo + list_runs)
- src/well_corp_sw/cli/runs.py (new)
- src/well_corp_sw/cli/app.py (modified — wire `runs`)
- tests/core/test_run_store.py (new)
- tests/cli/test_runs.py (new)

### Change Log

- 2026-06-09: Implemented story 1.9 — `wcs runs` lists the run store newest-first
  (id/status/cost/duration/goal) with an empty-state hint. 6 tests. Closes Epic 1.
  Status → review.
