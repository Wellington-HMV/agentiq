# Story 5.5: Per-agent worktree isolation

Status: review

## Story

As a developer,
I want concurrently-writing agents isolated,
so that parallel work doesn't conflict.

## Acceptance Criteria

1. **Given** isolation enabled (`worktree`) and agents writing concurrently,
   **When** they run, **Then** each writes in its own worktree and changes merge
   back without clobbering (FR35) — overlapping paths are reported, not silently
   overwritten.
2. **Given** isolation off (`serialize`), **When** concurrent writers run, **Then**
   they are serialized (one writer in the shared workspace at a time).
3. **Given** a run, **When** an isolation mode is configured, **Then** the
   orchestration exposes the matching isolation to the agent path.

## Tasks / Subtasks

- [x] Task 1: `core/isolation.py` — `Isolation` protocol (`workspace(agent_id)`
      async ctx + `merge_into(dest)` + `concurrent` flag), `WorktreeIsolation`
      (per-agent dirs, parallel writers, merge-with-conflict-report),
      `SerializeIsolation` (shared dir behind an `asyncio.Lock`), and
      `make_isolation(mode, *, project, worktree_base)`.
- [x] Task 2: Expose it on the agent path — `AgentAdapter.isolation` (optional);
      `run_orchestration(isolation_mode=...)` builds the isolation
      (worktree_base under the run dir, project as the shared workspace) and sets
      it on the adapter. `cli/run.py` passes `settings.isolation.mode`.
- [x] Task 3: Tests — worktree allows concurrent writers and merges disjoint files
      cleanly; worktree merge reports clobbered (overlapping) paths; serialize runs
      one writer at a time (max concurrency == 1); `make_isolation` selects the
      mode; `run_orchestration` wires the right isolation onto the adapter.

## Dev Notes

**FR35 — two isolation modes.**
- `worktree`: each agent gets its own directory (a git worktree in production), so
  parallel writes never touch the same files. `merge_into` folds the worktrees
  into the project and returns any relpath two agents both wrote — surfacing a
  conflict instead of clobbering. Disjoint work (the normal case for fanned-out
  subtasks) merges cleanly.
- `serialize`: all agents share one workspace guarded by an `asyncio.Lock`, so
  only one writer is inside at a time — no parallel speed-up, but no conflicts.
  The test proves the invariant by tracking max concurrent occupancy == 1.

**Seam, exposed via the adapter.** Isolation is offered to the agent path through
`adapter.isolation` (not a `strategy.run` signature change — that keeps the
Protocol and all strategy fakes stable). A writing strategy does
`async with adapter.isolation.workspace(agent_id) as ws: ...`. The shipped
`DeterministicStrategy` writes nothing, so isolation is inert offline (like the
resolver under the deterministic default); it matters for the Claude-SDK / any
file-writing strategy.

**Deterministic + offline implementations.** The classes are directory-based so
behavior is testable without git or network. Binding `worktree` to real
`git worktree add` (and a real 3-way merge) for the live file-writing path is a
follow-on — the seam and the merge/serialize semantics are settled here.

### Project Structure Notes

- New: `src/well_corp_sw/core/isolation.py`, `tests/core/test_isolation.py`.
- Modified: `agent/adapter.py` (`isolation` attribute), `core/orchestrator.py`
  (`isolation_mode` param builds + wires it), `cli/run.py` (pass config mode).
- import-linter: `core`/`agent` only; no tui import (NFR17 KEPT). `agent.adapter`
  imports `core.isolation` (stdlib-only module; no cycle).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.5] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR35 (per-agent worktree isolation).
- [Source: _bmad-output/planning-artifacts/architecture.md#Isolation] — isolation modes (serialize/worktree).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Completion Notes List

- `Isolation` seam with two deterministic, offline implementations: worktree
  (parallel + merge-with-conflict-report) and serialize (lock-shared workspace).
- Exposed via `adapter.isolation` (no strategy-Protocol churn); inert under the
  deterministic default, drives the file-writing strategy path.
- Real `git worktree add` + 3-way merge for the live path is a follow-on.

### File List

- src/well_corp_sw/core/isolation.py (new)
- tests/core/test_isolation.py (new)
- src/well_corp_sw/agent/adapter.py (modified — isolation attribute)
- src/well_corp_sw/core/orchestrator.py (modified — isolation_mode wiring)
- src/well_corp_sw/cli/run.py (modified — pass settings.isolation.mode)

### Change Log

- 2026-06-09: Implemented story 5.5 — `core/isolation.py` (worktree vs serialize)
  wired onto the adapter via `run_orchestration(isolation_mode=...)`. Worktree
  writers run parallel and merge without clobbering; serialize serializes them.
  Status → review.
- 2026-06-10: Follow-on landed — `GitWorktreeIsolation` does a real
  `git worktree add --detach` per agent (off-loop via `asyncio.to_thread`);
  `merge_into` copies changed+untracked files back; `make_isolation` auto-selects
  git vs plain-dir by `_is_git_repo(project)`. Deeper follow-on: 3-way git merge.
