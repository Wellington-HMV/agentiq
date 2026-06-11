// Canvas painters for the AGENTIQ factory — the art bible is AGENTIQ/ (Grok
// renders): charcoal chibi robots with gold trim and glowing capsule eyes,
// colored floor plates, a glowing central podium. Everything is drawn in
// screen space; callers pass the camera-projected position and scale.

export const PALETTE = {
  bg: "#16171a",
  floorA: "#222428",
  floorB: "#1d1f23",
  plateEdge: "#3a3d44",
  charcoal: "#33363c",
  charcoalDark: "#26282d",
  visor: "#17181c",
  gold: "#d4a017",
  goldSoft: "#b8901f",
  text: "#e8e6e3",
  dim: "#8a8f98",
  error: "#e05252",
  success: "#5fb878",
  zone: {
    library: "#58c26e",
    desk: "#4d9fe8",
    subagents: "#e8924d",
    floor: "#7a7f88",
    path: "#c9a86a",
  },
};

export function statusEyeColor(status) {
  switch (status) {
    case "failed":
      return PALETTE.error;
    case "done":
      return PALETTE.success;
    case "idle":
      return "#6e7178";
    default:
      return "#ffd76a"; // warm glowing amber — the mascot's lit eyes
  }
}

function rr(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
}

// A diamond (iso tile face) centered on (cx, cy); halfW/halfH in screen px.
function diamond(ctx, cx, cy, halfW, halfH) {
  ctx.beginPath();
  ctx.moveTo(cx, cy - halfH);
  ctx.lineTo(cx + halfW, cy);
  ctx.lineTo(cx, cy + halfH);
  ctx.lineTo(cx - halfW, cy);
  ctx.closePath();
}

// --- floor & plates ----------------------------------------------------------

export function drawFloorTile(ctx, sx, sy, s, shade) {
  diamond(ctx, sx, sy, 32 * s, 16 * s);
  ctx.fillStyle = shade ? PALETTE.floorA : PALETTE.floorB;
  ctx.fill();
}

// A zone plate: a colored, softly glowing platform with a name plate.
// grow ∈ [0,1] animates construction (scale-in + fade).
export function drawPlate(ctx, sx, sy, s, halfW, halfH, color, label, grow, t) {
  const g = easeOutBack(grow);
  const hw = halfW * s * g;
  const hh = halfH * s * g;
  if (g <= 0.01) return;

  // glow
  ctx.save();
  ctx.shadowColor = color;
  ctx.shadowBlur = 18 * s * grow;
  diamond(ctx, sx, sy, hw, hh);
  ctx.fillStyle = hexA(color, 0.16);
  ctx.fill();
  ctx.restore();

  // top face + rim
  diamond(ctx, sx, sy, hw, hh);
  ctx.fillStyle = hexA(color, 0.13 + 0.03 * Math.sin(t * 1.3));
  ctx.fill();
  ctx.strokeStyle = hexA(color, 0.75);
  ctx.lineWidth = 1.5 * s;
  ctx.stroke();
  // inner line
  diamond(ctx, sx, sy, hw * 0.92, hh * 0.92);
  ctx.strokeStyle = hexA(color, 0.25);
  ctx.lineWidth = 1 * s;
  ctx.stroke();

  // name plate
  if (grow > 0.8 && label) {
    ctx.font = `${Math.max(10, 11 * s)}px "Segoe UI", sans-serif`;
    ctx.textAlign = "center";
    ctx.fillStyle = hexA(color, 0.9);
    ctx.fillText(label, sx, sy - hh - 8 * s);
  }
}

// The MAIN podium: circular platform, rotating gold ring.
export function drawPodium(ctx, sx, sy, s, t, paused) {
  // base ellipse
  ctx.beginPath();
  ctx.ellipse(sx, sy + 6 * s, 52 * s, 26 * s, 0, 0, Math.PI * 2);
  ctx.fillStyle = PALETTE.charcoalDark;
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(sx, sy, 50 * s, 25 * s, 0, 0, Math.PI * 2);
  ctx.fillStyle = "#2c2f35";
  ctx.fill();
  ctx.strokeStyle = PALETTE.goldSoft;
  ctx.lineWidth = 1.5 * s;
  ctx.stroke();

  // rotating ring of gold dashes (stops when world paused on a decision)
  ctx.save();
  ctx.strokeStyle = PALETTE.gold;
  ctx.lineWidth = 2.5 * s;
  ctx.shadowColor = PALETTE.gold;
  ctx.shadowBlur = 10 * s;
  const spin = paused ? 0 : t * 0.9;
  for (let i = 0; i < 8; i++) {
    const a0 = spin + (i / 8) * Math.PI * 2;
    ctx.beginPath();
    ctx.ellipse(sx, sy, 42 * s, 21 * s, 0, a0, a0 + 0.42);
    ctx.stroke();
  }
  ctx.restore();
}

// --- the robot ---------------------------------------------------------------
// pose: {bob, walkCycle, slump, dim}; status drives eyes & accessories.
export function drawRobot(ctx, sx, sy, s, robot, t) {
  const { status, active, spawn } = robot;
  const u = 1.15 * s * (robot.main ? 1.35 : 1); // unit scale; MAIN is bigger
  const drop = spawn < 1 ? (1 - easeOutBounce(spawn)) * -60 * s : 0;
  const slump = status === "failed" ? 3 * u : 0;
  const walking = robot.walking;
  const bobAmp = walking ? 2.2 : isBusy(status) ? 1.6 : 0.7;
  const bob =
    Math.sin(t * (walking ? 9 : isBusy(status) ? 4 : 1.6) + robot.phase) *
    bobAmp *
    u;
  const y = sy + drop + bob * -1 + slump;
  const dimmed = status === "idle" || status === "done";
  ctx.save();
  ctx.globalAlpha = spawn < 1 ? 0.35 + 0.65 * spawn : dimmed && !active ? 0.78 : 1;

  // lean into the direction of travel while walking
  if (robot.lean) {
    ctx.translate(sx, sy);
    ctx.rotate(robot.lean * 0.09);
    ctx.translate(-sx, -sy);
  }

  // shadow
  ctx.beginPath();
  ctx.ellipse(sx, sy + 14 * u, 13 * u, 4.5 * u, 0, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(0,0,0,.45)";
  ctx.fill();

  // feet
  const step = walking ? Math.sin(t * 9 + robot.phase) * 2.5 * u : 0;
  ctx.fillStyle = PALETTE.charcoalDark;
  rr(ctx, sx - 8 * u, y + 9 * u + step, 6.5 * u, 5 * u, 2.5 * u);
  ctx.fill();
  rr(ctx, sx + 1.5 * u, y + 9 * u - step, 6.5 * u, 5 * u, 2.5 * u);
  ctx.fill();

  // body
  const bodyGrad = ctx.createLinearGradient(sx, y - 6 * u, sx, y + 12 * u);
  bodyGrad.addColorStop(0, "#3c4046");
  bodyGrad.addColorStop(1, PALETTE.charcoalDark);
  rr(ctx, sx - 10 * u, y - 4 * u, 20 * u, 15 * u, 6 * u);
  ctx.fillStyle = bodyGrad;
  ctx.fill();
  ctx.strokeStyle = "rgba(0,0,0,.35)";
  ctx.lineWidth = 1 * u;
  ctx.stroke();
  // gold belly plate
  rr(ctx, sx - 5 * u, y + 0.5 * u, 10 * u, 7 * u, 2.5 * u);
  ctx.strokeStyle = PALETTE.goldSoft;
  ctx.lineWidth = 1.2 * u;
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(sx, y + 4 * u, 2 * u, 0, Math.PI * 2);
  ctx.fillStyle = PALETTE.gold;
  ctx.fill();

  // arms
  ctx.fillStyle = PALETTE.charcoal;
  const armSwing = walking ? Math.sin(t * 9 + robot.phase) * 3 * u : 0;
  rr(ctx, sx - 14.5 * u, y - 2 * u + armSwing, 5 * u, 9 * u, 2.5 * u);
  ctx.fill();
  rr(ctx, sx + 9.5 * u, y - 2 * u - armSwing, 5 * u, 9 * u, 2.5 * u);
  ctx.fill();

  // head
  const hy = y - 18 * u;
  const headGrad = ctx.createLinearGradient(sx, hy - 10 * u, sx, hy + 12 * u);
  headGrad.addColorStop(0, "#43474e");
  headGrad.addColorStop(1, PALETTE.charcoal);
  rr(ctx, sx - 13 * u, hy - 9 * u, 26 * u, 21 * u, 8 * u);
  ctx.fillStyle = headGrad;
  ctx.fill();
  ctx.strokeStyle = robot.main ? PALETTE.goldSoft : "rgba(0,0,0,.35)";
  ctx.lineWidth = 1.2 * u;
  ctx.stroke();

  // ear caps (gold)
  ctx.fillStyle = PALETTE.goldSoft;
  rr(ctx, sx - 15.5 * u, hy - 2.5 * u, 3 * u, 7 * u, 1.5 * u);
  ctx.fill();
  rr(ctx, sx + 12.5 * u, hy - 2.5 * u, 3 * u, 7 * u, 1.5 * u);
  ctx.fill();

  // antenna (ball glows when busy)
  ctx.strokeStyle = PALETTE.charcoal;
  ctx.lineWidth = 1.4 * u;
  ctx.beginPath();
  ctx.moveTo(sx - 6 * u, hy - 9 * u);
  ctx.lineTo(sx - 9 * u, hy - 16 * u);
  ctx.stroke();
  ctx.save();
  if (isBusy(status)) {
    ctx.shadowColor = PALETTE.gold;
    ctx.shadowBlur = 8 * u;
  }
  ctx.beginPath();
  ctx.arc(sx - 9 * u, hy - 17 * u, 2.2 * u, 0, Math.PI * 2);
  ctx.fillStyle = isBusy(status) ? PALETTE.gold : PALETTE.goldSoft;
  ctx.fill();
  ctx.restore();

  // visor
  rr(ctx, sx - 10 * u, hy - 6 * u, 20 * u, 14 * u, 6 * u);
  ctx.fillStyle = PALETTE.visor;
  ctx.fill();
  ctx.strokeStyle = hexA(PALETTE.gold, robot.main ? 0.8 : 0.25);
  ctx.lineWidth = 1 * u;
  ctx.stroke();

  // eyes — THE status channel (glowing capsules)
  drawEyes(ctx, sx, hy + 0.5 * u, u, robot, t);

  // active highlight ring on the ground
  if (active) {
    ctx.save();
    ctx.strokeStyle = PALETTE.gold;
    ctx.shadowColor = PALETTE.gold;
    ctx.shadowBlur = 12 * u;
    ctx.lineWidth = 1.6 * u;
    ctx.beginPath();
    ctx.ellipse(sx, sy + 14 * u, 17 * u, 6.5 * u, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }

  // id label
  ctx.font = `${Math.max(9, 10 * u)}px monospace`;
  ctx.textAlign = "center";
  ctx.fillStyle = active ? PALETTE.text : PALETTE.dim;
  ctx.fillText(robot.label, sx, sy + 26 * u);

  ctx.restore();
}

function drawEyes(ctx, cx, cy, u, robot, t) {
  const color = statusEyeColor(robot.status);
  const blink =
    robot.status !== "failed" && Math.sin(t * 1.1 + robot.phase * 3) > 0.985;
  ctx.save();
  ctx.shadowColor = color;
  ctx.shadowBlur = 9 * u;
  ctx.fillStyle = color;
  ctx.strokeStyle = color;

  if (robot.status === "failed") {
    ctx.lineWidth = 2 * u;
    for (const dx of [-5 * u, 5 * u]) {
      ctx.beginPath();
      ctx.moveTo(cx + dx - 2.4 * u, cy - 2.4 * u);
      ctx.lineTo(cx + dx + 2.4 * u, cy + 2.4 * u);
      ctx.moveTo(cx + dx + 2.4 * u, cy - 2.4 * u);
      ctx.lineTo(cx + dx - 2.4 * u, cy + 2.4 * u);
      ctx.stroke();
    }
  } else if (blink) {
    ctx.lineWidth = 1.8 * u;
    for (const dx of [-5 * u, 5 * u]) {
      ctx.beginPath();
      ctx.moveTo(cx + dx - 2.2 * u, cy);
      ctx.lineTo(cx + dx + 2.2 * u, cy);
      ctx.stroke();
    }
  } else {
    const eh = robot.status === "idle" ? 3 * u : 6 * u;
    for (const dx of [-5 * u, 5 * u]) {
      rr(ctx, cx + dx - 2 * u, cy - eh / 2, 4 * u, eh, 2 * u);
      ctx.fill();
    }
    // smile
    if (robot.status !== "idle") {
      ctx.lineWidth = 1.3 * u;
      ctx.beginPath();
      ctx.arc(cx, cy + 3.2 * u, 2.6 * u, 0.15 * Math.PI, 0.85 * Math.PI);
      ctx.stroke();
    }
  }
  ctx.restore();
}

// --- effects -----------------------------------------------------------------

// Glowing delegation link. recent ∈ [0,1] fades old links down.
export function drawLink(ctx, x0, y0, x1, y1, s, t, recent) {
  ctx.save();
  ctx.strokeStyle = hexA(PALETTE.gold, 0.25 + 0.65 * recent);
  ctx.lineWidth = (1.5 + 1.5 * recent) * s;
  ctx.setLineDash([8 * s, 7 * s]);
  ctx.lineDashOffset = -t * 40 * s; // marching toward the target
  if (recent > 0.5) {
    ctx.shadowColor = PALETTE.gold;
    ctx.shadowBlur = 10 * s;
  }
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  // gentle arc
  const mx = (x0 + x1) / 2;
  const my = (y0 + y1) / 2 - 24 * s;
  ctx.quadraticCurveTo(mx, my, x1, y1);
  ctx.stroke();
  ctx.restore();
}

// Speech bubble above the active robot.
export function drawBubble(ctx, sx, sy, s, text, t) {
  const pad = 8 * s;
  ctx.font = `${Math.max(10, 12 * s)}px "Segoe UI", sans-serif`;
  const w = Math.min(ctx.measureText(text).width + pad * 2, 280 * s);
  const h = 24 * s;
  const x = sx - w / 2;
  const y = sy - h - 14 * s + Math.sin(t * 2) * 1.5 * s;

  ctx.save();
  rr(ctx, x, y, w, h, 8 * s);
  ctx.fillStyle = "rgba(20,21,24,.92)";
  ctx.fill();
  ctx.strokeStyle = PALETTE.goldSoft;
  ctx.lineWidth = 1 * s;
  ctx.stroke();
  // tail
  ctx.beginPath();
  ctx.moveTo(sx - 4 * s, y + h);
  ctx.lineTo(sx, y + h + 6 * s);
  ctx.lineTo(sx + 4 * s, y + h);
  ctx.fillStyle = "rgba(20,21,24,.92)";
  ctx.fill();

  ctx.fillStyle = PALETTE.text;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const clipped =
    ctx.measureText(text).width > w - pad * 2
      ? text.slice(0, Math.floor((w - pad * 2) / (6.2 * s))) + "…"
      : text;
  ctx.fillText(clipped, sx, y + h / 2);
  ctx.restore();
}

// Thinking gears / reading book accessory above a robot's head.
export function drawAccessory(ctx, sx, sy, s, status, t) {
  if (status === "thinking") {
    drawGear(ctx, sx + 14 * s, sy - 4 * s, 5.5 * s, t * 1.5, "#9fc6ef");
    drawGear(ctx, sx + 22 * s, sy - 10 * s, 3.8 * s, -t * 2.1, "#7da9d8");
  } else if (status === "reading") {
    ctx.save();
    ctx.translate(sx + 16 * s, sy - 6 * s);
    ctx.fillStyle = "#cdebd4";
    ctx.strokeStyle = "#58c26e";
    ctx.lineWidth = 1 * s;
    ctx.beginPath();
    ctx.moveTo(-6 * s, 0);
    ctx.quadraticCurveTo(0, -3 * s, 6 * s, 0);
    ctx.lineTo(6 * s, 5 * s);
    ctx.quadraticCurveTo(0, 2 * s, -6 * s, 5 * s);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, -1.5 * s);
    ctx.lineTo(0, 3.5 * s);
    ctx.stroke();
    ctx.restore();
  }
}

function drawGear(ctx, cx, cy, r, rot, color) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(rot);
  ctx.fillStyle = color;
  for (let i = 0; i < 8; i++) {
    ctx.rotate(Math.PI / 4);
    ctx.fillRect(-r * 0.16, -r * 1.25, r * 0.32, r * 0.5);
  }
  ctx.beginPath();
  ctx.arc(0, 0, r * 0.85, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#17181c";
  ctx.beginPath();
  ctx.arc(0, 0, r * 0.35, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

// A rotating red alarm beacon planted on a sector that has a failed robot.
export function drawBeacon(ctx, sx, sy, s, t) {
  const u = 1.2 * s;
  const pulse = 0.6 + 0.4 * Math.sin(t * 6);

  // ground glow
  ctx.save();
  ctx.globalAlpha = 0.25 * pulse;
  ctx.fillStyle = PALETTE.error;
  ctx.beginPath();
  ctx.ellipse(sx, sy + 2 * u, 16 * u, 6 * u, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  // pole + base
  ctx.fillStyle = "#2c2f35";
  ctx.fillRect(sx - 2 * u, sy - 14 * u, 4 * u, 14 * u);
  ctx.beginPath();
  ctx.ellipse(sx, sy, 6 * u, 2.5 * u, 0, 0, Math.PI * 2);
  ctx.fill();

  // rotating light cone (sweeps like a real giroflex)
  const angle = t * 5;
  ctx.save();
  ctx.translate(sx, sy - 17 * u);
  ctx.rotate(angle);
  const cone = ctx.createLinearGradient(0, 0, 26 * u, 0);
  cone.addColorStop(0, hexA(PALETTE.error, 0.55 * pulse));
  cone.addColorStop(1, hexA(PALETTE.error, 0));
  ctx.fillStyle = cone;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(26 * u, -7 * u);
  ctx.lineTo(26 * u, 7 * u);
  ctx.closePath();
  ctx.fill();
  // opposite sweep, dimmer
  ctx.rotate(Math.PI);
  ctx.globalAlpha = 0.5;
  ctx.fill();
  ctx.restore();

  // dome
  ctx.save();
  ctx.shadowColor = PALETTE.error;
  ctx.shadowBlur = 14 * u * pulse;
  ctx.fillStyle = PALETTE.error;
  ctx.beginPath();
  ctx.arc(sx, sy - 17 * u, 4.5 * u, Math.PI, 0);
  ctx.lineTo(sx + 4.5 * u, sy - 15 * u);
  ctx.lineTo(sx - 4.5 * u, sy - 15 * u);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

// A fading dust puff kicked up by a walking robot. k ∈ (0,1], 1 = fresh.
export function drawDust(ctx, sx, sy, s, k) {
  ctx.save();
  ctx.globalAlpha = 0.28 * k;
  ctx.fillStyle = "#9a9da6";
  const r = (3 + (1 - k) * 6) * s;
  ctx.beginPath();
  ctx.ellipse(sx, sy + 4 * s - (1 - k) * 6 * s, r, r * 0.55, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

// --- conveyor belts & crates ---------------------------------------------------

// A running conveyor belt between two screen points. Treads march toward the
// far end forever (the factory never sleeps); grow fades it in with its plate.
export function drawBelt(ctx, x0, y0, x1, y1, s, t, grow) {
  if (grow <= 0.05) return;
  const dx = x1 - x0;
  const dy = y1 - y0;
  const len = Math.hypot(dx, dy);
  if (len < 1) return;
  const ux = dx / len;
  const uy = dy / len;
  const px = -uy; // perpendicular
  const py = ux;
  const half = 9 * s;

  ctx.save();
  ctx.globalAlpha = grow;

  // dark band
  ctx.beginPath();
  ctx.moveTo(x0 + px * half, y0 + py * half);
  ctx.lineTo(x1 + px * half, y1 + py * half);
  ctx.lineTo(x1 - px * half, y1 - py * half);
  ctx.lineTo(x0 - px * half, y0 - py * half);
  ctx.closePath();
  ctx.fillStyle = "#1a1b1e";
  ctx.fill();

  // side rails
  ctx.strokeStyle = "#3a3d44";
  ctx.lineWidth = 2 * s;
  ctx.beginPath();
  ctx.moveTo(x0 + px * half, y0 + py * half);
  ctx.lineTo(x1 + px * half, y1 + py * half);
  ctx.moveTo(x0 - px * half, y0 - py * half);
  ctx.lineTo(x1 - px * half, y1 - py * half);
  ctx.stroke();

  // marching treads
  const gap = 16 * s;
  const offset = (t * 26 * s) % gap;
  ctx.strokeStyle = "#34373d";
  ctx.lineWidth = 2.5 * s;
  for (let d = offset; d < len; d += gap) {
    const cx = x0 + ux * d;
    const cy = y0 + uy * d;
    ctx.beginPath();
    ctx.moveTo(cx + px * (half - 2 * s), cy + py * (half - 2 * s));
    ctx.lineTo(cx - px * (half - 2 * s), cy - py * (half - 2 * s));
    ctx.stroke();
  }
  ctx.restore();
}

// A little iso crate (a task in transit). Slight bob + warm glow.
export function drawCrate(ctx, sx, sy, s, t) {
  const u = 1.1 * s;
  const y = sy - 6 * u + Math.sin(t * 6) * 0.8 * u;

  ctx.save();
  ctx.shadowColor = PALETTE.gold;
  ctx.shadowBlur = 8 * u;

  // side faces
  ctx.fillStyle = "#8a6a1f";
  ctx.beginPath();
  ctx.moveTo(sx - 7 * u, y);
  ctx.lineTo(sx, y + 4 * u);
  ctx.lineTo(sx, y + 11 * u);
  ctx.lineTo(sx - 7 * u, y + 7 * u);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#6e541a";
  ctx.beginPath();
  ctx.moveTo(sx + 7 * u, y);
  ctx.lineTo(sx, y + 4 * u);
  ctx.lineTo(sx, y + 11 * u);
  ctx.lineTo(sx + 7 * u, y + 7 * u);
  ctx.closePath();
  ctx.fill();
  // top face
  ctx.fillStyle = PALETTE.gold;
  ctx.beginPath();
  ctx.moveTo(sx, y - 4 * u);
  ctx.lineTo(sx + 7 * u, y);
  ctx.lineTo(sx, y + 4 * u);
  ctx.lineTo(sx - 7 * u, y);
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  // strap
  ctx.strokeStyle = "#3a2f10";
  ctx.lineWidth = 1.2 * u;
  ctx.beginPath();
  ctx.moveTo(sx - 7 * u, y + 3.5 * u);
  ctx.lineTo(sx, y + 7.5 * u);
  ctx.lineTo(sx + 7 * u, y + 3.5 * u);
  ctx.stroke();
}

// --- helpers -----------------------------------------------------------------

export function isBusy(status) {
  return ["reading", "thinking", "delegating", "working"].includes(status);
}

export function hexA(hex, a) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

export function easeOutBack(x) {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return Math.min(1, 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2));
}

export function easeOutBounce(x) {
  const n1 = 7.5625;
  const d1 = 2.75;
  if (x < 1 / d1) return n1 * x * x;
  if (x < 2 / d1) return n1 * (x -= 1.5 / d1) * x + 0.75;
  if (x < 2.5 / d1) return n1 * (x -= 2.25 / d1) * x + 0.9375;
  return n1 * (x -= 2.625 / d1) * x + 0.984375;
}
