# AGENTIQ Factory — Web Visual Layer Plan

**Status:** proposed 2026-06-10 (supersedes the TUI-only upgrade as the PRIMARY
visual surface; TUI + plain timeline remain as fallbacks already built)
**User intent:** real animated interface like the reference videos (`AGENTIQ/`):
cute charcoal+gold robots, factory floor, sectors per team, delegation arrows,
speech bubbles, conveyors — and the factory **grows** as the system spawns more
agents/subagents. Gamification of the orchestration. Backend is feature-complete;
this is purely a new projection of the existing event stream.

---

## 1. Why web (recommendation)

| Option | Verdict |
|---|---|
| **Browser app (PixiJS 2D engine) — RECOMMENDED** | Real sprites/tweens/particles at 60fps, cross-platform, zero install (opens in browser), trivially fed by WebSocket from Python. Game-engine feel without game-engine weight. |
| Textual TUI maxed | Colors + cell animation only; can never look like the videos. Stays as the terminal fallback (already works). |
| Godot/desktop engine | Real game engine, but heavy toolchain + packaging per-OS; overkill for a visualization. |
| Electron | Adds Chrome-the-app for nothing the browser doesn't already give. |

Architecture fit is perfect: the core is an event-sourced engine; **the web view
is just another subscriber/projection** — same events, same reducer semantics,
zero changes to orchestration (NFR17 intact). Replay and live use the same scene,
like the TUI does today.

**PRD note:** PRD says terminal-only — this is an explicit user-driven scope
change. PRD/architecture get an addendum (new optional surface; terminal remains
the no-dependency fallback).

## 2. System design

```
┌──────────────── existing core (untouched) ────────────────┐
│ orchestrator → EventBus → JSONL log → reducer/SceneState  │
└──────────────┬────────────────────────┬───────────────────┘
               │ live: bus subscriber    │ replay: read JSONL
        ┌──────▼──────────────────────────▼──────┐
        │  agentiq web  (FastAPI + WebSocket)    │
        │  · /ws/live/<run>   streams events     │
        │  · /ws/replay/<run> streams w/ seeking │
        │  · /api/runs, /api/summary             │
        │  · WebDecisionResolver (FR22 seam):    │
        │    decision.pending → UI modal → ws    │
        │    answer → resolver future            │
        └──────────────────┬─────────────────────┘
                           │ static files
        ┌──────────────────▼─────────────────────┐
        │  Factory front-end (PixiJS + TS, built │
        │  to static bundle, no Node at runtime) │
        │  · JS reducer mirrors event→scene      │
        │  · sprites, tweens, camera, UI         │
        └────────────────────────────────────────┘
```

- **Live:** `agentiq run "<goal>" --web` starts run + server, opens browser; events
  stream as they happen; pending decision pops a modal in the page, answer flows
  back through the existing `Resolver` seam (same as TUI's `TuiDecisionResolver`).
- **Replay:** `agentiq replay <id> --web`; server streams events with transport
  control (play/pause/seek/speed/jump-to-marker) — protocol mirrors `ReplayController`.
- **Determinism kept:** semantic state = events via one reducer (a small JS mirror
  of `replay/reducer.py`, locked by a shared JSON fixture test so Python and JS
  reduce identically). Tweens/particles are presentation-only.
- New deps: `fastapi` + `uvicorn` (server), PixiJS (front, vendored build). No
  database, no auth (localhost tool).

## 3. The Factory (visual + gamification design)

### 3.1 Scene anatomy (matches reference art)
- **MAIN podium** center: mascot robot (charcoal+gold, glowing eyes, antenna) on
  a glowing ring — the orchestrator, never moves.
- **Sectors** (team zones): colored floor plates (INFO green, OPS blue, EXEC
  orange, more hues as needed) with name plate, screens, conveyor edge.
- **Robots:** chibi sprites per agent — idle bob, blink, walk, think (gear
  bubble), read (vault book bubble), work (sparks), fail (red ✕ eyes + alarm
  light), done (✓ eyes, power-down). Subagents = smaller versions.
- **Delegation:** animated glowing arrow podium→sector + the new robot walks out
  of the sector door.
- **Speech bubbles:** active agent shows current action ("lendo vault:
  api-design"); one at a time + event ticker at the bottom (the conveyor carries
  event "crates" across the screen).
- **Vault** = library kiosk near the podium; reading robot walks there.

### 3.2 The factory GROWS (the core gamification loop)
Run starts small: bare floor + MAIN alone.
- **agent.spawned (first of a team)** → new sector plate slides/builds in
  (construction animation: scaffold → plate → name plate lights on).
- **agent.spawned (subagent)** → small robot assembled on the sector's conveyor
  (parts roll in, head drops on, eyes light up) and walks to its spot.
- Floor expands and **camera auto-zooms out** as sectors multiply; layout = ring
  of sectors around the podium (1–6+), then second ring.
- **task.delegated** → arrow pulse + crate travels the conveyor to the sector.
- **agent.usage / cost** → power gauge fills; near ceiling = factory lights dim
  amber (warning); `budget.exceeded` = breakers trip animation, fan-out halts visibly.
- **decision.pending** → factory pauses (belts stop, robots freeze mid-pose),
  spotlight on MAIN, modal with options + default. Resolve → everything whirs back.
- **failure** → sector alarm beacon (red rotating light) + robot slumps; persists
  as marker on the transport bar.
- **run.completed** → confetti restrained: lights sweep green, summary board
  (duration · cost · decisions · agents built).

### 3.3 HUD / usability (keyboard-first survives)
- Top bar: `[▣▣] AGENTIQ` · run id · mode · cost gauge · elapsed.
- Bottom: transport bar (scrub, ◆/✕ markers, speed, seq/total) — replay AND live
  (live = position pinned to end).
- Same keys as TUI: space, ←/→, n/p, f, g, enter(inspect), q. Mouse optional.
- Click/enter a robot → inspect side panel (event detail, tokens, vault refs,
  decision rationale).
- Reduced-motion toggle; everything also lives in ticker text (no info hidden in
  animation — UX-DR2 survives the upgrade).

### 3.4 Art pipeline
- Robots/props drawn as **vector (SVG→texture) chibi parts** matching the Grok
  mascot (rounded charcoal body, gold trim, glowing capsule eyes, antenna) —
  authored in code/SVG, no licensed assets needed; reference images stay as the
  art bible (`AGENTIQ/`).
- Palette tokens shared with TUI theme (charcoal #1d1f21-family, gold #d4a017-family,
  team hues) — one brand, two surfaces.

## 4. Phases

**Phase W0 — Pipe (~1 session):** `agentiq web`/`--web` flags · FastAPI app ·
`/ws/replay` streaming events from JSONL with play/pause/seek protocol ·
static page proving events arrive (raw list). Foundation, no art.

**Phase W1 — Floor v1 (~2 sessions):** PixiJS scene: floor, podium, MAIN sprite,
sector plates from teams, robot sprites with idle/walk/fail/done states, JS
reducer mirror + fixture parity test vs Python reducer.

**Phase W2 — Growth & life (~2 sessions):** sector build-in animation · robot
assembly on spawn · camera auto-zoom rings · delegation arrows + crates ·
speech bubbles + ticker conveyor · cost gauge.

**Phase W3 — Replay transport + live (~1–2 sessions):** transport bar UI wired to
seek protocol · markers/jumps · speed · live mode via bus subscriber ·
WebDecisionResolver modal (pause/resume world).

**Phase W4 — Inspect & polish (~1 session):** inspect panel · failure alarms ·
budget breakers · end-of-run summary board · reduced-motion · keyboard map.

**Parallel/optional:** Phase 0 rebrand (wcs→agentiq) still applies and should land
first; TUI visual plan (v3) drops to "nice fallback polish", do later or never.

## 5. Risks

- **JS reducer drift** vs Python → locked by shared JSON fixtures (same events →
  same scene snapshot) in CI.
- **Scope creep on art** → gamification elements must map to real events (the
  UX-DR2 gate); no decorative mechanics.
- **Front toolchain** (Node for build) → dev-only; runtime ships prebuilt static
  bundle, user never needs Node.
- **Two surfaces to maintain** → TUI frozen as-is (works today); web is the only
  surface under active visual development.
