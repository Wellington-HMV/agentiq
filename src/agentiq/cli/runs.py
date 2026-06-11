"""``agentiq runs`` — list past runs from the run store."""

from __future__ import annotations

import argparse

from agentiq.core.run import RunInfo, list_runs

_EMPTY_HINT = 'No runs yet. Start one with:  agentiq run "<goal>" --project <path>'


def _fmt_cost(cost: float | None) -> str:
    return f"${cost:.2f}" if cost is not None else "-"


def _fmt_duration(seconds: float | None) -> str:
    return f"{seconds:.1f}s" if seconds is not None else "-"


def _format_row(info: RunInfo) -> str:
    return (
        f"{info.run_id}  {info.status:<10}  "
        f"{_fmt_cost(info.cost_usd):>8}  {_fmt_duration(info.duration_seconds):>8}  "
        f"{info.goal}"
    )


def runs_command(args: argparse.Namespace) -> int:
    """List past runs newest-first; print a hint when there are none."""
    runs_root = getattr(args, "runs_root", None)
    infos = list_runs(runs_root)
    if not infos:
        print(_EMPTY_HINT)
        return 0
    print(f"{'RUN ID':<26}  {'STATUS':<10}  {'COST':>8}  {'DURATION':>8}  GOAL")
    for info in infos:
        print(_format_row(info))
    return 0
