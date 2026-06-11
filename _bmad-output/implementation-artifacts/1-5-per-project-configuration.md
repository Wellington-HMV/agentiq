# Story 1.5: Per-project configuration

Status: review

## Story

As a developer,
I want a `wcs.config.toml` parsed into typed settings with CLI overrides,
so that I can configure a project once and override per invocation.

## Acceptance Criteria

1. **Given** a `wcs.config.toml` at the project root, **When** `wcs` loads config,
   **Then** project binding, vault path(s), autonomy policy, cost ceiling, and
   isolation parse into typed (Pydantic) settings.
2. **Given** a loaded config, **When** a CLI flag provides a matching value,
   **Then** the CLI flag overrides the file value.
3. **Given** an invalid config (unknown key or wrong type), **When** it is loaded,
   **Then** loading fails fast with a specific message (not a generic error).
4. **Given** no config file (or missing sections), **When** config loads, **Then**
   documented defaults apply.

## Tasks / Subtasks

- [x] Task 0: Bump Python floor to 3.11 (stdlib TOML) — `requires-python >=3.11`,
      ruff `py311`, ty `3.11`. (Also surfaced UP017 in writer.py/run.py → autofixed to `datetime.UTC`.)
- [x] Task 1: Settings model (`config/settings.py`) — sectioned Pydantic v2
      (`project/vault/autonomy/cost/isolation`), documented defaults, `extra="forbid"` per level.
- [x] Task 2: Loader + overrides — `load_config` (tomllib, `ConfigError` on
      TOML/validation error naming file+problem), `find_config`, `apply_cli_overrides` (CLI > file, copy).
- [x] Task 3: Aligned `wcs.config.example.toml` to the real schema.
- [x] Task 4: Tests (`tests/config/test_settings.py`) — 7 tests: valid parse;
      empty→defaults; CLI override beats file (+ original untouched); unknown key;
      wrong type; invalid TOML; `find_config` present/absent.

## Dev Notes

Builds on the 1.1 scaffold and the `config/` package. Implements ONLY config
loading/validation/overrides. Do NOT wire config into orchestration or the CLI
run command yet (that lands when `wcs run` is implemented, story 1.7). The
`project` value here is the binding string; the run store (1.4) already resolves
project paths at `start_run`.

**Config schema (TOML → typed, from Architecture → Configuration & Policy):**
```toml
[project]
path = "."

[vault]
paths = ["../CSharp-Senior-Vault"]

[autonomy]
default = "ask"            # allow | deny | ask | default

[cost]
ceiling_usd = 5.0          # null/omitted = no ceiling

[isolation]
mode = "serialize"         # serialize | worktree
```
- CLI flags override file values (FR38). Precedence: CLI > file > defaults.
- Invalid config must fail fast with a precise message (FR37, NFR-style):
  surface which key/section/type is wrong, not a bare stack trace.

**Pydantic v2 specifics:**
- Use sectioned `BaseModel`s with `model_config = ConfigDict(extra="forbid")` so
  unknown keys are rejected (specific error → wrap in `ConfigError`).
- `autonomy.default` and `isolation.mode` are `Literal[...]` enums.
- `cost.ceiling_usd: float | None = None`.
- Keep the autonomy model minimal here — the full policy rule engine is story 4.2;
  this story only needs the default mode field to parse.

**TOML:** parse with stdlib `tomllib.loads(text)` (hence the 3.11 floor). Do NOT
add a third-party TOML library.

**Patterns:** `config/` may import nothing from `tui` (import-linter). Classes
`PascalCase` (`Settings`, `ConfigError`); functions `snake_case`. Synchronous.

### Project Structure Notes

- New: `src/well_corp_sw/config/settings.py`. Tests: `tests/config/test_settings.py`.
- Update `wcs.config.example.toml` (repo root) to match the schema.
- `pyproject.toml` floor bump (Task 0).

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Configuration & Policy] — `wcs.config.toml`, Pydantic settings, CLI overrides, fields.
- [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions] (Configuration & Policy) — TOML choice, precedence.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.5: Per-project configuration] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR37 (per-project config), FR38 (CLI flags override).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- `python -m uv sync` after the 3.11 floor bump (re-resolved cleanly).
- Gates: pytest 37 passed (4 cli + 7 config + 9 core + 17 events); ty clean;
  lint-imports KEPT. Ruff surfaced UP017 (`timezone.utc` → `datetime.UTC`) in
  writer.py/run.py once py311 was the target → autofixed; all green after.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- **Decision (minor, recorded):** bumped `requires-python` 3.10 → 3.11 so config
  TOML parsing can use stdlib `tomllib` without a `tomli` backfill dependency.
  Architecture noted the SDK floor as 3.10; 3.11 still satisfies the SDK.
- Implemented ONLY config loading/validation/overrides. Not yet wired into
  orchestration or `wcs run` (that's story 1.7) — scope held.
- Autonomy modelled minimally (`autonomy.default` only); the full policy rule
  engine is story 4.2, as noted in the story.
- `config/` imports only stdlib + pydantic — no tui/cross-boundary import.
- Updated `wcs.config.example.toml` to match the schema exactly.
- All 4 ACs satisfied; status → review.

### File List

- pyproject.toml (modified — Python floor 3.11, ruff/ty targets)
- src/well_corp_sw/config/settings.py (new)
- src/well_corp_sw/events/writer.py (modified — UP017 datetime.UTC)
- src/well_corp_sw/core/run.py (modified — UP017 datetime.UTC)
- wcs.config.example.toml (modified — aligned to schema)
- tests/config/test_settings.py (new)

### Change Log

- 2026-06-09: Implemented story 1.5 — sectioned Pydantic settings for
  `wcs.config.toml`, `load_config`/`find_config`/`apply_cli_overrides` with
  fail-fast `ConfigError` and CLI>file>defaults precedence. Bumped Python floor to
  3.11 for stdlib tomllib. 7 config tests. All ACs satisfied; status → review.
