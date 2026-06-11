# Story 3.4: Vault inspection command

Status: review

## Story

As a developer,
I want `wcs vault validate|info <path>`,
so that I can check and explore a vault outside a run.

## Acceptance Criteria

1. **Given** a vault path, **When** I run `wcs vault info <path>`, **Then** I see
   the manifest summary and entry list (id/title/tags) (FR11).
2. **Given** a vault path, **When** I run `wcs vault validate <path>`, **Then** it
   reports valid (exit 0) or the specific failure (non-zero).

## Tasks / Subtasks

- [x] Task 1: `cli/vault.py` `vault_command` — `validate` → `valid: <path>` or
      stderr `invalid: <VaultError>`; `info` → manifest summary + entries
      (`id  title  [tags]`), VaultError → stderr.
- [x] Task 2: wired `vault` subparser (vault_action choices validate|info + path),
      dispatch; removed from stub list (stub test now uses `config`).
- [x] Task 3: Tests (3) — info shows vault name + entry id; validate ok → "valid";
      validate on a dir without manifest → non-zero + "invalid".

## Dev Notes

Builds on 3.1 (provider), 3.2 (fail-fast validate). Read-only CLI surface over the
provider — no events, no run (agent consumption is story 3.5). Pipeable plain text,
no TTY required (NFR15).

**Exit codes:** reuse `core.exit_codes.ExitCode` — success 0, failure 1 (a
malformed vault). Keep messages specific (they come straight from `VaultError`).

**`info` vs `validate`:** `info` loads the index (so manifest/schema/frontmatter
errors still surface as failures) and lists entries; `validate` additionally
checks wikilinks and reports a clean valid/invalid verdict.

**Patterns:** `cli/vault.py` imports `vault/` + `core.exit_codes`; no tui. Plain
`print` to stdout for info, errors to stderr.

### Project Structure Notes

- New: `src/well_corp_sw/cli/vault.py`. Modified: `cli/app.py` (wire `vault`).
- Tests: `tests/cli/test_vault_cli.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#CLI Tool Specific Requirements] — `wcs vault <validate|info> <path>`.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR11 (inspect vault).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 112 passed (3 vault CLI); ruff/ty/format clean; lint-imports KEPT.
- Smoke: `wcs vault info tests/fixtures/vault` →
  `vault: test-vault (schema 1)` + entries `api-design`, `notes/auth.md`.
- The stub test (`test_subcommand_stub_returns_nonzero`) moved off `vault` (now a
  real command needing args) to `config`.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Read-only CLI over the provider; pipeable, no TTY (NFR15). Exit codes reuse
  `ExitCode` (0 ok / 1 invalid); error text comes straight from `VaultError` (specific).
- `info` lists entries (FR11); `validate` gives a clean valid/invalid verdict
  (incl. wikilink check from 3.2).
- Agent consumption during a run (FR5) is the last vault story, 3.5.
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/cli/vault.py (new)
- src/well_corp_sw/cli/app.py (modified — wire `vault`)
- tests/cli/test_vault_cli.py (new)
- tests/cli/test_app.py (modified — stub test uses `config`)

### Change Log

- 2026-06-09: Implemented story 3.4 — `wcs vault validate|info` over the harness
  provider. 3 tests. Status → review.
