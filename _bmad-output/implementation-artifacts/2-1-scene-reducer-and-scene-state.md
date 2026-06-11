# Story 2.1: Scene reducer and scene state

Status: review

## Story

As a developer,
I want a pure reducer that folds events into a scene state,
so that live and replay are guaranteed identical (one code path).

## Acceptance Criteria

1. **Given** a sequence of events from a run, **When** they are folded with
   `reduce(state, event)`, **Then** the resulting `SceneState` (agents, paths,
   current event, run status, caption) is deterministic.
2. **Given** the reducer, **When** applied, **Then** it is pure: it returns a new
   state and never mutates the input state.
3. **Given** an event type the reducer does not specially handle, **When** reduced,
   **Then** it is handled gracefully (seq advances, no crash) — forward-compat.

## Tasks / Subtasks

- [x] Task 1: `replay/scene_state.py` — `Zone`/`Status` constants, `AgentState`
      + `SceneState` dataclasses, `initial_state()`.
- [x] Task 2: `replay/reducer.py` — pure `reduce(state, event)` (copies agents/
      paths via `dataclasses.replace`, never mutates input; maps all known types to
      scene + caption; default branch advances seq for unhandled-but-valid types),
      `reduce_all(events, initial=None)`.
- [x] Task 3: Tests (4) — full-run fold (agents/paths/zones/status); determinism
      (equal folds); purity (input untouched, output advanced); unhandled valid
      event (`budget.exceeded`) advances seq, agents intact.

## Dev Notes

Builds on 1.2 (events). This is the SHARED projection that both replay (Epic 2)
and the live scene (Epic 5) render — there must be exactly ONE reducer so live and
replay can never diverge (NFR5, architecture "Rendering"). Implement ONLY the
reducer + state here; the timeline (2.2), transport (2.3/2.4), and Textual widgets
(2.5+) consume this state in later stories. No Textual import here — this is pure
domain projection in `replay/`.

**Purity (AC #2) is the crux:** `reduce(state, event)` must return a NEW
`SceneState` and leave `state` untouched. Copy the `agents` dict (and the
`AgentState` objects you change, via `dataclasses.replace`) and the `paths` list
before modifying. This is what lets the transport (2.3) cache states / step
backward and forward safely.

**Spatial mapping (UX floor-plan, Design Direction A):**
- `agent.spawned` (parent) → anchored parent; (subagent) → idle on the floor.
- `vault.read` → mover the agent to LIBRARY, status `reading`.
- `task.delegated` → add a path edge (from → to), delegating agent on PATH, target
  `working`.
- thinking/desk and richer motion come with the animated scene (2.6); keep the
  state model expressive enough now (status + zone) without animation concerns.
- `agent.failed` → status `failed`. run.completed/aborted → run_status + caption.

**Determinism:** the reducer uses no clock/random; identical event input →
identical `SceneState`. `ts` is never consulted (ordering is `seq`).

**Patterns:** `replay/` imports only `events/`; never `tui` or orchestration
(import-linter). Dataclasses `PascalCase`; functions `snake_case`.

### Project Structure Notes

- New: `src/well_corp_sw/replay/scene_state.py`, `src/well_corp_sw/replay/reducer.py`.
- Tests: `tests/replay/test_reducer.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Rendering (Frontend Architecture, adapted)] — scene state = reducer over events; same reducer for live and replay.
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Design Direction Decision] — office floor-plan: zones library/desks/subagents, delegation paths.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements] — NFR5 (deterministic; live/replay parity).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 63 passed; ruff clean; lint-imports KEPT. ty flagged a
  `dict[str, ...]` key typed `str | None` on `agent.spawned` → bound a local
  `key = aid or ""`; clean after.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- THE shared reducer for both replay (Epic 2) and the live scene (Epic 5) — one
  code path guarantees live/replay parity (NFR5).
- Pure: `reduce` copies `agents` (via `dataclasses.replace`) and `paths`, never
  mutating the input — verified by a purity test (input untouched).
- Spatial mapping per Design Direction A: spawned→floor/desk, vault.read→LIBRARY,
  task.delegated→PATH + edge. Richer motion/thinking comes with the animated scene (2.6).
- `replay/` imports only `events/` (import-linter KEPT); no Textual here.
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/replay/scene_state.py (new)
- src/well_corp_sw/replay/reducer.py (new)
- tests/replay/test_reducer.py (new)

### Change Log

- 2026-06-09: Implemented story 2.1 — pure scene reducer + SceneState/AgentState
  (the single shared live/replay projection). 4 tests. Status → review.
