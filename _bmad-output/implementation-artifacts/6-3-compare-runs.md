# Story 6.3: Compare runs

Status: review

## Story

As a developer,
I want to compare or diff two runs,
so that I can see what changed between attempts.

## Acceptance Criteria

1. **Given** two run-ids, **When** I compare them, **Then** differences in
   decisions, outcomes, and cost are shown side by side (FR30).
2. **Given** runs with differing fields, **When** rendered, **Then** the differing
   fields/decisions are flagged.
3. **Given** an unknown run-id, **When** I compare, **Then** it errors clearly
   (non-zero).

## Tasks / Subtasks

- [x] Task 1: `replay/compare.py` — pure projection. `facts(events) -> RunFacts`
      (run_id, status/outcome, cost_usd, agents_spawned, ordered `DecisionRecord`s)
      reusing `build_summary` for the aggregates and pairing
      `decision.pending`→`decision.resolved` FIFO for per-decision detail.
- [x] Task 2: `render_comparison(RunComparison)` — side-by-side table of status,
      cost, agents, decision count, then a decision-by-decision diff; differing
      rows/decisions flagged with an ascii-safe `!=`; uneven decision lists padded
      with `—`.
- [x] Task 3: `cli/compare.py` `compare_command` + `wcs compare <a> <b>` wired in
      `cli/app.py`; missing run-id → clear error / non-zero. Added `compare` to the
      completion registry (drift guard stays green).
- [x] Task 4: Tests — `facts` projects outcome/cost/decisions; render flags
      differences; uneven decision counts padded; no-decisions case; CLI prints the
      side-by-side and errors on an unknown id.

## Dev Notes

A pure projection over two event logs — FR30's "decisions, outcomes, cost side by
side" derived entirely from events (single source of truth), never from mutable
`meta.json`. `facts` reuses `build_summary` for status/cost/fan-out and adds the
ordered decisions by pairing each `decision.pending` with the next
`decision.resolved` (FIFO), so the diff shows *what* was decided and *who* decided
it (`choice(resolved_by)`), not just a count.

`render_comparison` is a plain two-column table; differing fields and decisions are
flagged with `!=` (ascii-safe — avoids console-encoding issues on Windows), and
uneven decision lists are padded with `—`. Kept pure (no glyphs/TTY) so it's fully
unit-tested.

Lives in `replay/` alongside the other projections (summary/reducer); the CLI is a
thin reader + printer. The first run-id position is completion-aware; completing a
second run-id is a minor follow-on (the completion engine fills one positional).

### Project Structure Notes

- New: `src/well_corp_sw/replay/compare.py`, `src/well_corp_sw/cli/compare.py`,
  `tests/replay/test_compare.py`, `tests/cli/test_compare_cli.py`.
- Modified: `cli/app.py` (wire `compare`), `cli/completion.py` (registry entry).
- Pure core-side projection; no tui import (NFR17 KEPT).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.3] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR30 (compare/diff two runs).
- [Source: _bmad-output/planning-artifacts/architecture.md#Event Sourcing] — runs as projections of their logs.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Completion Notes List

- `facts` = pure projection (reuses `build_summary`, pairs pending→resolved FIFO for
  per-decision detail); `render_comparison` = side-by-side table flagging diffs with
  ascii-safe `!=`, padding uneven decision lists with `—`.
- `wcs compare <a> <b>`; unknown id → non-zero. Added to completion registry.
- Second-positional run-id completion is a minor follow-on.

### File List

- src/well_corp_sw/replay/compare.py (new)
- src/well_corp_sw/cli/compare.py (new)
- src/well_corp_sw/cli/app.py (modified — wire compare)
- src/well_corp_sw/cli/completion.py (modified — registry entry)
- tests/replay/test_compare.py (new)
- tests/cli/test_compare_cli.py (new)

### Change Log

- 2026-06-10: Implemented story 6.3 — `replay/compare.py` (facts + side-by-side
  render) + `wcs compare <a> <b>` (FR30). Status → review.
