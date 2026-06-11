# Story 5.4: Author autonomy policy

Status: review

## Story

As a developer,
I want to define which decisions auto-resolve vs ask,
so that I tune autonomy to my comfort.

## Acceptance Criteria

1. **Given** the policy config, **When** I define rules (per-`kind` allow/deny/ask
   + a default action), **Then** the engine applies them to both live and headless
   decisions (FR25).
2. **Given** an `allow`/`deny` action, **When** a matching decision occurs, **Then**
   it auto-resolves (`resolved_by = policy`) with no human prompt.
3. **Given** an `ask` action, **When** a decision occurs live, **Then** it surfaces
   a `DecisionNote` (human answers); headless has no human, so the run aborts
   rather than hangs (NFR8).

## Tasks / Subtasks

- [x] Task 1: Headless wiring — `wcs run` builds `PolicyResolver(settings.autonomy)`
      and passes it into `run_orchestration` (the resolver seam from 5.2). `ask`
      has no human resolver headless, so it raises → the run aborts (NFR8).
- [x] Task 2: Live wiring — `LiveWatchApp` accepts `autonomy` and builds
      `PolicyResolver(autonomy, TuiDecisionResolver(self))`; `allow`/`deny`
      auto-resolve, `ask` falls through to a `DecisionNote`. `wcs run --watch`
      passes `settings.autonomy`.
- [x] Task 3: Tests — headless allow auto-resolves (`resolved_by=policy`); headless
      `ask` aborts without hanging (pending logged, no resolved); a per-`kind` rule
      beats the default; live `ask` surfaces the note then resumes on answer; live
      `allow` auto-resolves with no note.

## Dev Notes

The policy engine (`PolicyResolver`, story 4.2) and its rules
(`AutonomySection`/`AutonomyRule`, config) already existed and were unit-tested.
5.4 is the **wiring**: connect config-driven policy to the two real run paths so
FR25 holds end-to-end. Both paths use the single `resolver` seam added in 5.2, so
no new decision plumbing — only resolver construction differs:

- **Headless** (`cli/run.py`): `PolicyResolver(settings.autonomy)` with no
  `ask_resolver`. `allow`/`deny` settle; `ask` raises `DecisionUnresolved` →
  `run_orchestration` aborts the run (NFR8 — headless never hangs).
- **Live** (`tui/live.py`): `PolicyResolver(autonomy, TuiDecisionResolver(self))`.
  `ask` routes to the on-screen `DecisionNote` (5.2), which pauses the scene until
  the human answers.

One engine, one seam → identical rule semantics in both modes (FR25). The default
`AutonomySection()` is `default="ask"`, so out of the box live prompts and headless
aborts on an unmatched decision — safe by default; the user opens up autonomy by
adding `allow` rules.

The `DeterministicStrategy` emits no decisions, so the resolver is inert for the
shipped offline default; it drives the Claude-SDK path and any deciding strategy.
Tests use a small decision-emitting strategy to exercise the wiring directly.

### Project Structure Notes

- Modified: `cli/run.py` (headless + live resolver construction), `tui/live.py`
  (`autonomy` param + PolicyResolver wrap).
- New: `tests/core/test_policy_wiring.py`, `tests/tui/test_live_policy.py`.
- import-linter: `tui/live.py` imports `policy`/`config` (one-way, allowed); core
  side still never imports `tui` (NFR17 KEPT).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.4] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR25 (author autonomy policy).
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision / Human-in-the-Loop Model] — policy resolver on the decision seam.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Completion Notes List

- Pure wiring story: `PolicyResolver` + rules already existed; 5.4 connects them to
  the headless and live run paths via the 5.2 resolver seam (FR25).
- Default-by-design: `ask` everywhere → live prompts, headless aborts (NFR8); the
  user opens autonomy with `allow` rules.
- Resolver is inert under `DeterministicStrategy` (no decisions); it drives the
  Claude-SDK / deciding strategies.

### File List

- src/well_corp_sw/cli/run.py (modified — headless + live resolver wiring)
- src/well_corp_sw/tui/live.py (modified — autonomy param + PolicyResolver)
- tests/core/test_policy_wiring.py (new)
- tests/tui/test_live_policy.py (new)

### Change Log

- 2026-06-09: Implemented story 5.4 — wired `PolicyResolver` (config autonomy
  rules) into both the headless and live run paths through the 5.2 resolver seam.
  allow/deny auto-resolve; ask prompts live / aborts headless. Status → review.
