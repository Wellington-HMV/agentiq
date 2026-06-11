# Story 2.8: Inspect overlay

Status: review

## Story

As a developer,
I want to drill into a focused agent or event,
so that I can see detail without losing the scene.

## Acceptance Criteria

1. **Given** a focused event in the scene, **When** I press `enter`, **Then** an
   inspect overlay shows detail (event type/seq, payload, agent states, vault ref/
   decision rationale where present) without leaving the scene (UX-DR5).
2. **Given** the overlay, **When** I press `Esc`, **Then** it closes and the scene
   is restored with context intact.

## Tasks / Subtasks

- [x] Task 1: `tui/inspect.py` `render_inspect(controller)` — pure detail of the
      current event (seq/type/agent/ts) + payload lines + agents summary.
- [x] Task 2: `InspectOverlay(ModalScreen)` shows the text; `escape`/`i` dismiss
      (uses Textual's inherited `action_dismiss`); modal dims the scene beneath.
- [x] Task 3: app binding `enter`/`i` → `action_inspect` pushes the overlay from
      the controller (no-op without one); minimal centered/bordered TCSS.
- [x] Task 4: Tests (2) — render_inspect shows event type + payload value + agent
      id/status; `enter` pushes InspectOverlay (top screen), `escape` dismisses.

## Dev Notes

Builds on 2.3 (controller), 2.6 (scene), 2.7 (bindings). The overlay is a dumb
renderer of the controller's current state (NFR17) — drill-in detail, no new data
fetching. Decisions/cost specifics deepen in Epic 4; here show whatever the
current event payload carries (cause, ref, prompt, choice, etc.) generically.

**ModalScreen:** Textual's `ModalScreen` overlays the current screen and dims it,
so the scene is preserved underneath (UX: never destroy context). `escape`
dismisses via `self.dismiss()`. The overlay takes a pre-rendered text string so it
stays a pure renderer.

**Binding:** bind `enter` and `i` to `action_inspect`. The action builds the
inspect text from the controller and pushes the modal; it is a safe no-op when
there is no controller (static-scene path).

**Testing modals (headless):** in `run_test`, after `pilot.press("enter")` the
pushed screen is `app.screen` (top of the stack); assert its type. After
`pilot.press("escape")` the top screen is no longer the overlay.

**Patterns:** `tui/` only; pure `render_inspect`; no orchestration logic, no tui
import from core-side (import-linter).

### Project Structure Notes

- New: `src/well_corp_sw/tui/inspect.py`. Modified: `tui/app.py` (binding +
  action), `tui/scene.tcss` (overlay style). Tests: `tests/tui/test_inspect.py`.

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Component Strategy] — InspectOverlay (ModalScreen) drill-in; dims scene, Esc closes.
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#2.5 Experience Mechanics] — `enter` opens inspect without leaving the scene.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.8] — acceptance criteria.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 87 passed (2 inspect); ruff/format clean; lint-imports KEPT.
- ty flagged an LSP violation: my `action_dismiss` override was incompatible with
  `Screen.action_dismiss(result=None)` (async) → removed the override and let the
  `escape`/`i` bindings use Textual's inherited `action_dismiss`. Clean after.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- `render_inspect` is a pure renderer of the controller's current state — drill-in
  detail only, no data fetching (NFR17). Shows whatever the current event payload
  carries (ref/cause/prompt/choice) generically; richer decision/cost detail
  deepens in Epic 4.
- Modal preserves the scene beneath (dims, not destroys); Esc restores context.
- Bindings safe without a controller (static path) — `action_inspect` no-ops.
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/tui/inspect.py (new)
- src/well_corp_sw/tui/app.py (modified — inspect binding + action)
- src/well_corp_sw/tui/scene.tcss (modified — overlay style)
- tests/tui/test_inspect.py (new)

### Change Log

- 2026-06-09: Implemented story 2.8 — inspect overlay (`InspectOverlay` modal +
  pure `render_inspect`); `enter`/`i` opens, `esc` closes, scene preserved. 2 tests.
  Status → review.
