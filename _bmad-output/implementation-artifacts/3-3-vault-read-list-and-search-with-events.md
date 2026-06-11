# Story 3.3: Vault read, list, and search with events

Status: review

## Story

As a developer,
I want agents and I to read, list, and search vault entries,
so that the right context is pulled with minimal token cost.

## Acceptance Criteria

1. **Given** a loaded vault, **When** an entry is read by id or relative path,
   **Then** its body + metadata are returned and a `vault.read` event is emitted
   (FR10).
2. **Given** a loaded vault, **When** I `search(query|tags)`, **Then** matching
   entries are returned from the index.
3. **Given** a vault, **When** loaded by separate providers, **Then** the same
   vault yields identical entries across runs/projects (FR12).

## Tasks / Subtasks

- [x] Task 1: `agent/vault_access.py` `VaultReader(provider, adapter)` —
      `read(agent_id, ref)` returns the doc + emits `vault.read` via the adapter;
      `search(query, tags)` delegates (not logged).
- [x] Task 2: Tests (3) — read returns body + emits one `vault.read` (ref+agent in
      log); search delegates (tag filter); two providers over the fixture yield
      identical entry ids (FR12).

## Dev Notes

Builds on 3.1 (provider: entries/read/search), 1.6 (adapter: `vault_read` emits
`vault.read`). The provider stays PURE (no events) — the bridge that turns a read
into an event lives in `agent/` (which already depends on both `vault/` and the
adapter/events). This keeps the layering clean: `vault/` never imports `events`,
and `vault.read` events are emitted at the consumption boundary (FR10).

**Why a bridge, not provider-emits:** the architecture forbids the vault from
depending on the event system; `agent/` is the integration layer. `AgentAdapter`
already has `vault_read(agent_id, ref)` (story 1.6) which scrubs + writes +
publishes `vault.read`; `VaultReader` just pairs a fetch with that emit.

**Reuse (FR12):** a `HarnessVaultProvider` holds no run-specific state — pointing
two providers at the same vault path produces the same index. Tested directly.

**Search:** no `vault.search` event type exists (searching is a local index op,
not a logged agent action); `search` just delegates. Only actual reads are logged.

**Patterns:** `agent/` may import `vault/` + `events/` (core-side); never `tui`
(import-linter). `vault/` unchanged.

### Project Structure Notes

- New: `src/well_corp_sw/agent/vault_access.py`. Tests:
  `tests/agent/test_vault_access.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Vault Architecture] — vault reads emit `vault.read`; provider reads return body + metadata.
- [Source: _bmad-output/planning-artifacts/architecture.md#Orchestration & Agent Integration] — events emitted at the adapter boundary.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR10 (read context, emit), FR12 (reuse across runs/projects).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates clean first run: pytest 109 passed (3 vault_access); ruff/ty/format clean;
  lint-imports KEPT (agent→vault is allowed; vault never imports events).

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- The bridge lives in `agent/` so the vault stays pure (no event dependency) and
  `vault.read` is emitted at the consumption boundary (FR10) — clean layering.
- Reuses the 1.6 adapter's `vault_read` (scrub → log → bus); searching is a local
  index op, not logged (no `vault.search` event type).
- FR12 verified directly: separate providers over the same vault path yield the
  same index.
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/agent/vault_access.py (new)
- tests/agent/test_vault_access.py (new)

### Change Log

- 2026-06-09: Implemented story 3.3 — `VaultReader` bridge (read emits `vault.read`,
  search delegates); vault reuse verified. 3 tests. Status → review.
