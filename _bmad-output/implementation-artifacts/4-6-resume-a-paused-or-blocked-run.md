# Story 4.6: Resume a paused or blocked run

Status: review

## Story

As a developer,
I want to resume a run that paused or blocked on a decision,
so that I don't lose progress.

## Acceptance Criteria

1. **Given** a non-terminal run (no `run.completed`/`run.aborted`), **When** I run
   `wcs resume <run-id>`, **Then** the run reloads from its existing log and
   continues to a terminal state (FR28).
2. **Given** resuming, **When** events are appended, **Then** they continue the
   same log with monotonic `seq` (append-only, determinism preserved).
3. **Given** an already-finished run, **When** I resume it, **Then** it reports
   that it is already finished (non-zero) and does not append.

## Tasks / Subtasks

- [x] Task 1: `core/run.py` — `RunError` + `resume_run(run_id, *, runs_root=None)`
      (locate dir else RunError; meta terminal → RunError; reopen JsonlEventWriter,
      seq continues; Run status "running").
- [x] Task 2: `cli/resume.py` `resume_command` (resume_run, RunError→stderr/non-zero;
      `run.complete()` + re-project summary; print id+status) + wired `resume`
      subparser; removed from stub list.
- [x] Task 3: Tests (5) — resume reopens + seq continues (0,1,2) append-only;
      finished/unknown → RunError; `wcs resume` finalizes a blocked run (run.completed
      appended, summary written); unknown id → non-zero.

## Dev Notes

Builds on 1.2 (writer resumes seq from an existing log), 1.4 (run store/meta),
1.8 (summary). The MVP resume reopens an unfinished run's log and brings it to a
terminal state — the append-only writer continues `seq` so determinism/replay are
preserved (AC #2). Full mid-flight continuation (re-entering the orchestration at
the exact pending decision and resuming agent work) requires the real Claude-SDK
strategy + checkpointing and is a follow-on; here "continue" means finalize the
previously-open run.

**Terminal detection:** use `meta.json` `status` (running vs completed/aborted).
`start_run` writes status `running`; a finished run is completed/aborted. Resuming
a terminal run is refused (AC #3) so a done run is never reopened.

**Determinism (AC #2):** `JsonlEventWriter` already computes its next `seq` by
reading the existing log, so reopening continues monotonically and the reader's
strictly-increasing-seq invariant holds.

**Patterns:** `core/run.py` (resume primitive), `cli/resume.py` wires it +
`replay.summary`. No tui. Plain output; no TTY needed.

### Project Structure Notes

- Modified: `src/well_corp_sw/core/run.py` (RunError + resume_run), `cli/app.py`
  (wire `resume`). New: `src/well_corp_sw/cli/resume.py`.
- Tests: `tests/core/test_resume.py`, `tests/cli/test_resume_cli.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision / Human-in-the-Loop Model] — resume a paused/blocked run.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.6] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR28 (resume paused/blocked run).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 143 passed (5 resume); ty clean; lint-imports KEPT; one E501 in
  run.py fixed by wrapping the `Run(...)` call.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- MVP resume: reopen a non-terminal run's append-only log (writer continues seq from
  the existing log → determinism/replay preserved, AC#2) and finalize it. Full
  mid-flight continuation (re-enter the orchestration at the pending decision) needs
  the real Claude-SDK strategy + checkpointing — a follow-on.
- Terminal detection via `meta.json` status; a finished run is refused (AC#3).
- `core/run.py` + `cli/resume.py` (uses `replay.summary`); no tui (import-linter KEPT).
- **Closes Epic 4 (Decisions & Safety) AND the MVP (Epics 1–4).** ACs satisfied;
  status → review.

### File List

- src/well_corp_sw/core/run.py (modified — RunError + resume_run)
- src/well_corp_sw/cli/resume.py (new)
- src/well_corp_sw/cli/app.py (modified — wire `resume`)
- tests/core/test_resume.py (new)
- tests/cli/test_resume_cli.py (new)

### Change Log

- 2026-06-09: Implemented story 4.6 — `resume_run` + `wcs resume` (reopen
  non-terminal log, seq continues, finalize). 5 tests. Closes Epic 4 / MVP.
  Status → review.
