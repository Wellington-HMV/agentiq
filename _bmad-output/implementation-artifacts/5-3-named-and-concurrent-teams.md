# Story 5.3: Named and concurrent teams

Status: review

## Story

As a developer,
I want to organize agents into named teams that can run concurrently,
so that larger work is structured.

## Acceptance Criteria

1. **Given** a goal that warrants multiple teams, **When** the parent organizes
   work, **Then** agents are grouped into named teams (FR6) — each agent carries
   its team name and the scene exposes a team -> members grouping.
2. **Given** multiple teams, **When** they run concurrently, **Then** they
   execute as concurrent tasks without event-ordering corruption (FR7): the
   recorded log stays strictly increasing and contiguous, and replays identically.

## Tasks / Subtasks

- [x] Task 1: Team tag on the agent vocabulary — `AgentSpawnedPayload.team`
      (additive, forward-compat); `AgentAdapter.spawn(..., team=None)` stores it on
      `AgentContext` and emits it in `agent.spawned`.
- [x] Task 2: Scene projection — `AgentState.team`; reducer reads `team` from
      `agent.spawned`; `SceneState.teams` property groups team name -> sorted
      member ids (FR6). Single reducer → live and replay grouping never diverge.
- [x] Task 3: `TeamStrategy(teams)` in `core/orchestrator.py` — spawns a lead per
      team (under the parent) + members (under the lead), all team-tagged, and runs
      teams as concurrent `asyncio.gather` tasks that interleave (`await
      asyncio.sleep(0)`), proving FR7 under real interleaving.
- [x] Task 4: Tests — concurrent teams produce a strictly-increasing, contiguous
      log (FR7) and a correct team grouping (FR6); all team spawn/delegate events
      present; an 8-team stress run stays ordered.

## Dev Notes

**FR7 — no event-ordering corruption under concurrency.** The serialization
point is the writer: `JsonlEventWriter.write` assigns one `seq` and appends with
**no `await` between read-seq and increment**. Under asyncio (single thread) a
`write` runs to completion without yielding, so concurrent team coroutines (which
yield via `await asyncio.sleep(0)`) can interleave *between* writes but never
*within* one. The log therefore stays strictly increasing and contiguous; the
reader's strictly-increasing invariant (1.2) is the regression guard.
Determinism is per-recorded-log (NFR5): replaying a captured log is identical;
the live generation order across separate runs may differ (expected for
concurrency) and is not a correctness property.

**FR6 — named teams.** Team is a tag on the agent, not a new entity/event: minimal
and additive (`agent.spawned.team`). The grouping is a pure projection
(`SceneState.teams`) so both live and replay derive it from the one reducer.
`TeamStrategy` models the parent's organization: lead-per-team under the parent,
members under the lead, all carrying the team name.

The deterministic and Claude-SDK strategies are unchanged; `TeamStrategy` is an
additional `OrchestrationStrategy` on the same seam. The Claude-SDK path can adopt
team tagging later by passing `team=` to `adapter.spawn` (the SDK translation in
`claude_strategy.py`); not wired here.

### Project Structure Notes

- Modified: `events/models.py` (team field), `agent/adapter.py` (spawn team),
  `replay/scene_state.py` (AgentState.team + SceneState.teams),
  `replay/reducer.py` (read team), `core/orchestrator.py` (TeamStrategy).
- New: `tests/core/test_teams.py`.
- import-linter: changes are core-side only; no tui import (NFR17 unaffected).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.3] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR6 (named teams), FR7 (concurrent teams, no ordering corruption).
- [Source: _bmad-output/planning-artifacts/architecture.md#Event Sourcing] — single writer / monotonic seq as the ordering authority.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Completion Notes List

- Team is an additive tag (`agent.spawned.team`); grouping is a pure projection
  (`SceneState.teams`) off the one reducer.
- `TeamStrategy` runs teams via `asyncio.gather` with real interleaving; the
  synchronous single-writer log serializes seq (FR7).
- Claude-SDK team tagging is a follow-on (pass `team=` in the SDK translation).

### File List

- src/well_corp_sw/events/models.py (modified — AgentSpawnedPayload.team)
- src/well_corp_sw/agent/adapter.py (modified — spawn team)
- src/well_corp_sw/replay/scene_state.py (modified — AgentState.team + teams)
- src/well_corp_sw/replay/reducer.py (modified — read team)
- src/well_corp_sw/core/orchestrator.py (modified — TeamStrategy)
- tests/core/test_teams.py (new)

### Change Log

- 2026-06-09: Implemented story 5.3 — team-tagged agents + `SceneState.teams`
  grouping (FR6) and concurrent `TeamStrategy` proven not to corrupt log ordering
  (FR7). Status → review.
- 2026-06-10: Follow-on landed — `claude_strategy` now tags each SDK subagent
  `team=<delegating agent id>`, so live-SDK runs group into teams in the scene too.
