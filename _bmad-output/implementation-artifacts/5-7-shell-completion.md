# Story 5.7: Shell completion

Status: review

## Story

As a developer,
I want shell completion for `wcs`,
so that commands and run-ids are fast to type.

## Acceptance Criteria

1. **Given** completion installed, **When** I tab-complete, **Then** subcommands,
   per-subcommand flags, and existing run-ids complete.
2. **Given** a command that takes a run id (`replay`/`resume`/`rerun`), **When** I
   tab on its first positional, **Then** run-ids from the store complete
   (prefix-filtered); once the run id is given, further tabs complete flags.
3. **Given** an unsupported shell, **When** I request its script, **Then** it errors
   clearly (non-zero).

## Tasks / Subtasks

- [x] Task 1: `cli/completion.py` — pure `complete(words, runs_root=...)` engine:
      subcommands (prefix-filtered), per-subcommand flags (a `SUBCOMMANDS` registry),
      and run-ids (from `list_runs`) for run-id commands until the positional is
      filled.
- [x] Task 2: `completion_script(shell)` — bash/zsh/fish scripts that wire Tab to a
      hidden `wcs __complete` callback (dynamic: new run-ids appear without
      reinstalling). Unsupported shell → `ValueError`.
- [x] Task 3: CLI — `wcs completion <shell>` prints the script; hidden
      `wcs __complete <words...>` prints candidates (one per line). Wired in
      `cli/app.py` (`__complete` help suppressed).
- [x] Task 4: Tests — subcommand/prefix/flag/run-id completion; no run-ids after the
      positional is filled; bash script wires the dynamic callback; unknown shell
      raises; the registry stays in sync with the real parser; the two CLI commands
      print the script and candidates.

## Dev Notes

**No new dependency.** Rather than `argcomplete`, completion is a tiny in-house
engine + generated scripts. The shells call back into a hidden `wcs __complete`
subcommand on every Tab, so completions are **dynamic** — newly created run-ids
complete immediately without regenerating the script.

**Pure engine, testable without a shell.** `complete(words, ...)` takes the tokens
after `wcs` (last = the current partial) and returns candidates:
- 0–1 tokens → subcommands matching the prefix.
- partial starts with `-` → that subcommand's flags.
- run-id command with an unfilled positional → run-ids from the store, prefix-filtered.
- otherwise → flags.

**Drift guard.** A `SUBCOMMANDS` registry mirrors the argparse parser; a test asserts
it equals the parser's real subcommands (minus the hidden `__complete`), so adding a
command without updating completion fails CI.

**Scope.** Scripts are best-effort wiring for bash/zsh/fish; the engine and the
`__complete` contract are the durable, tested part. `vault`'s positionals
(`validate`/`info` + path) aren't value-completed — only its presence as a
subcommand — which is a reasonable MVP boundary.

### Project Structure Notes

- New: `src/well_corp_sw/cli/completion.py`, `tests/cli/test_completion.py`.
- Modified: `cli/app.py` (wire `completion` + hidden `__complete`).
- No tui import (NFR17 KEPT); `cli` depends on `core.run`/`core.exit_codes` only.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.7] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — shell completion (commands, flags, run-ids).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Completion Notes List

- In-house completion (no `argcomplete`): pure `complete()` engine + bash/zsh/fish
  scripts that call a hidden `wcs __complete` for dynamic run-id completion.
- Run-id commands (`replay`/`resume`/`rerun`) complete store run-ids until the
  positional is filled, then flags.
- A registry-vs-parser sync test prevents completion drifting from the real CLI.

### File List

- src/well_corp_sw/cli/completion.py (new)
- src/well_corp_sw/cli/app.py (modified — wire completion + __complete)
- tests/cli/test_completion.py (new)

### Change Log

- 2026-06-09: Implemented story 5.7 — `wcs completion <shell>` + hidden
  `wcs __complete`; pure completion engine for subcommands/flags/run-ids. Closes
  Epic 5 (Live Watch / Growth). Status → review.
