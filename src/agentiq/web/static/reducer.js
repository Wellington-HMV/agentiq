// JS mirror of agentiq/replay/reducer.py — the SINGLE scene projection.
// Must fold identically to the Python reducer (NFR5); any change there lands
// here too. Kept dependency-free so it can run in the browser and under Node
// for the parity fixture test.

export const Zone = {
  FLOOR: "floor",
  LIBRARY: "library",
  DESK: "desk",
  SUBAGENTS: "subagents",
  PATH: "path",
};

export const Status = {
  IDLE: "idle",
  READING: "reading",
  THINKING: "thinking",
  DELEGATING: "delegating",
  WORKING: "working",
  FAILED: "failed",
  DONE: "done",
};

export function initialState() {
  return {
    current_seq: -1,
    run_status: "pending",
    caption: "",
    agents: {}, // agent_id -> {agent_id, role, parent_id, status, zone, team}
    paths: [], // [from_id, to_id][]
  };
}

export function reduce(state, event) {
  const agents = {};
  for (const [aid, a] of Object.entries(state.agents)) agents[aid] = { ...a };
  const paths = state.paths.slice();
  let runStatus = state.run_status;
  let caption = state.caption;
  const aid = event.agent_id;
  const p = event.payload ?? {};

  switch (event.type) {
    case "run.started":
      runStatus = "running";
      caption = `run started: ${p.goal ?? ""}`;
      break;
    case "run.completed":
      runStatus = p.status ?? "completed";
      caption = `run ${runStatus}`;
      break;
    case "run.aborted":
      runStatus = "aborted";
      caption = `run aborted: ${p.reason ?? ""}`;
      break;
    case "agent.spawned": {
      const key = aid ?? "";
      const parentId = p.parent_id ?? null;
      agents[key] = {
        agent_id: key,
        role: p.role ?? null,
        parent_id: parentId,
        status: Status.IDLE,
        zone: parentId ? Zone.DESK : Zone.FLOOR,
        team: p.team ?? null,
      };
      caption = `spawned ${key}` + (p.role ? ` (${p.role})` : "");
      break;
    }
    case "task.delegated": {
      const toAgent = p.to_agent ?? "";
      paths.push([aid ?? "", toAgent]);
      if (aid && agents[aid]) {
        agents[aid].status = Status.DELEGATING;
        agents[aid].zone = Zone.PATH;
      }
      if (agents[toAgent]) agents[toAgent].status = Status.WORKING;
      caption = `${aid} -> ${toAgent}: ${p.task ?? ""}`;
      break;
    }
    case "vault.read":
      if (aid && agents[aid]) {
        agents[aid].zone = Zone.LIBRARY;
        agents[aid].status = Status.READING;
      }
      caption = `${aid} reads vault: ${p.ref ?? ""}`;
      break;
    case "decision.pending":
      caption = `decision pending: ${p.prompt ?? ""}`;
      break;
    case "decision.resolved":
      caption = `decision resolved: ${p.choice ?? ""}`;
      break;
    case "agent.failed":
      if (aid && agents[aid]) agents[aid].status = Status.FAILED;
      caption = `${aid} failed: ${p.cause ?? ""}`;
      break;
    default:
      // Valid but unhandled type: advance without crashing (forward-compat).
      caption = event.type;
  }

  return {
    current_seq: event.seq,
    run_status: runStatus,
    caption,
    agents,
    paths,
  };
}

export function reduceAll(events, initial = null) {
  let state = initial ?? initialState();
  for (const event of events) state = reduce(state, event);
  return state;
}

// Precompute one state per event index — O(1) seeking, like ReplayController.
export function statesPerIndex(events) {
  const states = [];
  let state = initialState();
  for (const event of events) {
    state = reduce(state, event);
    states.push(state);
  }
  return states;
}

export function isDecision(eventType) {
  return eventType.startsWith("decision.");
}

export function isFailure(eventType) {
  return eventType === "agent.failed" || eventType === "run.aborted";
}
