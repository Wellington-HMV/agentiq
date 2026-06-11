# Story 1.6: Agent runtime adapter with secret scrubbing

Status: review

## Story

As a developer,
I want a single adapter wrapping the Claude Agent SDK that emits domain events,
so that the rest of the system depends on our event vocabulary, not the SDK, and no secret leaks.

## Acceptance Criteria

1. **Given** the adapter is the only module importing the Claude Agent SDK, **When**
   the parent spawns subagents and they act, **Then** SDK lifecycle hooks are
   translated into domain events on the bus.
2. **Given** the adapter, **When** the same agent id is spawned twice, **Then** the
   subagent is reused (one `agent.spawned` event), each agent keeping its own context.
3. **Given** the adapter, **When** any event is emitted, **Then** a `scrub()` pass
   removes API credentials before the event is written to the log or published.
4. **Given** a payload containing a credential, **When** the event is emitted,
   **Then** a unit test confirms the credential string appears in neither the log
   file nor the published event (it is masked).

## Tasks / Subtasks

- [x] Task 1: Secret scrubbing (`agent/scrub.py`) — `scrub(value, secrets)`
      recursive dict/list/str masking + `sk-ant-…` pattern redaction;
      `collect_secrets()` reads `ANTHROPIC_API_KEY`/`CLAUDE_API_KEY` values.
- [x] Task 2: Adapter + context (`agent/adapter.py`) — `import claude_agent_sdk`
      (single seam) + `sdk_module()`; `AgentContext` (id/role/parent_id/memory);
      `AgentAdapter.emit` (scrub → writer → bus), `spawn` (reuse/no-dup),
      `delegate`/`vault_read`/`fail`.
- [x] Task 3: Tests (6) — scrub literal+pattern nested; spawn-once-then-reuse;
      lifecycle events to log AND bus (identical); env collect; **credential leak
      test** (secret absent from event JSON, on-disk log, and bus — masked `***`).

## Dev Notes

Builds on 1.2 (events model/writer), 1.3 (bus), 1.4 (run). This story implements
the SDK seam + scrubbing + spawn/reuse registry and the `emit` translation. It
does NOT actually drive the SDK to run agents over the network — that wiring is
orchestration (story 1.7). Tests exercise the translation layer directly with a
real `JsonlEventWriter` (tmp file) + `EventBus`; no network, no API key needed.

**Architecture (from Orchestration & Agent Integration):**
- The adapter is the ONLY module that touches the Claude Agent SDK. Everything
  else depends on our domain events, never on SDK types. This is the single,
  swappable, testable integration seam.
- SDK lifecycle hooks (tool calls, subagent spawn, vault reads, results, failures)
  are translated by the adapter into domain events on the bus.
- Secrets are scrubbed at this boundary (NFR9): a `scrub()` pass runs before any
  event is published or written. No credential ever reaches `events`,
  `summary.json`, or a vault.

**emit() ordering:** scrub → `writer.write` (assigns seq, fsync; log is source of
truth) → `bus.publish(event)` (live fan-out). The same `Event` object is logged
and published, so they can never diverge.

**Spawn/reuse (FR3):** keep a `dict[str, AgentContext]`. First spawn registers and
emits `agent.spawned`; a repeat spawn of the same id returns the existing context
(reuse) and emits nothing. Each `AgentContext` is a distinct object (its own
context window, represented minimally here).

**Event types:** reuse the 1.2 registry (`agent.spawned`, `task.delegated`,
`vault.read`, `agent.failed`). Do not add new types in this story.

**Scrubbing approach:** mask exact secret literals (from `collect_secrets()`) and
the `sk-ant-` API-key pattern. Recurse dicts/lists; only strings are rewritten.
Keep it conservative — never log the key name's value anywhere.

**Patterns:** `agent/` may import `events/` but MUST NOT import `tui`
(import-linter). The "only module importing the SDK" rule is a convention enforced
by code review (import-linter currently guards the tui boundary, not the SDK);
keep all `claude_agent_sdk` imports in `agent/adapter.py`.

### Project Structure Notes

- New: `src/well_corp_sw/agent/scrub.py`, `src/well_corp_sw/agent/adapter.py`.
- Tests: `tests/agent/test_scrub.py`, `tests/agent/test_adapter.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Orchestration & Agent Integration (API/Communication, adapted)] — single SDK seam, hooks→events, scrub at boundary.
- [Source: _bmad-output/planning-artifacts/architecture.md#Cost & Safety (Security, adapted)] — credentials never written to events/summary/vault (NFR9).
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.6] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR2, FR3 (spawn/reuse subagents).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Verified `claude_agent_sdk` imports with no network/key side effects before wiring.
- Gates: pytest 43 passed (6 agent + prior); ty clean; lint-imports KEPT. Ruff
  flagged a long docstring (E501) → shortened; format reflowed 2 files; all green.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented the SDK seam + scrub + spawn/reuse + emit translation ONLY. The
  adapter does NOT yet drive the SDK over the network — that is orchestration
  (story 1.7). Tests exercise the translation layer with a real writer + bus, no
  API key / network.
- `claude_agent_sdk` is imported only in `agent/adapter.py` (the single seam),
  surfaced via `sdk_module()`. Note: import-linter currently guards the tui
  boundary, not the SDK; the "only adapter imports the SDK" rule is a convention
  (could add an import-linter contract later).
- `emit` order is scrub → writer.write (source of truth, fsync) → bus.publish, so
  logged and published events are the same object and cannot diverge.
- Credential leak test passes: secret absent from the event JSON, the on-disk
  log, and the bus payload (masked `***`) — satisfies NFR9 / AC #4.
- All 4 ACs satisfied; status → review.

### File List

- src/well_corp_sw/agent/scrub.py (new)
- src/well_corp_sw/agent/adapter.py (new)
- tests/agent/test_scrub.py (new)
- tests/agent/test_adapter.py (new)

### Change Log

- 2026-06-09: Implemented story 1.6 — Claude Agent SDK seam (`agent/adapter.py`)
  translating agent lifecycle into scrubbed domain events on log + bus, with a
  spawn/reuse registry and boundary secret scrubbing (`agent/scrub.py`). 6 tests
  incl. a credential-leak assertion. All ACs satisfied; status → review.
