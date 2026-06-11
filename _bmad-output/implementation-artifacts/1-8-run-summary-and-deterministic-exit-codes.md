# Story 1.8: Run summary and deterministic exit codes

Status: review

## Story

As a developer,
I want a machine- and human-readable summary and documented exit codes,
so that runs are scriptable and CI-friendly.

## Acceptance Criteria

1. **Given** a finished run, **When** the run ends, **Then** `summary.json`
   (status, counts, cost, duration) is projected purely from the event log.
2. **Given** a run, **When** the process exits, **Then** it exits with a
   documented deterministic code per `docs/exit-codes.md` (NFR8).
3. **Given** headless mode, **When** there is no human resolution path, **Then**
   the run never hangs — it ends with a terminal event and a deterministic code.

## Tasks / Subtasks

- [x] Task 1: Summary projection (`replay/summary.py`) — `RunSummary` (Pydantic),
      `build_summary(events)` projecting status/goal/ts/counts/duration purely from
      the log (cost_usd 0.0 until Epic 4), `write_summary(events_path, out_path)`.
- [x] Task 2: Exit codes (`core/exit_codes.py`) — `ExitCode` (0/1/2/3/4),
      `status_to_exit_code` (completed→0, aborted→1, blocked→3, budget_exceeded→4, else 1).
- [x] Task 3: Wired — `run_orchestration` writes `summary.json` after the terminal
      event (try/except/else then projection); `wcs run` returns `status_to_exit_code`.
- [x] Task 4: Real `docs/exit-codes.md` table matching `ExitCode`.
- [x] Task 5: Tests (6) — summary projects completed + aborted runs, counts,
      cost 0.0, write_summary JSON; orchestration leaves matching summary.json;
      status→exit-code mapping incl. reserved codes.

## Dev Notes

Builds on 1.2 (events/reader), 1.4 (run dir), 1.7 (orchestrator, `wcs run`). This
story adds the projected summary + the exit-code contract. Do NOT implement
`wcs runs` listing (1.9) or decisions/cost (Epic 4); reserve their exit codes and
leave `cost_usd` at 0.0 with a note.

**Summary is a projection (Architecture → Event Architecture):** `summary.json`
is derived purely by replaying `events.jsonl` — never written field-by-field
during the run (avoids drift from the log). Compute it once the run has a terminal
event. Duration parses the `ts` ISO strings (informational) only for the human
duration field; ordering still comes from `seq`.

**Exit codes (NFR8):** headless runs must end with a deterministic code. Today the
deterministic strategy only produces completed/aborted; BLOCKED (unresolved
decision) and BUDGET_EXCEEDED arrive with Epic 4 — reserve their codes now so the
contract is stable. The loop already never blocks on input (no decision mechanism
yet), satisfying "never hangs" for the current slice.

**Patterns:** `replay/` imports only `events/` (no orchestration, no tui).
`core/exit_codes.py` is pure constants/logic. `run_orchestration` may import
`replay.summary` to write the projection (replay depends only on events; no cycle).

### Project Structure Notes

- New: `src/well_corp_sw/replay/summary.py`, `src/well_corp_sw/core/exit_codes.py`.
- Modified: `core/orchestrator.py` (write summary), `cli/run.py` (exit code),
  `docs/exit-codes.md` (real table).
- Tests: `tests/replay/test_summary.py`, `tests/core/test_exit_codes.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Event Architecture (Data Architecture, adapted)] — summary.json projected from events, not incremental.
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision / Human-in-the-Loop Model] — headless never hangs; deterministic exit codes.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.8] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR39 (summary), FR40 (deterministic exit codes); NFR8.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 53 passed; ty clean; lint-imports KEPT. Ruff flagged import order
  in a test + a reformat → autofixed; all green.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- `summary.json` is a pure projection of the finished log (built in `replay/`),
  written once after the terminal event — never incrementally (no drift).
- `cost_usd` is 0.0 until the Epic 4 cost meter emits usage events; BLOCKED(3) and
  BUDGET_EXCEEDED(4) exit codes are reserved now so the contract is stable.
- AC #3 ("never hangs"): the current headless loop has no decision/input path, so
  it always terminates with completed/aborted → a deterministic code; full
  decision/defer handling arrives in Epic 4.
- `core/orchestrator` imports `replay.summary` (replay depends only on events; no
  cycle); `replay/` never imports orchestration or tui (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/replay/summary.py (new)
- src/well_corp_sw/core/exit_codes.py (new)
- src/well_corp_sw/core/orchestrator.py (modified — write summary.json)
- src/well_corp_sw/cli/run.py (modified — status_to_exit_code)
- docs/exit-codes.md (modified — real table)
- tests/replay/test_summary.py (new)
- tests/core/test_exit_codes.py (new)
- tests/replay/__init__.py (new)

### Change Log

- 2026-06-09: Implemented story 1.8 — `summary.json` projected purely from the
  event log (`replay/summary.py`) and a deterministic exit-code contract
  (`core/exit_codes.py` + `docs/exit-codes.md`), wired into the orchestrator and
  `wcs run`. 6 tests. ACs satisfied; status → review.
