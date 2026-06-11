# Story 3.2: Vault validation with fail-fast

Status: review

## Story

As a developer,
I want a vault validated before a run starts,
so that a malformed vault never feeds agents bad context.

## Acceptance Criteria

1. **Given** a vault missing its manifest, with an unsupported `schema_version`,
   with unparseable note frontmatter, a duplicate entry id, or a broken wikilink,
   **When** validation runs, **Then** it fails fast with a specific message naming
   the offending file/entry (FR9).
2. **Given** a conformant vault, **When** validated, **Then** it validates
   successfully (no raise).

## Tasks / Subtasks

- [x] Task 1: `_index_note` wraps `yaml.safe_load` → `VaultError` naming the note;
      duplicate entry id → `VaultError` naming both paths; manifest/schema/wikilink
      errors from 3.1 kept (all specific).
- [x] Task 2: Tests (4) — invalid frontmatter names `notes/bad.md`; duplicate id
      'dup'; `schema_version = 2` → unsupported; conformant fixture validates.

## Dev Notes

Builds on 3.1 (provider/harness). This story only sharpens fail-fast validation so
every malformed-vault case yields a precise, actionable error pointing at the
offending file/entry (FR9). The `wcs vault validate` command surface is story 3.4;
running validation automatically before a run is story 3.5 — not here.

**Where errors arise:** frontmatter parse errors surface during `_index_note`
(wrap `yaml.safe_load`); duplicate ids during indexing; manifest/schema during
`_load`; wikilinks during `validate`. All raise `VaultError` with the relative
path so the developer knows exactly which note to fix.

**Fail-fast philosophy:** validation stops at the first concrete error with a
clear message rather than collecting all problems — matches the rest of the system
(config/event-log fail-fast). A future enhancement could aggregate, but a precise
single error is the MVP contract.

**Patterns:** `vault/` only (stdlib + pyyaml); no events/tui/orchestration here.

### Project Structure Notes

- Modified: `src/well_corp_sw/vault/harness.py` (frontmatter + duplicate-id guards).
- Tests: `tests/vault/test_validation.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Vault Integrity (harness standard)] — validate conformance before a run; malformed vault fails fast.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR9 (validate / fail fast).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 106 passed (4 validation); ruff/ty clean; format reflowed 1 file;
  lint-imports KEPT.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Hardened the loader so every malformed-vault case fails fast with a specific
  message naming the offending file/entry (FR9): invalid YAML frontmatter,
  duplicate entry id (joins both 3.1's manifest-missing / unsupported-schema /
  unresolved-wikilink errors).
- Fail-fast at the first concrete error (matches config/event-log behaviour);
  aggregating all problems is a possible later enhancement.
- `wcs vault validate` surface = story 3.4; auto-validate-before-run = story 3.5.
- `vault/` unchanged dependency surface (stdlib + pyyaml); import-linter KEPT.
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/vault/harness.py (modified — frontmatter + duplicate-id guards)
- tests/vault/test_validation.py (new)

### Change Log

- 2026-06-09: Implemented story 3.2 — fail-fast vault validation (invalid
  frontmatter + duplicate id guards naming the offending note). 4 tests.
  Status → review.
