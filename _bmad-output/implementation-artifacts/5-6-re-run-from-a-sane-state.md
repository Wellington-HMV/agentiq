# Story 5.6: Re-run from a sane state

Status: review

## Story

As a developer,
I want to re-run from the last good state after a failure,
so that I don't restart from scratch.

## Acceptance Criteria

1. **Given** a failed run, **When** I re-run from a sane prior point, **Then** a
   new run resumes from the last-good state rather than seq 0 (FR29) — the prior
   good events are carried forward and the continuation appends after the
   checkpoint.
2. **Given** the default re-run, **When** no checkpoint is given, **Then** the cut
   is just before the first `agent.failed`/`run.aborted`; an explicit `--at-seq`
   pins the checkpoint to a chosen prior seq.
3. **Given** re-running, **When** the new run is forked, **Then** the source run is
   left untouched (a fork, not a mutation); an unknown id or a run with no failure
   (and no `--at-seq`) is reported as an error.

## Tasks / Subtasks

- [x] Task 1: `core/run.py` — `rerun_from(run_id, *, at_seq=None, runs_root=None,
      new_run_id=None)`: read the source log, compute the last-good prefix (before
      the first failure marker, or `seq <= at_seq`), fork a NEW run (new ULID), seed
      it with the prefix re-stamped under the new id (seq preserved), and continue
      its writer after the checkpoint. `RunError` on unknown id / no-failure-without-
      at_seq / empty prefix.
- [x] Task 2: `cli/rerun.py` `rerun_command` + `wcs rerun <run-id> [--at-seq N]`
      wired in `cli/app.py`. MVP finalizes the forked run and re-projects its
      summary; prints the new id and the source id.
- [x] Task 3: Tests — default cut drops the failure and carries the good prefix
      forward (seq contiguous, ends `run.completed`); `--at-seq` pins the checkpoint;
      no-failure raises (but `at_seq` works); unknown id raises; the source log is
      byte-for-byte unchanged. CLI: forks + finalizes (new dir, no `agent.failed`,
      summary written); unknown id is non-zero.

## Dev Notes

Distinct from 4.6 `resume_run` (which *reopens a non-terminal run* and finalizes
the same log). 5.6 is for a **failed (terminal) run**: it **forks a new run**
seeded with the source's sane prefix, so the original record stays intact and the
re-run starts from the last-good state — not seq 0 (FR29).

**Checkpoint.** Default = index of the first `agent.failed`/`run.aborted`; the
prefix is everything before it. `--at-seq N` overrides with `seq <= N`. The prefix
must be non-empty (it always includes `run.started`).

**Seeding (event-sourcing-faithful).** The prefix events are re-written into the
new log via the same `JsonlEventWriter`, re-stamped with the new run id and their
original `ts`; the writer re-assigns `seq` 0..k contiguously (they were already
contiguous from the start, so `seq` is preserved) and `next_seq` continues right
after — the continuation appends at the checkpoint, never replaying it. The reader's
strictly-increasing invariant holds on the new log.

**Scope.** Like 4.6, the MVP `wcs rerun` seeds the sane prefix and finalizes the
forked run. Full mid-flight re-execution — re-entering the orchestration at the
checkpoint and redoing only the failed/after-failure work with the Claude-SDK
strategy + checkpointing — is a follow-on. The fork + last-good-prefix primitive is
the durable part settled here.

### Project Structure Notes

- Modified: `core/run.py` (`rerun_from` + `_FAILURE_TYPES`; imports `read_events`),
  `cli/app.py` (wire `rerun`).
- New: `cli/rerun.py`, `tests/core/test_rerun.py`, `tests/cli/test_rerun_cli.py`.
- No tui import (NFR17 KEPT). `core.run` imports `events.reader` (already a core
  dependency direction).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.6] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR29 (re-run from last-good state).
- [Source: _bmad-output/planning-artifacts/architecture.md#Event Sourcing] — append-only log / seq as the ordering authority; runs as projections of their log.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Completion Notes List

- `rerun_from` forks a NEW run seeded with the source's last-good prefix (default
  cut before the first failure; `--at-seq` overrides), so the continuation starts
  from the sane state, not seq 0 (FR29). Source run is never mutated.
- Seeding re-stamps prefix events under the new id (seq preserved); the writer
  continues after the checkpoint — event-sourcing-faithful, replay-valid.
- MVP CLI finalizes the fork; full mid-flight re-execution is a follow-on (needs
  the Claude-SDK strategy + checkpointing), mirroring 4.6's resume note.

### File List

- src/well_corp_sw/core/run.py (modified — rerun_from + _FAILURE_TYPES)
- src/well_corp_sw/cli/rerun.py (new)
- src/well_corp_sw/cli/app.py (modified — wire rerun)
- tests/core/test_rerun.py (new)
- tests/cli/test_rerun_cli.py (new)

### Change Log

- 2026-06-09: Implemented story 5.6 — `rerun_from` forks a new run seeded to the
  last-good prefix (FR29) + `wcs rerun [--at-seq]`. Source untouched; continuation
  resumes after the checkpoint. Status → review.
- 2026-06-10: Follow-on landed — `orchestrator.continue_run(run, strategy=...)`
  drives a forked/seeded run to a terminal state (no parent re-spawn), and
  `wcs rerun --continue` re-executes from the checkpoint instead of just finalizing.
