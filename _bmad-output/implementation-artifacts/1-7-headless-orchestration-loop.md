# Story 1.7: Headless orchestration loop

Status: review

## Story

As a developer,
I want to start a goal-driven run that the parent decomposes and delegates, unattended,
so that I can hand off work and walk away.

## Acceptance Criteria

1. **Given** `wcs run "<goal>" --project <path> --headless`, **When** the run
   executes with no human present, **Then** the parent decomposes the goal and
   delegates tasks to subagents (FR2).
2. **Given** headless mode, **When** the run executes, **Then** it completes or
   fails without requiring a TTY (FR4, NFR15).
3. **Given** a finished run, **When** its log is replayed, **Then** the event
   sequence is reproduced deterministically (FR18).

## Tasks / Subtasks

- [x] Task 1: Exposed `Run.writer` property (shared writer → continuous seq).
- [x] Task 2: `core/orchestrator.py` — `OrchestrationStrategy` Protocol;
      `DeterministicStrategy` (no-network fixed pipeline analyze/implement/verify);
      `run_orchestration` (start_run → spawn parent → strategy → complete; exception → abort, no raise).
- [x] Task 3: `cli/run.py` `run_command` (resolve project flag→config→".",
      asyncio.run, print run_id+status, exit 0/1) + wired `run` subparser in
      `app.py` (goal positional, --project/--headless/--watch/--policy; --watch → not-implemented).
- [x] Task 4: Tests — orchestrator (4): expected sequence; determinism (same
      goal → same (type,payload) seq); replay reproduces contiguous seq (FR18);
      failing strategy aborts without raising. CLI run (1): `wcs run` exits 0 +
      creates log (temp runs_root). Also fixed test-package `__init__.py` (basename clash).

## Dev Notes

Builds on 1.2 (events), 1.3 (bus), 1.4 (run), 1.6 (adapter). This story wires the
loop that turns a goal into a logged, deterministic run. It deliberately ships a
**deterministic, no-network strategy** as the default so `wcs run` works and is
testable without an API key. The real Claude-SDK-backed strategy (driving
`claude_agent_sdk` live, which needs `ANTHROPIC_API_KEY` + network) is a
follow-on; keep it out of this slice and behind the same `OrchestrationStrategy`
seam. Do NOT implement run summary/exit-code table (1.8) or `wcs runs` (1.9).

**Architecture (Orchestration & Agent Integration):**
- The parent is the coordinator; subagents do delegated work. The orchestrator
  owns the Run lifecycle and drives the adapter; the strategy decides the actual
  decomposition/delegation. Swapping the strategy (deterministic ↔ real SDK)
  changes behavior without touching the loop, log, or replay.
- Headless = no TTY, no stdin. The loop must never block on input; with no human
  resolution path a decision would fail/defer (decisions arrive in Epic 4 — not
  exercised here).

**Determinism (FR18, NFR5):** the default strategy must emit the same event
sequence for the same goal. The log is replayed via `read_events`; "deterministic
replay" means the on-disk `(seq, type, payload)` sequence is faithfully
reproduced and is stable across runs of the same goal (run_id and ts differ and
are excluded from the determinism comparison).

**Writer sharing:** `start_run` opens the writer and emits `run.started` (seq 0);
the adapter must reuse `run.writer` so subsequent events continue the same seq and
`run.complete` appends the terminal event on the same stream. Do not open a second
writer.

**Patterns:** `core/` may import `events/` and `agent/` but MUST NOT import `tui`
(import-linter). `cli/` wires everything. Async via `asyncio.run` at the CLI edge;
the core loop is `async`.

### Project Structure Notes

- New: `src/well_corp_sw/core/orchestrator.py`, `src/well_corp_sw/cli/run.py`.
- Modified: `src/well_corp_sw/core/run.py` (writer property),
  `src/well_corp_sw/cli/app.py` (wire `run`).
- Tests: `tests/core/test_orchestrator.py`, `tests/cli/test_run.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Orchestration & Agent Integration (API/Communication, adapted)] — parent/subagent, adapter seam, strategy.
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Sequence] — loop after adapter; deterministic replay.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.7] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR1, FR2, FR4, FR18; NFR15 (no-TTY).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 48 passed; ruff check + format clean; ty clean; lint-imports KEPT.
- Fixed a pytest collection clash (two `test_run.py`) by adding `__init__.py` to
  every `tests/` subpackage.
- **Real end-to-end smoke:** `wcs run "ship the thing" --project .` → exit 0,
  status `completed`, produced a run dir with an 9-event log (run.started → parent
  + 3 subagents spawned + 3 task.delegated → run.completed), seq 0–8 contiguous.
  (Note: `Path.home()` on Windows uses USERPROFILE, so the smoke run wrote to the
  real `~/.well-corp-sw/runs/`; the smoke run dir was deleted afterward. Tests use
  a patched temp runs_root.)

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- **First working `wcs run`** — the orchestration loop produces a complete,
  deterministic, replayable log end-to-end with NO API key (DeterministicStrategy).
- The real Claude-SDK-backed strategy (live agents, needs ANTHROPIC_API_KEY +
  network) is intentionally NOT in this slice — it plugs into the same
  `OrchestrationStrategy` seam later without touching the loop/log/replay.
- Failures become a terminal `run.aborted` event (run carries status), not a crash
  — keeps headless exit-code mapping (story 1.8) clean.
- `core/` imports `events/` + `agent/`, never `tui` (import-linter KEPT).
- ACs #1 (decompose+delegate), #2 (completes/fails, no TTY), #3 (deterministic
  replay) all satisfied; status → review.

### File List

- src/well_corp_sw/core/orchestrator.py (new)
- src/well_corp_sw/cli/run.py (new)
- src/well_corp_sw/core/run.py (modified — `writer` property)
- src/well_corp_sw/cli/app.py (modified — wired `run` subcommand + args)
- tests/core/test_orchestrator.py (new)
- tests/cli/test_run.py (new)
- tests/cli/test_app.py (modified — stub test uses `replay`)
- tests/__init__.py, tests/cli/__init__.py, tests/core/__init__.py,
  tests/events/__init__.py, tests/config/__init__.py, tests/agent/__init__.py (new)

### Change Log

- 2026-06-09: Implemented story 1.7 — headless orchestration loop with an
  injectable strategy seam and a deterministic no-network default; wired
  `wcs run`. First working end-to-end run producing a deterministic, replayable
  log. 48 tests. ACs satisfied; status → review.
