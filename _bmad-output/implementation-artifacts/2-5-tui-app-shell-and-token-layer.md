# Story 2.5: TUI app shell and token layer

Status: review

## Story

As a developer,
I want the Textual app shell with the TCSS token layer and a keybinding footer,
so that all screens share one visual language and discoverable keys.

## Acceptance Criteria

1. **Given** the Textual app, **When** any screen is shown, **Then** a persistent
   footer lists the active keybindings (UX-DR8).
2. **Given** the token layer, **When** widgets render, **Then** colors/glyphs come
   from a central place with ASCII + no-color fallbacks (UX-DR7).
3. **Given** the app, **When** `q`/Esc is pressed, **Then** it backs out / quits
   consistently. The app runs headless (no real TTY) for tests.

## Tasks / Subtasks

- [x] Task 1: `tui/tokens.py` — `GLYPHS` (◆/✕/▶/library/desk/done/agent) +
      `ASCII_FALLBACK` + `glyph(name, ascii_only=False)`; `COLOR_ROLES` vocabulary.
- [x] Task 2: `tui/scene.tcss` — minimal version-safe layout (placeholder fills
      screen, dim).
- [x] Task 3: `tui/app.py` — `WcsApp(App)` with Header + `#scene-placeholder` +
      Footer; `BINDINGS=[q→quit]`; settable title via `on_mount`.
- [x] Task 4: Tests (2) — `run_test()` headless: composes, placeholder + footer
      present, title set, `q` quits; `glyph()` unicode default + ascii fallback + unknown.

## Dev Notes

First Textual code in the project. This story builds ONLY the shell + token layer;
the spatial scene widget (`SceneWidget`/`Creature`) is story 2.6 and the transport
bar + full key bindings are 2.7. Keep the body a labeled placeholder for now.

**Headless testing:** Textual's `App.run_test()` yields a `Pilot` and runs with a
headless driver (no real TTY) — perfect for pytest. Tests are `async` (the project
already uses `pytest-asyncio` auto mode). Use `pilot.press("q")` to exercise the
quit binding; assert widgets via `app.query_one(...)`.

**Token layer (UX-DR7):** all glyphs/markers live in `tui/tokens.py` with ASCII
fallbacks so terminals without wide-Unicode still render meaning (paired with the
no-color path later). The `◆`/`✕`/`▶` glyphs are the TUI's (the plain timeline uses
ASCII `D`/`F`); keep them here so 2.6/2.7 consume one source.

**TCSS safety:** Textual theme-variable names vary across versions; for this story
keep `scene.tcss` minimal (layout only) to avoid coupling to a specific var set —
richer themed styling arrives with the scene (2.6).

**Dependency rule:** `tui/` MAY import `replay/`/`events/` later (renderers), but
core-side packages MUST NOT import `tui` (import-linter contract — already KEPT).
`tui/` importing Textual is expected and fine.

### Project Structure Notes

- New: `src/well_corp_sw/tui/tokens.py`, `src/well_corp_sw/tui/scene.tcss`,
  `src/well_corp_sw/tui/app.py`. Tests: `tests/tui/test_app.py` (+ `__init__.py`).

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Design System Foundation] — Textual + TCSS base, custom token layer.
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#UX Consistency Patterns] — persistent keybinding footer; q/Esc backs out.
- [Source: _bmad-output/planning-artifacts/architecture.md#Rendering (Frontend Architecture, adapted)] — TUI is a pure subscriber; no orchestration logic.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.5] — acceptance criteria.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- First Textual code. `App.run_test()` headless pilot works under pytest-asyncio
  (no real TTY). Gates: pytest 79 passed (2 tui); ruff/ty/format clean; lint-imports KEPT.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Shell only — Header + placeholder body + Footer. Spatial scene (SceneWidget/
  Creature) is 2.6; full transport key bindings are 2.7. BINDINGS kept to `q→quit`
  so the footer has no dangling actions.
- Token layer centralizes glyphs with ASCII fallbacks (UX-DR7); `◆/✕/▶` are the
  TUI's, distinct from the timeline's ASCII `D/F`.
- TCSS intentionally minimal/version-safe (layout only) to avoid coupling to a
  specific Textual theme-var set; themed styling lands with the scene (2.6).
- `tui/` imports Textual (expected); core-side packages still do not import `tui`
  (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/tui/tokens.py (new)
- src/well_corp_sw/tui/scene.tcss (new)
- src/well_corp_sw/tui/app.py (new)
- tests/tui/__init__.py (new)
- tests/tui/test_app.py (new)

### Change Log

- 2026-06-09: Implemented story 2.5 — Textual app shell (`WcsApp`: header,
  placeholder body, keybinding footer, q-quit) + central token layer
  (`tui/tokens.py`) with ASCII fallbacks + minimal TCSS. 2 tui tests (headless
  pilot). Status → review.
