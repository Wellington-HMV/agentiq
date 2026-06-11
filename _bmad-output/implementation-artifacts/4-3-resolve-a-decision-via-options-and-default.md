# Story 4.3: Resolve a decision via options and default

Status: review

## Story

As a developer,
I want to answer a pending decision by choosing an option with a visible default,
so that answering is one keystroke.

## Acceptance Criteria

1. **Given** a pending decision needing human input, **When** I am prompted,
   **Then** options are presented with a clearly marked default (FR23).
2. **Given** the prompt, **When** I press Enter, **Then** the default is accepted;
   **When** I enter a number, **Then** that option is picked.
3. **Given** a resolved decision, **When** the run is replayed, **Then** it
   persists in the log (a ◆ decision marker).

## Tasks / Subtasks

- [x] Task 1: `core/decision.py` — `format_decision_prompt` (numbered options,
      default marked), `parse_choice` (empty→default-or-raise, number→option,
      exact text→itself, else raise), `PromptResolver(input_fn=input)`.
- [x] Task 2: Tests (5) — format marks default; parse variants incl. raises;
      PromptResolver picks option; through `request_decision` lands as
      `decision.resolved` (resolved_by="human", a decision marker); PolicyResolver
      `ask` routes to the prompt.

## Dev Notes

Builds on 4.1 (request_decision/Resolver) and 4.2 (PolicyResolver routes `ask`
here). This is the human resolver. The on-screen `DecisionNote` widget (live TUI)
is Growth (story 5.2); here resolution is a line-based prompt with an INJECTABLE
input function so it's testable and can't hang in tests. In a real TTY the default
`input_fn = input` is used; headless without a resolver still raises
`DecisionUnresolved` (NFR8) — unchanged.

**Choice semantics (FR23):** options are numbered 1..N with the default marked;
Enter (empty) accepts the default; a number selects; the exact option text also
works. Invalid input raises `DecisionUnresolved` (caller aborts; the loop/re-prompt
is a UI concern for the live note in 5.2). `resolved_by="human"`.

**Persistence (AC #3):** nothing new — `request_decision` already emits
`decision.resolved`, which the timeline marks `D` and the scene/transport mark ◆.
A test confirms the end-to-end log entry via a `PromptResolver`.

**Patterns:** all in `core/decision.py` (no tui); `input_fn` typed
`Callable[[str], str]`.

### Project Structure Notes

- Modified: `src/well_corp_sw/core/decision.py` (format/parse/PromptResolver).
- Tests: `tests/core/test_prompt_resolver.py`.

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#2.5 Experience Mechanics] — options + visible default; Enter=default, number=option.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.3] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR23 (resolve via options/default).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates clean first run: pytest 129 passed (5 prompt-resolver); ruff/ty/format
  clean; lint-imports KEPT.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Human resolver with an INJECTABLE `input_fn` (default `input`) so it's testable
  and can't hang; invalid input raises `DecisionUnresolved` (caller aborts) — the
  re-prompt loop is a live-note UI concern for story 5.2.
- Plugs into 4.2: `PolicyResolver(ask_resolver=PromptResolver(...))` routes `ask`
  decisions to the human prompt.
- AC#3 needed no new code — `request_decision` (4.1) already logs
  `decision.resolved`, which timeline marks `D` and scene/transport mark ◆;
  verified via a PromptResolver round-trip.
- All in `core/decision.py`; no tui (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/core/decision.py (modified — format/parse/PromptResolver)
- tests/core/test_prompt_resolver.py (new)

### Change Log

- 2026-06-09: Implemented story 4.3 — human decision resolution
  (`format_decision_prompt`/`parse_choice`/`PromptResolver`); Enter=default,
  number=option; routes from policy `ask`. 5 tests. Status → review.
