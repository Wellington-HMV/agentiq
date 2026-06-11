# Live calibration guide — `ClaudeStrategy` ↔ the real Agent SDK

`agent/claude_strategy.py` translates the Claude Agent SDK message stream into our
domain events. It was built and tested **offline** against a fake `query_fn` whose
objects *mimic* the SDK schema (class names + attributes). Before trusting it
live, calibrate those assumptions against the real SDK — that is the only part the
offline tests can't verify.

This guide lists every assumption the translation makes, how to check it, and what
to change if reality differs.

## 0. Prerequisites

```bash
export ANTHROPIC_API_KEY=sk-ant-...        # PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
python -m uv run python scripts/live_smoke.py --dump      # raw SDK shapes
python -m uv run python scripts/live_smoke.py             # full run + report
AGENTIQ_LIVE=1 python -m uv run pytest tests/live -q          # opt-in live tests
```

`--dump` prints, for every message: its class name + attribute names, and for each
content block its class name, and for `ToolUseBlock`s the `name`/`id`/`input` keys.
That output is the ground truth. Compare it to the table below.

## 1. Assumptions to verify (and where each lives)

| # | Assumption | Code | If wrong |
|---|-----------|------|----------|
| 1 | Message classes are named `AssistantMessage` and `ResultMessage` (matched by `type(msg).__name__`) | `_handle` | Update the name checks; consider matching on attributes instead of `__name__` if the SDK renames or wraps. |
| 2 | Assistant content is iterable on `message.content`; tool calls are `ToolUseBlock` (by `__name__`) | `_handle_assistant` | Adjust the block-type check / attribute path. |
| 3 | Subagent-spawning tool is named `Task` (or `Agent`) | `_SUBAGENT_TOOLS` | Add/replace the real tool name(s). |
| 4 | `ToolUseBlock` exposes `.name`, `.id`, `.input` | `_spawn_subagent`, `_guard_tool` | Re-map the attribute names. |
| 5 | Spawn input keys are `subagent_type` / `prompt` / `description` | `_spawn_subagent` | Re-map to the real input keys (role + task). |
| 6 | A subagent always has a stable `.id` | `_spawn_subagent` (`or "sub"`) | **Known weak spot** — see §3. |
| 7 | Token usage is a dict with `input_tokens` / `output_tokens` | `_handle_assistant` | Re-map keys / type. |
| 8 | `ResultMessage` carries `total_cost_usd` (cumulative) and `is_error` | `_handle` | Re-map; if cost is per-turn not cumulative, change the metering (see §4). |
| 9 | File/shell tool names are `Write/Edit/MultiEdit/NotebookEdit/Bash`; outbound are `WebFetch/WebSearch`; path is in `file_path`/`path`/`notebook_path` | `_IRREVERSIBLE_TOOLS`, `_OUTWARD_TOOLS`, `_action_for_tool` | Update the sets + path keys so the safety guard sees the right actions. |

## 2. What "calibrated" looks like

Run `--dump` on a delegating goal and confirm:

- The parent's tool calls appear as `ToolUseBlock` with `name` == your spawn tool.
- `input` contains the role + task under the keys in assumption #5.
- A final `ResultMessage` carries a non-null cost and the error flag.

Then run the full smoke (`scripts/live_smoke.py`) and confirm the report shows:

- `events:` includes `agent.spawned` + `task.delegated` (if the model delegated),
  `agent.usage`, and a terminal `run.completed`/`run.aborted`.
- `cost_usd:` is non-zero and plausible.
- `spawned:` lists distinct subagent ids (no collisions — see §3).

## 3. Known weak spot: subagent id fallback (assumption #6)

`_spawn_subagent` uses `sub_id = block.id or "sub"`. If the SDK ever omits `id`,
**every** such subagent collapses to the id `"sub"`: the adapter's spawn-reuse
registry then emits only one `agent.spawned`, and all delegations point at one
node — the scene/tree silently under-counts agents.

If `--dump` shows any `ToolUseBlock` without an `id`, replace the fallback with a
deterministic unique id, e.g. derived from the message index + block position
(avoid `uuid`/randomness so replays stay deterministic):

```python
sub_id = getattr(block, "id", None) or f"sub-{agent_id}-{block_index}"
```

(thread a per-message block index into `_spawn_subagent`).

## 4. Cost metering nuance (assumption #8)

Today cost is metered once, from `ResultMessage.total_cost_usd` (cumulative, at the
end). So `budget.exceeded` is emitted post-hoc and the `_halted` fan-out brake only
matters if more messages follow the result. If the live stream instead reports
**incremental** cost per turn (e.g. on assistant messages), move the
`apply_usage(...)` call to where the per-turn cost arrives so the ceiling halts
fan-out mid-run (NFR12) as intended. The `_halted` mechanism already does the right
thing once it's set at the right moment.

## 5. Safety + decision guard (live)

With a `SafetyGuard` (built from config in `cli/run.py` for `--live`), a non-`Task`
tool use is confined to the project/vault scope and an irreversible/outward one is
gated by a `request_decision` through the resolver (`PolicyResolver` in the real
run). Verify live that:

- A `Write` inside the project triggers a `decision.pending`/`resolved` pair.
- A path outside scope is refused (`SafetyDenied`) with no prompt and no crash.
- The autonomy policy's `ask`/`allow`/`deny` rules actually drive the outcome.

If the SDK does its own tool execution (the agent edits files itself rather than
emitting tool-use blocks we intercept), the guard can only *observe*, not *prevent*
— in that case restrict `allowed_tools` in `_build_options` so the SDK cannot run
the dangerous tools at all, and let the guard handle the rest.

## 5b. Live findings — 2026-06-10 (first real run)

First live `--dump` against the real SDK confirmed and corrected the schema:

- **Message classes seen:** `HookEventMessage`, `SystemMessage`, `AssistantMessage`,
  `ResultMessage`. We only translate the last two by `__name__`; the rest are
  ignored harmlessly. ✓ assumptions #1–#2.
- **`AssistantMessage`** attrs: `content, error, message_id, model,
  parent_tool_use_id, session_id, stop_reason, usage, uuid`. ✓ our `content` /
  `parent_tool_use_id` / `usage` reads.
- **`ResultMessage`** attrs include `subtype, is_error, total_cost_usd, result,
  usage, model_usage, stop_reason, num_turns, errors, permission_denials, ...`.
- **`subtype` is the SDK *envelope* status, NOT the API outcome.** A failed call
  still came back with `subtype='success'` while `is_error=True` and
  `result='Invalid API key ...'`. So **trust `is_error`** (our mapping is correct);
  do NOT switch to `subtype`.
- **The SDK raises *after* yielding the terminal `ResultMessage`** (`Exception:
  Claude Code returned an error result: success`). Fixed: `ClaudeStrategy.run`
  now swallows a trailing exception once a result was seen, and only propagates a
  failure that happens before any result (→ orchestration aborts). Covered by
  `test_trailing_sdk_error_after_result_is_tolerated` /
  `test_error_before_any_result_propagates`.
- **Auth:** `claude_agent_sdk` drives the **Claude Code CLI**, which surfaced
  `Invalid API key · Fix external API key` for a well-formed `sk-ant-…` key. A
  valid `ANTHROPIC_API_KEY` alone may not be enough — the CLI may be authenticated
  separately (interactive login) or the key may be revoked/wrong-scope. Resolve
  CLI auth before re-running; `total_cost_usd` stayed 0 because the call never ran.
- **Cost note:** with this CLI path `total_cost_usd` may be 0 even on success, so
  the cost ceiling can't be relied on for spend control here — confirm once a valid
  key produces a real, costed result.

**Auth that actually works:** the Claude Code CLI **subscription login** — do NOT
set `ANTHROPIC_API_KEY` (setting it forces "external API key" mode and broke the
run with an invalid key). With the login and no env key, a run completes and
`total_cost_usd` is real (e.g. 0.1784), so the cost ceiling DOES gate spend on this
path. (The API-key/credits path is a separate option, not required.)

### Delegating-run findings (second live run, login auth)

- **The subagent tool is named `Agent`** (not `Task`) in practice; `input_keys =
  ['description', 'prompt', 'subagent_type']` — matches `_SUBAGENT_TOOLS` and
  `_spawn_subagent`'s key reads. ✓ assumptions #3–#5.
- **Every `ToolUseBlock` has a real `id`** (`toolu_…`). The `sub_id == "sub"`
  collision (§3) does not occur in practice — but keep the guard.
- **Other block types in assistant content:** `ThinkingBlock` (`signature`,
  `thinking`), `TextBlock` (`text`), `ToolResultBlock` (`content`, `is_error`,
  `tool_use_id`). We act only on `ToolUseBlock`; the rest are ignored. ✓
- **`allowed_tools=["Task"]` does NOT constrain the CLI.** The subscription CLI ran
  `Bash`, `Glob`, `Read` itself (one `Bash` even carried
  `dangerouslyDisableSandbox`). So on this path the SDK **executes tools directly**
  — our `SafetyGuard` is **observe-only**, it cannot prevent. To actually confine,
  use the SDK's permission mechanism (`permission_mode` / a `can_use_tool`
  callback) or run the agents under OS-level sandboxing; `allowed_tools` alone is
  not a control. **Open follow-on.**
- **Windows console crash:** the SDK prints tool output to stdout and chokes on
  `→` (`→`) under cp1252 (`UnicodeEncodeError`). Set `PYTHONUTF8=1` (or
  `PYTHONIOENCODING=utf-8`) when running live on Windows. `ClaudeStrategy.run` and
  the `--dump` loop already swallow such trailing teardown errors.

### End-to-end translation confirmed (delegating run, login auth)

A goal that delegates produced, through the full orchestration:

```
run -> completed
events: run.started:1 agent.spawned:3 agent.usage:69 task.delegated:2
        budget.exceeded:1 run.completed:1
cost_usd: 2.1878   spawned: ['parent', 'toolu_…', 'toolu_…']
```

- **spawn + delegate translation works**: parent + 2 subagents (the `Agent` tool),
  2 `task.delegated`, distinct real `toolu_…` ids (no `sub_id` collision).
- **cost guard fires**: cost 2.19 crossed the 0.50 ceiling → exactly one
  `budget.exceeded`. The log stays valid (`read_events` enforces seq).
- **Confirms §4**: cumulative cost only arrives on the final `ResultMessage`, so
  the breach is post-hoc and fan-out was NOT halted mid-run (cost overshot the
  ceiling 4×). To gate spend in-flight, find a per-turn cost signal (token usage ×
  model price?) and meter that, not just the final total.

## 7. Real tool prevention — wired (2026-06-10)

`ClaudeStrategy` now configures three SDK controls (replacing the observe-only
translation gate) when a `SafetyGuard` is given:

- **`can_use_tool` callback** — the SDK calls it *before* running a tool; we route
  through `SafetyGuard` → allow / deny (out-of-scope or denied op) / confirm (a
  decision via the resolver). **Requires streaming-input mode**: the prompt must be
  an `AsyncIterable[dict]`, not a string, or the SDK aborts with *"can_use_tool
  callback requires streaming mode"*. Fixed: `_prompt_stream` yields
  `{"type":"user","message":{"role":"user","content":goal},"parent_tool_use_id":
  None,"session_id":"default"}` whenever the callback is set.
  **Caveat (live):** the CLI only consults `can_use_tool` when it would otherwise
  prompt for permission. A subscription session with pre-approved tools may **skip
  it** — in two live probes no `[perm]` debug line printed and no decision events
  appeared. So treat `can_use_tool` as best-effort scope/decision gating.
- **`disallowed_tools`** (from `denied_ops`) — the **authoritative, always-enforced
  hard block**: the CLI refuses these tools regardless of permission settings. Use
  this for tools that must never run (e.g. `Bash`). Wired from
  `SafetyGuard.denied_ops`.
- **`max_budget_usd`** (from the cost ceiling) — the SDK caps spend **in-flight**
  (closes §4's "post-hoc only" gap); our `apply_usage` still logs the final cost +
  `budget.exceeded`.

Debug: set `AGENTIQ_DEBUG_PERMS=1` to print `[perm] <tool> -> allow|deny` to stderr each
time the callback fires — use it to confirm whether the CLI is consulting it.

Try it: `python scripts/live_smoke.py --guard` (confines to cwd, hard-blocks Bash,
denies confirms).

Open follow-on: to make `can_use_tool` authoritative regardless of CLI settings,
investigate `permission_mode` (e.g. forcing prompts) or run agents under
`SandboxSettings`; for now pair it with `disallowed_tools` for guaranteed blocks.

## 6. After calibrating

- Update `agent/claude_strategy.py` to match the verified shapes.
- Update the fake objects in `tests/agent/test_claude_strategy.py` so the offline
  tests mirror the real schema (keep them as the fast regression net).
- Re-run all gates: `python -m uv run pytest && ruff check . && ruff format --check . && ty check && lint-imports`.
- Record any schema surprises here so the next calibration is faster.
