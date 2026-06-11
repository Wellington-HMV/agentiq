"""FastAPI app serving the AGENTIQ factory front-end and the run-store API.

Endpoints:

- ``POST /api/runs``               — open a demand: {goal, project, live}. The
  orchestration runs as a background task in this process, aimed at the given
  repository (whose own agentiq.config.toml governs policy/ceiling/vault);
  returns {run_id} immediately so the browser can attach live.
- ``GET /``                        — the factory single-page app.
- ``GET /api/runs``                — run listing (mirrors ``agentiq runs``).
- ``GET /api/runs/{id}/events``    — the full validated event log as JSON; the
  browser owns the transport (instant scrubbing, NFR "seek feels instant").
- ``GET /api/runs/{id}/summary``   — summary.json projection, when present.
- ``WS  /ws/live/{id}``            — real-time event stream: replays what's in
  the log, then tails the append-only JSONL (fsync-per-write) and pushes each
  new event as it lands. Works even when the run executes in another process —
  the store IS the bus. Closes after the run's terminal event.

- ``GET/POST /api/runs/{id}/decision`` — the file decision bridge: GET shows the
  pending decision, POST answers it ("" = default, "2" = option 2, or the option
  text). The orchestration-side ``FileDecisionResolver`` picks the answer up.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agentiq.core.decision import DecisionRequest, DecisionUnresolved, parse_choice
from agentiq.core.decision_bridge import read_pending, write_answer
from agentiq.core.run import find_run_dir, list_runs
from agentiq.events.reader import EventLogError, read_events

STATIC_DIR = Path(__file__).parent / "static"

# A run is over once one of these lands; the live socket closes after it.
_TERMINAL_EVENTS = frozenset({"run.completed", "run.aborted"})

_POLL_SECONDS = 0.25  # JSONL tail cadence; events are fsynced per write


class DecisionAnswer(BaseModel):
    """POST body for answering the pending decision ("" = accept the default)."""

    choice: str = ""


class NewDemand(BaseModel):
    """POST body for opening a demand: a goal aimed at a target repository."""

    goal: str
    project: str = "."  # the repository the agents will work on
    live: bool = False  # real Claude agents (CLI login) vs offline deterministic


def _demand_strategy(live: bool, settings, project: Path):  # noqa: ANN001, ANN202
    """Mirror of the CLI's strategy selection, scoped to the target repo."""
    if live:
        from agentiq.agent.claude_strategy import ClaudeStrategy
        from agentiq.policy.safety import SafetyGuard

        guard = SafetyGuard(
            str(project),
            vault_paths=settings.vault.paths,
            denied_ops=settings.safety.denied_ops,
        )
        return ClaudeStrategy(cost_ceiling_usd=settings.cost.ceiling_usd, safety=guard)
    from agentiq.core.orchestrator import DeterministicStrategy

    return DeterministicStrategy()


def create_app(runs_root: str | Path | None = None) -> FastAPI:
    """Build the web app. ``runs_root=None`` uses the default (+legacy) store."""
    app = FastAPI(title="AGENTIQ", docs_url=None, redoc_url=None)

    @app.get("/api/runs")
    def api_runs() -> list[dict[str, object]]:
        return [asdict(info) for info in list_runs(runs_root)]

    @app.get("/api/runs/{run_id}/events")
    def api_events(run_id: str) -> list[dict[str, object]]:
        run_dir = find_run_dir(run_id, runs_root)
        if run_dir is None:
            raise HTTPException(status_code=404, detail=f"no run {run_id!r}")
        try:
            return [e.model_dump() for e in read_events(run_dir / "events.jsonl")]
        except EventLogError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/api/runs/{run_id}/summary")
    def api_summary(run_id: str) -> dict[str, object]:
        run_dir = find_run_dir(run_id, runs_root)
        if run_dir is None:
            raise HTTPException(status_code=404, detail=f"no run {run_id!r}")
        summary_path = run_dir / "summary.json"
        if not summary_path.is_file():
            raise HTTPException(status_code=404, detail="no summary (run not final?)")
        return json.loads(summary_path.read_text(encoding="utf-8"))

    # Demands launched from the browser run as background tasks in this
    # process; keep strong references so the event loop never drops them.
    app.state.demand_tasks = set()

    @app.post("/api/runs")
    async def api_open_demand(body: NewDemand) -> dict[str, str]:
        goal = body.goal.strip()
        if not goal:
            raise HTTPException(status_code=400, detail="goal must not be empty")
        # Trivial localhost stat; not worth a thread hop (ASYNC240).
        project = Path(body.project or ".").expanduser()  # noqa: ASYNC240
        if not project.is_dir():  # noqa: ASYNC240
            raise HTTPException(
                status_code=400, detail=f"project directory not found: {project}"
            )

        from agentiq.config.settings import Settings, find_config, load_config
        from agentiq.core.decision_bridge import FileDecisionResolver
        from agentiq.core.ids import new_ulid
        from agentiq.core.orchestrator import run_orchestration
        from agentiq.core.run import default_runs_root
        from agentiq.policy.policy import PolicyResolver
        from agentiq.vault.harness import HarnessVaultProvider

        # The TARGET repo's config governs the run (policy, ceiling, vault).
        cfg_path = find_config(project)
        try:
            settings = load_config(cfg_path) if cfg_path is not None else Settings()
        except Exception as e:  # ConfigError: surface it to the form
            raise HTTPException(status_code=400, detail=str(e)) from e

        vault = None
        if settings.vault.paths:
            vault_path = Path(settings.vault.paths[0])
            if not vault_path.is_absolute():
                vault_path = project / vault_path
            vault = HarnessVaultProvider(vault_path)

        run_id = new_ulid()
        store = Path(runs_root) if runs_root is not None else default_runs_root()
        resolver = PolicyResolver(
            settings.autonomy, FileDecisionResolver(store / run_id)
        )
        strategy = _demand_strategy(body.live, settings, project)

        task = asyncio.ensure_future(
            run_orchestration(
                goal,
                project,
                strategy=strategy,
                vault=vault,
                runs_root=runs_root,
                run_id=run_id,
                resolver=resolver,
                isolation_mode=settings.isolation.mode,
            )
        )
        app.state.demand_tasks.add(task)
        task.add_done_callback(app.state.demand_tasks.discard)
        return {"run_id": run_id}

    @app.get("/api/runs/{run_id}/decision")
    def api_decision(run_id: str) -> dict[str, object]:
        run_dir = find_run_dir(run_id, runs_root)
        if run_dir is None:
            raise HTTPException(status_code=404, detail=f"no run {run_id!r}")
        pending = read_pending(run_dir)
        if pending is None:
            raise HTTPException(status_code=404, detail="no pending decision")
        return pending

    @app.post("/api/runs/{run_id}/decision")
    def api_answer_decision(run_id: str, body: DecisionAnswer) -> dict[str, object]:
        run_dir = find_run_dir(run_id, runs_root)
        if run_dir is None:
            raise HTTPException(status_code=404, detail=f"no run {run_id!r}")
        pending = read_pending(run_dir)
        if pending is None:
            raise HTTPException(status_code=409, detail="no pending decision")
        raw_options = pending.get("options")
        raw_default = pending.get("default")
        request = DecisionRequest(
            agent_id=str(pending.get("agent_id", "")),
            prompt=str(pending.get("prompt", "")),
            options=[str(o) for o in raw_options]
            if isinstance(raw_options, list)
            else [],
            default=raw_default if isinstance(raw_default, str) else None,
        )
        try:
            choice = parse_choice(request, body.choice)
        except DecisionUnresolved as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        write_answer(run_dir, choice)
        return {"ok": True, "choice": choice}

    @app.websocket("/ws/live/{run_id}")
    async def ws_live(ws: WebSocket, run_id: str) -> None:
        await ws.accept()
        run_dir = find_run_dir(run_id, runs_root)
        if run_dir is None:
            await ws.close(code=4004, reason=f"no run {run_id!r}")
            return
        log_path = run_dir / "events.jsonl"
        sent = 0
        try:
            while True:
                try:
                    events = list(read_events(log_path))
                except EventLogError:
                    # A line is mid-write (or trailing garbage after a crash):
                    # don't kill the stream — wait for the writer's next fsync.
                    await asyncio.sleep(_POLL_SECONDS)
                    continue
                for event in events[sent:]:
                    await ws.send_json({"type": "event", "event": event.model_dump()})
                    if event.type in _TERMINAL_EVENTS:
                        await ws.send_json({"type": "end"})
                        await ws.close()
                        return
                sent = len(events)
                await asyncio.sleep(_POLL_SECONDS)
        except WebSocketDisconnect:
            return

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
