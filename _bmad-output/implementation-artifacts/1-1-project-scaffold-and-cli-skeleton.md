# Story 1.1: Project scaffold and CLI skeleton

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want an installable `wcs` CLI scaffold with linting, typing, and tests wired up,
so that I have a clean, cross-platform foundation to build every other feature on.

## Acceptance Criteria

1. **Given** a clean machine with uv installed, **When** the project is initialized
   per Architecture (`uv init --package`, deps added), **Then** `wcs --version` and
   `wcs --help` run and exit 0 with no TTY required.
2. **Given** the scaffold, **When** `ruff check`, `ruff format --check`, and `ty`
   are run, **Then** all pass on the empty scaffold.
3. **Given** the scaffold, **When** `pytest` is run (even with zero/one trivial
   test), **Then** it succeeds; **And** CI runs ruff + ty + pytest on Windows,
   macOS, and Linux.
4. **Given** the module layout, **When** `tui` is imported from any core-side
   module (`core`, `events`, `agent`, `vault`, `policy`, `cost`), **Then** an
   import-linter rule fails the build (enforces the one-way dependency direction,
   NFR17).

## Tasks / Subtasks

- [x] Task 1: Initialize the uv package project (AC: #1)
  - [x] Authored `pyproject.toml` in place (repo already existed) — packaged
        project with a `wcs` console entry point. (uv was not on PATH; installed
        via `python -m pip install uv` with user approval, invoked as `python -m uv`.)
  - [x] Set `requires-python = ">=3.10"`; dev runtime is the installed Python 3.14.
  - [x] Runtime deps `claude-agent-sdk`, `textual` declared and resolved.
  - [x] Dev deps `ruff`, `ty`, `pytest`, `pytest-asyncio`, `import-linter` declared.
  - [x] `uv.lock` generated via `uv sync`.
- [x] Task 2: Create the src-layout package skeleton (AC: #1, #4)
  - [x] Created `src/well_corp_sw/` with all boundary packages (`core`, `events`,
        `agent`, `vault`, `replay`, `tui`, `policy`, `cost`, `config`, `cli`), each
        with a documented `__init__.py`.
  - [x] `src/well_corp_sw/cli/app.py` — `wcs` root, `--version`/`--help`, no TTY.
  - [x] Console script wired: `wcs = "well_corp_sw.cli.app:main"`.
  - [x] `uv run wcs --version` → `wcs 0.1.0` (rc 0); `--help` prints usage (rc 0).
- [x] Task 3: Configure tooling in pyproject.toml (AC: #2)
  - [x] `[tool.ruff]` (py310, src layout) + vendor dir excludes (`.claude`, `_bmad`, …).
  - [x] `[tool.ty.environment]` + `[tool.ty.src]` scoped to `src`/`tests`.
  - [x] `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`.
  - [x] `ruff format --check`, `ruff check`, `ty check` all pass clean.
- [x] Task 4: Add the import-linter dependency rule (AC: #4)
  - [x] `import-linter` added as a dev dep.
  - [x] `[tool.importlinter]` forbidden contract: core-side packages must not import `well_corp_sw.tui`.
  - [x] Verified empirically: a probe `core` → `tui` import BREAKS the contract; removed → KEPT.
- [x] Task 5: Minimal test + test layout (AC: #3)
  - [x] `tests/` with `conftest.py` mirroring the package tree.
  - [x] `tests/cli/test_app.py` — 4 tests (version, help, no-command, stub subcommand).
  - [x] `uv run pytest` → 4 passed.
- [x] Task 6: CI workflow (AC: #3)
  - [x] `.github/workflows/ci.yml` on `[ubuntu, macos, windows]`.
  - [x] Steps: setup-uv, `uv sync --frozen`, ruff format/check, ty, lint-imports, pytest.
- [x] Task 7: Repo hygiene
  - [x] `.gitignore` (Python/uv/tool caches/runtime state).
  - [x] `README.md` (what `wcs` is + dev quickstart).
  - [x] `wcs.config.example.toml` stub (real schema in story 1.5).
  - [x] `docs/exit-codes.md` stub (real table in story 1.8).

## Dev Notes

This is the **first story** — greenfield scaffold. Everything is NEW; no files are
being modified. The goal is ONLY the foundation: an installable, lint/type/test-clean,
cross-platform `wcs` package with the module boundaries that every later story fills
in. Do NOT implement orchestration, events, TUI, vault, etc. here — just the empty
package skeleton and tooling.

**Tech stack (exact, from Architecture):**
- Python `>=3.10` (Claude Agent SDK floor), asyncio for the future core.
- `claude-agent-sdk` (the Python Agent SDK), `textual` (TUI) — added now but not used yet.
- Tooling: `uv` (env/deps/lock/run), `ruff` (lint+format), `ty` (type check),
  `pytest` + `pytest-asyncio`, `import-linter` (dependency direction).
- Package manager / runner is `uv` exclusively. All commands run via `uv run`.

**Module layout to create (src-layout) — responsibilities are for context only;
keep the dirs empty (just `__init__.py`) except `cli/app.py`:**
```
src/well_corp_sw/
  core/      # orchestration loop, run lifecycle — NO TTY, NO render imports
  events/    # event models (Pydantic), EventBus, JSONL writer/reader
  agent/     # Claude Agent SDK adapter (SDK <-> domain events)
  vault/     # VaultProvider ABC + HarnessVaultProvider
  replay/    # event reducer + scene projection + plain timeline
  tui/       # Textual app + widgets + TCSS (subscriber only)
  policy/    # autonomy policy + safety scoping
  cost/      # token/cost meter
  config/    # Pydantic settings, wcs.config.toml loader
  cli/       # command entrypoints (wcs ...)  <-- app.py lives here
```

**CRITICAL dependency rule (NFR17, AC #4):** import direction is one-way toward
`events`. `core`, `events`, `agent`, `vault`, `policy`, `cost` MUST NOT import
`tui`. `tui` and `replay` MUST NOT import orchestration logic. The import-linter
contract enforces (at minimum) "no core-side package imports `tui`". This is the
architectural invariant that keeps the headless core decoupled from render — get
the guardrail in place now, before any code can violate it.

**CLI command surface (full target, for context — only `--version`/`--help` are in
THIS story; the subcommands are stubbed/added in their own stories):**
`wcs run | replay | runs | vault | config | resume`. Subcommand names use
`lower-kebab`; flags use `--kebab-case`. Exit codes are deterministic and
documented in `docs/exit-codes.md` (populated in story 1.8). For now `--version`
and `--help` exit 0.

**No-TTY requirement (NFR15):** the CLI core must not assume a TTY. `wcs --version`
/`--help` must work when stdout is piped/redirected. Do not import or initialize
Textual in the CLI entry path for these commands.

**Naming conventions (enforced by Ruff):** modules/files `snake_case.py`,
packages `snake_case/`, classes `PascalCase`, functions/vars `snake_case`,
constants `UPPER_SNAKE`. Async I/O functions are verb-first, no `_async` suffix.

**Testing standards:** tests live in `tests/` mirroring the package tree,
`test_<module>.py`; async tests use `pytest-asyncio` (`asyncio_mode = "auto"`).
For this story a single trivial CLI test is enough to prove the harness runs.
"Done" = `ruff format --check`, `ruff check`, `ty`, `lint-imports`, and `pytest`
all green locally and in CI.

**Distribution note:** standalone binary packaging (PyInstaller/shiv) is explicitly
DEFERRED to a later distribution phase — do NOT attempt it here. MVP install path
is `uv`/pip.

### Project Structure Notes

- Aligns exactly with the Architecture "Project Structure & Boundaries" tree.
  Create the full directory skeleton now even though most dirs stay empty — it
  establishes the boundaries the import-linter enforces and that later stories
  fill in.
- `wcs.config.toml` is a PER-PROJECT file at a target project root (consumed in
  story 1.5); the repo only ships `wcs.config.example.toml` as a stub here.
- Runtime state lives under `~/.well-corp-sw/` (created in story 1.4) — not part
  of this story.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation] — `uv init --package`, deps, tooling, init command.
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries] — full src-layout tree, console script, CI.
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules] — naming, one-way import rule, import-linter enforcement.
- [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions] (Infrastructure & Deployment) — no servers/DB; CI = Ruff + Ty + pytest cross-OS.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1: Project scaffold and CLI skeleton] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements] — NFR15 (cross-OS, no-TTY core), NFR17 (separable modules via event bus).
- [Source: _bmad-output/planning-artifacts/prd.md#CLI Tool Specific Requirements] — `wcs` command surface, JSONL/exit-code direction.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- `python -m pip install uv` → uv 0.11.19 (uv was not preinstalled; user approved).
  Invoked throughout as `python -m uv` because the Scripts dir is not on the bash PATH.
- `python -m uv sync` → venv + uv.lock; installed textual 8.2.7, pydantic 2.13.4,
  ruff 0.15.16, ty 0.0.46, pytest 9.0.3, pytest-asyncio 1.4.0, import-linter, etc.
- Smoke: `wcs --version` → `wcs 0.1.0` (rc 0); `wcs --help` (rc 0).
- Gates: ruff format --check (14 files formatted) ✓; ruff check (All checks passed) ✓;
  ty check (All checks passed) ✓; lint-imports (1 kept, 0 broken) ✓; pytest (4 passed) ✓.
- AC#4 proof: temporary `core/_violation_probe.py` importing `tui` → contract BROKEN;
  probe removed → contract KEPT.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Greenfield scaffold only — no orchestration/event/TUI/vault logic implemented (scope held).
- **Deviation (approved):** uv not preinstalled → installed via pip and invoked as
  `python -m uv`. On a machine with uv on PATH the documented `uv …` commands work as-is.
- **Deviation (minor):** initialized in place by authoring `pyproject.toml` directly
  (repo pre-existed with `_bmad/` etc.) rather than `uv init --package well-corp-sw`,
  which would have created a nested subdir. Net result matches the story intent.
- Ruff/ty scoped to `src`/`tests`; the vendored BMad dirs (`.claude`, `_bmad`,
  `_bmad-output`) are excluded so gates only judge our code.
- Dev runtime is Python 3.14.2; `requires-python` floor kept at `>=3.10` per architecture.
- All 4 ACs satisfied.

### File List

- pyproject.toml (new)
- uv.lock (new, generated)
- .gitignore (new)
- README.md (new)
- wcs.config.example.toml (new)
- docs/exit-codes.md (new)
- .github/workflows/ci.yml (new)
- src/well_corp_sw/__init__.py (new)
- src/well_corp_sw/core/__init__.py (new)
- src/well_corp_sw/events/__init__.py (new)
- src/well_corp_sw/agent/__init__.py (new)
- src/well_corp_sw/vault/__init__.py (new)
- src/well_corp_sw/replay/__init__.py (new)
- src/well_corp_sw/tui/__init__.py (new)
- src/well_corp_sw/policy/__init__.py (new)
- src/well_corp_sw/cost/__init__.py (new)
- src/well_corp_sw/config/__init__.py (new)
- src/well_corp_sw/cli/__init__.py (new)
- src/well_corp_sw/cli/app.py (new)
- tests/conftest.py (new)
- tests/cli/test_app.py (new)

### Change Log

- 2026-06-09: Implemented story 1.1 — uv-packaged `wcs` scaffold, src-layout
  module skeleton, ruff/ty/pytest/import-linter tooling, cross-OS CI, repo hygiene.
  All ACs satisfied; status → review.
