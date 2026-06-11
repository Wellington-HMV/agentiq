"""Tests for the file-based decision bridge (browser-answered decisions)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from agentiq.core.decision import DecisionRequest
from agentiq.core.decision_bridge import (
    FileDecisionResolver,
    answer_path,
    pending_path,
    read_pending,
    write_answer,
)

REQUEST = DecisionRequest(
    agent_id="parent",
    prompt="pick a db",
    options=["postgres", "sqlite"],
    default="postgres",
)


async def test_resolver_publishes_pending_and_awaits_answer(tmp_path: Path) -> None:
    resolver = FileDecisionResolver(tmp_path, poll_seconds=0.02)
    task = asyncio.create_task(resolver.resolve(REQUEST))

    # The request becomes visible to other processes as a file.
    for _ in range(100):
        if read_pending(tmp_path) is not None:
            break
        await asyncio.sleep(0.01)
    pending = read_pending(tmp_path)
    assert pending is not None
    assert pending["prompt"] == "pick a db"
    assert pending["options"] == ["postgres", "sqlite"]

    # Another process answers (by option text), the awaitable resolves human.
    write_answer(tmp_path, "sqlite")
    choice, resolved_by = await asyncio.wait_for(task, timeout=2)
    assert (choice, resolved_by) == ("sqlite", "human")

    # Both bridge files are cleaned up.
    assert not pending_path(tmp_path).exists()
    assert not answer_path(tmp_path).exists()


async def test_resolver_accepts_number_and_empty_as_default(tmp_path: Path) -> None:
    resolver = FileDecisionResolver(tmp_path, poll_seconds=0.02)
    task = asyncio.create_task(resolver.resolve(REQUEST))
    await asyncio.sleep(0.05)
    write_answer(tmp_path, "")  # empty = accept default
    choice, _ = await asyncio.wait_for(task, timeout=2)
    assert choice == "postgres"


async def test_resolver_discards_invalid_answer_and_keeps_waiting(
    tmp_path: Path,
) -> None:
    resolver = FileDecisionResolver(tmp_path, poll_seconds=0.02)
    task = asyncio.create_task(resolver.resolve(REQUEST))
    await asyncio.sleep(0.05)

    write_answer(tmp_path, "not-an-option")
    await asyncio.sleep(0.1)
    assert not task.done()  # bad answer ignored, still pending
    assert read_pending(tmp_path) is not None

    write_answer(tmp_path, "2")  # numbered pick, like the keyboard shortcut
    choice, _ = await asyncio.wait_for(task, timeout=2)
    assert choice == "sqlite"


async def test_stale_answer_from_before_is_never_accepted(tmp_path: Path) -> None:
    # An answer file left over from a previous decision must not leak in.
    answer_path(tmp_path).write_text(json.dumps({"choice": "sqlite"}), encoding="utf-8")
    resolver = FileDecisionResolver(tmp_path, poll_seconds=0.02)
    task = asyncio.create_task(resolver.resolve(REQUEST))
    await asyncio.sleep(0.1)
    assert not task.done()  # the stale file was wiped before waiting
    write_answer(tmp_path, "postgres")
    choice, _ = await asyncio.wait_for(task, timeout=2)
    assert choice == "postgres"
