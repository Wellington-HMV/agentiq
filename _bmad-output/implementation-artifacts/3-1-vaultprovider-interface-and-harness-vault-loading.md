# Story 3.1: VaultProvider interface and harness vault loading

Status: review

## Story

As a developer,
I want a `VaultProvider` interface with a `HarnessVaultProvider` that loads my Obsidian-style vault,
so that agents can use a reusable knowledge library by a stable convention.

## Acceptance Criteria

1. **Given** a vault dir with `.harness/manifest.toml` + markdown notes, **When**
   the provider loads it, **Then** the manifest (schema_version, include/exclude,
   entry_id) is parsed and an in-memory index is built.
2. **Given** the provider, **When** used, **Then** it exposes
   `validate/list/read/search/metadata` behind the `VaultProvider` ABC (NFR16).
3. **Given** notes with YAML frontmatter (id/title/tags/type), **When** loaded,
   **Then** they are indexed; `[[wikilinks]]` resolve within the vault.

## Tasks / Subtasks

- [x] Task 1: `vault/provider.py` — `VaultEntry`/`VaultDocument`/`VaultError` +
      `VaultProvider` ABC (`validate`, `entries`, `read`, `search`, `metadata`).
      (Method named `entries()` not `list()` — `list` shadows the builtin in
      annotations under `from __future__ import annotations`.)
- [x] Task 2: `vault/harness.py` `HarnessVaultProvider` — tomllib manifest, glob
      include−exclude, pyyaml frontmatter, id→entry index (id = frontmatter id
      else rel_path), entries/read(by id or rel_path)/search(query+tags)/metadata,
      validate (manifest + schema_version==1 + wikilinks resolve to id or stem).
- [x] Task 3: fixture `tests/fixtures/vault/` (manifest + api-design.md w/
      frontmatter+`[[auth]]`, auth.md no-frontmatter) + 8 tests (index, fallback id,
      read by id/relpath, unknown-ref raises, search by tag/query, wikilink resolve,
      metadata, missing manifest + unresolved wikilink raise).

## Dev Notes

This story builds the vault engine. Validation here is structural; story 3.2
sharpens fail-fast error messages and the "validate before a run" wiring, and 3.3
adds `vault.read` events during runs + the `VaultProvider` consumption by agents.
The `wcs vault` command is 3.4. Keep it pure I/O over the filesystem; no events,
no orchestration here.

**Harness vault format (from architecture, resolved):** an Obsidian-style markdown
vault + a `.harness/manifest.toml`:
```toml
schema_version = 1
name = "..."
include = ["**/*.md"]
exclude = [".obsidian/**"]
entry_id = "frontmatter.id || relpath"
```
Notes: markdown with optional YAML frontmatter (`id`, `title`, `tags`, `type`),
body may contain `[[wikilinks]]`.

**Parsing:** manifest = stdlib `tomllib`; frontmatter = `yaml.safe_load` of the
leading `---`-fenced block (a note without frontmatter is allowed → empty meta).
`entry_id`: use frontmatter `id` when present, else the note's relative path.
`type` defaults to `doc`.

**Wikilinks:** `[[target]]` resolves if `target` matches an entry id OR a note
filename stem (Obsidian-style). `validate()` fails if any wikilink is unresolved.

**Schema version:** only `schema_version == 1` is supported now; anything else is
a `VaultError` (forward-safety).

**Patterns:** `vault/` imports stdlib + pyyaml only (no events/tui/orchestration);
core-side never imports tui (import-linter). Classes `PascalCase`.

### Project Structure Notes

- New: `src/well_corp_sw/vault/provider.py`, `src/well_corp_sw/vault/harness.py`.
- New fixture: `tests/fixtures/vault/...`. Tests: `tests/vault/test_harness.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Harness Vault Format (resolved)] — manifest, layout, VaultProvider behavior, wikilinks.
- [Source: _bmad-output/planning-artifacts/architecture.md#Vault Architecture] — VaultProvider ABC (validate/list/read/search), in-memory index.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR8 (load harness vault); NFR16 (VaultProvider interface).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Added `pyyaml` (frontmatter) + `types-pyyaml` (dev) via `uv add`.
- Gates: pytest 102 passed (8 vault); ruff/format clean; lint-imports KEPT.
- ty flagged 6 `invalid-type-form`: a method named `list` shadowed builtin `list`
  in the return/param annotations → renamed the provider method to `entries()`;
  also fixed an E501. Clean after.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Vault engine only — structural load + the 5 ABC methods. Sharper fail-fast
  messages / "validate before run" wiring is story 3.2; `vault.read` events +
  agent consumption is 3.3/3.5; `wcs vault` CLI is 3.4.
- `entry_id` = frontmatter `id` else relative path (matches the resolved harness
  format); a note without frontmatter is allowed.
- Wikilinks resolve to an entry id OR a note filename stem (Obsidian-style);
  validate() raises on unresolved links and on schema_version != 1.
- `vault/` imports stdlib + pyyaml only (no events/tui/orchestration); core-side
  never imports tui (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/vault/provider.py (new)
- src/well_corp_sw/vault/harness.py (new)
- pyproject.toml (modified — pyyaml dep + types-pyyaml dev dep)
- tests/vault/__init__.py (new)
- tests/vault/test_harness.py (new)
- tests/fixtures/vault/.harness/manifest.toml (new)
- tests/fixtures/vault/notes/api-design.md (new)
- tests/fixtures/vault/notes/auth.md (new)

### Change Log

- 2026-06-09: Implemented story 3.1 — VaultProvider ABC + HarnessVaultProvider
  (manifest + frontmatter index, entries/read/search/metadata/validate, wikilink
  resolution). pyyaml added. 8 tests + fixture vault. Status → review.
