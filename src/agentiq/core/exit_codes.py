"""Deterministic CLI exit codes (NFR8).

Headless runs must end with a stable, documented exit code. BLOCKED and
BUDGET_EXCEEDED are reserved for Epic 4 (decisions / cost ceiling) so the contract
is stable now. Keep this in sync with ``docs/exit-codes.md``.
"""

from __future__ import annotations

from typing import Final


class ExitCode:
    SUCCESS: Final = 0
    FAILED: Final = 1
    USAGE: Final = 2
    BLOCKED: Final = 3  # reserved: unresolved decision (Epic 4)
    BUDGET_EXCEEDED: Final = 4  # reserved: cost ceiling hit (Epic 4)


_STATUS_MAP: dict[str, int] = {
    "completed": ExitCode.SUCCESS,
    "aborted": ExitCode.FAILED,
    "blocked": ExitCode.BLOCKED,
    "budget_exceeded": ExitCode.BUDGET_EXCEEDED,
}


def status_to_exit_code(status: str) -> int:
    """Map a terminal run status to its deterministic exit code."""
    return _STATUS_MAP.get(status, ExitCode.FAILED)
