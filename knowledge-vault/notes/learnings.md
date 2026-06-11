---
id: learnings
title: Learnings & Gotchas
tags: [learnings, gotchas, python, textual]
type: rule
---

# Learnings & Gotchas

Concrete things that bit us this session — apply them to avoid repeats.

**Environment**
- `uv` is NOT on the bash PATH here; installed via `python -m pip install uv` and
  invoked as `python -m uv ...`. Dev Python is 3.14, but `requires-python = >=3.11`.
- Python floor is 3.11 (bumped from 3.10) so config can use stdlib `tomllib` without
  a `tomli` backfill.

**Python / typing (ty)**
- A method named `list` shadows the builtin `list` in annotations under
  `from __future__ import annotations` → ty errors. The VaultProvider method is
  `entries()`, not `list()`.
- Do NOT override `Screen.action_dismiss` in a Textual `ModalScreen` (its signature
  is `async def action_dismiss(result=None)`) — bind `escape` to the inherited one.

**Textual (headless tests via `App.run_test()`)**
- Query the PUSHED screen via `app.screen.query_one(...)` (not `app.query_one`),
  after `await pilot.pause()`.
- `Static` has no `.renderable` in this version — assert the source text instead.
- `DataTable.add_row(..., key=...)` needs an explicit key, or `row_key.value` is None;
  handle selection in `on_data_table_row_selected` (the table consumes Enter).
- Live mode: subscribe to the bus BEFORE starting the orchestration worker.

**Events / determinism**
- Run lifecycle events (`run.started`/`completed`/`aborted`) must be published to the
  bus too (via `Run.emit`/`start_run(bus=)`), not only written to the log — else live
  subscribers miss them.
- JSONL `seq` (not wall-clock `ts`) is the only ordering authority; the writer
  resumes `seq` from an existing log (used by `wcs resume`).

**Process**
- Use `pytest.approx` for float assertions (cost sums).
- Keep lines <= 88 (Ruff E501); shorten docstrings rather than fighting the formatter.

**Textual action-name collisions (found live)**
- `App` reserves `action_focus(widget_id)` and the `_animate` attribute. A binding
  action named `focus` (→ `action_focus`) breaks LSP (ty flags it); a `set_interval`
  callback named `_animate` resolves to the SDK's `BoundAnimator` and crashes.
  Renamed to `action_focus_agent` / `_tick_creatures`.

**Reducer purity — NOT a bug (don't "fix" it)**
- `reduce()` copies `agents`/`paths` at the top (`replace(a)`), so mutating those
  copies does not touch the input state. A reviewer flagging "mutation" here is a
  false positive.

**Live Claude SDK (this session) — see [[live-integration]] for the full list**
- Subscription login works with NO API key; setting `ANTHROPIC_API_KEY` (invalid)
  breaks it. `can_use_tool` needs streaming-input prompt + is best-effort (CLI may
  skip it); `disallowed_tools` is the hard block; `max_budget_usd` caps spend live.
  Windows needs `PYTHONUTF8=1`. Trust `ResultMessage.is_error`, not `subtype`.

**Tool entry point**
- The TUI is a terminal app (Textual) — run `python -m uv run wcs replay <id>
  --scene` in a REAL terminal (TTY). It won't render in a non-TTY shell (falls back
  to the plain timeline) or in a chat prompt.

See [[conventions]], [[architecture]], and [[live-integration]].
