// Presentation model: turns reducer SceneStates into a living factory.
// Semantic truth comes ONLY from the reducer; everything here (tweens, walk
// cycles, build-ins, glow) is presentation between two reducer states.

import {
  drawAccessory,
  drawBeacon,
  drawBelt,
  drawBubble,
  drawCrate,
  drawDust,
  drawFloorTile,
  drawLink,
  drawPlate,
  drawPodium,
  drawRobot,
  PALETTE,
} from "/static/art.js";

// Fixed map (the spatial mnemonic): podium center, plates around it.
// Plates exist for the zones the reducer actually assigns (library/desk/floor);
// "path" (delegating) keeps the robot at its desk while its link glows.
export const PLATES = {
  library: { wx: -4.2, wy: -0.6, halfW: 105, halfH: 52, label: "LIBRARY" },
  desk: { wx: 0.6, wy: -4.0, halfW: 130, halfH: 65, label: "DESKS" },
  floor: { wx: 3.8, wy: 1.4, halfW: 100, halfH: 50, label: "FLOOR" },
};

// Slot offsets (world units) inside a plate, row-major.
const SLOTS = [
  [0, 0],
  [-1.1, 0.5], [1.1, -0.5],
  [-0.55, -0.9], [0.55, 0.9],
  [-1.6, -0.4], [1.6, 0.4],
  [0, -1.4], [0, 1.4],
  [-2.0, 0.8], [2.0, -0.8], [-1.0, 1.6],
];

const WALK_SPEED = 2.3; // world units / second — slow enough to be WATCHED
const ARROW_TTL = 2.6; // seconds a demand arrow stays on screen
const CRATE_SECONDS = 2.2; // travel time of a task crate along its belt

// Conveyor route from the podium edge to a plate's edge (world coords).
function beltRoute(zone) {
  const p = PLATES[zone];
  const len = Math.hypot(p.wx, p.wy);
  const ux = p.wx / len;
  const uy = p.wy / len;
  return {
    from: [ux * 1.7, uy * 1.7], // just outside the podium ring
    to: [p.wx - ux * 1.5, p.wy - uy * 1.5], // just before the plate
  };
}

export class FactoryScene {
  constructor() {
    this.robots = new Map(); // agent_id -> visual
    this.plateGrow = new Map(); // zone -> 0..1 construction progress
    this.arrows = []; // transient demand arrows: {from,to,ttl}
    this.crates = []; // task crates in transit: {zone, progress}
    this.dust = []; // walking dust puffs: {wx,wy,ttl}
    this.activeId = null;
    this.runStatus = "pending";
    this.decision = null; // payload of a current decision.pending
    this.failedFlash = 0;
  }

  // Apply a reducer state. zonesVisible = zones ever occupied up to this seq
  // (the factory grows; it only shrinks when scrubbing backwards).
  setState(state, event, zonesVisible, { snap = false } = {}) {
    this.runStatus = state.run_status;
    this.activeId = event?.agent_id ?? null;
    this.decision = event?.type === "decision.pending" ? event.payload : null;
    if (event?.type === "agent.failed") this.failedFlash = 1;

    // plates: start/maintain construction for every visible zone
    for (const zone of Object.keys(PLATES)) {
      if (zonesVisible.has(zone) && !this.plateGrow.has(zone)) {
        this.plateGrow.set(zone, snap ? 1 : 0);
      }
      if (!zonesVisible.has(zone)) this.plateGrow.delete(zone);
    }

    // robots: position targets from zone slots
    const byZone = {};
    const agents = Object.values(state.agents).sort((a, b) =>
      a.agent_id < b.agent_id ? -1 : 1,
    );
    for (const agent of agents) {
      const zone = this._plateZone(agent);
      (byZone[zone] ??= []).push(agent);
    }
    const present = new Set();
    for (const [zone, members] of Object.entries(byZone)) {
      members.forEach((agent, i) => {
        present.add(agent.agent_id);
        const main = agent.parent_id == null;
        const [tx, ty] = this._slotPos(zone, i, main);
        let robot = this.robots.get(agent.agent_id);
        if (!robot) {
          robot = {
            label: agent.agent_id,
            wx: tx,
            wy: ty,
            phase: hashPhase(agent.agent_id),
            spawn: snap ? 1 : 0,
            main,
          };
          this.robots.set(agent.agent_id, robot);
        }
        robot.tx = tx;
        robot.ty = ty;
        robot.status = agent.status;
        robot.active = agent.agent_id === this.activeId;
        robot.main = main;
        if (snap) {
          robot.wx = tx;
          robot.wy = ty;
          robot.spawn = 1;
        }
      });
    }
    for (const id of this.robots.keys()) {
      if (!present.has(id)) this.robots.delete(id);
    }

    // A demand arrow fires ONLY at the moment of delegation (MAIN -> sector
    // leader, leader -> subordinate) and fades out; no persistent web of lines.
    if (event?.type === "task.delegated") {
      this.arrows.push({
        from: event.agent_id ?? "",
        to: event.payload?.to_agent ?? "",
        ttl: ARROW_TTL,
      });
      // ...and the task itself ships as a crate down the target's conveyor.
      const target = state.agents[event.payload?.to_agent ?? ""];
      if (target) {
        const zone = this._plateZone(target);
        if (zone in PLATES) this.crates.push({ zone, progress: 0 });
      }
    }
    if (snap) {
      this.arrows = [];
      this.crates = [];
    }

    // alarm beacons: any sector currently holding a failed robot (pure state)
    this.alarms = new Set();
    for (const agent of Object.values(state.agents)) {
      if (agent.status !== "failed" || agent.parent_id == null) continue;
      const zone = this._plateZone(agent);
      if (zone in PLATES) this.alarms.add(zone);
    }
  }

  _plateZone(agent) {
    if (agent.parent_id == null) return "podium"; // MAIN lives on the podium
    if (agent.zone === "path") return "desk"; // delegating: stays put, link glows
    return agent.zone in PLATES ? agent.zone : "floor";
  }

  _slotPos(zone, index, main) {
    if (zone === "podium" || main) return [0, 0];
    const plate = PLATES[zone];
    const [dx, dy] = SLOTS[index % SLOTS.length];
    const spread = 1 + Math.floor(index / SLOTS.length) * 0.35;
    return [plate.wx + dx * spread, plate.wy + dy * spread];
  }

  update(dt) {
    for (const grow of this.plateGrow.keys()) {
      this.plateGrow.set(grow, Math.min(1, this.plateGrow.get(grow) + dt * 1.6));
    }
    for (const robot of this.robots.values()) {
      robot.spawn = Math.min(1, (robot.spawn ?? 1) + dt * 1.4);
      const dx = robot.tx - robot.wx;
      const dy = robot.ty - robot.wy;
      const dist = Math.hypot(dx, dy);
      if (dist > 0.02) {
        const step = Math.min(dist, WALK_SPEED * dt);
        robot.wx += (dx / dist) * step;
        robot.wy += (dy / dist) * step;
        robot.walking = true;
        // lean into the screen-space direction of travel
        robot.lean = Math.sign(dx - dy) * Math.min(1, dist);
        // kick up dust puffs while on the move
        robot.dustTimer = (robot.dustTimer ?? 0) - dt;
        if (robot.dustTimer <= 0) {
          robot.dustTimer = 0.16;
          this.dust.push({ wx: robot.wx, wy: robot.wy, ttl: 0.5 });
        }
      } else {
        robot.walking = false;
        robot.lean = 0;
      }
    }
    for (const puff of this.dust) puff.ttl -= dt;
    this.dust = this.dust.filter((p) => p.ttl > 0);
    this.failedFlash = Math.max(0, this.failedFlash - dt * 1.2);
    for (const arrow of this.arrows) arrow.ttl -= dt;
    this.arrows = this.arrows.filter((a) => a.ttl > 0);
    for (const crate of this.crates) crate.progress += dt / CRATE_SECONDS;
    this.crates = this.crates.filter((c) => c.progress < 1);
  }

  // Points the camera should keep in frame.
  framePoints() {
    const pts = [[0, 0], [1.6, 1.6], [-1.6, -1.6]]; // podium neighborhood
    for (const [zone, grow] of this.plateGrow) {
      if (grow <= 0) continue;
      const p = PLATES[zone];
      const hw = p.halfW / 32; // halfW px ≈ tiles via TILE_W/2
      const hh = p.halfH / 16;
      pts.push([p.wx - hw / 2, p.wy - hh / 2], [p.wx + hw / 2, p.wy + hh / 2]);
    }
    return pts;
  }

  draw(ctx, cam, t, caption) {
    const s = cam.scale;

    // ground tiles (a soft checker patch under everything)
    for (let wx = -8; wx <= 8; wx++) {
      for (let wy = -8; wy <= 8; wy++) {
        const [sx, sy] = cam.toScreen(wx, wy);
        drawFloorTile(ctx, sx, sy, s, (wx + wy) % 2 === 0);
      }
    }

    // conveyor belts (under the plates), one per built sector — always running
    for (const [zone, grow] of this.plateGrow) {
      const route = beltRoute(zone);
      const [bx0, by0] = cam.toScreen(...route.from);
      const [bx1, by1] = cam.toScreen(...route.to);
      drawBelt(ctx, bx0, by0, bx1, by1, s, t, grow);
    }

    // plates
    for (const [zone, grow] of this.plateGrow) {
      const p = PLATES[zone];
      const [sx, sy] = cam.toScreen(p.wx, p.wy);
      drawPlate(ctx, sx, sy, s, p.halfW / 1, p.halfH / 1, PALETTE.zone[zone], p.label, grow, t);
    }

    // podium
    const [px, py] = cam.toScreen(0, 0);
    drawPodium(ctx, px, py, s, t, this.decision != null);

    // alarm beacons on failed sectors (planted at the plate's top corner)
    for (const zone of this.alarms ?? []) {
      if (!this.plateGrow.has(zone)) continue;
      const p = PLATES[zone];
      const [ax, ay] = cam.toScreen(p.wx, p.wy);
      drawBeacon(ctx, ax, ay - (p.halfH + 6) * s, s, t);
    }

    // transient demand arrows (under robots), fading with their ttl
    for (const arrow of this.arrows) {
      const a = this.robots.get(arrow.from);
      const b = this.robots.get(arrow.to);
      if (!a || !b) continue;
      const [x0, y0] = cam.toScreen(a.wx, a.wy);
      const [x1, y1] = cam.toScreen(b.wx, b.wy);
      drawLink(ctx, x0, y0 - 8 * s, x1, y1 - 8 * s, s, t, Math.min(1, arrow.ttl / 1.2));
    }

    // walking dust puffs (under everything that moves)
    for (const puff of this.dust) {
      const [dx, dy] = cam.toScreen(puff.wx, puff.wy);
      drawDust(ctx, dx, dy, s, puff.ttl / 0.5);
    }

    // task crates riding their belts
    for (const crate of this.crates) {
      if (!this.plateGrow.has(crate.zone)) continue;
      const route = beltRoute(crate.zone);
      const k = easeInOutQuad(crate.progress);
      const wx = route.from[0] + (route.to[0] - route.from[0]) * k;
      const wy = route.from[1] + (route.to[1] - route.from[1]) * k;
      const [cx, cy] = cam.toScreen(wx, wy);
      drawCrate(ctx, cx, cy, s, t);
    }

    // robots, painter's order (back to front)
    const robots = [...this.robots.values()].sort(
      (a, b) => a.wx + a.wy - (b.wx + b.wy),
    );
    for (const robot of robots) {
      const [sx, sy] = cam.toScreen(robot.wx, robot.wy);
      drawRobot(ctx, sx, sy - 10 * s, s, robot, t);
      drawAccessory(ctx, sx, sy - 52 * s, s, robot.status, t);
    }

    // speech bubble for the active robot
    const active = this.activeId && this.robots.get(this.activeId);
    if (active && caption) {
      const [sx, sy] = cam.toScreen(active.wx, active.wy);
      drawBubble(ctx, sx, sy - 64 * s * (active.main ? 1.3 : 1), s, caption, t);
    }

    // failure vignette flash
    if (this.failedFlash > 0) {
      ctx.save();
      ctx.fillStyle = `rgba(224,82,82,${0.12 * this.failedFlash})`;
      ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
      ctx.restore();
    }
  }
}

// Which plates does this state occupy? (drives factory growth)
export function occupiedPlateZones(state) {
  const zones = new Set();
  for (const agent of Object.values(state.agents)) {
    if (agent.parent_id == null) continue; // MAIN is the podium, always there
    if (agent.zone === "path") zones.add("desk");
    else zones.add(agent.zone in PLATES ? agent.zone : "floor");
  }
  return zones;
}

function easeInOutQuad(x) {
  return x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
}

function hashPhase(id) {
  let h = 0;
  for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) % 997;
  return (h / 997) * Math.PI * 2;
}
