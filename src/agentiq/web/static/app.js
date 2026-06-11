// AGENTIQ factory — app orchestration. REAL TIME first:
// - LIVE: WebSocket tail of the run's JSONL, the factory reacts as it happens.
// - Finished runs: "cinema mode" — they auto-play from the start at a natural
//   pace, no transport bar. (Space pauses/resumes if you want to linger.)
// Semantic state comes only from reducer.js; FactoryScene animates between.

import { Camera } from "/static/iso.js";
import { initialState, isDecision, reduce, statesPerIndex } from "/static/reducer.js";
import { FactoryScene, occupiedPlateZones } from "/static/scene.js";

const $ = (sel) => document.querySelector(sel);

const canvas = $("#factory");
const ctx = canvas.getContext("2d");
const scene = new FactoryScene();
const cam = new Camera();
window.__scene = scene; // debug/test hook (Playwright visual checks)

const app = {
  mode: null, // "cinema" | "live"
  runId: null,
  events: [],
  states: [],
  zonesEver: [], // per-index Set of plate zones occupied so far
  pos: -1,
  playing: false,
  acc: 0, // playback accumulator (seconds)
  ws: null,
  liveEnded: false,
  decision: { interactive: false, sent: false },
  lastFrame: performance.now(),
};

// --- runs sidebar (poll: new runs appear in real time) ----------------------

async function refreshRuns() {
  let runs;
  try {
    runs = await (await fetch("/api/runs")).json();
  } catch {
    return;
  }
  const list = $("#runs-list");
  list.innerHTML = "";
  if (!runs.length) {
    list.innerHTML =
      '<li class="hint">No runs yet. Start one with: agentiq run "&lt;goal&gt;"</li>';
    return;
  }
  for (const run of runs) {
    const li = document.createElement("li");
    li.dataset.runId = run.run_id;
    if (run.run_id === app.runId) li.classList.add("active");
    const live = run.status === "running" || run.status === "pending";
    const cost = run.cost_usd != null ? ` · $${run.cost_usd.toFixed(2)}` : "";
    li.innerHTML = `
      <span class="goal">${escapeHtml(run.goal)}</span>
      <span class="sub">
        ${live ? '<span class="live-badge">● LIVE</span>' : `<span class="status-${run.status}">${run.status}</span>`}
        · ${run.run_id.slice(0, 10)}…${cost}</span>`;
    li.addEventListener("click", () => (live ? openLive(run.run_id) : openCinema(run.run_id)));
    list.appendChild(li);
  }
  // follow mode: auto-attach to the newest live run
  if (followMode && !app.runId) {
    const live = runs.find((r) => r.status === "running" || r.status === "pending");
    if (live) openLive(live.run_id);
  }
}

// --- cinema mode (finished runs auto-play) -----------------------------------

async function openCinema(runId) {
  closeWs();
  const res = await fetch(`/api/runs/${runId}/events`);
  if (!res.ok) return;
  app.events = await res.json();
  app.states = statesPerIndex(app.events);
  app.zonesEver = zonesEverPerIndex(app.states);
  app.mode = "cinema";
  app.runId = runId;
  enterStage();
  applyIndex(0, { snap: true });
  app.playing = true; // roll the movie
  refreshRuns();
}

function zonesEverPerIndex(states) {
  const out = [];
  let acc = new Set();
  for (const state of states) {
    acc = new Set([...acc, ...occupiedPlateZones(state)]);
    out.push(acc);
  }
  return out;
}

function applyIndex(pos, { snap = false } = {}) {
  if (!app.events.length) return;
  app.pos = Math.max(0, Math.min(pos, app.events.length - 1));
  scene.setState(app.states[app.pos], app.events[app.pos], app.zonesEver[app.pos], {
    snap,
  });
  pushTicker(app.events[app.pos]);
  syncHud();
}

// --- live mode ----------------------------------------------------------------

function openLive(runId) {
  closeWs();
  app.mode = "live";
  app.runId = runId;
  app.events = [];
  app.states = [];
  app.zonesEver = [];
  app.pos = -1;
  app.liveEnded = false;
  enterStage();
  connectWs(runId);
  refreshRuns();
}

function connectWs(runId) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/live/${runId}`);
  app.ws = ws;
  ws.onmessage = (msg) => {
    const data = JSON.parse(msg.data);
    if (data.type === "event") liveAppend(data.event);
    else if (data.type === "end") {
      app.liveEnded = true;
      showSummary();
      syncHud();
    }
  };
  ws.onclose = () => {
    if (app.mode === "live" && app.runId === runId && !app.liveEnded) {
      setTimeout(() => app.ws === ws && connectWs(runId), 1000);
    }
  };
}

function liveAppend(event) {
  if (event.type === "decision.pending") {
    app.decision = { interactive: false, sent: false };
    probeDecision(); // the resolver drops its file right after the event
  } else if (event.type === "decision.resolved") {
    app.decision = { interactive: false, sent: false };
  }
  const prevState = app.states.at(-1) ?? initialState();
  const state = reduce(prevState, event);
  const prevZones = app.zonesEver.at(-1) ?? new Set();
  app.events.push(event);
  app.states.push(state);
  app.zonesEver.push(new Set([...prevZones, ...occupiedPlateZones(state)]));
  app.pos = app.events.length - 1;
  scene.setState(state, event, app.zonesEver.at(-1), { snap: app.pos === 0 });
  pushTicker(event);
  syncHud();
}

function closeWs() {
  if (app.ws) {
    const ws = app.ws;
    app.ws = null;
    ws.close();
  }
  app.playing = false;
  hideSummary();
  $("#ticker").innerHTML = "";
}

// --- HUD / overlays -------------------------------------------------------------

function enterStage() {
  $("#stage-hint").hidden = true;
  canvas.hidden = false;
  $("#hud-bottom").hidden = false;
  $("#live-pill").hidden = false;
  hideSummary();
}

function syncHud() {
  const state = app.states[app.pos];
  if (!state) return;
  const cost = costThrough(app.pos);
  $("#runmeta").textContent =
    `run ${app.runId.slice(0, 14)}… · ${state.run_status}` +
    (cost > 0 ? ` · $${cost.toFixed(2)}` : "");
  $("#caption").textContent = `▸ ${state.caption}`;

  const pill = $("#live-pill");
  if (app.mode === "live") {
    pill.textContent = app.liveEnded
      ? `■ finished · ${app.events.length} events`
      : `● LIVE · ${app.events.length} events`;
    pill.classList.toggle("ended", app.liveEnded);
  } else {
    const done = app.pos >= app.events.length - 1;
    pill.textContent = done ? "■ fim" : app.playing ? "▶ reprise" : "⏸ pausado";
    pill.classList.toggle("ended", !app.playing || done);
  }

  renderDecisionCard();

  if (app.mode === "cinema" && app.pos === app.events.length - 1) showSummary();
}

// --- decision answering (live) ---------------------------------------------------

// The pending-decision file may land instants after the event; retry briefly.
async function probeDecision(attempt = 0) {
  if (app.mode !== "live") return;
  try {
    const res = await fetch(`/api/runs/${app.runId}/decision`);
    if (res.ok) {
      app.decision.interactive = true;
      renderDecisionCard();
      return;
    }
  } catch {
    /* fall through to retry */
  }
  if (attempt < 6 && scene.decision) setTimeout(() => probeDecision(attempt + 1), 450);
}

async function answerDecision(choice) {
  if (!app.decision.interactive || app.decision.sent) return;
  const res = await fetch(`/api/runs/${app.runId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ choice }),
  });
  if (res.ok) {
    app.decision.sent = true;
    renderDecisionCard();
  }
}

function renderDecisionCard() {
  const card = $("#decision-card");
  if (!scene.decision) {
    card.hidden = true;
    return;
  }
  card.hidden = false;
  $("#decision-prompt").textContent = scene.decision.prompt ?? "";
  const options = scene.decision.options ?? [];
  const interactive = app.decision.interactive && !app.decision.sent;
  const list = $("#decision-options");
  list.innerHTML = "";
  options.forEach((opt, i) => {
    const li = document.createElement("li");
    const isDefault = opt === scene.decision.default;
    li.className = (isDefault ? "default " : "") + (interactive ? "pick" : "");
    li.textContent = `${i + 1}. ${opt}${isDefault ? " ◂ default" : ""}`;
    if (interactive) li.addEventListener("click", () => answerDecision(opt));
    list.appendChild(li);
  });
  const hint = $("#decision-hint");
  if (app.decision.sent) hint.textContent = "✓ resposta enviada — retomando…";
  else if (interactive)
    hint.textContent = "clique numa opção · Enter = default · 1-9 = opção";
  else hint.textContent = app.mode === "live" ? "aguardando canal…" : "";
}

document.addEventListener("keydown", (e) => {
  if (app.mode !== "live" || !scene.decision || !app.decision.interactive) return;
  if (e.key === "Enter") {
    e.preventDefault();
    answerDecision("");
  } else if (/^[1-9]$/.test(e.key)) {
    const opt = (scene.decision.options ?? [])[Number(e.key) - 1];
    if (opt !== undefined) {
      e.preventDefault();
      answerDecision(opt);
    }
  }
});

function costThrough(pos) {
  let total = 0;
  for (let i = 0; i <= pos && i < app.events.length; i++) {
    if (app.events[i].type === "agent.usage") {
      total += app.events[i].payload?.cost_usd ?? 0;
    }
  }
  return total;
}

async function showSummary() {
  const card = $("#summary-card");
  const wanted = app.runId;
  try {
    const res = await fetch(`/api/runs/${app.runId}/summary`);
    if (!res.ok) return;
    const s = await res.json();
    const stillAtEnd =
      app.runId === wanted &&
      (app.mode === "live" || app.pos === app.events.length - 1);
    if (!stillAtEnd) return;
    $("#summary-body").innerHTML = `
      <div>status: <b class="status-${s.status}">${s.status}</b></div>
      <div>events: ${app.events.length}</div>
      ${s.cost_usd != null ? `<div>cost: $${Number(s.cost_usd).toFixed(2)}</div>` : ""}
      ${s.duration_seconds != null ? `<div>duration: ${Number(s.duration_seconds).toFixed(1)}s</div>` : ""}`;
    card.hidden = false;
  } catch {
    /* no summary yet */
  }
}
function hideSummary() {
  $("#summary-card").hidden = true;
}

function pushTicker(event) {
  const ticker = $("#ticker");
  const el = document.createElement("span");
  el.className = "tick";
  if (event.type === "agent.failed" || event.type === "run.aborted") el.classList.add("bad");
  if (isDecision(event.type)) el.classList.add("gold");
  el.textContent = `${event.seq} ${event.type}`;
  ticker.prepend(el);
  while (ticker.children.length > 8) ticker.lastChild.remove();
}

// Space pauses/resumes the cinema playback (no visible transport — power key).
document.addEventListener("keydown", (e) => {
  if (e.key === " " && app.mode === "cinema" && app.events.length) {
    e.preventDefault();
    app.playing = !app.playing;
    syncHud();
  }
});

// --- render loop -------------------------------------------------------------------

function resize() {
  canvas.width = canvas.clientWidth * devicePixelRatio;
  canvas.height = canvas.clientHeight * devicePixelRatio;
}
window.addEventListener("resize", resize);

function frame(now) {
  const dt = Math.min((now - app.lastFrame) / 1000, 0.1);
  app.lastFrame = now;
  const t = now / 1000;

  // cinema auto-advance; decisions linger so the pause is felt, and walks
  // (vault.read sends a robot across the floor) get time to complete
  if (app.mode === "cinema" && app.playing) {
    app.acc += dt;
    const type = app.events[app.pos]?.type ?? "";
    const tick = isDecision(type) ? 2.4 : type === "vault.read" ? 2.0 : 0.9;
    if (app.acc >= tick) {
      app.acc = 0;
      if (app.pos >= app.events.length - 1) {
        app.playing = false;
        syncHud();
      } else {
        applyIndex(app.pos + 1);
      }
    }
  }

  if (canvas.width !== canvas.clientWidth * devicePixelRatio) resize();
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);

  if (app.pos >= 0) {
    cam.fitWorldBounds(scene.framePoints(), canvas.clientWidth, canvas.clientHeight);
    cam.update(dt);
    scene.update(dt);
    scene.draw(ctx, cam, t, app.states[app.pos]?.caption ?? "");
  }
  requestAnimationFrame(frame);
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

// --- boot ----------------------------------------------------------------------

const params = new URLSearchParams(location.search);
const followMode = params.get("follow") === "1";

resize();
requestAnimationFrame(frame);
refreshRuns().then(() => {
  const runId = params.get("run");
  if (runId && params.get("live") === "1") openLive(runId);
  else if (runId) openCinema(runId);
});
setInterval(refreshRuns, 2500);
