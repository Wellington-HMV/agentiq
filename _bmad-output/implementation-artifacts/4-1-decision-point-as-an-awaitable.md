# Story 4.1: Decision point as an awaitable

Status: review

## Story

As a developer,
I want the core to pause at a decision point and await resolution,
so that human-in-the-loop never blocks forever.

## Acceptance Criteria

1. **Given** the orchestration reaches a decision point, **When** it needs a
   choice, **Then** it emits `decision.pending` and awaits resolution (FR22).
2. **Given** headless mode with no resolution path, **When** a decision arises,
   **Then** it fails (deterministically) rather than hanging (NFR8).
3. **Given** a resolution, **When** it is produced, **Then** `decision.resolved`
   is emitted with the choice and who resolved it.

## Tasks / Subtasks

- [x] Task 1: `core/decision.py` — `DecisionRequest`, `Resolver` Protocol,
      `DefaultResolver` (default-or-`DecisionUnresolved`), `request_decision`
      (emit pending → await resolver → emit resolved → return choice).
- [x] Task 2: Tests (3) — default resolves + both events (resolved_by="default");
      no-default raises `DecisionUnresolved` after pending only (no hang); custom
      resolver picks an option (resolved_by="policy").

## Dev Notes

First Epic 4 story. Establishes the decision MECHANISM only: emit-pending →
await-resolver → emit-resolved. The full policy engine (auto allow/deny/ask) is
4.2; interactive option/default UI resolution is 4.3; cost/safety are 4.4/4.5.
Here the only resolver is `DefaultResolver` (default-or-fail), which proves the
shape and the NFR8 "never hangs" property.

**Awaitable (FR22, NFR8):** `request_decision` awaits `resolver.resolve(...)`. A
resolver that waits on real human input (later) must back its await with a
future + timeout/default so it can never hang; the headless `DefaultResolver`
resolves immediately or raises. Raising `DecisionUnresolved` propagates to the
orchestrator, which aborts the run (terminal event + deterministic exit code) —
never a hang.

**Events:** reuse the 1.2 registry — `decision.pending` (prompt/options/default)
and `decision.resolved` (choice/resolved_by). Emitted via the adapter so they are
scrubbed, logged, and published like any event (and show as ◆ markers in replay).

**Patterns:** `core/decision.py` imports `agent.adapter` for typing/emit; no tui.
`request_decision` is async. `resolved_by` ∈ {"default", "policy", "human"}.

### Project Structure Notes

- New: `src/well_corp_sw/core/decision.py`. Tests: `tests/core/test_decision.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision / Human-in-the-Loop Model] — decision = awaitable; emit pending, await, resolve; never block forever.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR22 (pause at decision); NFR8 (never hang).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 118 passed (3 decision); ty clean; lint-imports KEPT; fixed one
  E501 (module docstring) then ruff/format clean.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Decision mechanism only: emit-pending → await-resolver → emit-resolved. The
  policy engine (4.2), interactive option/default resolution (4.3), cost/safety
  (4.4/4.5) are resolvers/guards on this same shape.
- NFR8 proven: `DefaultResolver` with no default raises `DecisionUnresolved`
  (pending emitted, no resolved) — the orchestrator will abort rather than hang.
- Events reuse the 1.2 registry (decision.pending/resolved), emitted via the
  adapter (scrubbed/logged/published; show as ◆ in replay).
- `core/decision.py` imports `agent.adapter`; no tui (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/core/decision.py (new)
- tests/core/test_decision.py (new)

### Change Log

- 2026-06-09: Implemented story 4.1 — decision-as-awaitable (`request_decision` +
  `Resolver`/`DefaultResolver`/`DecisionUnresolved`). 3 tests. Status → review.
