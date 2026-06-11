# Story 4.5: Action scoping and confirm-before-irreversible

Status: review

## Story

As a developer,
I want agent actions confined to allowed scope and gated before irreversible ones,
so that autonomous runs stay safe.

## Acceptance Criteria

1. **Given** a bound project + configured vault paths, **When** an agent attempts
   a file/shell action outside that scope, **Then** it is denied (FR33, NFR10).
2. **Given** an irreversible or outward-facing action, **When** attempted, **Then**
   it is blocked pending an explicit decision (FR34, NFR11).
3. **Given** a denied operation kind (config), **When** attempted, **Then** it is
   denied.

## Tasks / Subtasks

- [x] Task 1: `config/settings.py` — `SafetySection(denied_ops=[])` + `Settings.safety`.
- [x] Task 2: `policy/safety.py` — `AgentAction`, `SafetyDenied`, `SafetyGuard`
      (`in_scope` via `is_relative_to`; `evaluate` deny/confirm/allow),
      `authorize` (allow→True, deny→raise, confirm→`request_decision` proceed/cancel).
- [x] Task 3: Tests (5) — in_scope project/vault/outside; evaluate verdicts;
      authorize allow / deny-raises / confirm proceed+cancel (2 decision pairs logged).

## Dev Notes

Builds on 4.1 (decision) + 4.2/4.3 (resolvers). The guard is the enforcement point
the adapter/strategy consults before an agent acts; the real Claude-SDK strategy
will call `authorize` on each tool action. Scoping confines file/shell actions to
the bound project + vault paths (NFR10); irreversible/outward actions require an
explicit decision (FR34/NFR11) — reusing the decision mechanism (a `confirm`
becomes a `decision.pending`/`resolved` pair).

**Scope check:** resolve the action path and test `is_relative_to` each allowed
root (project + vaults). No path → not a filesystem action (scope N/A). Denied-op
kinds (from config `safety.denied_ops`) are refused outright.

**Confirm flow:** `authorize` turns a `confirm` verdict into a
`DecisionRequest(kind="irreversible", options=["proceed","cancel"], default=None)`
and runs `request_decision`; headless with no resolver → `DecisionUnresolved`
(run aborts — never silently proceeds with something irreversible).

**Layering:** `policy/safety.py` imports `core.decision` + `agent.adapter`
(core-side); no tui (import-linter). Pure `evaluate`; async `authorize`.

### Project Structure Notes

- New: `src/well_corp_sw/policy/safety.py`. Modified: `config/settings.py`
  (SafetySection). Tests: `tests/policy/test_safety.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Cost & Safety (Security, adapted)] — action scoping; irreversible/outward blocked pending decision.
- [Source: _bmad-output/planning-artifacts/architecture.md#Autonomous-Agent Safety] — allowed/denied ops, confirm before irreversible.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.5] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR33 (allowed/denied ops), FR34 (confirm irreversible); NFR10/NFR11.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates clean first run: pytest 138 passed (5 safety); ruff/ty/format clean; lint-imports KEPT.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- The guard is the enforcement point an agent's tool actions pass through (the real
  Claude-SDK strategy will call `authorize` per action). Scope via `is_relative_to`
  (3.11) against project + vault roots; denied-op kinds refused; irreversible/outward
  → `confirm`.
- `confirm` reuses the decision mechanism (kind="irreversible", proceed/cancel),
  so blocks show as ◆ in replay; headless with no resolver → `DecisionUnresolved`
  (run aborts — never silently does something irreversible).
- `policy/safety.py` imports `core.decision` + `agent.adapter` (core-side); no tui
  (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/policy/safety.py (new)
- src/well_corp_sw/config/settings.py (modified — SafetySection)
- tests/policy/test_safety.py (new)

### Change Log

- 2026-06-09: Implemented story 4.5 — `SafetyGuard` (scope confinement + denied
  ops) + `authorize` (confirm-before-irreversible via decision). 5 tests.
  Status → review.
