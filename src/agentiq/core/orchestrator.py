"""Headless orchestration loop.

Turns a goal into a logged, deterministic run: open the run, optionally validate a
knowledge vault, spawn the parent, let a strategy decompose and delegate (reading
vault context + verifying results when a vault is present), then close with a
terminal event. The strategy is a seam — the shipped ``DeterministicStrategy``
runs with no network; a real Claude-SDK-backed strategy plugs into the same
``OrchestrationStrategy`` protocol later without touching the loop/log/replay.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from agentiq.agent.adapter import AgentAdapter
from agentiq.agent.vault_access import VaultReader
from agentiq.core.decision import DefaultResolver, Resolver
from agentiq.core.isolation import make_isolation
from agentiq.core.run import Run, start_run
from agentiq.events.bus import EventBus
from agentiq.replay.summary import write_summary
from agentiq.vault.provider import VaultError, VaultProvider

PARENT_ID = "parent"


class OrchestrationStrategy(Protocol):
    """Decides how a goal is decomposed and delegated, driving the adapter."""

    async def run(
        self,
        goal: str,
        project: Path,
        adapter: AgentAdapter,
        vault: VaultReader | None = None,
        resolver: Resolver | None = None,
    ) -> str:
        """Execute the goal; return the terminal status (e.g. "completed").

        ``resolver`` settles human-in-the-loop decisions (FR22/FR26); a strategy
        that makes no decisions ignores it.
        """
        ...


class DeterministicStrategy:
    """No-network default: a fixed subtask pipeline. Deterministic per goal."""

    def __init__(self, subtasks: tuple[str, ...] = ("analyze", "implement", "verify")):
        self._subtasks = subtasks

    async def run(
        self,
        goal: str,
        project: Path,
        adapter: AgentAdapter,
        vault: VaultReader | None = None,
        resolver: Resolver | None = None,
    ) -> str:
        # No decisions in the deterministic path; resolver is unused here.
        # If a vault is present, pick a deterministic reference to consult.
        ref = None
        if vault is not None:
            found = vault.search()
            ref = found[0].id if found else None
        for i, subtask in enumerate(self._subtasks, start=1):
            agent_id = f"a{i}"
            adapter.spawn(agent_id, role=subtask, parent_id=PARENT_ID)
            adapter.delegate(PARENT_ID, task=f"{subtask}: {goal}", to_agent=agent_id)
            if vault is not None and ref is not None:
                # Subagent reads context; the parent verifies against the same context.
                vault.read(agent_id, ref)
                vault.read(PARENT_ID, ref)
        return "completed"


class TeamStrategy:
    """Organizes the goal into named teams that run concurrently (FR6/FR7).

    Each team gets a lead (spawned under the parent) and members (spawned under
    the lead), all tagged with the team name. Teams run as concurrent tasks; the
    synchronous, single-writer log (one ``seq`` assigned per ``write`` with no
    ``await`` mid-write) serializes their events, so interleaving never corrupts
    ordering — the recorded log stays strictly increasing and replays identically.
    """

    def __init__(self, teams: Mapping[str, tuple[str, ...]]):
        self._teams = teams

    async def run(
        self,
        goal: str,
        project: Path,
        adapter: AgentAdapter,
        vault: VaultReader | None = None,
        resolver: Resolver | None = None,
    ) -> str:
        await asyncio.gather(
            *(
                self._run_team(name, members, goal, adapter)
                for name, members in self._teams.items()
            )
        )
        return "completed"

    async def _run_team(
        self,
        name: str,
        members: tuple[str, ...],
        goal: str,
        adapter: AgentAdapter,
    ) -> None:
        lead = f"{name}-lead"
        adapter.spawn(lead, role="lead", parent_id=PARENT_ID, team=name)
        adapter.delegate(PARENT_ID, task=f"{name}: {goal}", to_agent=lead)
        for i, member in enumerate(members, start=1):
            mid = f"{name}-{i}"
            adapter.spawn(mid, role=member, parent_id=lead, team=name)
            adapter.delegate(lead, task=f"{member}: {goal}", to_agent=mid)
            await asyncio.sleep(0)  # yield so teams genuinely interleave


async def run_orchestration(
    goal: str,
    project: str | Path,
    *,
    strategy: OrchestrationStrategy,
    vault: VaultProvider | None = None,
    runs_root: str | Path | None = None,
    run_id: str | None = None,
    bus: EventBus | None = None,
    resolver: Resolver | None = None,
    isolation_mode: str | None = None,
) -> Run:
    """Run a goal and return the finished Run (status carries outcome).

    Pass ``bus`` to share the event stream with a live subscriber (watch mode);
    headless callers omit it and a private bus is used. ``resolver`` settles
    human decisions; it defaults to ``DefaultResolver`` (default-or-fail) so
    headless runs never hang (NFR8). ``isolation_mode`` (``worktree``/
    ``serialize``) gives concurrently-writing agents isolated workspaces (FR35);
    it is exposed on the adapter for a writing strategy to use.
    """
    resolver = resolver if resolver is not None else DefaultResolver()
    bus = bus if bus is not None else EventBus()
    run = start_run(goal, project, runs_root=runs_root, run_id=run_id, bus=bus)
    isolation = (
        make_isolation(
            isolation_mode,
            project=run.project,
            worktree_base=run.root_dir / "workspaces",
        )
        if isolation_mode is not None
        else None
    )
    adapter = AgentAdapter(run.run_id, run.writer, bus, isolation=isolation)

    reader: VaultReader | None = None
    if vault is not None:
        try:
            vault.validate()  # fail fast — a malformed vault never feeds agents
        except VaultError as e:
            run.abort(f"vault invalid: {e}")
            write_summary(run.events_path, run.root_dir / "summary.json")
            return run
        reader = VaultReader(vault, adapter)

    adapter.spawn(PARENT_ID, role="parent")
    try:
        status = await strategy.run(goal, run.project, adapter, reader, resolver)
    except Exception as e:  # noqa: BLE001 - failures become a terminal event, not a crash
        run.abort(f"{type(e).__name__}: {e}")
    else:
        run.complete(status)
    # summary.json is a projection of the finished log (never written incrementally).
    write_summary(run.events_path, run.root_dir / "summary.json")
    return run


async def continue_run(
    run: Run,
    *,
    strategy: OrchestrationStrategy,
    vault: VaultProvider | None = None,
    resolver: Resolver | None = None,
    isolation_mode: str | None = None,
    bus: EventBus | None = None,
) -> Run:
    """Drive an already-open run to a terminal state (5.6 mid-flight re-exec).

    Used after ``rerun_from`` forks + seeds the last-good prefix: rather than
    merely finalizing, this re-executes the strategy on the open run so work
    actually resumes from the sane state (FR29). The run's writer continues the
    seq from the seeded prefix; the parent is assumed present in that prefix, so
    it is NOT re-spawned (avoiding a duplicate ``agent.spawned``).
    """
    resolver = resolver if resolver is not None else DefaultResolver()
    bus = bus if bus is not None else EventBus()
    isolation = (
        make_isolation(
            isolation_mode,
            project=run.project,
            worktree_base=run.root_dir / "workspaces",
        )
        if isolation_mode is not None
        else None
    )
    adapter = AgentAdapter(run.run_id, run.writer, bus, isolation=isolation)

    reader: VaultReader | None = None
    if vault is not None:
        try:
            vault.validate()
        except VaultError as e:
            run.abort(f"vault invalid: {e}")
            write_summary(run.events_path, run.root_dir / "summary.json")
            return run
        reader = VaultReader(vault, adapter)

    try:
        status = await strategy.run(run.goal, run.project, adapter, reader, resolver)
    except Exception as e:  # noqa: BLE001 - failures become a terminal event
        run.abort(f"{type(e).__name__}: {e}")
    else:
        run.complete(status)
    write_summary(run.events_path, run.root_dir / "summary.json")
    return run
