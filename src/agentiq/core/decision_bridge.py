"""File-based decision bridge — answer a pending decision from another process.

The run's directory is the bus (same philosophy as the JSONL log): the
orchestration-side ``FileDecisionResolver`` drops ``decision.pending.json`` in
the run dir and polls for ``decision.answer.json``; any other process (the web
server's POST endpoint, a script, even a human with an editor) writes the
answer. The resolver validates it with the same ``parse_choice`` every other
human resolver uses, emits nothing itself (``request_decision`` owns the
events), and cleans both files up.

Only one decision can be pending per run at a time — the world pauses on a
decision by design (FR26), so a single pending file is the honest model.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from agentiq.core.decision import DecisionRequest, DecisionUnresolved, parse_choice

PENDING_FILENAME = "decision.pending.json"
ANSWER_FILENAME = "decision.answer.json"


def pending_path(run_dir: str | Path) -> Path:
    return Path(run_dir) / PENDING_FILENAME


def answer_path(run_dir: str | Path) -> Path:
    return Path(run_dir) / ANSWER_FILENAME


def read_pending(run_dir: str | Path) -> dict[str, object] | None:
    """The currently pending decision in this run dir, or None."""
    path = pending_path(run_dir)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_answer(run_dir: str | Path, choice: str) -> None:
    """Drop an answer for the pending decision (validated by the resolver too)."""
    answer_path(run_dir).write_text(json.dumps({"choice": choice}), encoding="utf-8")


class FileDecisionResolver:
    """``Resolver`` that publishes the request as a file and awaits the answer.

    ``parse_choice`` validates whatever lands in the answer file ("" = default,
    a number = that option, exact option text); an invalid answer is discarded
    and the wait continues, so a typo can be corrected by answering again.
    """

    def __init__(self, run_dir: str | Path, *, poll_seconds: float = 0.3) -> None:
        self._run_dir = Path(run_dir)
        self._poll = poll_seconds

    async def resolve(self, request: DecisionRequest) -> tuple[str, str]:
        pending = pending_path(self._run_dir)
        answer = answer_path(self._run_dir)
        answer.unlink(missing_ok=True)  # never accept a stale answer
        pending.write_text(
            json.dumps(
                {
                    "agent_id": request.agent_id,
                    "prompt": request.prompt,
                    "options": list(request.options),
                    "default": request.default,
                    "kind": request.kind,
                }
            ),
            encoding="utf-8",
        )
        try:
            while True:
                if answer.is_file():
                    raw = json.loads(answer.read_text(encoding="utf-8"))
                    try:
                        choice = parse_choice(request, str(raw.get("choice", "")))
                    except DecisionUnresolved:
                        answer.unlink(missing_ok=True)  # bad answer: keep waiting
                        continue
                    return choice, "human"
                await asyncio.sleep(self._poll)
        finally:
            pending.unlink(missing_ok=True)
            answer.unlink(missing_ok=True)
