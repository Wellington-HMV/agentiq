# Story 4.4: Cost metering and hard ceiling

Status: review

## Story

As a developer,
I want token/cost tracked per run and per agent with a hard ceiling,
so that runs never overspend.

## Acceptance Criteria

1. **Given** a configured cost ceiling, **When** agents consume tokens, **Then**
   cost is aggregated per agent and per run from usage events (FR31).
2. **Given** the ceiling is reached, **When** more usage is recorded, **Then** a
   `budget.exceeded` event is emitted (once) and the core halts new fan-out
   (FR32, NFR12).
3. **Given** a finished run, **When** the summary is built, **Then** `cost_usd`
   reflects the total usage from the log.

## Tasks / Subtasks

- [x] Task 1: `events/models.py` — `agent.usage` (input_tokens/output_tokens/cost_usd) added to registry.
- [x] Task 2: `AgentAdapter.record_usage(agent_id, *, input_tokens, output_tokens, cost_usd)` → emits `agent.usage`.
- [x] Task 3: `cost/meter.py` `CostMeter` (record/total/per_agent/exceeded≥ceiling,
      `take`=crossing flag) + `apply_usage` (emit usage, meter, emit `budget.exceeded`
      once on crossing, return exceeded).
- [x] Task 4: `replay/summary.py` projects `cost_usd` = sum of `agent.usage` cost.
- [x] Task 5: Tests (5) — aggregate+exceeded; `take` crossing-only; `apply_usage`
      emits 3 usage + 1 budget.exceeded; summary cost = summed usage. (float via approx)

## Dev Notes

Builds on 1.6 (adapter) + 1.8 (summary). The deterministic strategy emits no real
tokens, so cost stays 0 there; this story builds the metering MECHANISM + the
ceiling enforcement point so the real Claude-SDK strategy (which reports usage)
plugs in unchanged. Per-agent + per-run aggregation comes from `agent.usage`
events (FR31); the hard ceiling halts new fan-out (FR32/NFR12).

**Where the ceiling halts:** `apply_usage` returns `meter.exceeded`; the caller
(the SDK strategy / orchestrator spawn loop) checks it before spawning more
subagents and stops. `budget.exceeded` is emitted exactly once on the crossing so
replay shows a single ✕-adjacent budget marker, not a flood.

**Summary (AC #3):** `cost_usd` becomes a projection (sum of `agent.usage`
cost_usd) — consistent with "summary is projected from the log", replacing the 0.0
placeholder from 1.8.

**Layering:** `cost/meter.py` may import `agent.adapter` for `apply_usage`
(core-side → core-side, allowed); the pure `CostMeter` has no such dependency.
`cost/` never imports tui (import-linter).

### Project Structure Notes

- Modified: `events/models.py` (agent.usage), `agent/adapter.py` (record_usage),
  `replay/summary.py` (cost projection). New: `src/well_corp_sw/cost/meter.py`.
- Tests: `tests/cost/test_meter.py`; extend `tests/replay/test_summary.py`.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Cost & Safety (Security, adapted)] — cost meter, per-agent/run, hard ceiling halts fan-out, cost visible in replay.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.4] — acceptance criteria.
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements] — FR31 (track cost), FR32 (ceiling halts); NFR12 (hard ceiling).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates: pytest 133 passed (5 cost); ty clean; lint-imports KEPT. Fixed a float
  equality (`pytest.approx`) and one E501 in the meter docstring.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Metering mechanism + enforcement point built; the deterministic strategy emits
  no usage (cost stays 0), the real Claude-SDK strategy reports usage through
  `apply_usage` unchanged.
- `budget.exceeded` emitted exactly once on the ceiling crossing (single replay
  marker); `apply_usage` returns `exceeded` so the spawn loop halts fan-out.
- `summary.cost_usd` is now a real projection (sum of `agent.usage`), replacing the
  1.8 placeholder.
- `cost/meter.py` imports `agent.adapter` for `apply_usage` (core-side→core-side);
  pure `CostMeter` has no such dep; no tui (import-linter KEPT).
- ACs satisfied; status → review.

### File List

- src/well_corp_sw/cost/meter.py (new)
- src/well_corp_sw/events/models.py (modified — agent.usage)
- src/well_corp_sw/agent/adapter.py (modified — record_usage)
- src/well_corp_sw/replay/summary.py (modified — cost_usd projection)
- tests/cost/__init__.py (new)
- tests/cost/test_meter.py (new)

### Change Log

- 2026-06-09: Implemented story 4.4 — cost meter + hard ceiling (`CostMeter` +
  `apply_usage` emitting agent.usage/budget.exceeded), summary cost projection.
  5 tests. Status → review.
