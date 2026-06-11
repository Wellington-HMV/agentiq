"""Tests for the web factory server (phase W0): API over the run store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from agentiq.events.writer import JsonlEventWriter
from agentiq.web.server import create_app


def _fabricate_run(runs_root: Path, run_id: str = "01TESTRUN") -> Path:
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    with JsonlEventWriter(run_dir / "events.jsonl") as w:
        w.write("run.started", {"goal": "g", "project": "."}, run_id=run_id)
        w.write("agent.spawned", {"role": "dev"}, run_id=run_id, agent_id="a1")
        w.write("decision.pending", {"prompt": "pick"}, run_id=run_id, agent_id="a1")
        w.write("run.completed", {"status": "completed"}, run_id=run_id)
    (run_dir / "meta.json").write_text(
        json.dumps({"run_id": run_id, "goal": "g", "status": "completed"}),
        encoding="utf-8",
    )
    (run_dir / "summary.json").write_text(
        json.dumps({"run_id": run_id, "status": "completed", "cost_usd": 0.0}),
        encoding="utf-8",
    )
    return run_dir


def test_api_runs_lists_store(tmp_path: Path) -> None:
    _fabricate_run(tmp_path)
    client = TestClient(create_app(runs_root=tmp_path))
    runs = client.get("/api/runs").json()
    assert [r["run_id"] for r in runs] == ["01TESTRUN"]
    assert runs[0]["status"] == "completed"


def test_api_events_returns_full_validated_log(tmp_path: Path) -> None:
    _fabricate_run(tmp_path)
    client = TestClient(create_app(runs_root=tmp_path))
    events = client.get("/api/runs/01TESTRUN/events").json()
    assert [e["seq"] for e in events] == [0, 1, 2, 3]
    assert events[0]["type"] == "run.started"
    assert events[2]["payload"]["prompt"] == "pick"


def test_api_events_404_for_unknown_run(tmp_path: Path) -> None:
    client = TestClient(create_app(runs_root=tmp_path))
    assert client.get("/api/runs/NOPE/events").status_code == 404


def test_api_summary(tmp_path: Path) -> None:
    _fabricate_run(tmp_path)
    client = TestClient(create_app(runs_root=tmp_path))
    summary = client.get("/api/runs/01TESTRUN/summary").json()
    assert summary["status"] == "completed"


def test_index_serves_factory_page(tmp_path: Path) -> None:
    client = TestClient(create_app(runs_root=tmp_path))
    res = client.get("/")
    assert res.status_code == 200
    assert "AGENTIQ" in res.text


def test_static_assets_served(tmp_path: Path) -> None:
    client = TestClient(create_app(runs_root=tmp_path))
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/reducer.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_ws_live_streams_log_then_tails_new_events(tmp_path: Path) -> None:
    run_id = "01LIVERUN"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    log = run_dir / "events.jsonl"
    writer = JsonlEventWriter(log)
    writer.write("run.started", {"goal": "g", "project": "."}, run_id=run_id)
    writer.write("agent.spawned", {"role": "dev"}, run_id=run_id, agent_id="a1")

    client = TestClient(create_app(runs_root=tmp_path))
    with client.websocket_connect(f"/ws/live/{run_id}") as ws:
        # Catch-up: everything already in the log arrives first, in order.
        assert ws.receive_json()["event"]["type"] == "run.started"
        assert ws.receive_json()["event"]["seq"] == 1

        # Tail: an event appended AFTER connect is pushed too.
        writer.write("run.completed", {"status": "completed"}, run_id=run_id)
        assert ws.receive_json()["event"]["type"] == "run.completed"
        # Terminal event ends the stream explicitly.
        assert ws.receive_json() == {"type": "end"}
    writer.close()


def test_decision_endpoints_roundtrip(tmp_path: Path) -> None:
    from agentiq.core.decision_bridge import answer_path, pending_path

    _fabricate_run(tmp_path)
    run_dir = tmp_path / "01TESTRUN"
    client = TestClient(create_app(runs_root=tmp_path))

    # No pending decision yet.
    assert client.get("/api/runs/01TESTRUN/decision").status_code == 404
    res = client.post("/api/runs/01TESTRUN/decision", json={"choice": ""})
    assert res.status_code == 409

    # The orchestration side publishes a pending decision.
    pending_path(run_dir).write_text(
        json.dumps(
            {
                "agent_id": "parent",
                "prompt": "pick",
                "options": ["a", "b"],
                "default": "a",
            }
        ),
        encoding="utf-8",
    )
    pending = client.get("/api/runs/01TESTRUN/decision").json()
    assert pending["options"] == ["a", "b"]

    # An invalid choice is rejected and writes nothing.
    assert (
        client.post("/api/runs/01TESTRUN/decision", json={"choice": "zzz"}).status_code
        == 400
    )
    assert not answer_path(run_dir).exists()

    # A numbered pick resolves to the option and lands in the answer file.
    res = client.post("/api/runs/01TESTRUN/decision", json={"choice": "2"})
    assert res.json() == {"ok": True, "choice": "b"}
    assert json.loads(answer_path(run_dir).read_text(encoding="utf-8")) == {
        "choice": "b"
    }


def test_ws_live_unknown_run_closes(tmp_path: Path) -> None:
    client = TestClient(create_app(runs_root=tmp_path))
    with client.websocket_connect("/ws/live/NOPE") as ws:
        # Server closes with the application close code for "not found".
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4004
