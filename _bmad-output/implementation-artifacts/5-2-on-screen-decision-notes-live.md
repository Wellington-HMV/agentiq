# Story 5.2: On-screen decision notes (live)

Status: review

## Story

As a developer,
I want pending decisions to surface as first-class notes in the live scene,
so that I can answer without leaving the world.

## Acceptance Criteria

1. **Given** a live run hits a human decision, **When** it pauses, **Then** a
   `DecisionNote` overlay shows the prompt, numbered options, and the marked
   default (FR26), and the scene pauses while it is open.
2. **Given** the overlay is open, **When** I pick an option (number) or press
   Enter (default), **Then** the decision resolves and the world resumes (the
   awaiting orchestration continues; `decision.resolved` is logged with the
   chosen value and `resolved_by = human`).
3. **Given** an invalid key (out-of-range digit, or Enter with no default),
   **When** pressed, **Then** the overlay stays open (no bad resolution).

## Tasks / Subtasks

- [x] Task 1: Resolver seam through the orchestration loop —
      `OrchestrationStrategy.run(..., resolver=None)`; `run_orchestration` gains a
      `resolver` param (defaults to `DefaultResolver`) and passes it to the
      strategy. `DeterministicStrategy`/`ClaudeStrategy.run` accept it (the
      deterministic path makes no decisions; the SDK path will route human
      decisions through it). Keeps human-in-the-loop a single seam (FR22/FR26).
- [x] Task 2: `tui/decision_note.py` — `DecisionNote(ModalScreen[str])` renders
      `format_decision_prompt` (prompt + numbered options + default); digit keys
      pick via `parse_choice`, Enter accepts the default; invalid keys are
      ignored (overlay stays). `TuiDecisionResolver` implements `Resolver`:
      `resolve()` awaits `app.push_screen_wait(DecisionNote(request))` and returns
      `(choice, "human")`.
- [x] Task 3: Wire `LiveWatchApp` to pass a `TuiDecisionResolver(self)` into
      `run_orchestration` so a live decision pauses the scene (the orchestrate
      worker awaits the modal) and resumes on resolution.
- [x] Task 4: Tests — `DecisionNote` renders prompt/options/default; digit picks
      the option; Enter picks the default; invalid digit keeps it open;
      `TuiDecisionResolver` resolves `request_decision` end-to-end (a worker blocks
      until the modal is answered, then `decision.resolved` is logged with the
      human choice). Updated the failing-strategy fake to accept `resolver`.

## Dev Notes

The decision is already an awaitable (4.3): `request_decision(adapter, request,
resolver)` emits `decision.pending`, awaits the `Resolver`, emits
`decision.resolved`. 5.2 adds the **TUI resolver**: instead of `PromptResolver`
reading a line, `TuiDecisionResolver` shows a modal and awaits the user's pick via
`push_screen_wait`. Because the orchestration runs in a Textual worker that
`await`s the resolver, the scene **pauses for free** while the modal is open and
**resumes** when it dismisses — no extra pause/resume state machine (AC #1/#2).

The resolver is threaded through the existing strategy seam rather than the bus:
the bus is render-only (NFR2, non-blocking) and a decision needs a value fed
*back* to the awaiting strategy, which only the resolver can do. `run_orchestration`
defaults to `DefaultResolver` so headless runs are unchanged (default-or-fail,
NFR8).

Reuses `format_decision_prompt`/`parse_choice` from `core/decision.py` so the live
overlay and the headless prompt share one render/parse — no divergence. Invalid
keys catch `DecisionUnresolved` and ignore it (overlay stays open, AC #3).

The deterministic strategy emits no decisions, so the end-to-end live trigger is
exercised via the real Claude-SDK strategy (a follow-on, like 4.6's resume note);
here the resolver + widget are proven against `request_decision` directly, which
is the exact call the SDK path will make.

### Project Structure Notes

- New: `src/well_corp_sw/tui/decision_note.py`, `tests/tui/test_decision_note.py`.
- Modified: `core/orchestrator.py` (resolver param), `agent/claude_strategy.py`
  (accept resolver), `tui/live.py` (pass TuiDecisionResolver),
  `tests/core/test_orchestrator.py` (fake accepts resolver).
- import-linter: `tui` may import `core`/`agent` (one-way rule unaffected; core
  side still must not import `tui`).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR26 (on-screen decision notes), FR22 (decision-as-awaitable).
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision / Human-in-the-Loop Model] — resolver seam.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Completion Notes List

- Resolver threaded through the strategy seam; `run_orchestration` defaults to
  `DefaultResolver` (headless unchanged).
- `DecisionNote` reuses `format_decision_prompt`/`parse_choice`; pause/resume is
  implicit (the worker awaits `push_screen_wait`).
- Live end-to-end decision trigger needs the Claude-SDK strategy (follow-on); the
  resolver + widget are verified against `request_decision` directly.

### File List

- src/well_corp_sw/tui/decision_note.py (new)
- src/well_corp_sw/core/orchestrator.py (modified — resolver seam)
- src/well_corp_sw/agent/claude_strategy.py (modified — accept resolver)
- src/well_corp_sw/tui/live.py (modified — pass TuiDecisionResolver)
- tests/tui/test_decision_note.py (new)
- tests/core/test_orchestrator.py (modified — fake accepts resolver)

### Change Log

- 2026-06-09: Implemented story 5.2 — `DecisionNote` overlay + `TuiDecisionResolver`
  + resolver seam through the orchestration loop. Live decisions pause/resume the
  scene. Status → review.
