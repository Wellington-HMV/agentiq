# TUI Visual Upgrade Plan v3 — "AGENTIQ"

**Status:** approved direction (user decisions 2026-06-10) — ready to implement
**Decisions:**
1. **Full rebrand**: product = **AGENTIQ** ("ferramenta de agentes"); CLI `wcs` → `agentiq`.
2. **Scene layout = office floor-plan from the UX spec** (LIBRARY / DESKS / SUBAGENTS);
   AGENTIQ enters as identity: mascot sprites, charcoal+gold palette, bubbles, ticker.
**Inputs:** `ux-design-specification.md`, current `src/well_corp_sw/tui/*`,
reference art `AGENTIQ/*.jpg|mp4` (mascot, logo, factory scenes, animation cues).
**Invariants:** pure reducer single source of state; widgets dumb (NFR17); same
visual language live/replay (NFR5); charm bounded by legibility (UX-DR2); ASCII /
no-color / `--no-anim` / plain-timeline degradation always available.

---

## 1. AGENTIQ identity decoded (from the reference art)

| Element in art | TUI translation |
|---|---|
| Mascot: charcoal robot, gold trim, glowing rounded eyes, antenna, smile | 2-line box-drawing sprite `⌐▣▣` + id; eyes are THE status channel (color+glyph) |
| Gold-on-charcoal logo `AGENTIQ` | Header brand `[▣▣] AGENTIQ` gold on charcoal; replaces default Textual Header |
| MAIN robot on glowing podium | Parent agent anchored, distinct framed box, gold ring — fixed mnemonic anchor |
| Speech bubbles with charts/text above robots | One caption bubble at the ACTIVE agent (`╭─ reads vault ─╮`) |
| Thinking bubble with gears | `⚙⚙` eye-state + bubble pulse while thinking |
| Glowing arrows between robots/zones | Delegation arrows with marching-dash animation `─ ─ ▶` |
| Conveyor belts carrying gears | **Esteira ticker**: scrolling strip of recent events |
| Team colors green/blue/orange | `$role-*` palette for roles/teams (badges + sprite tint) |

Color rules kept from spec: gold `accent` = brand + MAIN + **pending decisions
only**; red = failures only; nominal stays quiet/dim.

---

## 2. Target Visualization

### 2.1 Replay/watch screen — full tier (≥120×40), office layout + AGENTIQ skin

```
┌ [▣▣] AGENTIQ · run 01JX4… ─────────────────────── replay · $0.42 · 03:12 · 42/118 ┐
│                                                                                     │
│   ┌─ LIBRARY ──────────┐          ┌─ DESKS ───────────────────┐                     │
│   │  ▤▤▤ ▤▤▤           │          │        ╭─ ⚙ thinking ─╮   │                     │
│   │   ⌐◉◉  ╭─ reads ──╮│          │  ⌐⚙⚙   ╰──────────────╯   │                     │
│   │    a3  │ api-design││          │   a1                      │                     │
│   │        ╰───────────╯│          │  ╶┬─╴  ╶┬─╴  ╶┬─╴         │                     │
│   └────────────────────┘          └───────────────────────────┘                     │
│            ·· ⌐▣▣ a2 walking ··▶                                                    │
│                                          ┌─ SUBAGENTS ──────────┐                   │
│   ╔══════════════╗                       │  ▪a4  ▪a5            │                   │
│   ║  ⌐▣▣  MAIN   ║ ═ ═ ▶ ─ ─ ─ ─ ─ ─ ─ ▶ │  ✕a6 (failed)        │                   │
│   ╚═◉══════════◉═╝                       └──────────────────────┘                   │
│                                                                                     │
│  ░▒▓  esteira ▸ vault.read ▸ task.delegated ▸ agent.usage ▸ decision.pending  ▓▒░  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  ──────◆────────◆━━▶━━━━✕──────────────────────────────────  42/118  1.0×           │
└─ space play · ←→ step · n/p ◆ · f ✕ · g seq · enter inspect · q quit ───────────────┘
```

- Fixed map (UX-DR1): LIBRARY top-left, DESKS top-right, MAIN podium bottom-left,
  SUBAGENTS bottom-right. Rooms = framed boxes with titles.
- Active agent (current event's) bright + bubble; others dim. One bubble at a time.
- Walking: sprite tweens along dotted path between rooms; delegation = animated
  dashed arrow MAIN→SUBAGENTS while `task.delegated` is current; persists as `═▶`.
- Esteira ticker: last N events scroll; pauses with playback (deterministic).
- Teams (when present): colored role badge on the sprite id (`a4₍ops₎` tinted) +
  `v` view = team grouping (existing 6.1), now color-coded.

### 2.2 Sprite language (charcoal + glowing eyes)

MAIN (parent, 2 lines + podium frame):
```
 ⌐▣▣      ⌐■■      ⌐✕✕      ⌐✓✓
 MAIN     MAIN     MAIN     MAIN
 idle/blink working failed   done
```

Agent (2 lines full tier / 1 line compact):
```
 ⌐▣▣    ⌐_▣    ⌐◉◉     ⌐⚙⚙     ➤▣▣      ⌐✕✕    ⌐✓✓    ⌐··
  a1     a1     a3      a1      a2       a6     a5     a7
 active blink  reading thinking walking  failed done   idle(dim)
```

Worker/dense: `▪a4` (dim) `▫a4` (active) `✕a6` (failed).

Rules (UX-DR2): eye glyph always shows true status; frames only blink/pulse/march;
`(state, frame)` deterministic; reduced-motion pins frame 0.
ASCII twins: `[oo] [..] [**] [xx] [vv] >oo`.

### 2.3 DecisionNote

```
        ┌─◆ DECISION · MAIN ──────────────────────────┐
        │  ⌐▣▣  Which database driver for the API?     │
        │                                              │
        │   ▶ 1. asyncpg          (default)            │
        │     2. psycopg3                              │
        │     3. defer to vault preference             │
        │                                              │
        │  Enter = default · 1-3 = pick · Esc = defer  │
        └──────────────────────────────────────────────┘
```
Gold border (the only glow), scene dimmed behind, world paused (already works).

### 2.4 Compact tier (80×24)

```
┌ [▣▣] AGENTIQ · 01JX4… · $0.42 · 42/118 ┐
│ LIB   ⌐◉◉ a3  « reads api-design »      │
│ DESK  ⌐⚙⚙ a1                            │
│ SUB   ▪a4 ▪a5 ✕a6                       │
│ MAIN  ⌐▣▣ ══▶ SUB                       │
│ ▸ vault.read ▸ task.delegated ▸ …       │
│ ───◆───◆━▶━━✕─────────  42/118          │
└ space ←→ n p f g i q ───────────────────┘
```
Below 80×24 → existing tree/timeline (recolored only).

---

## 3. Technical Design

### 3.1 Scene composition (replaces single-Static blob in full tier)
```
SceneWidget (container)
├── ZoneBox × 3          — LIBRARY / DESKS / SUBAGENTS, framed, fixed anchors
├── PodiumBox            — MAIN sprite, gold frame, fixed anchor
├── PathLayer            — dotted walk paths + delegation arrows (marching frames)
├── BubbleLayer          — speech bubble at active agent
├── ConveyorTicker       — scrolling recent-events strip
└── CaptionLine          — a11y textual twin of bubble/playhead
```
- Anchors: pure `layout(SceneState, size) -> dict[agent_id,(x,y)]` (deterministic,
  snapshot-testable; single place for breakpoints).
- Walking: `creature.styles.animate("offset", anchor, duration=token)`; reduced-motion snaps.
- Existing flat `render_scene` = compact/ASCII/minimal tier (kept, recolored).
- Crowding: zone shows ≤6 sprites, then `▪×12` badge (CROWD_THRESHOLD per-zone).

### 3.2 Theme tokens (TCSS + tokens.py)
- Brand: `$bg` charcoal (#1d1f21-family), `$surface` lighter, `$gold` (#d4a017-family)
  for brand/MAIN/pending, `$text`/`$text-dim`.
- Status: `$error` red (failures only), `$success`, `$warning`.
- Roles/teams: green/blue/orange + 3 reserves (colorblind-checked), stable
  hash-assignment by team name.
- Motion: blink 1.2s · think-pulse 600ms · arrow-march 250ms · walk 400ms ·
  ticker 1 cell/250ms — capped, render never starves core.

### 3.3 Transport bar v2 + keys
- Proportional fixed-width track; collision priority `▶ > ✕ > ◆`.
- Speed `<`/`>` (0.25–4×) wired to controller's existing speed; tick = base/speed.
- `g` = go-to-seq (spec); team view moves to `v`. End-of-run summary panel
  (outcome · decisions · cost · duration) from `summary.py`.

### 3.4 Rebrand scope (decision 1 — full)
- `pyproject.toml`: project name `agentiq`, console script `agentiq` (+ keep `wcs`
  alias one release for muscle memory).
- Package rename `well_corp_sw` → `agentiq` (imports, tests, import-linter contracts, CI).
- Config: `agentiq.config.toml` (reader falls back to `wcs.config.toml` with deprecation note).
- Run store: `~/.agentiq/runs/` (reader also lists legacy `~/.well-corp-sw/runs/`).
- Docs/README/BMad artifacts header + TUI titles + completion scripts.
- Repo/dir name stays `well-corp-sw` until user renames it (outside code scope).

### 3.5 Visual iteration harness
1. `agentiq replay --demo` — synthetic scripted run (vault reads, thinking,
   delegation, decision, failure) for free visual iteration.
2. `App.save_screenshot()` → SVGs of each key state for approval.
3. `pytest-textual-snapshot` locks approved looks (full/compact/ASCII/no-anim).

---

## 4. Implementation Phases

**Phase 0 — Rebrand (~1 session):** package/CLI/config/store rename + alias +
fallbacks; all 230 tests green under new name. Done first so new code lands renamed.

**Phase A — Brand & theme shell (~1 session):** charcoal+gold TCSS · AGENTIQ
header + status strip · DecisionNote restyle · key fixes (`g`/`v`, `<`/`>`) · `--demo`.

**Phase B — Spatial scene (~2 sessions, the heart):** ZoneBox/PodiumBox + anchor
`layout()` · per-agent sprite widgets · walking tween · PathLayer arrows ·
active-bright/dim.

**Phase C — Life & feedback (~1 session):** speech bubbles · blink/think-pulse/
arrow-march frames · ConveyorTicker · failure flash.

**Phase D — Transport v2 (~1 session):** proportional track · speed · go-to-seq ·
end-of-run summary.

**Phase E — Degradation & lock-in (~1 session):** compact/minimal restyle · ASCII
sprites · `--no-anim` parity · SVG + snapshot suite · Windows Terminal glyph audit
(`⌐ ▣ ⚙ ◉ ╔ ◆` widths) · cross-OS CI.

Each phase ends: demo run → SVG screenshots → approve → snapshot tests lock.

---

## 5. Risks

- **Windows glyph widths** (`⌐ ▣ ⚙`): audit on Windows Terminal first; ASCII twin
  for every sprite; wide emoji never in layout-critical cells.
- **Rebrand churn:** mechanical but wide (imports/tests/CI); Phase 0 isolated +
  gates green before visual work starts.
- **Determinism:** ticker/arrows/blink are pure `f(state, frame)`; snapshot tests
  assert settled frames, not mid-tween.
- **Bubble noise:** one bubble (active agent) at a time; content duplicated in
  caption + ticker (a11y, no hidden-in-animation state).
