---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
releaseMode: phased
goal: 'Solo dev hands off a task to a project; Claude agents (parent -> teams -> subagents) self-organize, consult harness vaults, decide autonomously, run headless. The dev later (or live) reviews everything via a legible replay rendered as a living spatial scene (library/desk/path) and understands every decision. Reliable autonomy + legible replay = the product.'
inputDocuments: []
workflowType: 'prd'
classification:
  projectType: 'CLI/TUI animated agent orchestrator'
  domain: 'Developer tools / AI orchestration'
  complexity: 'high'
  projectContext: 'greenfield'
corePrinciples:
  - 'Reliable autonomy is the product; animation is the hook/observability, not the value'
  - 'Headless core decoupled from render via event stream; core never waits on UI'
  - 'Human supervision is opt-in: autonomous (headless) and accompanied (animated) modes'
  - 'Human decision = blocking point resolvable by policy (auto) OR input (on-screen note)'
  - 'Replay/timeline required to audit headless runs'
  - 'Vaults follow harness standard via VaultProvider interface'
  - 'Spatial metaphor as mental map (library=vault, desk=thinking, path=delegation); pretty serves comprehensible'
---

# Product Requirements Document - well-corp-sw

**Author:** User
**Date:** 2026-05-29

## Executive Summary

well-corp-sw is a personal CLI/TUI tool for a solo developer to orchestrate
Claude-based multi-agent work across their own projects. The user points it at
a project, states the goal, and a parent agent self-organizes the work —
spawning teams and subagents, consulting harness-standard knowledge vaults, and
resolving most decisions autonomously. The system runs headless by default;
human supervision is opt-in.

The deeper problem: multi-agent orchestration today is invisible and
illegible. Work happens behind raw logs and cold dashboards, so the developer
can neither trust the outcome nor reconstruct how it was reached. well-corp-sw
solves this with a **clear replay** — after a run (or live, opt-in), the
developer reviews everything as a legible spatial scene: which agent went to
the library (vault), which paused to think, which delegated, what decisions
were made and why. Understanding what N agents did stops being log archaeology.

### What Makes This Special

- **Reliable autonomy is the product, not the spectacle.** It works fully
  headless; the animated scene is an opt-in lens for trust and audit.
- **Legible replay as the killer moment.** Orchestration is rendered as a
  living spatial scene (library = vault, desk = thinking, path = delegation),
  turning a debugging chore into an understandable story.
- **Reusable harness-standard vaults.** Agent knowledge lives in structured
  vaults (via a VaultProvider interface), reusable across runs and projects.
- **Human-in-the-loop without babysitting.** Decisions are blocking points the
  core resolves by policy (auto) or by a single on-screen note when the call is
  the developer's.

The core insight: logs don't tell a story — a spatial scene plus replay does.
This is what closes orchestration's two real gaps, trust and legibility.

## Project Classification

- **Project Type:** CLI/TUI application — Claude agent orchestrator with an
  optional animation layer
- **Domain:** Developer tools / AI orchestration
- **Complexity:** High — headless multi-agent orchestration + animated TUI
  engine + Claude Agent SDK integration + harness vaults + human-decision UI
- **Project Context:** Greenfield
- **Primary User:** Solo developer orchestrating their own projects

## Success Criteria

### User Success
The solo developer can hand off a task, walk away, and later understand 100% of
what happened through replay alone — without reading raw logs. Reconstructing
what N agents did takes under ~2 minutes of replay. Trust is high enough to run
headless: the "aha" moment is opening the replay and having the spatial scene
tell the story by itself.

### Business Success (Personal Value)
Not a commercial product — success is sustained personal adoption. The tool is
used on real projects regularly (not abandoned after novelty wears off) and
measurably cuts the time spent understanding agent work versus reading logs.

### Technical Success
- Headless core never blocks waiting on the UI (render fully decoupled, zero
  logic coupling).
- Replay deterministically reconstructs any run from the event log.
- Animation runs smoothly (~30fps) without slowing orchestration.
- VaultProvider successfully loads a harness-standard vault.

### Measurable Outcomes
- ≥80% of tasks complete autonomously with no human intervention.
- Replay lets the developer reconstruct a full run in under ~2 minutes.
- Animation sustains ~30fps decoupled from the orchestration loop.

> **Product Scope** (MVP / Growth / Vision) is defined in detail in the
> [Project Scoping & Phased Development](#project-scoping--phased-development)
> section below.

## User Journeys

### Journey 1 — The Hand-off (primary, happy path = the GOAL)
Alex finishes scoping a feature but doesn't want to babysit the work. They point
well-corp-sw at the project, type the goal, and hit run in headless mode. They
close the laptop. The parent agent spins up teams, subagents pull context from
the harness vault, decisions resolve by policy, work proceeds unattended.
Later, Alex opens the replay. The spatial scene plays back: an agent walks to
the library (vault), pauses at a desk to think, hands a task down a path to a
subagent. In under two minutes Alex understands exactly what happened and why —
no raw logs. New reality: hand off, walk away, trust, verify by watching.

### Journey 2 — Watching Live (accompanied mode, opt-in)
Curious about a tricky task, Alex runs in accompanied mode and keeps the window
open. Creatures move in real time as work flows. A decision the policy can't
resolve surfaces as an on-screen note with clear options and a visible default.
Alex picks one; the world resumes. Emotional arc: from "is it stuck?" anxiety to
"I can see exactly where it is" calm.

### Journey 3 — Something Went Wrong (edge / recovery)
A subagent fails, a vault path is missing, or a decision blocks with no policy.
The scene clearly marks the stuck point (not buried in logs). Alex opens the
replay up to the failure, sees the last good state and the cause, fixes the
vault or answers the decision, and re-runs from a sane point. Failure is
legible, not archaeology.

### Journey 4 — Setup (configuration)
Before first real run, Alex connects a project directory, points the
VaultProvider at a harness-standard vault, and sets basic autonomy policy
(what auto-resolves vs what asks). Minimal, one-time, gets out of the way.

### Journey Requirements Summary
- **Orchestration core:** parent→team→subagent spawning, headless execution.
- **Event log:** every spawn/delegate/vault-read/decision captured, replayable.
- **Replay engine:** deterministic reconstruction, spatial scene rendering,
  scrub to any point, jump to failure.
- **Live render (opt-in):** real-time scene from the same event stream.
- **Decision handling:** policy auto-resolve + on-screen note with options/default.
- **VaultProvider:** load harness-standard vault, expose context to agents.
- **Setup/config:** project binding, vault path, autonomy policy.
- **Failure surfacing:** mark stuck points, resume from a sane state.

## Domain-Specific Requirements

### Autonomous-Agent Safety
- Agents act on a real project (filesystem, possibly shell). Headless autonomy
  needs guardrails: allowed/denied operations, a blast-radius limit, and the
  ability to require a decision note before irreversible or outward-facing
  actions. Mirror the "confirm before hard-to-reverse" principle.

### Cost & Resource Control
- Multi-agent fan-out multiplies Claude API token spend. The system must track
  token/cost per run and per agent, and support a budget ceiling that throttles
  or halts fan-out when hit. Cost is visible in replay.

### Determinism & Auditability
- Replay must be deterministic from the event log even though agent outputs are
  not. The log captures inputs, decisions, and outcomes so a run is faithfully
  reconstructable regardless of model nondeterminism.

### Sandboxing / Isolation
- Parallel subagents mutating the same project can conflict. Support isolation
  (e.g. per-agent worktree) when agents write concurrently; serialize otherwise.

### Vault Integrity (harness standard)
- Vaults are the agents' knowledge source. The VaultProvider validates that a
  vault conforms to the harness standard before a run; a malformed vault fails
  fast rather than feeding agents bad context.

## Innovation & Novel Patterns

### Detected Innovation Areas
- **Spatial replay as comprehension UI.** Existing orchestrators show logs,
  trees, or dashboards. Rendering agent work as a legible spatial scene
  (library/desk/path) for *understanding* — not decoration — is the novel core.
- **Autonomy-first, observability opt-in.** Most agent UIs assume you watch.
  Here the headless core is primary and the living scene is a lens you open when
  you want trust/audit. Inverts the usual coupling.
- **Emotional legibility as a feature.** Borrows the affective pull of
  terminal-pet aesthetics (Claude Buddy) but bends it toward auditability rather
  than novelty — creatures convey real state, not cuteness.
- **Harness-standard vaults as reusable agent memory.** Knowledge libraries in a
  standard format, reused across runs/projects via a VaultProvider.

### Market Context & Competitive Landscape
- **Ralph TUI** — real-time agent→subagent hierarchy in a TUI (closest on
  orchestration; no spatial/replay metaphor).
- **agent-harbor / TUICommander / Hermes (Ink)** — dashboards for many parallel
  agents (functional, cold, no narrative legibility).
- **OrchVis** (research) — hierarchical orchestration with human oversight
  (theory base for parent-distributes-and-verifies).
- **Claude Buddy** (Anthropic) — terminal-pet charm; decorative, not a worker.
- **Gap:** none combine reliable autonomy + legible spatial replay + harness
  vaults. That intersection is the defensible novelty.

### Validation Approach
- Build the MVP replay first and test the core claim: can the developer
  reconstruct a full run in under ~2 minutes from the scene alone, with no logs?
  If yes, the concept holds. If the scene isn't clearer than logs, the premise
  fails fast.

### Risk Mitigation
- **Risk: animation becomes theater, not comprehension.** Fallback: replay must
  always degrade to a plain event timeline; the scene is an enhancement over a
  working textual replay, never a replacement.
- **Risk: spatial metaphor doesn't scale to many agents.** Fallback: zoom /
  group-by-team / focus-follow; validate legibility at N=10+ early.

## CLI Tool Specific Requirements

### Project-Type Overview
well-corp-sw is a terminal-first tool that operates in two modes from a single
binary/CLI: **scriptable/headless** (autonomous runs, CI-friendly, no TTY) and
**interactive TUI** (accompanied mode with the live animated scene). Both drive
the same orchestration core; the TUI is a renderer over the event stream.

### Command Structure
- `wcs run <goal> --project <path> [--headless|--watch] [--policy <file>]`
  — start an orchestration run.
- `wcs replay <run-id> [--scene|--timeline]` — replay a past run as spatial
  scene or plain text timeline.
- `wcs runs` — list past runs (id, goal, status, cost, duration).
- `wcs vault <validate|info> <path>` — inspect/validate a harness vault.
- `wcs config` — view/set project binding, vault path, autonomy policy.
- `wcs resume <run-id>` — resume a paused/blocked run.

### Output Formats
- **Live TUI scene** (watch mode) — animated spatial render, ~30fps, decoupled.
- **Replay scene** — same spatial render driven from the event log.
- **Plain timeline** — textual fallback replay (always available, scriptable).
- **Event log** — append-only JSONL, the source of truth for replay.
- **Run summary** — status, decisions made, token cost, duration; machine and
  human readable.

### Config Schema
- File-based config (per-project), e.g. `wcs.config.*` at project root:
  project path binding, VaultProvider path(s), autonomy policy (auto-resolve vs
  ask rules), cost ceiling, isolation mode. CLI flags override file values.

### Scripting Support
- Headless mode is fully non-interactive: deterministic exit codes, JSONL event
  stream to stdout/file, no prompts (unresolved decisions fail or defer per
  policy). Composable in scripts/CI.

### Implementation Considerations
- Single core, two front-ends (headless emitter + TUI renderer) over one event
  bus. No TTY assumptions in core. Shell completion deferred to Growth.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy
**MVP Approach:** Problem-solving MVP — prove the GOAL's core claim (legible
replay beats logs) on the shortest path. Single developer, incremental build,
no commercial pressure. Fastest path to validated learning: "can I reconstruct
a full run in <2 min from the scene, no logs?"
**Resource Requirements:** Solo developer; one stack decision up front (core
language + TUI framework + Claude Agent SDK).

### MVP Feature Set (Phase 1)
**Core User Journeys Supported:** Journey 1 (Hand-off / happy path),
Journey 4 (Setup), partial Journey 3 (failure is at least surfaced in timeline).

**Must-Have Capabilities:**
- Headless parent→subagent orchestration via Claude Agent SDK.
- Append-only JSONL event log (spawn, delegate, vault-read, decision, result).
- Legible replay over the log: plain timeline first, then a simple spatial scene.
- Minimal decision handling: core blocks, simple prompt, resolve by input or policy.
- VaultProvider reading one harness-standard vault (with validation).
- Basic CLI: `run --headless`, `replay`, `runs`, `vault validate`, `config`.
- Cost/token tracking per run with a budget ceiling.
- Safety guardrails: allowed/denied ops, require decision before irreversible acts.

### Post-MVP Features
**Phase 2 (Growth):**
- Rich live animated scene (watch mode): creatures walking, library/desk/path.
- On-screen decision notes as first-class UI with options/default.
- Named teams; multiple concurrent teams.
- Policy engine for autonomous decision resolution.
- Per-agent isolation (worktree) for concurrent writes; resume from sane state.
- Shell completion.

**Phase 3 (Vision / Expansion):**
- Full "company of little creatures": agent personalities, expressive world.
- Multi-team spatial choreography; zoom/group/focus for scale (N=10+).
- Run comparison/diffing.

### Risk Mitigation Strategy
**Technical Risks:** Hardest part = decoupled render that never blocks core, and
deterministic replay over nondeterministic agents. Mitigation: event log is the
single source of truth; both live and replay render from it; timeline fallback
always works. Validate the <2-min-comprehension claim before investing in rich
animation.
**Market Risks:** N/A commercially (personal tool). Real "market" risk = the
spatial metaphor not being clearer than logs. Mitigation: kill-criterion — if
MVP scene isn't clearer than the timeline, stop and rethink before Growth.
**Resource Risks:** Solo dev, limited time. Mitigation: each phase ships
independently usable; MVP is valuable even if Growth never happens.

## Functional Requirements

### Orchestration
- FR1: A developer can start an orchestration run by giving a goal and a target
  project. [MVP]
- FR2: A parent agent can decompose a goal into tasks and delegate them to
  subagents. [MVP]
- FR3: A parent agent can spawn subagents on demand and reuse already-spawned
  agents for related tasks. [MVP]
- FR4: The system can run a full orchestration unattended (headless), with no
  human present. [MVP]
- FR5: The parent agent can verify subagent results against vault context before
  accepting them. [MVP]
- FR6: A developer can organize agents into named teams. [Growth]
- FR7: The system can run multiple teams concurrently. [Growth]

### Knowledge Vaults
- FR8: The system can load a knowledge vault that follows the harness standard
  via a VaultProvider. [MVP]
- FR9: The system can validate that a vault conforms to the harness standard and
  fail fast on a malformed vault. [MVP]
- FR10: Agents can read context from a loaded vault during a run. [MVP]
- FR11: A developer can inspect a vault's contents and metadata. [MVP]
- FR12: The system can reuse the same vault across multiple runs and projects.
  [MVP]

### Event Capture & Replay
- FR13: The system can record every orchestration event (spawn, delegate,
  vault-read, decision, result, failure) to an append-only log. [MVP]
- FR14: A developer can replay a past run as a plain textual timeline. [MVP]
- FR15: A developer can replay a past run as a spatial scene (library = vault,
  desk = thinking, path = delegation). [MVP]
- FR16: A developer can scrub a replay to any point in the run. [MVP]
- FR17: A developer can jump a replay directly to the point of a failure. [MVP]
- FR18: The system can reconstruct a run deterministically from its event log
  regardless of model nondeterminism. [MVP]

### Live Observability
- FR19: A developer can watch a run live as an animated spatial scene. [Growth]
- FR20: The live scene reflects real orchestration state and never blocks or
  slows the orchestration core. [Growth]
- FR21: A developer can zoom, group by team, or focus-follow an agent to keep
  the scene legible at scale. [Vision]

### Decisions & Human-in-the-Loop
- FR22: The system can pause a run at a decision point that requires human input.
  [MVP]
- FR23: A developer can resolve a pending decision by selecting from presented
  options with a visible default. [MVP]
- FR24: The system can auto-resolve a decision by policy without human input.
  [MVP]
- FR25: A developer can define autonomy policy specifying which decisions
  auto-resolve and which require asking. [Growth]
- FR26: Pending decisions can surface as first-class on-screen notes in the live
  scene. [Growth]

### Run Management
- FR27: A developer can list past runs with id, goal, status, cost, and
  duration. [MVP]
- FR28: A developer can resume a paused or blocked run. [MVP]
- FR29: A developer can re-run from a sane prior state after a failure. [Growth]
- FR30: A developer can compare or diff two runs. [Vision]

### Cost & Safety Controls
- FR31: The system can track token and cost usage per run and per agent. [MVP]
- FR32: A developer can set a cost ceiling that throttles or halts fan-out when
  reached. [MVP]
- FR33: The system can enforce allowed/denied operation rules on agent actions.
  [MVP]
- FR34: The system can require a human decision before an irreversible or
  outward-facing action. [MVP]
- FR35: The system can isolate concurrently-writing agents (e.g. per-agent
  worktree) to prevent conflicts. [Growth]

### Configuration & Setup
- FR36: A developer can bind a project directory to the tool. [MVP]
- FR37: A developer can configure vault path(s), autonomy policy, cost ceiling,
  and isolation mode via per-project config. [MVP]
- FR38: A developer can override config values with CLI flags. [MVP]
- FR39: The system can emit a machine- and human-readable run summary
  (status, decisions, cost, duration). [MVP]
- FR40: A developer can drive the tool fully non-interactively with deterministic
  exit codes for scripting/CI. [MVP]

## Non-Functional Requirements

### Performance
- NFR1: The live animated scene sustains ~30fps and runs on a separate
  thread/process so it never blocks or slows the orchestration core.
- NFR2: The orchestration core makes zero blocking calls into the render layer;
  rendering is purely a consumer of the event stream.
- NFR3: A developer can reconstruct and understand a full run via replay in
  under ~2 minutes (the core comprehension target).
- NFR4: Event capture adds negligible overhead to orchestration (logging must
  not become a bottleneck on fan-out).

### Reliability & Determinism
- NFR5: Replay is deterministic — the same event log always reproduces the same
  timeline and scene, regardless of model nondeterminism.
- NFR6: The event log is append-only and crash-safe: an interrupted run leaves a
  replayable log up to the last completed event.
- NFR7: A run can always degrade to the plain textual timeline if scene
  rendering is unavailable; the textual replay is never lost.
- NFR8: Headless runs complete or fail with deterministic exit codes; an
  unresolved decision never hangs indefinitely (fails or defers per policy).

### Security & Safety
- NFR9: Claude API credentials are read from the environment/secure config and
  never written to the event log, run summary, or vault.
- NFR10: Agent actions are confined to the bound project and configured vault
  paths; operations outside the allowed scope are denied.
- NFR11: Irreversible or outward-facing actions are blocked pending an explicit
  decision (policy or human), per the safety guardrails.
- NFR12: Cost ceilings are enforced hard — fan-out halts when the ceiling is
  reached rather than overspending.

### Usability (Legibility)
- NFR13: The spatial scene must be measurably clearer than raw logs for
  understanding a run (validated against the <2-min target); if not, it is a
  failed premise, not shipped.
- NFR14: The scene stays legible as agent count grows (validated at N=10+ via
  zoom/group/focus in later phases).

### Portability
- NFR15: The tool runs on Windows, macOS, and Linux terminals from a single
  codebase, with no TTY assumptions in the core (headless works without a TTY).

### Maintainability & Extensibility
- NFR16: The VaultProvider is an interface, allowing alternative
  harness-standard vault sources without changing the core.
- NFR17: Core, headless emitter, and TUI renderer are separable modules
  communicating only through the event bus (no logic in the render layer).
