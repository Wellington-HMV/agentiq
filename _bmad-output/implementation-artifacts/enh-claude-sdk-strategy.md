# Enhancement: Real Claude Agent SDK orchestration strategy

Status: review

## Goal

A real `OrchestrationStrategy` that drives live Claude agents via the Claude Agent
SDK, so `wcs run --live` performs actual agent work (not the deterministic stub).
Plugs into the existing seam — the loop, event log, replay, vault, decisions, cost,
and safety are unchanged.

## Acceptance Criteria

1. `ClaudeStrategy` implements `OrchestrationStrategy`, driving `claude_agent_sdk.query`
   and translating its message stream into domain events via the adapter.
2. `wcs run --live` selects `ClaudeStrategy`; without `--live`, the deterministic
   strategy runs (no API key needed). Live requires `ANTHROPIC_API_KEY` + network.
3. Translation is testable without network (injectable `query_fn` + a fake stream).

## Tasks / Subtasks

- [x] `agent/claude_strategy.py` `ClaudeStrategy(query_fn=claude_agent_sdk.query)`:
      build `ClaudeAgentOptions` (orchestrator system prompt, `allowed_tools=["Task"]`);
      `run` iterates `query(prompt, options)` and translates each message:
      - `AssistantMessage`: `ToolUseBlock` named Task/Agent → `adapter.spawn` +
        `adapter.delegate` (agent id from `parent_tool_use_id`); `usage` dict →
        `adapter.record_usage`.
      - `ResultMessage`: `total_cost_usd` → `adapter.record_usage`; `is_error` →
        "failed" else "completed".
- [x] `cli/run.py` `_resolve_strategy` + `wcs run --live` flag.
- [x] Tests (`tests/agent/test_claude_strategy.py`, 2) with a fake `query_fn`:
      translates Task tool-use + usage + cost → events, returns "completed";
      `ResultMessage(is_error=True)` → "failed".

## Dev Notes

Not a planned MVP story — an enhancement that makes orchestration do real agent
work. SDK usage stays confined to the `agent/` package (`adapter.py` +
`claude_strategy.py`); the rest of the system still depends only on domain events.

**Live vs deterministic:** `wcs run --live` → `ClaudeStrategy` (real agents, needs
`ANTHROPIC_API_KEY` + network); default → `DeterministicStrategy` (offline,
reproducible). This avoids accidental spend and keeps tests/CI hermetic.

**Caveat — not verified live:** the message→event translation is best-effort
against the introspected SDK schema (AssistantMessage.content/usage/
parent_tool_use_id; ToolUseBlock.id/name/input; ResultMessage.total_cost_usd/
is_error) and reads fields defensively. It is covered by a fake-stream unit test
but has NOT been run against the live API here (no key/network). Expect to adjust
field/tool-name mapping (e.g. the exact subagent tool name and input keys) on the
first real run. Cost/safety/decision wiring into the live loop (calling
`apply_usage`/`authorize`/`request_decision` from within the SDK hook flow) is a
further refinement.

## File List

- src/well_corp_sw/agent/claude_strategy.py (new)
- src/well_corp_sw/cli/run.py (modified — --live strategy selection)
- src/well_corp_sw/cli/app.py (modified — --live flag)
- tests/agent/test_claude_strategy.py (new)

## Change Log

- 2026-06-09: Implemented the real Claude Agent SDK strategy behind the
  OrchestrationStrategy seam (`wcs run --live`), with a fake-stream test. Not yet
  validated against the live API. Status → review.
