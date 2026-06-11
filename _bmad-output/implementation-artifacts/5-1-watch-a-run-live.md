# Story 5.1: Watch a run live

Status: review

## Story

As a developer,
I want `wcs run --watch` to show the scene updating in real time,
so that I can observe a tricky run as it happens.

## Acceptance Criteria

1. **Given** a run started with `--watch` on a TTY, **When** the run executes,
   **Then** the scene subscribes to the live event bus and updates as events arrive
   (FR19).
2. **Given** the live render, **When** the run executes, **Then** the render is a
   pure subscriber and never blocks or slows the core (FR20, NFR1, NFR2).
3. **Given** no TTY, **When** `--watch` is used, **Then** it falls back to a
   headless run (NFR7) rather than failing.

## Tasks / Subtasks

- [x] Task 1: `run_orchestration(..., bus=None)` shares the stream; ALSO routed run
      lifecycle through the bus — `Run.emit`/`start_run(bus=)` publish
      run.started/completed/aborted (previously written only to the log, so live
      subscribers never saw them).
- [x] Task 2: `tui/live.py` `LiveWatchApp(WcsApp)` — owns an EventBus, mounts
      SceneWidget; on_mount subscribes then runs two workers (orchestrate with the
      shared bus + consume the subscription, folding via reducer until terminal).
- [x] Task 3: `wcs run --watch` on a TTY launches `LiveWatchApp`; no TTY → headless.
- [x] Task 4: Test (1) — `run_test` workers run; scene state reaches `completed`
      with parent + subagents folded from the live stream.

## Dev Notes

First Growth story. The live mechanism reuses everything: the headless core
publishes to the bus (unchanged), and the TUI is a pure subscriber that folds the
same events through the single reducer (2.1) — so live and replay are identical
(NFR5) and the render never back-pressures the core (the bus publish is
non-blocking, story 1.3 / NFR2).

**Concurrency:** Textual owns the event loop; `LiveWatchApp` starts the
orchestration and the bus-consumer as Textual workers. Subscribe BEFORE starting
the orchestration so no early events are missed (the bounded queue buffers them).

**Determinism note:** the `DeterministicStrategy` emits all events almost
instantly, so "animation" is effectively immediate; the real Claude-SDK strategy
streams over time, giving the gradual motion. Either way the consume path is the
same.

**No-TTY fallback (AC#3):** `--watch` without a TTY runs headless (same as a
normal run) — the scene needs a terminal; never fail.

**Patterns:** `tui/live.py` imports `core.orchestrator` + `replay`/`events`;
core-side never imports tui (import-linter).

### Project Structure Notes

- Modified: `core/orchestrator.py` (bus param), `cli/run.py` (--watch launches live).
- New: `src/well_corp_sw/tui/live.py`. Tests: `tests/tui/test_live.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Rendering (Frontend Architecture, adapted)] — TUI pure subscriber; live + replay share the reducer.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR19/FR20; NFR1/NFR2.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 146 passed (1 live); ruff/ty/format clean; lint-imports KEPT.
- Found in testing: live subscriber received agent events but NOT run.started/
  completed (those were written straight to the log by `start_run`/`Run.complete`,
  bypassing the bus) → added `Run.emit` + `start_run(bus=)` so lifecycle events
  publish too. Updated the 1.7 CLI test's `fake_start` to accept the new `bus` kwarg.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Live render is a pure bus subscriber folding the single reducer (live==replay,
  NFR5); publish is non-blocking so the core is never back-pressured (NFR2).
- Subscribe-before-orchestrate avoids missing early events (bounded queue buffers).
- Deterministic strategy emits instantly (animation is immediate); the real
  Claude-SDK strategy streams over time for gradual motion — same consume path.
- `--watch` needs a TTY; without one it runs headless (NFR7).
- `tui/live.py` imports core/replay/events; core-side never imports tui (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/tui/live.py (new)
- src/well_corp_sw/core/orchestrator.py (modified — bus param)
- src/well_corp_sw/core/run.py (modified — Run.emit + bus on lifecycle/start_run)
- src/well_corp_sw/cli/run.py (modified — --watch launches LiveWatchApp)
- src/well_corp_sw/cli/app.py (modified — --watch help)
- tests/tui/test_live.py (new)
- tests/cli/test_run.py (modified — fake_start accepts bus)

### Change Log

- 2026-06-09: Implemented story 5.1 — live watch mode (`LiveWatchApp` + shared bus;
  lifecycle events now published to the bus). 1 test. Status → review.
