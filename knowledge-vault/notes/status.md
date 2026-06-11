---
id: status
title: Build Status
tags: [status, progress]
type: doc
---

# Build Status

**FEATURE-COMPLETE.** All 6 epics / 41 stories implemented + tested. **230 tests
+ 2 skipped (live), all gates green** (ruff / ruff format / ty / import-linter).
Live SDK path validated against the real Claude (subscription). Stories are at
`review` (not yet run through the BMad code-review workflow → `done`).

## Epics (all implemented)

- **E1 Autonomous Run & Faithful Log (9):** `wcs run`/`runs`; event model + JSONL
  log; async EventBus; run store + ULID; per-project config; agent adapter + secret
  scrub; headless deterministic orchestration; summary + exit codes.
- **E2 Legible Replay (10):** `wcs replay` (timeline + spatial scene); pure reducer;
  transport (O(1) seek) + markers; Textual shell; SceneWidget floor-plan; transport
  bar; inspect overlay; runs browser; responsive/a11y.
- **E3 Knowledge Vaults (5):** VaultProvider + HarnessVaultProvider (fail-fast);
  VaultReader; `wcs vault validate|info`; vault-aware orchestration.
- **E4 Decisions & Safety (6):** decision-as-awaitable; policy engine; prompt
  resolver; cost meter + ceiling; action scoping + confirm-irreversible; `wcs resume`.
- **E5 Live Watch / Growth (7):** `wcs run --watch` (LiveWatchApp); on-screen
  DecisionNote (resolver seam); named/concurrent teams; autonomy policy wired live +
  headless; per-agent isolation; `wcs rerun` (+`--continue`); shell completion.
- **E6 Scale & Vision (4):** zoom/team/focus view modes; org-tree view; `wcs compare`
  (diff two runs); creature personalities (animated, legibility-bounded).

## Real Claude SDK — validated live

`ClaudeStrategy` (`wcs run --live`) runs through the machine's `claude` CLI on the
**subscription login** — no funded API key needed. Schema calibrated, spawn/delegate
+ cost + safety/decision guards wired and proven. See [[live-integration]].

## Done this session beyond features

- **Code-review pass** (6 parallel reviewers): fixed 7 real bugs (scrub dict keys,
  render_view dropped frame, run_command swallow ConfigError, config read errors,
  harness non-list tags, resume empty-log, teams sorted) + 6 regression tests.
- **5.x follow-on seams landed:** git-worktree isolation, SDK team-tag,
  `continue_run` mid-flight re-exec.
- **Live guards:** can_use_tool + disallowed_tools + max_budget_usd.

## Backlog (deferred, not urgent)

1. `ClaudeCliStrategy` — spawn `claude -p` subprocess directly (user-requested).
2. Make `can_use_tool` authoritative regardless of CLI settings (`permission_mode` /
   `SandboxSettings`); today `disallowed_tools` is the hard block.
3. Full 3-way `git merge` in GitWorktreeIsolation.
4. Run BMad code-review workflow → flip `review`→`done`; epic retrospectives.

See [[conventions]] to continue, [[learnings]] for gotchas, [[live-integration]] for
the SDK path.
