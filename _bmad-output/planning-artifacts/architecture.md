---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments: ['_bmad-output/planning-artifacts/prd.md']
workflowType: 'architecture'
project_name: 'well-corp-sw'
user_name: 'User'
date: '2026-06-05'
lastStep: 8
status: 'complete'
completedAt: '2026-06-08'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:** 40 FRs across 8 capability areas — Orchestration,
Knowledge Vaults, Event Capture & Replay, Live Observability, Decisions &
Human-in-the-Loop, Run Management, Cost & Safety Controls, Configuration. The
architectural spine is dictated by the FRs: an orchestration core that emits a
complete event stream, a persisted event log as the single source of truth, and
two front-ends (headless emitter, animated TUI renderer) that are pure consumers
of that stream.

**Non-Functional Requirements:** 17 NFRs. The decisive ones:
- Decoupling (NFR1, NFR2, NFR17): core makes zero blocking calls into render;
  modules talk only through the event bus.
- Determinism & crash-safety (NFR5, NFR6, NFR7): replay reproduces exactly from
  an append-only log; textual timeline always available as fallback.
- No-hang autonomy (NFR8): headless runs end with deterministic exit codes;
  decisions never block forever.
- Safety & cost (NFR9-NFR12): scoped agent actions, hard cost ceiling, secrets
  never logged.
- Portability (NFR15): single codebase on Win/macOS/Linux; core needs no TTY.

### Scale & Complexity
- Primary domain: terminal-first developer tool + multi-agent AI orchestration.
- Complexity level: high (concurrency, event sourcing, animation, agent SDK,
  cross-platform, safety).
- Estimated architectural components: ~7 — Orchestration Core, Event Bus,
  Event Log/Store, Replay Engine, TUI Render Engine, VaultProvider, Agent
  Runtime Adapter (Claude Agent SDK), plus Config/Policy & Cost/Safety as
  cross-cutting services.

### Technical Constraints & Dependencies
- Claude Agent SDK for agent spawning/subagents (FR1-FR5).
- Event log format = append-only JSONL (PRD CLI section).
- Harness-standard vaults consumed via a VaultProvider interface.
- Must run headless (no TTY) and as an interactive TUI from one binary.

### Cross-Cutting Concerns Identified
- Event sourcing & logging (foundation for replay, live, summary).
- Concurrency model (parent + N subagents; render loop isolated from core).
- Autonomy policy engine (auto-resolve vs ask).
- Safety guardrails & sandbox/isolation (allowed-ops, worktree isolation).
- Cost/token accounting with hard ceilings.
- Secret handling (creds out of logs/summaries/vault).
- Cross-platform portability.

## Starter Template Evaluation

### Primary Technology Domain
Terminal-first Python application: orchestration core (asyncio) + animated TUI
(Textual) + Claude Agent SDK (Python). Cross-platform CLI installable to PATH.

### Starter Options Considered
- **uv `uv init --package` scaffold (selected):** Modern Python 2026 baseline.
  No heavyweight third-party boilerplate; the ecosystem convention is a uv
  packaged project plus explicit dependency adds. Keeps the tree minimal and
  fully under our control — appropriate for a novel architecture (event bus +
  decoupled render) that a generic starter would not model anyway.
- **Third-party Textual app templates:** Rejected — they assume a UI-centric
  app where the TUI is the core. Our core is headless; the TUI is an optional
  consumer. A UI-first template would invert our architecture.
- **cookiecutter-based Python templates:** Rejected — heavier, opinionated,
  often stale; uv init covers the same ground cleaner.

### Selected Starter: uv packaged project
**Rationale for Selection:**
Our decisive NFR is a headless core decoupled from render (NFR1, NFR2, NFR17).
No existing starter models that; a generic UI/CLI template would fight the
architecture. uv gives a clean, packaged, cross-platform CLI scaffold with
nothing to unlearn, and we layer the event-sourced architecture on top.

**Initialization Command:**

```bash
uv init --package well-corp-sw        # packaged CLI, exposes `wcs` entrypoint
cd well-corp-sw
uv add claude-agent-sdk textual       # agent runtime + animated TUI
uv add --dev ruff ty pytest pytest-asyncio   # lint/format, typecheck, tests
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:** Python 3.10+ (Agent SDK floor), asyncio for the
concurrent orchestration core.

**Styling Solution:** Textual CSS (TCSS) for the TUI scene styling/animation.

**Build Tooling:** uv for env, dependency resolution, locking (uv.lock), and
running; PEP 621 `pyproject.toml` as single source of truth; packaged so a
`wcs` executable lands on PATH.

**Testing Framework:** pytest + pytest-asyncio (core is async).

**Code Organization:** src-layout package; modules split along the event bus
boundary — `core/` (orchestration, no TTY), `events/` (bus + JSONL log),
`replay/`, `tui/` (Textual renderer), `vault/` (VaultProvider), `agent/`
(Claude Agent SDK adapter), `cli/` (commands).

**Development Experience:** Ruff (lint + format), Ty (type check), uv run for
tasks; hot iteration via `textual run --dev` for the TUI layer.

**Note:** Project initialization with the command above should be the first
implementation story. Standalone binary packaging (PyInstaller/shiv) is deferred
to a distribution phase and does not block the MVP.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Event bus & concurrency model (the spine; everything depends on it)
- Event log format & run store layout
- Replay reconstruction model (event sourcing)
- Orchestration ↔ Agent SDK mapping
- Decision/blocking resolution model

**Important Decisions (Shape Architecture):**
- VaultProvider interface & harness vault format
- Cost/safety interception model
- Config & policy schema/format

**Deferred Decisions (Post-MVP):**
- Standalone binary packaging (PyInstaller/shiv) — distribution phase.
- Per-agent worktree isolation — Growth (MVP serializes concurrent writers).
- Policy DSL — MVP uses simple declarative rules; richer engine in Growth.

### Event Architecture (Data Architecture, adapted)
- **Event sourcing is the foundational pattern.** The orchestration core is the
  sole producer of immutable, ordered events. Every state (live scene, replay,
  run summary) is a projection of the event stream. No separate mutable store of
  record — the log IS the database.
- **In-process async pub/sub bus.** Core publishes events to an `asyncio`-based
  bus; subscribers (JSONL writer, optional TUI renderer, cost meter) consume
  independently. Publish is non-blocking (bounded queue per subscriber); a slow
  subscriber never stalls the core (satisfies NFR2). A subscriber that overflows
  drops to a "catch up from log" path rather than back-pressuring the core.
- **Event log = append-only JSONL, one file per run.** Each line: monotonically
  increasing `seq`, logical timestamp, `run_id`, `agent_id`, `type`, `payload`.
  Logical ordering (`seq`) drives replay, not wall-clock — guarantees
  determinism (NFR5). fsync on write for crash-safety (NFR6).
- **Run store = filesystem directory per run.** `~/.well-corp-sw/runs/<run_id>/`
  holds `events.jsonl`, `summary.json`, and metadata. `run_id` = sortable
  ULID-style id (no DB needed; `runs` command globs this dir).
- **Validation:** Pydantic v2 models for every event type and config; events are
  validated at publish and on replay-load (fail fast on a corrupt line).

### Orchestration & Agent Integration (API/Communication, adapted)
- **Parent agent = a Claude Agent SDK session** that has the `Agent` tool
  enabled to spawn subagents (parallel, each own context window). The core wraps
  the SDK in an **Agent Runtime Adapter** so the rest of the system depends on
  our event vocabulary, not SDK internals.
- **SDK hooks → events.** SDK lifecycle hooks (tool calls, subagent spawn, vault
  reads, results) are translated by the adapter into domain events on the bus.
  This is the single integration seam (swappable, testable).
- **Error handling standard:** every agent/tool failure becomes a `failure`
  event with cause + last-good `seq`; never a silent exception. Replay can jump
  to it (FR17).

### Decision / Human-in-the-Loop Model
- **A decision point is an awaitable.** Core emits `decision.pending` and awaits
  a future. Resolution comes from one of: (a) policy auto-resolve, (b) human
  input (TUI note or headless prompt), (c) timeout/default per policy. The core
  never blocks indefinitely (NFR8) — unresolved + no policy + headless = fail
  with deterministic exit code or defer per config.
- **Policy = declarative rules** (MVP): match on action type / risk, action =
  allow | deny | ask | default. Evaluated before irreversible/outward actions
  (FR34, NFR11).

### Vault Architecture
- **`VaultProvider` is an abstract interface** (FR8, NFR16): `validate()`,
  `list()`, `read(ref)`, `metadata()`, `search(query|tags)`. MVP ships one
  concrete `HarnessVaultProvider`. Validation runs before a run starts; malformed
  vault fails fast (FR9). Vault reads emit `vault.read` events.

#### Harness Vault Format (resolved)
A harness vault IS an Obsidian-style markdown vault (reuses existing vaults like
`CSharp-Senior-Vault`) with a thin harness convention layer on top.

**On-disk layout:**
```
<vault>/
  .harness/
    manifest.toml        # harness metadata (required)
  index.md               # optional human/agent MOC (Obsidian map-of-content)
  **/*.md                # notes: markdown + YAML frontmatter, wikilinks allowed
```

**`.harness/manifest.toml` (required, the marker that makes a vault "harness"):**
```toml
schema_version = 1            # provider checks compatibility; mismatch = fail fast
name = "csharp-senior"
description = "C# senior-level reference"
include = ["**/*.md"]         # globs the provider exposes to agents
exclude = [".obsidian/**", "templates/**"]
entry_id = "frontmatter.id || relpath"   # how an entry is addressed by ref
```

**Note frontmatter (YAML, per entry):**
```yaml
---
id: api-design            # stable ref (optional; falls back to relative path)
title: API Design
tags: [api, rest]
type: doc                 # doc | snippet | rule (informational; default doc)
---
# body markdown (wikilinks [[other-note]] resolved within the vault)
```

**VaultProvider behavior:**
- `validate()` — `.harness/manifest.toml` exists, `schema_version` supported, all
  included notes parse (valid frontmatter + readable markdown), wikilinks resolve
  within the vault. Any failure → fail fast before the run (FR9).
- `list()` — entries from `include` minus `exclude`, with id/title/tags/type.
- `read(ref)` — fetch one entry by `id` (or relative path); returns body +
  metadata; emits a `vault.read` event.
- `search(query|tags)` — tag/text lookup over the index so agents pull only what
  they need (keeps token cost down).
- An index is built in memory on load (from frontmatter + optional `index.md`);
  no external DB.

### Cost & Safety (Security, adapted)
- **Credentials:** Claude API key from environment / OS keyring only; never
  written to events, summary, or vault (NFR9). Event payloads are scrubbed of
  secrets at the adapter boundary.
- **Cost meter** subscribes to token-usage events, aggregates per-agent and
  per-run, and enforces a hard ceiling: on breach it emits `budget.exceeded` and
  the core halts new fan-out (FR32, NFR12).
- **Action scoping:** agent file/shell actions confined to the bound project +
  configured vault paths; out-of-scope ops denied at the adapter (NFR10).

### Configuration & Policy
- **`wcs.config.toml` at project root** (TOML — Python-native, comment-friendly,
  matches pyproject ergonomics). Holds project binding, vault path(s), autonomy
  policy, cost ceiling, isolation mode. Parsed into Pydantic settings; CLI flags
  override file (FR37, FR38).

### Rendering (Frontend Architecture, adapted)
- **TUI is a pure bus subscriber** built in Textual. It holds NO orchestration
  logic (NFR17) — it maps events → scene state and animates via TCSS. Same
  projection code drives live (subscribe to bus) and replay (feed from JSONL).
- **Scene state = a reducer over events** (entities: agents, vault, desks,
  paths). Identical reducer for live and replay guarantees they match.

### Infrastructure & Deployment
- **No servers, no cloud, no DB.** Single local CLI; state on local filesystem.
  Distribution: `uv`/pip install for MVP; standalone binary deferred.
- **CI:** GitHub Actions running Ruff + Ty + pytest across Win/macOS/Linux
  (NFR15).

### Decision Impact Analysis

**Implementation Sequence:**
1. Event model + bus + JSONL writer (foundation — everything depends on it).
2. Agent Runtime Adapter (SDK → events) + minimal orchestration.
3. Replay reducer + plain timeline.
4. VaultProvider (harness) + vault events.
5. Decision model + simple policy.
6. Cost meter + safety scoping.
7. Config/CLI surface.
8. Textual scene (reuses replay reducer).

**Cross-Component Dependencies:**
- The event vocabulary is the contract between core, adapter, replay, TUI, cost
  meter. Define it first and freeze it carefully — every component couples to it
  (and only to it).
- Replay reducer and live scene MUST share one reducer, or determinism (NFR5)
  and live/replay parity break.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined
Critical conflict points for a Python event-sourced TUI: event naming/shape,
async discipline, module boundaries, error-as-event, secret handling, and the
shared reducer. These are the seams where independent agents diverge.

### Naming Patterns

**Code Naming (PEP 8, enforced by Ruff):**
- Modules/files: `snake_case.py`. Packages: `snake_case/`.
- Classes: `PascalCase` (e.g. `EventBus`, `HarnessVaultProvider`).
- Functions/vars: `snake_case`. Constants: `UPPER_SNAKE`.
- Async functions that do I/O: verb-first, no `_async` suffix (`async def run(...)`).
- Pydantic event models: `PascalCase` + `Event` suffix (`SpawnEvent`).

**Event Naming (the contract — freeze early):**
- Event `type` strings are `lower.dotted`: `agent.spawned`, `task.delegated`,
  `vault.read`, `decision.pending`, `decision.resolved`, `agent.failed`,
  `budget.exceeded`, `run.started`, `run.completed`.
- Format = `<entity>.<past-tense-verb>` for facts; `<entity>.pending` for an
  awaited request. NEVER present-tense or `CamelCase` event types.

**File/CLI Naming:**
- CLI subcommands: `lower-kebab` if multiword; flags `--kebab-case`.
- Run ids: lowercase ULID. Run dir: `~/.well-corp-sw/runs/<ulid>/`.

### Structure Patterns

**Project Organization (src-layout, by responsibility along the bus boundary):**
```
src/well_corp_sw/
  core/        # orchestration loop, run lifecycle — NO TTY, NO render imports
  events/      # event models (Pydantic), EventBus, JSONL writer/reader
  agent/       # Claude Agent SDK adapter (SDK <-> domain events)
  vault/       # VaultProvider ABC + HarnessVaultProvider
  replay/      # event reducer + scene projection + plain timeline
  tui/         # Textual app + widgets + TCSS (subscriber only)
  policy/      # autonomy policy + safety scoping
  cost/        # token/cost meter
  config/      # Pydantic settings, wcs.config.toml loader
  cli/         # command entrypoints (wcs ...)
```
- **Dependency rule:** `core`, `events`, `agent`, `vault`, `policy`, `cost`
  MUST NOT import `tui`. `tui` and `replay` MUST NOT import orchestration logic.
  Import direction is one-way toward `events` (the shared vocabulary).
- **Tests:** `tests/` mirroring the package tree; `test_<module>.py`. Async
  tests use `pytest-asyncio`.

### Format Patterns

**Event payload (every JSONL line):**
```json
{"seq": 42, "ts": "2026-06-08T...Z", "run_id": "01J...", "agent_id": "a3",
 "type": "vault.read", "payload": { ... }}
```
- `seq`: int, monotonic per run, the ONLY ordering authority (not `ts`).
- Field naming inside JSON: `snake_case`.
- Timestamps: ISO-8601 UTC strings, informational only.
- `payload`: a typed Pydantic model per event type; never free-form dict.

**Run summary (`summary.json`):** snake_case, derived purely by replaying events
— never written incrementally by the core (avoids drift from the log).

### Communication Patterns

**Event system:**
- Producers publish via `bus.publish(event)` — fire-and-forget, never awaited
  on a subscriber. One producer (core/adapter); many subscribers.
- Subscribers are async consumers of a bounded queue; on overflow they resync
  from the JSONL log, never back-pressure the producer.
- New event types are ADDITIVE; never repurpose an existing `type` or field.
  Unknown event types must be ignored gracefully by old reducers (forward-compat).

**State management (scene):**
- Scene state is rebuilt by a PURE reducer: `reduce(state, event) -> state`.
- The SAME reducer feeds live (bus) and replay (JSONL). No second code path.
- Immutable updates (return new state); no in-place mutation of shared state.

### Process Patterns

**Error handling:**
- Failures are EVENTS, not exceptions that escape the core. Catch at the
  adapter/core boundary, emit `agent.failed` (or `*.failed`) with `cause` and
  `last_good_seq`, then continue or halt per policy.
- Exceptions only for truly unexpected programmer errors; those still get logged
  as a `run.aborted` event before exit.
- User-facing CLI errors: non-zero deterministic exit codes (documented table).

**Secrets:**
- API keys read only via `config`/env/keyring. A single `scrub()` pass at the
  adapter boundary strips secrets before any event is published. No secret ever
  reaches `events`, `summary.json`, or a vault.

**Async discipline:**
- Core is fully `async`; no blocking calls on the event loop (file I/O for the
  JSONL writer runs in a thread executor or async file API).
- Cancellation-safe: a cancelled run flushes the log and emits `run.aborted`.

### Enforcement Guidelines

**All AI agents MUST:**
- Treat the event vocabulary (`events/`) as the contract; change it only
  additively and update the reducer in the same change.
- Never import `tui` from core-side modules; never put logic in `tui`.
- Represent every failure as an event with `cause` + `last_good_seq`.
- Run `ruff format`, `ruff check`, and `ty` clean before considering work done.
- Keep live and replay on the one shared reducer.

**Pattern Enforcement:**
- Ruff + Ty in CI gate naming/format/types. A lightweight import-linter rule
  enforces the one-way dependency direction (no `tui` import from core).

### Pattern Examples

**Good:** `bus.publish(VaultReadEvent(run_id=rid, agent_id=aid, payload=...))`
then both `replay.reduce` and the live TUI render it identically.

**Anti-pattern:** core calling `tui.update_scene(...)` directly (couples core to
render, violates NFR2/NFR17); or the core writing `summary.json` field-by-field
during the run instead of projecting it from events.

## Project Structure & Boundaries

### Complete Project Directory Structure
```
well-corp-sw/
├── README.md
├── pyproject.toml              # PEP 621, deps, tool config (ruff/ty/pytest)
├── uv.lock
├── .python-version
├── .gitignore
├── wcs.config.example.toml     # sample per-project config
├── .github/
│   └── workflows/
│       └── ci.yml              # ruff + ty + pytest on win/mac/linux
├── src/
│   └── well_corp_sw/
│       ├── __init__.py
│       ├── cli/                # FR1, FR11, FR27, FR28, FR36-FR40
│       │   ├── __init__.py
│       │   ├── app.py          # CLI root, arg parsing, exit codes
│       │   ├── run.py          # `wcs run`
│       │   ├── replay.py       # `wcs replay`
│       │   ├── runs.py         # `wcs runs`
│       │   ├── vault.py        # `wcs vault validate|info`
│       │   ├── config.py       # `wcs config`
│       │   └── resume.py       # `wcs resume`
│       ├── core/               # FR2-FR5, FR22, run lifecycle (no TTY)
│       │   ├── __init__.py
│       │   ├── orchestrator.py # parent loop, delegation, verify
│       │   ├── run.py          # Run aggregate, lifecycle, run_id (ULID)
│       │   └── decision.py     # decision point = awaitable future
│       ├── events/             # FR13, FR18 — the contract
│       │   ├── __init__.py
│       │   ├── models.py       # Pydantic event models + payloads
│       │   ├── bus.py          # async pub/sub, bounded queues
│       │   ├── writer.py       # append-only JSONL writer (fsync)
│       │   └── reader.py       # JSONL loader/validator
│       ├── agent/              # FR2-FR5, FR10 — SDK seam
│       │   ├── __init__.py
│       │   ├── adapter.py      # Claude Agent SDK <-> domain events
│       │   └── scrub.py        # secret scrubbing at boundary (NFR9)
│       ├── vault/              # FR8-FR12, NFR16
│       │   ├── __init__.py
│       │   ├── provider.py     # VaultProvider ABC
│       │   └── harness.py      # HarnessVaultProvider + validation
│       ├── replay/             # FR14-FR18 — shared reducer
│       │   ├── __init__.py
│       │   ├── reducer.py      # pure reduce(state, event) -> state
│       │   ├── scene_state.py  # entities: agents, vault, desks, paths
│       │   ├── timeline.py     # plain textual replay (fallback)
│       │   └── summary.py      # project summary.json from events
│       ├── tui/                # FR15, FR19-FR21 — subscriber only
│       │   ├── __init__.py
│       │   ├── app.py          # Textual App
│       │   ├── scene.py        # scene widget (renders SceneState)
│       │   ├── decision_note.py# on-screen decision UI (Growth)
│       │   └── scene.tcss      # Textual CSS (animation/layout)
│       ├── policy/             # FR24, FR25, FR33, FR34, NFR10/11
│       │   ├── __init__.py
│       │   ├── policy.py       # declarative rules: allow|deny|ask|default
│       │   └── safety.py       # action scoping / blast radius
│       ├── cost/               # FR31, FR32, NFR12
│       │   ├── __init__.py
│       │   └── meter.py        # token/cost aggregation + hard ceiling
│       └── config/             # FR37, FR38
│           ├── __init__.py
│           └── settings.py     # Pydantic settings, wcs.config.toml loader
├── tests/                      # mirrors src tree; pytest + pytest-asyncio
│   ├── conftest.py
│   ├── events/
│   ├── core/
│   ├── replay/
│   ├── vault/
│   ├── policy/
│   ├── cost/
│   └── fixtures/               # sample event logs, sample harness vault
└── docs/
    └── exit-codes.md           # deterministic CLI exit-code table (NFR8)
```

### Architectural Boundaries

**Event boundary (the only inter-module contract):** all modules communicate via
events in `events/`. Producers = `core` + `agent/adapter`. Consumers =
`events/writer`, `cost/meter`, `tui` (optional), `replay` (offline). No module
calls another module's internals across this line.

**Component boundaries:**
- `core` ⟶ publishes events; awaits decision futures; never imports `tui`.
- `agent/adapter` ⟶ the ONLY code touching the Claude Agent SDK; emits events.
- `tui` ⟶ subscribes, renders; zero orchestration logic (NFR17).
- `replay` ⟶ offline consumer of JSONL; shares `reducer`/`scene_state` with `tui`.

**Data boundaries:**
- Run store on filesystem: `~/.well-corp-sw/runs/<ulid>/{events.jsonl,
  summary.json, meta.json}`. No DB.
- `vault/` is the only reader of vault contents; exposes typed reads, emits
  `vault.read`. Agents never read the filesystem vault directly.

### Requirements to Structure Mapping

**Capability → location:**
- Orchestration (FR1-FR7) → `core/`, `agent/adapter.py`
- Knowledge Vaults (FR8-FR12) → `vault/`
- Event Capture & Replay (FR13-FR18) → `events/`, `replay/`
- Live Observability (FR19-FR21) → `tui/`
- Decisions & HITL (FR22-FR26) → `core/decision.py`, `policy/`, `tui/decision_note.py`
- Run Management (FR27-FR30) → `cli/runs.py`, `cli/resume.py`, `core/run.py`
- Cost & Safety (FR31-FR35) → `cost/`, `policy/safety.py`, `agent/scrub.py`
- Configuration (FR36-FR40) → `config/`, `cli/`

**Cross-cutting concerns:**
- Event vocabulary → `events/models.py` (touched by nearly all; additive only).
- Shared scene reducer → `replay/reducer.py` (used by both `replay` and `tui`).
- Secret scrubbing → `agent/scrub.py` (applied before any publish).

### Integration Points

**Internal communication:** in-process async `EventBus`; fire-and-forget
publish, bounded per-subscriber queues, resync-from-log on overflow.

**External integrations:** Claude Agent SDK (only via `agent/adapter.py`);
filesystem (run store, project, vault); terminal (Textual, only via `tui`).

**Data flow:** `core`/`adapter` → `EventBus` → {`writer`→JSONL, `cost/meter`,
`tui` live} ; offline: JSONL → `reader` → `reducer` → {`timeline`, `summary`,
`tui` replay}.

### File Organization Patterns
- **Configuration:** project config = `wcs.config.toml` at the target project
  root; tool config in `pyproject.toml`; runtime state under `~/.well-corp-sw/`.
- **Source:** src-layout, one package per responsibility along the bus boundary.
- **Tests:** mirror the package tree; shared fixtures (sample logs/vault) in
  `tests/fixtures/`.
- **Assets:** Textual `.tcss` lives beside its widget in `tui/`.

### Development Workflow Integration
- **Dev:** `uv run wcs ...` for the CLI; `uv run textual run --dev
  well_corp_sw.tui.app:WcsApp` for hot TUI iteration.
- **Build:** uv builds the package; `wcs` entrypoint via `[project.scripts]`.
- **Deploy:** pip/uv install for MVP; standalone binary (PyInstaller/shiv)
  deferred to a distribution phase.

## Architecture Validation Results

### Coherence Validation ✅
**Decision Compatibility:** Stack is internally consistent — Python 3.10+ /
asyncio / Textual / Claude Agent SDK / Pydantic v2 / uv all interoperate; no
version conflicts. Event-sourcing pattern aligns with the decoupling NFRs.
**Pattern Consistency:** Naming (PEP 8 + dotted event types), one-way import
rule, shared reducer, and error-as-event all reinforce the architectural
decisions rather than contradicting them.
**Structure Alignment:** The src-layout package boundaries physically enforce
the event boundary; `tui` and `core` cannot import each other.

### Requirements Coverage Validation ✅
**Functional Requirements Coverage:** All 40 FRs map to a concrete module
(see Requirements-to-Structure mapping). MVP-tagged FRs all land in
`core/events/agent/vault/replay/policy/cost/config/cli`; Growth/Vision FRs
(FR6-7, FR19-21, FR25-26, FR29-30, FR35) have a defined home and do not require
re-architecting.
**Non-Functional Requirements Coverage:**
- NFR1/2/17 (decoupling) → event bus + import rule + pure-subscriber TUI.
- NFR5/6/7 (determinism/crash-safety) → seq-ordered JSONL, fsync, timeline
  fallback, shared reducer.
- NFR8 (no-hang) → decision-as-awaitable with policy/timeout + exit codes.
- NFR9-12 (secrets/scope/cost) → scrub boundary, action scoping, hard ceiling.
- NFR15 (portability) → pure-Python, no-TTY core, cross-OS CI.
- NFR16 (extensibility) → VaultProvider ABC.

### Implementation Readiness Validation ✅
**Decision Completeness:** Critical decisions documented with concrete choices
(event model, bus, log format, run store, SDK seam, decision model).
**Structure Completeness:** Full directory tree with per-file responsibility and
FR tags; boundaries and data flow explicit.
**Pattern Completeness:** Naming, structure, format, communication, and process
(error/secret/async) patterns all specified with examples and enforcement.

### Gap Analysis Results
**Critical Gaps:** None.
**Important Gaps:** None open.
- ~~Harness vault format not yet formally specified.~~ **RESOLVED** — see
  "Harness Vault Format (resolved)" under Vault Architecture. A harness vault is
  an Obsidian-style markdown vault + a `.harness/manifest.toml` convention layer;
  the `VaultProvider` contract and validation rules are now pinned.
**Nice-to-Have Gaps:**
- Deterministic exit-code table content (`docs/exit-codes.md`) to be filled in.
- Concrete autonomy-policy rule syntax examples (declarative shape agreed;
  exact keys to finalize during the policy story).

### Validation Issues Addressed
The vault-format gap is scoped to the vault implementation story rather than
blocking, because the interface boundary isolates it: the rest of the system
depends on `VaultProvider`, not the concrete format. No architectural rework
needed — only a schema definition.

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment
**Overall Status:** READY FOR IMPLEMENTATION
**Confidence Level:** high
(Updated: the one important gap — harness vault format — is now resolved; all 16
checklist items checked, no critical or important gaps remain. Only nice-to-have
items, exit-code table content and policy-rule syntax examples, are deferred to
their implementation stories.)

**Key Strengths:**
- Hard core/render decoupling enforced physically by structure.
- Event sourcing makes determinism, replay, live, and summary one mechanism.
- Single SDK seam keeps agent-runtime swappable and testable.
- Every FR traces to a file; clear MVP-first build sequence.

**Areas for Future Enhancement:**
- Policy rule DSL maturity (Growth).
- Per-agent worktree isolation (Growth).
- Standalone binary packaging (distribution phase).

### Implementation Handoff
**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented.
- Treat `events/models.py` as the frozen contract; extend only additively.
- Never import `tui` from core-side modules; keep logic out of `tui`.
- Keep live and replay on the one shared reducer.
- Run ruff + ty + pytest clean before completing any story.

**First Implementation Priority:**
`uv init --package well-corp-sw` then `uv add claude-agent-sdk textual` and the
event model + bus + JSONL writer (the foundation everything depends on).
