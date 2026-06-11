"""FastAPI app serving the AGENTIQ factory front-end and the run-store API.

Endpoints (all read-only over the run store — phase W0):

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
