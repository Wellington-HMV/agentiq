"""Per-agent workspace isolation (story 5.5 / FR35).

Two modes tune how concurrently-writing agents share the project tree:

- ``worktree``: each agent gets its own workspace. When the project is a git repo
  this is a real ``git worktree`` (``GitWorktreeIsolation``); otherwise a plain
  per-agent directory (``WorktreeIsolation``). Agents write in parallel with no
  clobbering; ``merge_into`` folds each worktree's changes back into the project,
  reporting overlapping paths instead of silently overwriting.
- ``serialize``: all agents share the one workspace, guarded by a lock, so
  concurrent writers run one-at-a-time (no parallel speed-up, but no conflicts).

``make_isolation`` picks the backing automatically. The deeper follow-on is a full
3-way ``git merge`` on ``merge_into`` (today it copies changed + untracked files).
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path
from typing import Protocol


class Isolation(Protocol):
    """Hands each agent a workspace; ``concurrent`` says if writers run parallel."""

    concurrent: bool

    def workspace(self, agent_id: str) -> AbstractAsyncContextManager[Path]:
        """Async context manager yielding the agent's workspace path."""
        ...

    def merge_into(self, dest: str | Path) -> list[str]:
        """Fold workspaces into ``dest``; return overlapping (clobbered) relpaths."""
        ...


class WorktreeIsolation:
    """Per-agent directories that write in parallel, then merge (FR35)."""

    concurrent = True

    def __init__(self, base: str | Path) -> None:
        self._base = Path(base)
        self._base.mkdir(parents=True, exist_ok=True)
        self._dirs: dict[str, Path] = {}

    @asynccontextmanager
    async def workspace(self, agent_id: str) -> AsyncIterator[Path]:
        d = self._base / agent_id
        d.mkdir(parents=True, exist_ok=True)
        self._dirs[agent_id] = d
        yield d  # retained after exit so merge_into can collect it

    def merge_into(self, dest: str | Path) -> list[str]:
        dest_dir = Path(dest)
        dest_dir.mkdir(parents=True, exist_ok=True)
        written: set[str] = set()
        conflicts: list[str] = []
        for agent_id in sorted(self._dirs):
            d = self._dirs[agent_id]
            for f in sorted(d.rglob("*")):
                if not f.is_file():
                    continue
                rel = f.relative_to(d).as_posix()
                if rel in written:
                    conflicts.append(rel)  # two agents wrote the same path
                written.add(rel)
                target = dest_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)
        return conflicts


class SerializeIsolation:
    """One shared workspace behind a lock — concurrent writers are serialized."""

    concurrent = False

    def __init__(self, workspace: str | Path) -> None:
        self._ws = Path(workspace)
        self._ws.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def workspace(self, agent_id: str) -> AsyncIterator[Path]:
        async with self._lock:  # only one writer inside at a time
            yield self._ws

    def merge_into(self, dest: str | Path) -> list[str]:
        return []  # writers already shared the destination workspace


def _is_git_repo(path: str | Path) -> bool:
    """True if ``path`` is inside a git work tree (and git is available)."""
    try:
        r = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0 and r.stdout.strip() == "true"


class GitWorktreeIsolation:
    """Real ``git worktree`` per agent (5.5 follow-on).

    Each agent gets its own linked worktree detached at HEAD, so agents edit in
    parallel with no contention on the shared index/working tree. ``merge_into``
    copies each worktree's changed + untracked files back into the destination,
    reporting overlaps (a full 3-way ``git merge`` is the deeper follow-on).
    ``cleanup`` removes the worktrees. Falls back to a plain directory if a
    ``git worktree add`` fails.
    """

    concurrent = True

    def __init__(self, repo_root: str | Path, base: str | Path) -> None:
        self._repo = Path(repo_root)
        self._base = Path(base)
        self._base.mkdir(parents=True, exist_ok=True)
        self._dirs: dict[str, Path] = {}

    @asynccontextmanager
    async def workspace(self, agent_id: str) -> AsyncIterator[Path]:
        d = self._base / agent_id
        if agent_id not in self._dirs:
            cmd = ["git", "-C", str(self._repo), "worktree", "add", "--detach", str(d)]
            try:
                # Run the blocking git call off the event loop.
                await asyncio.to_thread(
                    subprocess.run, cmd, check=True, capture_output=True, text=True
                )
            except (OSError, subprocess.CalledProcessError):
                d.mkdir(parents=True, exist_ok=True)  # fallback: plain dir
            self._dirs[agent_id] = d
        yield self._dirs[agent_id]

    def _changed_files(self, worktree: Path) -> list[str]:
        rels: set[str] = set()
        for args in (
            ["diff", "--name-only", "HEAD"],
            ["ls-files", "--others", "--exclude-standard"],
        ):
            try:
                out = subprocess.run(
                    ["git", "-C", str(worktree), *args],
                    capture_output=True,
                    text=True,
                ).stdout
            except (OSError, subprocess.SubprocessError):
                continue
            rels.update(line for line in out.splitlines() if line)
        return sorted(rels)

    def merge_into(self, dest: str | Path) -> list[str]:
        dest_dir = Path(dest)
        dest_dir.mkdir(parents=True, exist_ok=True)
        written: set[str] = set()
        conflicts: list[str] = []
        for agent_id in sorted(self._dirs):
            wt = self._dirs[agent_id]
            for rel in self._changed_files(wt):
                src = wt / rel
                if not src.is_file():
                    continue
                if rel in written:
                    conflicts.append(rel)
                written.add(rel)
                target = dest_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
        return conflicts

    def cleanup(self) -> None:
        for d in self._dirs.values():
            try:
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(self._repo),
                        "worktree",
                        "remove",
                        "--force",
                        str(d),
                    ],
                    capture_output=True,
                    text=True,
                )
            except (OSError, subprocess.SubprocessError):
                pass


def make_isolation(
    mode: str, *, project: str | Path, worktree_base: str | Path
) -> Isolation:
    """Build the isolation for ``mode``.

    ``worktree`` uses real ``git worktree`` checkouts when ``project`` is a git
    repo (parallel edits merged back into ``project``), else falls back to plain
    per-agent directories; ``serialize`` shares ``project`` behind a lock.
    """
    if mode == "worktree":
        if _is_git_repo(project):
            return GitWorktreeIsolation(project, worktree_base)
        return WorktreeIsolation(worktree_base)
    return SerializeIsolation(project)
