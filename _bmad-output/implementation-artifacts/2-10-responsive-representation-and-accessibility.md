# Story 2.10: Responsive representation and accessibility

Status: review

## Story

As a developer,
I want the scene to adapt to terminal size/capability and stay accessible,
so that it's legible everywhere and never hides the truth.

## Acceptance Criteria

1. **Given** different terminal sizes, **When** the scene is shown, **Then** the
   representation tier is chosen by (cols, rows): full ≥120×40, compact ≥80×24,
   else minimal (UX-DR9).
2. **Given** a terminal without wide-Unicode (or `--ascii`), **When** the scene
   renders, **Then** glyphs use ASCII fallbacks; meaning is never colour-only (UX-DR10).
3. **Given** `--no-anim` (reduced motion), **When** I play, **Then** the scene
   does not auto-animate — it advances a single step instead of running a timer.
4. **Given** a minimal tier or no TTY, **When** `wcs replay --scene` runs, **Then**
   it falls back to the plain timeline (NFR7).

## Tasks / Subtasks

- [x] Task 1: `tui/capabilities.py` — `choose_representation` (full≥120×40 /
      compact≥80×24 / minimal), frozen `Capabilities`, pure `detect(...)`,
      `from_environment` (shutil size + stdout-encoding unicode check).
- [x] Task 2: `WcsApp(..., ascii_only=False, reduced_motion=False)` passes ascii to
      SceneWidget/TransportBar; reduced_motion → `toggle_play` steps once (no timer).
- [x] Task 3: `wcs replay --scene` + `--ascii`/`--no-anim` flags; detect caps,
      route to timeline on no-TTY or minimal tier, else launch the scene with caps.
- [x] Task 4: Tests (4) — breakpoints; detect ascii (unicode_ok/flag) + motion
      carried; `WcsApp(ascii_only=True)` → SceneWidget ascii; reduced-motion space
      advances one step, `playing` stays False.

## Dev Notes

Builds on the token layer (2.5, ASCII fallbacks already exist), the scene/bar
(2.6/2.7). Closes Epic 2. The colour tiers (truecolor→256→16→no-colour) are
handled by Textual's own renderer + `NO_COLOR`; our explicit, testable controls
are the representation tier, ASCII glyph fallback, and reduced-motion. Keep the
detection pure (inputs in) with a thin `from_environment` wrapper.

**Representation (UX-DR9):** full ≥120×40, compact ≥80×24, else minimal. The full
vs compact visual difference (denser spacing) can be refined later; the decisive,
tested behaviour now is the tier function + that the minimal tier / no-TTY routes
to the timeline (NFR7) so the scene never breaks a small or non-interactive terminal.

**Accessibility (UX-DR10):** never colour-only — the scene already pairs glyph +
label + status text, so it reads at no-colour. `ascii_only` swaps glyphs to their
ASCII fallbacks (already in `tui/tokens.py`). Reduced motion (`--no-anim`) avoids
the auto-play timer: `space` advances a single step so nothing animates on a
timer; the user still scrubs manually.

**Patterns:** `tui/capabilities.py` is pure (stdlib only) + a thin env wrapper;
`tui/` may import it; no orchestration, no core-side tui import (import-linter).

### Project Structure Notes

- New: `src/well_corp_sw/tui/capabilities.py`. Modified: `tui/app.py` (ascii/
  reduced-motion wiring), `cli/replay.py` + `cli/app.py` (flags + tier routing).
- Tests: `tests/tui/test_capabilities.py` (+ extend app tests).

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Responsive Design & Accessibility] — breakpoints, capability tiers, reduced-motion, timeline fallback.
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#UX Consistency Patterns] — never colour-only.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.10] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements] — NFR7 (degrade to timeline), NFR13/NFR14 (legibility).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 94 passed (4 capabilities); ruff/format/ty clean after fixes;
  lint-imports KEPT. Fixed a long help string (E501) and switched the test to
  `query_one(SceneWidget)` (ty: `query_one("#scene")` returns base `Widget`).

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Capability detection is pure (`detect`/`choose_representation`) + a thin
  `from_environment` wrapper — testable without a real terminal.
- Colour tiers (truecolor→256→16→no-colour) are delegated to Textual + NO_COLOR;
  our explicit controls are representation tier, ASCII glyph fallback, reduced motion.
- Accessibility: scene already pairs glyph+label+status (never colour-only);
  `--ascii` swaps to ASCII glyphs; `--no-anim` avoids the auto-play timer (space
  steps once) — manual scrubbing still works.
- `wcs replay --scene` routes to the plain timeline on no-TTY OR the minimal tier
  (terminal too small) so the scene never breaks a small/headless terminal (NFR7).
- **Closes Epic 2 (Legible Replay): all 10 stories implemented.** ACs satisfied;
  status → review.

### File List

- src/well_corp_sw/tui/capabilities.py (new)
- src/well_corp_sw/tui/app.py (modified — ascii_only/reduced_motion wiring)
- src/well_corp_sw/cli/replay.py (modified — capability detection + tier routing)
- src/well_corp_sw/cli/app.py (modified — --ascii/--no-anim flags)
- tests/tui/test_capabilities.py (new)

### Change Log

- 2026-06-09: Implemented story 2.10 — terminal capability detection
  (representation tier + ASCII fallback + reduced motion) wired through the app
  and `wcs replay --scene`. 4 tests. Closes Epic 2. Status → review.
