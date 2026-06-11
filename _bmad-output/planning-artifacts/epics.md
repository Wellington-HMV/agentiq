---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories']
inputDocuments: ['_bmad-output/planning-artifacts/prd.md', '_bmad-output/planning-artifacts/architecture.md', '_bmad-output/planning-artifacts/ux-design-specification.md']
---

# well-corp-sw - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for well-corp-sw,
decomposing the requirements from the PRD, UX Design, and Architecture into
implementable stories.

## Requirements Inventory

### Functional Requirements

**Orchestration**
- FR1: A developer can start an orchestration run by giving a goal and a target project. [MVP]
- FR2: A parent agent can decompose a goal into tasks and delegate them to subagents. [MVP]
- FR3: A parent agent can spawn subagents on demand and reuse already-spawned agents. [MVP]
- FR4: The system can run a full orchestration unattended (headless). [MVP]
- FR5: The parent agent can verify subagent results against vault context. [MVP]
- FR6: A developer can organize agents into named teams. [Growth]
- FR7: The system can run multiple teams concurrently. [Growth]

**Knowledge Vaults**
- FR8: The system can load a harness-standard vault via a VaultProvider. [MVP]
- FR9: The system can validate vault conformance and fail fast on a malformed vault. [MVP]
- FR10: Agents can read context from a loaded vault during a run. [MVP]
- FR11: A developer can inspect a vault's contents and metadata. [MVP]
- FR12: The system can reuse the same vault across runs and projects. [MVP]

**Event Capture & Replay**
- FR13: The system records every orchestration event to an append-only log. [MVP]
- FR14: A developer can replay a past run as a plain textual timeline. [MVP]
- FR15: A developer can replay a past run as a spatial scene. [MVP]
- FR16: A developer can scrub a replay to any point in the run. [MVP]
- FR17: A developer can jump a replay directly to the point of a failure. [MVP]
- FR18: The system reconstructs a run deterministically from its event log. [MVP]

**Live Observability**
- FR19: A developer can watch a run live as an animated spatial scene. [Growth]
- FR20: The live scene reflects real state and never blocks/slows the core. [Growth]
- FR21: A developer can zoom/group-by-team/focus-follow for legibility at scale. [Vision]

**Decisions & Human-in-the-Loop**
- FR22: The system can pause a run at a decision point requiring human input. [MVP]
- FR23: A developer can resolve a pending decision via options with a visible default. [MVP]
- FR24: The system can auto-resolve a decision by policy. [MVP]
- FR25: A developer can define autonomy policy (auto-resolve vs ask). [Growth]
- FR26: Pending decisions surface as first-class on-screen notes in the live scene. [Growth]

**Run Management**
- FR27: A developer can list past runs (id, goal, status, cost, duration). [MVP]
- FR28: A developer can resume a paused or blocked run. [MVP]
- FR29: A developer can re-run from a sane prior state after a failure. [Growth]
- FR30: A developer can compare or diff two runs. [Vision]

**Cost & Safety Controls**
- FR31: The system tracks token and cost usage per run and per agent. [MVP]
- FR32: A developer can set a cost ceiling that throttles/halts fan-out. [MVP]
- FR33: The system enforces allowed/denied operation rules on agent actions. [MVP]
- FR34: The system requires a human decision before irreversible/outward actions. [MVP]
- FR35: The system isolates concurrently-writing agents (worktree). [Growth]

**Configuration & Setup**
- FR36: A developer can bind a project directory to the tool. [MVP]
- FR37: A developer can configure vault path(s), policy, ceiling, isolation via per-project config. [MVP]
- FR38: A developer can override config values with CLI flags. [MVP]
- FR39: The system emits a machine- and human-readable run summary. [MVP]
- FR40: A developer can drive the tool non-interactively with deterministic exit codes. [MVP]

### NonFunctional Requirements

- NFR1: Live scene sustains ~30fps on a separate thread/process; never blocks core.
- NFR2: Core makes zero blocking calls into render; render is a pure event consumer.
- NFR3: A developer reconstructs a full run via replay in under ~2 minutes.
- NFR4: Event capture adds negligible overhead to orchestration.
- NFR5: Replay is deterministic — same log always reproduces same timeline/scene.
- NFR6: Event log is append-only and crash-safe (replayable up to last completed event).
- NFR7: A run always degrades to the plain textual timeline; textual replay never lost.
- NFR8: Headless runs end with deterministic exit codes; decisions never hang forever.
- NFR9: API credentials never written to log/summary/vault.
- NFR10: Agent actions confined to bound project + configured vault paths.
- NFR11: Irreversible/outward actions blocked pending explicit decision.
- NFR12: Cost ceilings enforced hard — fan-out halts on breach.
- NFR13: Spatial scene measurably clearer than logs (validated vs <2-min target).
- NFR14: Scene stays legible as agent count grows (validated N=10+).
- NFR15: Runs on Win/macOS/Linux from one codebase; core needs no TTY.
- NFR16: VaultProvider is an interface allowing alternative harness sources.
- NFR17: Core/emitter/renderer are separable modules talking only via the event bus.

### Additional Requirements

(from Architecture — technical/implementation requirements)

- AR1: **Project initialization (Epic 1, Story 1):** `uv init --package well-corp-sw`
  + `uv add claude-agent-sdk textual` + dev deps `ruff ty pytest pytest-asyncio`;
  src-layout package; `wcs` entrypoint via `[project.scripts]`.
- AR2: Event model = Pydantic v2 models per event type; append-only JSONL writer
  with `seq` ordering + fsync; JSONL reader/validator.
- AR3: In-process async `EventBus` (pub/sub, bounded per-subscriber queues,
  resync-from-log on overflow, non-blocking publish).
- AR4: Agent Runtime Adapter — only code touching Claude Agent SDK; SDK hooks →
  domain events; secret `scrub()` at the boundary.
- AR5: Shared pure scene reducer `reduce(state, event) -> state` driving both live
  and replay (single code path).
- AR6: Run store on filesystem `~/.well-corp-sw/runs/<ulid>/{events.jsonl,
  summary.json, meta.json}`; ULID run ids; `summary.json` projected from events.
- AR7: `HarnessVaultProvider` — Obsidian-style markdown vault + `.harness/manifest.toml`
  convention; validate/list/read/search; vault reads emit events.
- AR8: Config = `wcs.config.toml` per project parsed to Pydantic settings; CLI
  flags override file.
- AR9: CLI surface (`wcs run|replay|runs|vault|config|resume`) with deterministic
  exit-code table (`docs/exit-codes.md`).
- AR10: CI = Ruff + Ty + pytest across Win/macOS/Linux; import-linter rule
  enforcing one-way dependency direction (no `tui` import from core).
- AR11: Autonomy/safety policy = declarative rules (allow|deny|ask|default);
  action scoping / blast-radius; cost meter with hard ceiling.

### UX Design Requirements

- UX-DR1: `SceneWidget` — fixed top-down office floor-plan: zones LIBRARY / DESKS /
  SUBAGENTS, anchored parent, delegation paths; renders `SceneState`; full /
  compact / minimal / static representations. [MVP basic, Growth rich]
- UX-DR2: `Creature` widget — agent sprite; position+posture+frame encode state
  (idle/walking/reading/thinking/delegating/failed/done/dimmed); role glyph+color;
  ASCII fallback frames; parent vs subagent variant.
- UX-DR3: `TransportBar` — playhead ▶, progress track, decision ◆ + failure ✕
  markers, seq/total counter, current-event caption; keys space/←→/n-p/f/g/</>.
- UX-DR4: `DecisionNote` modal — prompt + numbered options + highlighted default +
  context line; Enter=default, number=option, Esc=defer; persists as ◆ in replay.
- UX-DR5: `InspectOverlay` modal — drill into focused agent/event/decision (detail,
  vault ref, token/cost, rationale) without leaving the scene.
- UX-DR6: `TimelineView` — plain textual replay (one line per event), pipeable,
  the universal fallback (no-TTY/reduced/accessibility).
- UX-DR7: TCSS token layer — semantic color roles (bg/surface/text/accent/success/
  warning/error/role-*/zone), glyph set with ASCII fallbacks, motion timings;
  capability tiers truecolor→256→16→no-color.
- UX-DR8: Keyboard-first interaction model — single-key actions, Enter=primary,
  q/Esc=back, persistent `Footer` keybinding hints on every screen.
- UX-DR9: Responsive representation selection — function of (size tier, capability
  tier) choosing full/compact/minimal/timeline; reacts to terminal resize.
- UX-DR10: Accessibility — never color-only (glyph+label pair), reduced-motion
  (`--no-anim`) renders same semantic scene static, colorblind-safe palette.
- UX-DR11: Runs browser screen (`DataTable`) + empty/loading/idle states (empty
  shows the exact `wcs run` command; loading is labeled; idle agents dimmed).

### FR Coverage Map

- FR1: Epic 1 — start a run (goal + project)
- FR2: Epic 1 — parent decomposes/delegates
- FR3: Epic 1 — spawn/reuse subagents
- FR4: Epic 1 — headless unattended run
- FR5: Epic 3 — verify results against vault
- FR6: Epic 5 — named teams
- FR7: Epic 5 — concurrent teams
- FR8: Epic 3 — load harness vault
- FR9: Epic 3 — validate vault / fail fast
- FR10: Epic 3 — agents read vault context
- FR11: Epic 3 — inspect vault
- FR12: Epic 3 — reuse vault across runs/projects
- FR13: Epic 1 — record events to append-only log
- FR14: Epic 2 — replay as plain timeline
- FR15: Epic 2 — replay as spatial scene
- FR16: Epic 2 — scrub to any point
- FR17: Epic 2 — jump to failure
- FR18: Epic 1 — deterministic reconstruction from log
- FR19: Epic 5 — watch live animated scene
- FR20: Epic 5 — live scene never blocks core
- FR21: Epic 6 — zoom/group/focus at scale
- FR22: Epic 4 — pause at decision point
- FR23: Epic 4 — resolve decision via options/default
- FR24: Epic 4 — auto-resolve by policy
- FR25: Epic 5 — define autonomy policy
- FR26: Epic 5 — decision notes as first-class live UI
- FR27: Epic 1 — list past runs
- FR28: Epic 4 — resume paused/blocked run
- FR29: Epic 5 — re-run from sane state
- FR30: Epic 6 — compare/diff runs
- FR31: Epic 4 — track token/cost per run+agent
- FR32: Epic 4 — cost ceiling halts fan-out
- FR33: Epic 4 — allowed/denied operation rules
- FR34: Epic 4 — require decision before irreversible
- FR35: Epic 5 — isolate concurrent writers (worktree)
- FR36: Epic 1 — bind project directory
- FR37: Epic 1 — per-project config
- FR38: Epic 1 — CLI flags override config
- FR39: Epic 1 — run summary output
- FR40: Epic 1 — non-interactive deterministic exit codes

## Epic List

### Epic 1: Autonomous Run & Faithful Log
A developer points the tool at a project, gives a goal, and Claude agents
(parent → subagents) run unattended (headless), producing a complete,
deterministic, replayable event log plus a run summary. Delivers the foundation
and the first user value: hand off a goal, get back a faithful record.
**FRs covered:** FR1, FR2, FR3, FR4, FR13, FR18, FR27, FR36, FR37, FR38, FR39, FR40
**Supports:** NFR2, NFR5, NFR6, NFR8, NFR9, NFR15, NFR17 · AR1-AR6, AR8, AR9, AR10

### Epic 2: Legible Replay (Timeline + Spatial Scene)
A developer opens a finished run and understands it in under ~2 minutes — first
as a plain textual timeline, then as the top-down spatial scene with scrubbing
and jump-to-failure. The product's killer experience and the PRD kill-criterion.
**FRs covered:** FR14, FR15, FR16, FR17
**Supports:** UX-DR1-UX-DR11 · NFR3, NFR7, NFR13

### Epic 3: Knowledge Vaults
Agents draw on a reusable harness-standard knowledge vault during a run; the
developer can inspect and validate vaults; the parent verifies subagent results
against vault context.
**FRs covered:** FR5, FR8, FR9, FR10, FR11, FR12
**Supports:** NFR16 · AR7

### Epic 4: Decisions & Safety Controls
Runs respect the developer's limits and ask only when needed: blocking decision
points, policy auto-resolve/ask, on-screen decision notes, hard cost ceiling,
action scoping, confirm-before-irreversible, and resume. Completes the MVP.
**FRs covered:** FR22, FR23, FR24, FR28, FR31, FR32, FR33, FR34
**Supports:** NFR10, NFR11, NFR12 · AR11

### Epic 5: Live Watch Mode (Growth)
Watch a run live as an animated scene with real-time decision notes; organize
named teams running concurrently; richer policy engine; per-agent worktree
isolation; re-run from a sane state; shell completion.
**FRs covered:** FR6, FR7, FR19, FR20, FR25, FR26, FR29, FR35

### Epic 6: Scale & Vision (Vision)
Stay legible at scale (zoom / group-by-team / focus-follow), an alternate
org-tree view, run comparison/diffing, and full creature personalities.
**FRs covered:** FR21, FR30

## Epic 1: Autonomous Run & Faithful Log

A developer points the tool at a project, gives a goal, and Claude agents run
unattended, producing a complete, deterministic, replayable event log + summary.

### Story 1.1: Project scaffold and CLI skeleton

As a developer,
I want an installable `wcs` CLI scaffold with linting, typing, and tests wired up,
So that I have a clean, cross-platform foundation to build every other feature on.

**Acceptance Criteria:**

**Given** a clean machine with uv installed
**When** the project is initialized per Architecture (`uv init --package`, deps added)
**Then** `wcs --version` and `wcs --help` run and exit 0 with no TTY required
**And** `ruff check`, `ruff format --check`, and `ty` pass on the empty scaffold
**And** `pytest` runs (even with zero tests) and CI runs all three on Win/macOS/Linux
**And** an import-linter rule fails the build if `core` imports `tui`.

### Story 1.2: Event model and append-only JSONL log

As a developer,
I want typed events written to an append-only, seq-ordered JSONL log,
So that every run has a faithful, crash-safe, replayable record.

**Acceptance Criteria:**

**Given** the event models (Pydantic v2) for run/agent/vault/decision/result/failure
**When** events are written during a run
**Then** each line is `{seq, ts, run_id, agent_id, type, payload}` with monotonic `seq`
**And** the writer fsyncs so an interrupted run leaves a valid log up to the last event
**And** the reader validates each line and fails fast on a corrupt/incompatible line
**And** ordering is by `seq` only, never wall-clock (NFR5).

### Story 1.3: In-process async event bus

As a developer,
I want a non-blocking async pub/sub bus,
So that the core can emit events without ever waiting on a consumer (NFR2).

**Acceptance Criteria:**

**Given** the bus with one producer and multiple subscribers (bounded queues)
**When** the core publishes an event
**Then** publish returns without awaiting any subscriber
**And** a slow/overflowing subscriber does not back-pressure the producer
**And** an overflowed subscriber can resync from the JSONL log rather than losing events.

### Story 1.4: Run store and lifecycle

As a developer,
I want each run persisted under a stable run directory with a project binding,
So that runs can be listed, resumed, and replayed later.

**Acceptance Criteria:**

**Given** a run is started against a bound project directory
**When** the run begins
**Then** a `~/.well-corp-sw/runs/<ulid>/` dir is created with `meta.json` + `events.jsonl`
**And** the `run_id` is a sortable ULID
**And** `run.started` and `run.completed`/`run.aborted` events bound the lifecycle.

### Story 1.5: Per-project configuration

As a developer,
I want a `wcs.config.toml` parsed into typed settings with CLI overrides,
So that I can configure a project once and override per invocation.

**Acceptance Criteria:**

**Given** a `wcs.config.toml` at the project root
**When** `wcs` loads config
**Then** project binding, vault path(s), policy, cost ceiling, isolation parse into Pydantic settings
**And** a CLI flag overrides the matching file value
**And** an invalid config fails fast with a specific message (not a generic error).

### Story 1.6: Agent runtime adapter with secret scrubbing

As a developer,
I want a single adapter wrapping the Claude Agent SDK that emits domain events,
So that the rest of the system depends on our event vocabulary, not the SDK, and no secret leaks.

**Acceptance Criteria:**

**Given** the adapter is the only module importing the Claude Agent SDK
**When** the parent spawns subagents and they act
**Then** SDK lifecycle hooks are translated into domain events on the bus
**And** subagents can be spawned and reused (FR3), each with its own context
**And** a `scrub()` pass removes API credentials before any event is published (NFR9)
**And** a unit test asserts no credential string appears in any emitted event or summary.

### Story 1.7: Headless orchestration loop

As a developer,
I want to start a goal-driven run that the parent decomposes and delegates, unattended,
So that I can hand off work and walk away.

**Acceptance Criteria:**

**Given** `wcs run "<goal>" --project <path> --headless`
**When** the run executes with no human present
**Then** the parent decomposes the goal and delegates tasks to subagents (FR2)
**And** the run completes or fails without requiring a TTY (FR4, NFR15)
**And** replaying the resulting log reproduces the same event sequence deterministically (FR18).

### Story 1.8: Run summary and deterministic exit codes

As a developer,
I want a machine- and human-readable summary and documented exit codes,
So that runs are scriptable and CI-friendly.

**Acceptance Criteria:**

**Given** a finished run
**When** the run ends
**Then** `summary.json` (status, decisions, cost, duration) is projected purely from events
**And** the process exits with a documented deterministic code per `docs/exit-codes.md` (NFR8)
**And** an unresolved decision in headless mode never hangs — it fails or defers per config.

### Story 1.9: List past runs

As a developer,
I want to list previous runs,
So that I can find a run to replay or resume.

**Acceptance Criteria:**

**Given** one or more runs exist in the run store
**When** I run `wcs runs`
**Then** I see id, goal, status, cost, and duration for each, newest first
**And** with no runs, I see a one-line hint showing the exact `wcs run` command.

## Epic 2: Legible Replay (Timeline + Spatial Scene)

A developer opens a finished run and understands it in under ~2 minutes via a
plain timeline and the top-down spatial scene.

### Story 2.1: Scene reducer and scene state

As a developer,
I want a pure reducer that folds events into a scene state,
So that live and replay are guaranteed identical (one code path).

**Acceptance Criteria:**

**Given** a sequence of events from a run
**When** they are folded with `reduce(state, event)`
**Then** the resulting `SceneState` (agents, zones, paths, current event) is deterministic
**And** the reducer is pure (same input → same output, no side effects)
**And** unknown event types are ignored gracefully (forward-compat).

### Story 2.2: Plain textual timeline replay

As a developer,
I want to replay a run as a plain text timeline,
So that I always have a complete, pipeable, fallback view of any run.

**Acceptance Criteria:**

**Given** a run's event log
**When** I run `wcs replay <run-id> --timeline`
**Then** I see one line per event (`seq · ts · agent · type · summary`) in order
**And** decision and failure events are marked inline
**And** it works with no TTY and is pipeable (FR14, NFR7).

### Story 2.3: Replay transport and seeking

As a developer,
I want to play, pause, step, and seek through a run,
So that I can move to any moment instantly.

**Acceptance Criteria:**

**Given** a replay is open
**When** I press space / ←/→ / home/end / </>
**Then** playback toggles, steps one event, jumps to start/end, and changes speed
**And** seeking to any seq is immediate (no perceptible lag) (FR16).

### Story 2.4: Jump to decisions and failures

As a developer,
I want to jump straight to decisions and failures,
So that I can answer "why?" and "where did it break?" in one keypress.

**Acceptance Criteria:**

**Given** a replay with decision and failure events
**When** I press `n`/`p` (decision) or `f` (failure)
**Then** the replay lands on the next/previous decision or failure
**And** landing on a failure shows the cause and last-good state (FR17).

### Story 2.5: TUI app shell and token layer

As a developer,
I want the Textual app shell with the TCSS token layer and a keybinding footer,
So that all screens share one visual language and discoverable keys.

**Acceptance Criteria:**

**Given** the Textual app
**When** any screen is shown
**Then** a persistent `Footer` lists the active keybindings (UX-DR8)
**And** colors/glyphs/motion come from central TCSS tokens with ASCII + no-color fallbacks (UX-DR7)
**And** `q`/Esc consistently backs out one level.

### Story 2.6: Spatial scene rendering

As a developer,
I want the top-down office floor-plan with creatures,
So that I can read agent activity spatially at a glance.

**Acceptance Criteria:**

**Given** a `SceneState` during replay
**When** `wcs replay <run-id>` (scene mode) renders
**Then** fixed zones LIBRARY/DESKS/SUBAGENTS and the anchored parent are shown (UX-DR1)
**And** each `Creature`'s position/posture/frame encodes its state, not color alone (UX-DR2)
**And** the scene matches the reducer state exactly at every seq (FR15, NFR5).

### Story 2.7: Transport bar widget

As a developer,
I want a visual transport bar with markers and a caption,
So that I always know where I am and what's happening.

**Acceptance Criteria:**

**Given** the scene replay
**When** it renders
**Then** a `TransportBar` shows playhead ▶, progress, ◆ decision + ✕ failure markers, and seq/total (UX-DR3)
**And** a one-line present-tense caption names the current event.

### Story 2.8: Inspect overlay

As a developer,
I want to drill into a focused agent or event,
So that I can see detail without losing the scene.

**Acceptance Criteria:**

**Given** a focused agent/event in the scene
**When** I press `enter`
**Then** an `InspectOverlay` shows detail (state, vault ref, token/cost, decision rationale) (UX-DR5)
**And** Esc closes it and returns to the scene with context intact.

### Story 2.9: Runs browser screen

As a developer,
I want a runs list screen with clear empty/loading/idle states,
So that picking a run to read is effortless.

**Acceptance Criteria:**

**Given** the runs browser (`DataTable`)
**When** runs exist
**Then** I can select one to open its replay
**And** with no runs an empty state shows the exact `wcs run` command (UX-DR11)
**And** loading is labeled ("loading runs…"), never a bare spinner.

### Story 2.10: Responsive representation and accessibility

As a developer,
I want the scene to adapt to terminal size/capability and stay accessible,
So that it's legible everywhere and never hides the truth.

**Acceptance Criteria:**

**Given** different terminal sizes and color capabilities
**When** the scene renders or the terminal is resized
**Then** representation switches full/compact/minimal/timeline by (size, capability) tier (UX-DR9)
**And** `--no-anim` renders the same semantic scene statically (UX-DR10)
**And** meaning is never color-only (glyph+label pair); below threshold it degrades to the timeline (NFR7, NFR13).

## Epic 3: Knowledge Vaults

Agents draw on a reusable harness-standard vault; the developer can inspect and
validate it; the parent verifies results against vault context.

### Story 3.1: VaultProvider interface and harness vault loading

As a developer,
I want a `VaultProvider` interface with a `HarnessVaultProvider` that loads my Obsidian-style vault,
So that agents can use a reusable knowledge library by a stable convention.

**Acceptance Criteria:**

**Given** a vault dir with `.harness/manifest.toml` + markdown notes
**When** the provider loads it
**Then** the manifest (schema_version, include/exclude, entry_id) is parsed and an in-memory index is built
**And** the provider exposes `validate/list/read/search` behind the `VaultProvider` ABC (NFR16)
**And** notes' YAML frontmatter (id/title/tags/type) is indexed; wikilinks resolve within the vault.

### Story 3.2: Vault validation with fail-fast

As a developer,
I want a vault validated before a run starts,
So that a malformed vault never feeds agents bad context.

**Acceptance Criteria:**

**Given** a vault that is missing its manifest, has an unsupported schema_version, or has unparseable notes/broken wikilinks
**When** validation runs (at load or via `wcs vault validate`)
**Then** it fails fast with a specific error pointing at the offending entry (FR9)
**And** a conformant vault validates successfully.

### Story 3.3: Vault read, list, and search with events

As a developer,
I want agents and I to read, list, and search vault entries,
So that the right context is pulled with minimal token cost.

**Acceptance Criteria:**

**Given** a loaded vault
**When** an entry is read by id or relative path
**Then** its body + metadata are returned and a `vault.read` event is emitted (FR10)
**And** `search(query|tags)` returns matching entries from the index
**And** the same vault loads unchanged across different runs and projects (FR12).

### Story 3.4: Vault inspection command

As a developer,
I want `wcs vault validate|info <path>`,
So that I can check and explore a vault outside a run.

**Acceptance Criteria:**

**Given** a vault path
**When** I run `wcs vault info <path>`
**Then** I see the manifest summary and entry list (id/title/tags) (FR11)
**And** `wcs vault validate <path>` reports valid or the specific failures.

### Story 3.5: Agents use vault context and verify results

As a developer,
I want subagents to read vault context and the parent to verify results against it,
So that runs are grounded in my knowledge library.

**Acceptance Criteria:**

**Given** a run configured with a valid vault
**When** subagents work
**Then** they read relevant vault entries (emitting `vault.read`) during the run (FR10)
**And** the parent verifies subagent results against vault context before accepting them (FR5).

## Epic 4: Decisions & Safety Controls

Runs respect the developer's limits and ask only when needed. Completes the MVP.

### Story 4.1: Decision point as an awaitable

As a developer,
I want the core to pause at a decision point and await resolution,
So that human-in-the-loop never blocks forever.

**Acceptance Criteria:**

**Given** the orchestration reaches a decision point
**When** it needs a choice
**Then** it emits `decision.pending` and awaits a future (FR22)
**And** in headless mode with no resolution path it fails or defers per config (never hangs) (NFR8)
**And** resolution emits `decision.resolved`.

### Story 4.2: Autonomy policy engine

As a developer,
I want declarative policy rules deciding allow/deny/ask/default,
So that most decisions resolve automatically.

**Acceptance Criteria:**

**Given** policy rules in config
**When** a decision is evaluated
**Then** a matching rule auto-resolves it (allow/deny/default) without human input (FR24)
**And** an `ask` match (or no match) routes to human resolution
**And** the applied rule is recorded on the `decision.resolved` event.

### Story 4.3: Resolve a decision via options and default

As a developer,
I want to answer a pending decision by choosing an option with a visible default,
So that answering is one keystroke.

**Acceptance Criteria:**

**Given** a pending decision needing human input
**When** I am prompted (headless prompt or, later, the on-screen note)
**Then** options are presented with a clearly marked default (FR23)
**And** Enter accepts the default and a number picks an option
**And** the resolved decision persists in the log (surfaces as a ◆ marker in replay).

### Story 4.4: Cost metering and hard ceiling

As a developer,
I want token/cost tracked per run and per agent with a hard ceiling,
So that runs never overspend.

**Acceptance Criteria:**

**Given** a configured cost ceiling
**When** agents consume tokens
**Then** cost is aggregated per agent and per run from usage events (FR31)
**And** on breach the meter emits `budget.exceeded` and the core halts new fan-out (FR32, NFR12)
**And** current cost is available to the summary and the scene.

### Story 4.5: Action scoping and confirm-before-irreversible

As a developer,
I want agent actions confined to allowed scope and gated before irreversible ones,
So that autonomous runs stay safe.

**Acceptance Criteria:**

**Given** allowed/denied operation rules and a bound project + vault paths
**When** an agent attempts an action
**Then** out-of-scope file/shell actions are denied at the adapter (FR33, NFR10)
**And** an irreversible or outward-facing action is blocked pending an explicit decision (FR34, NFR11).

### Story 4.6: Resume a paused or blocked run

As a developer,
I want to resume a run that paused or blocked on a decision,
So that I don't lose progress.

**Acceptance Criteria:**

**Given** a run paused/blocked on a pending decision
**When** I run `wcs resume <run-id>`
**Then** the run reloads from its log and continues from the pending decision (FR28)
**And** resuming appends to the same event log without breaking determinism.

## Epic 5: Live Watch Mode (Growth)

### Story 5.1: Watch a run live
As a developer, I want `wcs run --watch` to show the scene updating in real time,
So that I can observe a tricky run as it happens.
**Acceptance Criteria:**
**Given** a run started with `--watch`
**When** the run executes
**Then** the scene subscribes to the live bus and animates current activity (FR19)
**And** the render runs separately and never blocks or slows the core (FR20, NFR1, NFR2).

### Story 5.2: On-screen decision notes (live)
As a developer, I want pending decisions to surface as first-class notes in the live scene,
So that I can answer without leaving the world.
**Acceptance Criteria:**
**Given** a live run hits a human decision
**When** it pauses
**Then** a `DecisionNote` overlay shows prompt/options/default and pauses the scene (FR26)
**And** resolving it resumes the world.

### Story 5.3: Named and concurrent teams
As a developer, I want to organize agents into named teams that can run concurrently,
So that larger work is structured.
**Acceptance Criteria:**
**Given** a goal that warrants multiple teams
**When** the parent organizes work
**Then** agents are grouped into named teams (FR6)
**And** multiple teams run concurrently without event-ordering corruption (FR7).

### Story 5.4: Author autonomy policy
As a developer, I want to define which decisions auto-resolve vs ask,
So that I tune autonomy to my comfort.
**Acceptance Criteria:**
**Given** the policy config
**When** I define rules
**Then** the engine applies them to live and headless decisions (FR25).

### Story 5.5: Per-agent worktree isolation
As a developer, I want concurrently-writing agents isolated,
So that parallel work doesn't conflict.
**Acceptance Criteria:**
**Given** isolation enabled and agents writing concurrently
**When** they run
**Then** each writes in its own worktree and changes merge without clobbering (FR35)
**And** with isolation off, concurrent writers are serialized.

### Story 5.6: Re-run from a sane state
As a developer, I want to re-run from the last good state after a failure,
So that I don't restart from scratch.
**Acceptance Criteria:**
**Given** a failed run
**When** I re-run from a sane prior point
**Then** the run resumes from the last-good state rather than seq 0 (FR29).

### Story 5.7: Shell completion
As a developer, I want shell completion for `wcs`,
So that commands and run-ids are fast to type.
**Acceptance Criteria:**
**Given** completion installed
**When** I tab-complete
**Then** subcommands, flags, and existing run-ids complete.

## Epic 6: Scale & Vision (Vision)

### Story 6.1: Legibility at scale
As a developer, I want zoom / group-by-team / focus-follow,
So that the scene stays readable with many agents.
**Acceptance Criteria:**
**Given** a run with 10+ agents
**When** the scene would crowd
**Then** I can zoom, group by team, or focus-follow one agent and stay legible (FR21, NFR14).

### Story 6.2: Org-tree alternate view
As a developer, I want an alternate hierarchical org-tree view,
So that I can read structure densely when preferred.
**Acceptance Criteria:**
**Given** a run
**When** I switch view
**Then** a parent→subagent tree with per-node state renders from the same reducer state.

### Story 6.3: Compare runs
As a developer, I want to compare or diff two runs,
So that I can see what changed between attempts.
**Acceptance Criteria:**
**Given** two run-ids
**When** I compare them
**Then** differences in decisions, outcomes, and cost are shown side by side (FR30).

### Story 6.4: Creature personalities
As a developer, I want expressive creature personalities,
So that the living-office feel is fully realized.
**Acceptance Criteria:**
**Given** the scene
**When** agents act
**Then** creatures show characterful idle/role animations that still encode real state (charm bounded by legibility).
