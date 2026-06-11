# Story 1.4: Run store and lifecycle

Status: review

## Story

As a developer,
I want each run persisted under a stable run directory with a project binding,
so that runs can be listed, resumed, and replayed later.

## Acceptance Criteria

1. **Given** a run is started against a bound project directory, **When** the run
   begins, **Then** a `~/.well-corp-sw/runs/<run_id>/` dir is created with
   `meta.json` + `events.jsonl`.
2. **Given** a started run, **When** the `run_id` is generated, **Then** it is a
   sortable ULID (lexicographically increasing with time).
3. **Given** a run, **When** it starts and finishes, **Then** a `run.started`
   event opens the log and a `run.completed` (or `run.aborted`) event closes it.
4. **Given** a finished run, **When** `meta.json` is read, **Then** it records
   run_id, goal, project (resolved absolute path), status, and created timestamp.

## Tasks / Subtasks

- [x] Task 1: Sortable ULID (`core/ids.py`) (AC: #2)
  - [x] `new_ulid(timestamp_ms=None, randomness=None)` — 26-char Crockford base32, 48-bit time + 80-bit random, injectable.
  - [x] Lexicographic order tracks time.
- [x] Task 2: Run store + lifecycle (`core/run.py`) (AC: #1, #3, #4)
  - [x] `default_runs_root()` = `~/.well-corp-sw/runs`; override via `runs_root`.
  - [x] `start_run(goal, project, *, runs_root=None, run_id=None) -> Run`: ULID dir,
        `JsonlEventWriter` on `events.jsonl`, `meta.json` (status running), emit `run.started`.
  - [x] `Run` holds run_id/goal/project(resolved)/root_dir/events_path/meta_path/writer/status.
  - [x] `Run.complete(status)` → `run.completed` + meta + close.
  - [x] `Run.abort(reason)` → `run.aborted` + meta `aborted` + close.
  - [x] Context manager: clean exit completes; exception aborts (reason from exc) and re-raises.
- [x] Task 3: Tests (`tests/core/test_ids.py`, `tests/core/test_run.py`) (AC: all) — 9 tests:
  - [x] ULID: length 26; time-sortable; Crockford alphabet.
  - [x] `start_run` creates `<root>/<run_id>/{meta.json,events.jsonl}`.
  - [x] First event `run.started` seq 0 with goal + resolved project.
  - [x] `complete()` appends `run.completed` + meta status; `abort()` appends `run.aborted` + reason.
  - [x] meta.json round-trips fields.
  - [x] Context manager aborts on exception and re-raises.

## Dev Notes

Builds on 1.2 (`events/writer.py`, `events/models.py`, `events/reader.py`). This
story persists a run as a directory and bounds its lifecycle with events. Do NOT
implement config loading (1.5), the agent adapter (1.6), orchestration (1.7), or
`wcs runs` listing (1.9 / story 1.8) — only the on-disk run store + lifecycle.

**Run store layout (from Architecture → Event Architecture):**
```
~/.well-corp-sw/runs/<ulid>/
  events.jsonl     # the append-only log (story 1.2 writer)
  meta.json        # run_id, goal, project, status, created_ts
  summary.json     # NOT here — projected in story 1.8
```
- `run_id` = sortable ULID (no DB; `wcs runs` later globs this dir).
- The writer from 1.2 owns `events.jsonl`; this story opens it on the right path
  and drives the lifecycle events.
- `meta.json` is small mutable run metadata; the authoritative record is still the
  event log. `summary.json` is deferred to 1.8 (projected from events) — do not
  write it here.

**Lifecycle events (use the 1.2 model registry):**
- `run.started` payload = `{goal, project}` (RunStartedPayload).
- `run.completed` payload = `{status}` (RunCompletedPayload).
- `run.aborted` payload = `{reason}` (RunAbortedPayload).
These already exist in `EVENT_PAYLOADS`; do not add new event types here.

**Project binding:** resolve `project` to an absolute path and store it; this is
the directory agents will later operate on. Full validation (exists, policy,
vault) belongs to config (1.5) — here just resolve + record.

**ULID:** implement locally (no new dependency). Crockford base32 alphabet
`0123456789ABCDEFGHJKMNPQRSTVWXYZ`. 128 bits = 48-bit ms timestamp (high) + 80-bit
randomness (low) → 26 chars. Make timestamp/randomness injectable so tests are
deterministic. Real runtime may use `time.time()` and `os.urandom` (these are
fine in app code — the no-clock/no-random rule applies only to Workflow scripts).

**Patterns:** `core/` may import `events/` but MUST NOT import `tui` (import-linter).
Classes `PascalCase` (`Run`); functions `snake_case`. Keep file I/O synchronous
here (matches the 1.2 sync writer); async orchestration wraps it later.

### Project Structure Notes

- New: `src/well_corp_sw/core/ids.py`, `src/well_corp_sw/core/run.py` (the `core`
  package already exists from 1.1).
- Tests: `tests/core/test_ids.py`, `tests/core/test_run.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Event Architecture (Data Architecture, adapted)] — run store dir per run, ULID, meta.json/events.jsonl, summary.json projected later.
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision / Human-in-the-Loop Model] — run lifecycle events bound a run.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4: Run store and lifecycle] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements] — NFR6 (crash-safe log), NFR8 (run ends deterministically).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates (via `python -m uv run`): pytest 30 passed (4 cli + 9 core + 17 events);
  ruff check clean; ruff format reformatted run.py once then clean; ty clean;
  lint-imports KEPT.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented ONLY `core/ids.py` + `core/run.py`. No config (1.5), adapter (1.6),
  orchestration (1.7), or `wcs runs` listing — scope held.
- ULID implemented locally (no new dependency); timestamp/randomness injectable
  for deterministic tests.
- Reused the 1.2 event types from `EVENT_PAYLOADS` (run.started/completed/aborted);
  no new event types added.
- `summary.json` intentionally NOT written (projected from events in story 1.8).
- `core/run.py` imports `events/` only (writer) — no tui/cross-boundary import.
- All 4 ACs satisfied; status → review.

### File List

- src/well_corp_sw/core/ids.py (new)
- src/well_corp_sw/core/run.py (new)
- tests/core/test_ids.py (new)
- tests/core/test_run.py (new)

### Change Log

- 2026-06-09: Implemented story 1.4 — sortable ULID + run store/lifecycle
  (`~/.well-corp-sw/runs/<ulid>/` with meta.json + events.jsonl, run.started/
  completed/aborted lifecycle, context-manager abort-on-exception). 9 tests.
  All ACs satisfied; status → review.
