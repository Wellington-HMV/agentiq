# Story 1.2: Event model and append-only JSONL log

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want typed events written to an append-only, seq-ordered JSONL log,
so that every run has a faithful, crash-safe, replayable record.

## Acceptance Criteria

1. **Given** the event models (Pydantic v2) for run/agent/vault/decision/result/
   failure, **When** events are written during a run, **Then** each line is
   `{seq, ts, run_id, agent_id, type, payload}` with monotonic `seq`.
2. **Given** the writer, **When** an event is written, **Then** the writer fsyncs
   so an interrupted run leaves a valid log up to the last completed event.
3. **Given** a log file, **When** the reader loads it, **Then** it validates each
   line and fails fast on a corrupt/incompatible line.
4. **Given** a log, **When** events are read, **Then** ordering is by `seq` only,
   never wall-clock (NFR5), and the reader reproduces the exact written sequence.

## Tasks / Subtasks

- [x] Task 1: Event model (`events/models.py`) (AC: #1, #4)
  - [x] `Event` envelope (Pydantic v2): `seq`, `ts`, `run_id`, `agent_id`, `type`, `payload`.
  - [x] Typed payload models + `EVENT_PAYLOADS` registry for all 10 event types.
  - [x] `type` is lower.dotted; unknown `type` rejected via `model_validator`.
  - [x] Forward-compat: payload base `extra="ignore"`; payload kept as dict for lossless round-trip.
- [x] Task 2: Append-only JSONL writer (`events/writer.py`) (AC: #1, #2)
  - [x] `JsonlEventWriter(path)` append mode, UTF-8, `\n`.
  - [x] `write(type, payload, *, run_id, agent_id, ts)` assigns monotonic seq (0 fresh, resumes from existing log).
  - [x] flush + `os.fsync` after every line (crash-safe).
  - [x] seq is sole ordering authority; ts stamped via `datetime.now(UTC)`, informational.
  - [x] `close()` + context manager.
- [x] Task 3: JSONL reader/validator (`events/reader.py`) (AC: #3, #4)
  - [x] `read_events(path) -> Iterator[Event]` validating each line.
  - [x] `EventLogError` with line number on corrupt JSON / schema-incompatible line.
  - [x] Strictly-increasing seq enforced; ordering by seq not ts.
  - [x] Round-trip reproduces the written sequence.
- [x] Task 4: Tests (`tests/events/`) (AC: all)
  - [x] Model tests (5): valid; unknown type; missing required field; forward-compat extra keys; json round-trip.
  - [x] Writer tests (4): monotonic-from-0; one-object-per-line; fsync spy; append continues seq.
  - [x] Reader tests (4): round-trip equality; corrupt line → EventLogError(line 2); non-increasing seq rejected; partial trailing line reads prefix then fails.

## Dev Notes

Builds directly on the story 1.1 scaffold. This story implements ONLY the
`events/` foundation: the model, the writer, the reader. Do NOT implement the
EventBus (story 1.3), the run store/`~/.well-corp-sw/runs/` layout (story 1.4),
orchestration, or any consumer. The writer takes an explicit file path — the run
store decides the path later; here a temp file in tests is enough.

**Why this is first after scaffold:** the event vocabulary is the single contract
every other component couples to (core, adapter, replay, TUI, cost meter). The log
IS the database (event sourcing). Get the shape right and additive-only.

**Event envelope (exact JSON line shape, from Architecture):**
```json
{"seq": 42, "ts": "2026-06-09T12:00:00Z", "run_id": "01J...", "agent_id": "a3",
 "type": "vault.read", "payload": { ... }}
```
- `seq`: int, monotonic per run, the ONLY ordering authority (NFR5). Not wall-clock.
- `ts`: ISO-8601 UTC string, informational.
- field naming inside JSON: `snake_case`.
- `payload`: a typed Pydantic model per `type`; never a free-form dict.

**Pydantic v2 specifics:**
- Use `pydantic.BaseModel`; consider a discriminated union on `type` via
  `Field(discriminator="type")`, or a `type -> payload-model` registry mapping.
  Either is fine; the registry is simpler to extend additively. Pick one and keep
  it the single place new event types are added.
- For forward-compat on READ, payload models should tolerate unknown keys
  (`model_config = ConfigDict(extra="ignore")`) so older readers survive newer logs.
- Reject unknown top-level `type` strings at construction with a clear error.
- Validate envelopes with `model_validate_json` per line.

**Determinism & crash-safety (NFR5, NFR6):**
- The writer must `flush()` then `os.fsync()` after every line so an interrupted
  process leaves the log valid up to the last fully-written line.
- The reader must tolerate a trailing partial/corrupt final line by failing fast
  with a precise error (do not silently drop), but everything before it must read.
- Replers downstream rely on `seq` ordering; the reader asserts strictly
  increasing `seq`.

**Naming / async (from Implementation Patterns):**
- Modules `snake_case`; classes `PascalCase` (`Event`, `JsonlEventWriter`,
  `EventLogError`); functions `snake_case`.
- The writer here can be synchronous; the async bus (1.3) will wrap/offload file
  I/O. Do NOT add async to the writer in this story unless a test needs it — keep
  it simple and synchronous, fsync-per-write.
- Event `type` strings are `lower.dotted`, never `CamelCase`.

**Scope guard:** keep all new code under `src/well_corp_sw/events/`. Do not import
`tui` (import-linter will fail the build). Do not touch other packages.

### Project Structure Notes

- New files live in `src/well_corp_sw/events/` (the package already exists with an
  `__init__.py` from story 1.1): add `models.py`, `writer.py`, `reader.py`.
- Tests in `tests/events/` mirroring the package.
- No run-store path here; the writer is path-agnostic (tests use `tmp_path`).

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Event Architecture (Data Architecture, adapted)] — event sourcing, JSONL envelope, seq ordering, fsync, Pydantic validation.
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules] — event naming (lower.dotted), payload typed not free-form, additive-only, snake_case JSON.
- [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements] — NFR5 (deterministic replay), NFR6 (append-only crash-safe).
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2: Event model and append-only JSONL log] — acceptance criteria.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates (via `python -m uv run`): pytest 17 passed (4 cli + 13 events); ruff check
  + format clean; ty check clean; lint-imports KEPT (NFR17).
- ty initially flagged `Event(**base)` (object kwargs) in test helper → switched to
  `Event.model_validate(base)`; clean after.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented ONLY the `events/` foundation (model, writer, reader). No bus (1.3),
  run store (1.4), orchestration, or consumers — scope held.
- Payload kept as `dict` on the envelope (validated against typed registry models)
  for lossless JSON round-trips; forward-compat via `extra="ignore"` on payloads.
- Writer is synchronous + fsync-per-write (async bus wraps I/O in 1.3, per story note).
- `writer` imports `reader` (resume seq) — both in `events/`, no cross-boundary/tui import.
- All 4 ACs satisfied; status → review.

### File List

- src/well_corp_sw/events/models.py (new)
- src/well_corp_sw/events/writer.py (new)
- src/well_corp_sw/events/reader.py (new)
- tests/events/test_models.py (new)
- tests/events/test_writer.py (new)
- tests/events/test_reader.py (new)

### Change Log

- 2026-06-09: Implemented story 1.2 — Pydantic v2 event model + registry,
  append-only fsync-per-write JSONL writer, fail-fast validating reader with
  strict seq ordering. 13 event tests. All ACs satisfied; status → review.
