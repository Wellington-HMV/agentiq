"""Tests for per-agent workspace isolation (story 5.5 / FR35)."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest

from agentiq.core.isolation import (
    GitWorktreeIsolation,
    SerializeIsolation,
    WorktreeIsolation,
    _is_git_repo,
    make_isolation,
)
from agentiq.core.orchestrator import run_orchestration

_needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init"], repo)
    _git(["config", "user.email", "t@example.com"], repo)
    _git(["config", "user.name", "Test"], repo)
    (repo / "f.txt").write_text("hi", encoding="utf-8")
    _git(["add", "."], repo)
    _git(["commit", "-m", "init"], repo)
    return repo


async def test_worktree_allows_concurrent_writers_and_merges(tmp_path: Path) -> None:
    iso = WorktreeIsolation(tmp_path / "wt")
    active = 0
    max_active = 0

    async def work(aid: str) -> None:
        nonlocal active, max_active
        async with iso.workspace(aid) as ws:
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0)  # yield: let peers enter concurrently
            (ws / f"{aid}.txt").write_text(aid)
            active -= 1

    await asyncio.gather(*(work(f"a{i}") for i in range(3)))
    assert max_active > 1  # writers genuinely ran in parallel

    conflicts = iso.merge_into(tmp_path / "proj")
    assert conflicts == []  # disjoint files merge without clobbering
    names = sorted(p.name for p in (tmp_path / "proj").iterdir())
    assert names == ["a0.txt", "a1.txt", "a2.txt"]


async def test_worktree_merge_reports_clobbered_paths(tmp_path: Path) -> None:
    iso = WorktreeIsolation(tmp_path / "wt")
    async with iso.workspace("a") as wa:
        (wa / "shared.txt").write_text("A")
    async with iso.workspace("b") as wb:
        (wb / "shared.txt").write_text("B")
    conflicts = iso.merge_into(tmp_path / "proj")
    assert conflicts == ["shared.txt"]  # overlap surfaced, not silently lost


async def test_serialize_runs_one_writer_at_a_time(tmp_path: Path) -> None:
    iso = SerializeIsolation(tmp_path / "ws")
    active = 0
    max_active = 0
    shared: list[str] = []

    async def work(aid: str) -> None:
        nonlocal active, max_active
        async with iso.workspace(aid):
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0)
            shared.append(aid)
            active -= 1

    await asyncio.gather(*(work(f"a{i}") for i in range(5)))
    assert max_active == 1  # never two writers inside the shared workspace at once
    assert sorted(shared) == ["a0", "a1", "a2", "a3", "a4"]


def test_make_isolation_selects_mode(tmp_path: Path) -> None:
    # Non-git project -> plain directory worktrees.
    wt = make_isolation(
        "worktree", project=tmp_path / "nonrepo", worktree_base=tmp_path / "wt"
    )
    sr = make_isolation("serialize", project=tmp_path, worktree_base=tmp_path / "wt2")
    assert isinstance(wt, WorktreeIsolation) and wt.concurrent is True
    assert isinstance(sr, SerializeIsolation) and sr.concurrent is False


@_needs_git
async def test_git_worktree_isolates_and_merges_back(
    git_repo: Path, tmp_path: Path
) -> None:
    assert _is_git_repo(git_repo)
    iso = GitWorktreeIsolation(git_repo, tmp_path / "wt")
    async with iso.workspace("a1") as ws:
        assert (ws / "f.txt").exists()  # real checkout of HEAD
        (ws / "new.txt").write_text("from a1", encoding="utf-8")
    conflicts = iso.merge_into(git_repo)
    assert conflicts == []
    assert (git_repo / "new.txt").read_text(encoding="utf-8") == "from a1"  # merged
    iso.cleanup()


@_needs_git
def test_make_isolation_uses_git_for_repo(git_repo: Path, tmp_path: Path) -> None:
    iso = make_isolation("worktree", project=git_repo, worktree_base=tmp_path / "wt")
    assert isinstance(iso, GitWorktreeIsolation)


class _CaptureStrategy:
    """Records the isolation the adapter exposes."""

    def __init__(self) -> None:
        self.concurrent: bool | None = None

    async def run(
        self,
        goal: str,
        project: Path,
        adapter: object,
        vault: object | None = None,
        resolver: object | None = None,
    ) -> str:
        iso = getattr(adapter, "isolation", None)
        self.concurrent = None if iso is None else iso.concurrent
        return "completed"


async def test_run_orchestration_wires_isolation_to_adapter(tmp_path: Path) -> None:
    strat = _CaptureStrategy()
    await run_orchestration(
        "g",
        tmp_path,
        strategy=strat,
        runs_root=tmp_path / "runs",
        isolation_mode="worktree",
    )
    assert strat.concurrent is True  # adapter carries the worktree isolation

    strat2 = _CaptureStrategy()
    await run_orchestration(
        "g",
        tmp_path,
        strategy=strat2,
        runs_root=tmp_path / "runs",
        isolation_mode="serialize",
    )
    assert strat2.concurrent is False
