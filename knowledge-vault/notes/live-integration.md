---
id: live-integration
title: Live Claude SDK Integration
tags: [live, sdk, claude, auth, safety, calibration]
type: reference
---

# Live Claude SDK Integration

How `ClaudeStrategy` drives the real Claude. Full detail in
`docs/live-calibration.md`; this is the durable summary.

## Auth — subscription, no funded API key

`claude_agent_sdk` drives the machine's **Claude Code CLI**, which authenticates via
the **subscription login** (interactive `claude` login). So `wcs run --live` works
with NO API key and NO API credits — it bills the subscription, same as an
interactive `claude` session.

- **Do NOT set `ANTHROPIC_API_KEY`.** Setting it forces "external API key" mode; an
  invalid/empty key then fails with `Invalid API key - Fix external API key`. A
  user who pasted a funded-less key into the env var must delete it:
  `[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $null, "User")` then
  reopen the shell.
- Proven: live runs completed on subscription, real `total_cost_usd` reported
  (e.g. 0.13 / 0.18 / 2.19).

## SDK message schema (calibrated live)

- Message classes: `HookEventMessage`, `SystemMessage`, `AssistantMessage`,
  `ResultMessage` (we translate the last two by `__name__`).
- `AssistantMessage.content` blocks: `ThinkingBlock`, `TextBlock`, `ToolUseBlock`
  (`id`, `name`, `input`), `ToolResultBlock`. Every `ToolUseBlock` has a real `id`.
- **Subagent tool is `Agent`** (we accept `{"Task","Agent"}`); spawn input keys
  `subagent_type` / `prompt` / `description`.
- `ResultMessage`: trust **`is_error`** for outcome — `subtype` is the SDK envelope
  status (was `'success'` on a failed call), NOT the API result.
- The SDK **raises after the terminal ResultMessage** during stream teardown
  (e.g. `returned an error result: success`). `ClaudeStrategy.run` swallows a
  trailing exception once a result was seen; propagates only a pre-result failure.
- Windows: set `PYTHONUTF8=1` — the SDK prints tool output (`->`) and chokes on
  cp1252 otherwise (`UnicodeEncodeError`).

## Guards (ClaudeAgentOptions)

- **`can_use_tool`** callback — called before a tool runs; routes through the
  `SafetyGuard` (allow / deny out-of-scope+denied-op / confirm via the resolver).
  **Requires streaming-input mode**: pass the prompt as `AsyncIterable[dict]`
  (`_prompt_stream` yields a user-message dict), not a string, or the SDK aborts
  with "can_use_tool callback requires streaming mode". **Best-effort:** the CLI
  only consults it when it would otherwise prompt — a session with pre-approved
  tools skips it.
- **`disallowed_tools`** (from `SafetyGuard.denied_ops`) — the **authoritative hard
  block**; the CLI always refuses these. Use for must-never-run tools (e.g. `Bash`).
- **`max_budget_usd`** (from the cost ceiling) — caps spend in-flight (the SDK halts
  when crossed). Cumulative cost otherwise only arrives on the final ResultMessage.
- Debug: `WCS_DEBUG_PERMS=1` prints `[perm] <tool> -> allow|deny` when the callback
  fires.

## Tooling

- `scripts/live_smoke.py` — manual smoke (subscription auth note; `--dump` prints raw
  message shapes; `--guard` enables SafetyGuard + deny resolver + hard-blocks Bash).
- `tests/live/test_live_smoke.py` — opt-in (skipped unless `WCS_LIVE=1`).

## Backlog

`ClaudeCliStrategy` (spawn `claude -p ... --output-format stream-json` directly as a
subprocess) is a planned alternative transport — see [[status]].

See [[architecture]] for the strategy seam, [[learnings]] for the gotchas.
