# Story 4.2: Autonomy policy engine

Status: review

## Story

As a developer,
I want declarative policy rules deciding allow/deny/ask,
so that most decisions resolve automatically.

## Acceptance Criteria

1. **Given** policy rules in config, **When** a decision is evaluated, **Then** a
   matching rule auto-resolves it (allow/deny) without human input (FR24).
2. **Given** an `ask` match (or no match falling to an `ask` default), **When**
   evaluated, **Then** it routes to human resolution (or `DecisionUnresolved` when
   there is no human path — headless).
3. **Given** a resolution, **When** recorded, **Then** `decision.resolved` notes
   who resolved it (`policy`).

## Tasks / Subtasks

- [x] Task 1: `config/settings.py` — `AutonomyRule(kind, action)` +
      `AutonomySection(default: allow|deny|ask = "ask", rules: list[AutonomyRule])`;
      `AutonomyAction` Literal (dropped the old extra "default" value).
- [x] Task 2: `DecisionRequest.kind: str = "general"`.
- [x] Task 3: `policy/policy.py` `PolicyResolver(autonomy, ask_resolver=None)` —
      action for kind (first rule else default); allow→default/first-option/"allow",
      deny→"deny" (resolved_by="policy"); ask→delegate or `DecisionUnresolved`.
- [x] Task 4: example config shows `[autonomy] default` + `[[autonomy.rules]]`.
- [x] Task 5: Tests (6) — allow (w/ + w/o default), deny, ask-no-resolver raises,
      ask delegates to human, no-match → default action.

## Dev Notes

Builds on 4.1 (decision mechanism / `Resolver`). The policy engine is just a
`Resolver` that maps a decision's `kind` to an action via config rules — it plugs
into `request_decision` unchanged. Interactive (human) `ask` resolution is story
4.3 (the `ask_resolver`); cost/safety guards are 4.4/4.5. Keep matching simple:
exact `kind` match, first rule wins, else the default action.

**Action semantics:** `allow` resolves to a concrete affirmative choice (the
request's default, else its first option, else the literal "allow"); `deny`
resolves to "deny"; both are `resolved_by="policy"` (auto, no human). `ask` means
"a human must decide" → delegate to the injected `ask_resolver`, or raise
`DecisionUnresolved` in headless (NFR8 — the orchestrator aborts, no hang).

**Config:** `AutonomySection.default` is the fallback ACTION (allow|deny|ask),
default `ask`. `rules` is a list of `{kind, action}` (TOML `[[autonomy.rules]]`).
(Earlier the field allowed an extra "default" value; simplified to allow|deny|ask.)

**Patterns:** `policy/` imports `core.decision` (Resolver/DecisionRequest) +
`config`; no tui. `PolicyResolver.resolve` is async.

### Project Structure Notes

- Modified: `config/settings.py` (AutonomyRule + rules), `core/decision.py`
  (kind field), `wcs.config.example.toml`.
- New: `src/well_corp_sw/policy/policy.py`. Tests: `tests/policy/test_policy.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision / Human-in-the-Loop Model] — declarative rules allow|deny|ask|default; record applied rule.
- [Source: _bmad-output/planning-artifacts/architecture.md#Configuration & Policy] — autonomy policy in config.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR24 (auto-resolve by policy), FR25 (define policy).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 124 passed (6 policy); ty clean; lint-imports KEPT; one E501 in a
  test fixed by `ruff format`.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- `PolicyResolver` is just a `Resolver` (4.1) — plugs into `request_decision`
  unchanged. `allow`/`deny` are auto (resolved_by="policy"); `ask` delegates to an
  injected human resolver (story 4.3) or raises `DecisionUnresolved` headless (NFR8).
- Config gained `[[autonomy.rules]]` (kind→action); the old extra "default" action
  value was dropped (allow|deny|ask). Existing config tests still pass.
- `policy/` imports `core.decision` + `config`; no tui (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/policy/policy.py (new)
- src/well_corp_sw/config/settings.py (modified — AutonomyRule + rules)
- src/well_corp_sw/core/decision.py (modified — kind field)
- wcs.config.example.toml (modified — rules example)
- tests/policy/__init__.py (new)
- tests/policy/test_policy.py (new)

### Change Log

- 2026-06-09: Implemented story 4.2 — autonomy policy engine (`PolicyResolver` over
  config rules; allow/deny auto, ask delegates/raises). 6 tests. Status → review.
