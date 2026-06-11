"""Run store and lifecycle.

A run is persisted as a directory ``<runs_root>/<ulid>/`` holding the append-only
``events.jsonl`` (story 1.2) and a small mutable ``meta.json``. The event log is
the authoritative record; ``meta.json`` is convenience metadata. A run's life is
bounded by a ``run.started`` event and a terminal ``run.completed`` or
``run.aborted`` event. ``summary.json`` is intentionally NOT written here — it is
projected from events in story 1.8.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

from agentiq.core.ids import new_ulid
from agentiq.events.bus import EventBus
from agentiq.events.reader import read_events
from agentiq.events.writer import JsonlEventWriter


def default_runs_root() -> Path:
    """The default run store root: ``~/.agentiq/runs``."""
    return Path.home() / ".agentiq" / "runs"


def legacy_runs_root() -> Path:
    """The pre-rebrand run store root, still readable: ``~/.well-corp-sw/runs``."""
    return Path.home() / ".well-corp-sw" / "runs"


def _search_roots(runs_root: str | Path | None) -> list[Path]:
    # An explicit root is authoritative; the default search also covers the
    # legacy store so old runs stay replayable after the rebrand.
    if runs_root is not None:
        return [Path(runs_root)]
    return [default_runs_root(), legacy_runs_root()]


def find_run_dir(run_id: str, runs_root: str | Path | None = None) -> Path | None:
    """Return the run's directory if it holds an event log, else None."""
    for root in _search_roots(runs_root):
        candidate = root / run_id
        if (candidate / "events.jsonl").is_file():
            return candidate
    return None


@dataclass
class RunInfo:
    """A run store listing entry (from meta.json + optional summary.json)."""

    run_id: str
    goal: str
    status: str
    cost_usd: float | None = None
    duration_seconds: float | None = None


def list_runs(runs_root: str | Path | None = None) -> list[RunInfo]:
    """List runs in the store, newest first (ULIDs sort chronologically)."""
    infos: list[RunInfo] = []
    seen: set[str] = set()
    for root in _search_roots(runs_root):
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if child.name in seen:
                continue
            meta_path = child / "meta.json"
            if not meta_path.is_file():
                continue
            seen.add(child.name)
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            cost: float | None = None
            duration: float | None = None
            summary_path = child / "summary.json"
            if summary_path.is_file():
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                cost = summary.get("cost_usd")
                duration = summary.get("duration_seconds")
            infos.append(
                RunInfo(
                    run_id=meta["run_id"],
                    goal=meta["goal"],
                    status=meta["status"],
                    cost_usd=cost,
                    duration_seconds=duration,
                )
            )
    infos.sort(key=lambda r: r.run_id, reverse=True)
    return infos


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class Run:
    """A single orchestration run: its directory, log writer, and lifecycle."""

    def __init__(
        self,
        run_id: str,
        goal: str,
        project: Path,
        root_dir: Path,
        writer: JsonlEventWriter,
        bus: EventBus | None = None,
    ) -> None:
        self.run_id = run_id
        self.goal = goal
        self.project = project
        self.root_dir = root_dir
        self.events_path = root_dir / "events.jsonl"
        self.meta_path = root_dir / "meta.json"
        self.status = "running"
        self.created_ts = _utc_now_iso()
        self._writer = writer
        self._bus = bus
        self._closed = False

    @property
    def writer(self) -> JsonlEventWriter:
        """The run's event-log writer (shared so seq stays continuous)."""
        return self._writer

    def emit(self, type: str, payload: dict[str, object]) -> None:
        """Write a lifecycle event to the log and (if present) the live bus."""
        event = self._writer.write(type, payload, run_id=self.run_id)
        if self._bus is not None:
            self._bus.publish(event)

    # --- metadata -----------------------------------------------------------
    def _write_meta(self) -> None:
        meta = {
            "run_id": self.run_id,
            "goal": self.goal,
            "project": str(self.project),
            "status": self.status,
            "created_ts": self.created_ts,
        }
        self.meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # --- lifecycle ----------------------------------------------------------
    def complete(self, status: str = "completed") -> None:
        """Emit ``run.completed`` and close the run."""
        if self._closed:
            return
        self.emit("run.completed", {"status": status})
        self.status = status
        self._write_meta()
        self._writer.close()
        self._closed = True

    def abort(self, reason: str) -> None:
        """Emit ``run.aborted`` and close the run."""
        if self._closed:
            return
        self.emit("run.aborted", {"reason": reason})
        self.status = "aborted"
        self._write_meta()
        self._writer.close()
        self._closed = True

    def __enter__(self) -> Run:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc is not None:
            self.abort(f"{exc_type.__name__ if exc_type else 'error'}: {exc}")
        else:
            self.complete()


def start_run(
    goal: str,
    project: str | Path,
    *,
    runs_root: str | Path | None = None,
    run_id: str | None = None,
    bus: EventBus | None = None,
) -> Run:
    """Create a run directory, open its log, and emit ``run.started``."""
    root = Path(runs_root) if runs_root is not None else default_runs_root()
    rid = run_id or new_ulid()
    root_dir = root / rid
    root_dir.mkdir(parents=True, exist_ok=True)

    resolved_project = Path(project).resolve()
    writer = JsonlEventWriter(root_dir / "events.jsonl")
    run = Run(rid, goal, resolved_project, root_dir, writer, bus=bus)
    run._write_meta()
    run.emit("run.started", {"goal": goal, "project": str(resolved_project)})
    return run


class RunError(Exception):
    """Raised when a run cannot be resumed (missing or already finished)."""


_TERMINAL = {"completed", "aborted"}


def resume_run(run_id: str, *, runs_root: str | Path | None = None) -> Run:
    """Reopen a non-terminal run's log (seq continues) for continuation (FR28)."""
    root_dir = find_run_dir(run_id, runs_root)
    if root_dir is None:
        raise RunError(f"no run found with id {run_id!r}")
    meta = json.loads((root_dir / "meta.json").read_text(encoding="utf-8"))
    status = meta.get("status")
    if status in _TERMINAL:
        raise RunError(f"run {run_id} already finished ({status})")

    events_path = root_dir / "events.jsonl"
    if events_path.stat().st_size == 0:
        # Empty log but a non-terminal meta = a run that crashed before run.started.
        # Resuming would assign seq 0 to the wrong event type; refuse.
        raise RunError(f"run {run_id} has an empty log; nothing to resume")
    writer = JsonlEventWriter(events_path)  # resumes seq from the log
    run = Run(
        run_id,
        meta.get("goal", ""),
        Path(meta.get("project", ".")),
        root_dir,
        writer,
    )
    run.status = "running"
    return run


# events that mark where a run went wrong (the cut point for a sane re-run)
_FAILURE_TYPES = {"agent.failed", "run.aborted"}


def rerun_from(
    run_id: str,
    *,
    at_seq: int | None = None,
    runs_root: str | Path | None = None,
    new_run_id: str | None = None,
) -> Run:
    """Fork a NEW run seeded with the source's last-good prefix (FR29).

    The continuation starts from the last sane state, not seq 0: the new run's log
    replays the prior good events (re-stamped under the new id, seq preserved) and
    its writer continues right after the checkpoint. By default the cut is just
    before the first ``agent.failed``/``run.aborted``; pass ``at_seq`` to pin the
    checkpoint to an explicit prior seq. The source run is left untouched.
    """
    src_dir = find_run_dir(run_id, runs_root)
    if src_dir is None:
        raise RunError(f"no run found with id {run_id!r}")
    events = list(read_events(src_dir / "events.jsonl"))

    if at_seq is not None:
        prefix = [e for e in events if e.seq <= at_seq]
    else:
        cut = next((i for i, e in enumerate(events) if e.type in _FAILURE_TYPES), None)
        if cut is None:
            raise RunError(f"run {run_id} has no failure to re-run from; pass at_seq")
        prefix = events[:cut]
    if not prefix:
        raise RunError(f"no sane prior state to re-run from for {run_id}")

    meta = json.loads((src_dir / "meta.json").read_text(encoding="utf-8"))
    root = Path(runs_root) if runs_root is not None else default_runs_root()
    rid = new_run_id or new_ulid()
    root_dir = root / rid
    root_dir.mkdir(parents=True, exist_ok=True)

    writer = JsonlEventWriter(root_dir / "events.jsonl")
    for e in prefix:  # seed the sane prefix; writer re-assigns seq 0..k contiguously
        writer.write(e.type, e.payload, run_id=rid, agent_id=e.agent_id, ts=e.ts)

    run = Run(
        rid,
        meta.get("goal", ""),
        Path(meta.get("project", ".")),
        root_dir,
        writer,
    )
    run.status = "running"
    run._write_meta()
    return run
