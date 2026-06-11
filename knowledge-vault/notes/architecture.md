---
id: architecture
title: Architecture
tags: [architecture, event-sourcing]
type: doc
---

# Architecture

**Stack:** Python 3.11+ · asyncio · Textual (TUI) · claude-agent-sdk · Pydantic v2 ·
uv + Ruff + Ty + pytest + import-linter. CLI command = `wcs`.

**Core pattern: event sourcing.** The headless core is the SOLE producer of an
append-only JSONL event log (one file per run, `seq`-ordered, fsync-per-write) —
the single source of truth. Everything else (JSONL writer, cost meter, TUI, replay)
is a pure subscriber of an in-process async `EventBus`. The core NEVER blocks on or
imports the render layer (enforced by import-linter: core-side packages must not
import `tui`).

**Run store:** `~/.well-corp-sw/runs/<ulid>/` holds `events.jsonl`, `meta.json`,
`summary.json` (summary is PROJECTED from the log, never written incrementally).

**Shared reducer:** one pure `reduce(state, event) -> SceneState` drives both live
and replay, guaranteeing they never diverge (NFR5). Same reducer feeds the spatial
scene and the plain timeline (the universal fallback).

**Strategy seam:** `OrchestrationStrategy` — `DeterministicStrategy` (offline,
reproducible, default) and `ClaudeStrategy` (real agents via `wcs run --live`,
needs ANTHROPIC_API_KEY). Both drive the same loop/log/replay.

**SDK seam:** the Claude Agent SDK is touched only inside `agent/` (adapter +
claude_strategy); the rest depends on domain events. Secrets scrubbed at the
adapter boundary before any event is logged/published (NFR9).

**Modules (src/well_corp_sw/):** core, events, agent, vault, replay, tui, policy,
cost, config, cli. See [[conventions]] for the dependency rule.

Harness vault format: an Obsidian-style markdown vault + `.harness/manifest.toml`
(schema_version, include/exclude globs, entry_id); notes carry YAML frontmatter
(id/title/tags/type), wikilinks resolve in-vault. This very vault is an example.
