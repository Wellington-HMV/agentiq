# Story 3.5: Agents use vault context and verify results

Status: review

## Story

As a developer,
I want subagents to read vault context and the parent to verify results against it,
so that runs are grounded in my knowledge library.

## Acceptance Criteria

1. **Given** a run configured with a valid vault, **When** subagents work,
   **Then** they read relevant vault entries (emitting `vault.read`) during the
   run (FR10).
2. **Given** a run, **When** subagents produce results, **Then** the parent
   verifies them against vault context before accepting (FR5).
3. **Given** an invalid vault, **When** the run starts, **Then** it fails fast
   (run aborted) before any agent work (FR9).

## Tasks / Subtasks

- [x] Task 1: Vault-aware orchestration (`core/orchestrator.py`)
  - [x] `run_orchestration(..., vault: VaultProvider | None = None)`: when a vault
        is given, `validate()` it first (fail fast → `run.abort("vault invalid: …")`,
        project summary, return); else build a `VaultReader(vault, adapter)` and
        pass it to the strategy.
  - [x] `OrchestrationStrategy.run(goal, project, adapter, vault=None)` — protocol
        gains the optional vault reader.
  - [x] `DeterministicStrategy`: when a vault is present, each subtask's subagent
        reads a deterministic entry (`vault.read`) and the parent reads the same
        entry to verify before accepting (FR5).
- [x] Task 2: Wire `wcs run` to the configured vault (`cli/run.py`)
  - [x] Resolve the first `vault.paths` entry from config into a
        `HarnessVaultProvider` and pass it to `run_orchestration`; no vault → runs as before.
- [x] Task 3: Tests (`tests/core/test_orchestrator_vault.py`)
  - [x] Run with vault → `vault.read` events from the subagent AND the parent
        (verification), with the expected ref.
  - [x] Run without vault → no `vault.read` events.
  - [x] Invalid vault → run aborted with "vault invalid".

## Dev Notes

Builds on 3.1-3.3 (provider, validate, VaultReader) + 1.7 (orchestration loop).
Closes Epic 3. The deterministic strategy models "read context + parent verifies"
as `vault.read` events (subagent reads, parent reads the same ref to verify); the
real reasoning-based verification arrives with the Claude-SDK strategy, which
plugs into the same seam. Validation runs before any agent work so a malformed
vault never feeds agents bad context (FR9).

### Project Structure Notes

- Modified: `core/orchestrator.py` (vault param + validate + VaultReader; strategy
  protocol signature), `cli/run.py` (resolve vault from config).
- Tests: `tests/core/test_orchestrator_vault.py`; updated `_FailingStrategy` in
  `test_orchestrator.py` to the new strategy signature.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Orchestration & Agent Integration] — parent verifies subagent results against vault context.
- [Source: _bmad-output/planning-artifacts/architecture.md#Vault Integrity (harness standard)] — validate before a run.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.5] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR5 (verify against vault), FR10 (read context).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 115 passed (3 vault-orchestration); ruff/ty/format clean; lint-imports KEPT.
- Updated `_FailingStrategy.run` in test_orchestrator.py to the new 4-arg strategy
  signature (the protocol gained `vault`); ty flagged the mismatch until fixed.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Vault validated before any agent work (FR9); a valid vault yields `vault.read`
  events for both the subagent (context) and the parent (verification, FR5),
  visible in the log/replay.
- Deterministic strategy models verification as the parent reading the same vault
  ref; real reasoning-based verification comes with the Claude-SDK strategy on the
  same seam.
- `core` imports `agent.vault_access` + `vault` (core-side; never `tui`) — import-linter KEPT.
- **Closes Epic 3 (Knowledge Vaults): all 5 stories implemented.** ACs satisfied; status → review.

### File List

- src/well_corp_sw/core/orchestrator.py (modified — vault param, validate, VaultReader, strategy sig)
- src/well_corp_sw/cli/run.py (modified — resolve vault from config)
- tests/core/test_orchestrator_vault.py (new)
- tests/core/test_orchestrator.py (modified — _FailingStrategy signature)

### Change Log

- 2026-06-09: Implemented story 3.5 — vault-aware orchestration (subagents read
  context + parent verifies; validate-before-run), wired `wcs run` to the
  configured vault. 3 tests. Closes Epic 3. Status → review.
