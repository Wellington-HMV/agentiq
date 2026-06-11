"""``agentiq rerun`` — fork a new run seeded from a failed run's last-good state."""

from __future__ import annotations

import argparse
import asyncio
import sys

from agentiq.core.exit_codes import ExitCode, status_to_exit_code
from agentiq.core.orchestrator import DeterministicStrategy, continue_run
from agentiq.core.run import RunError, rerun_from
from agentiq.replay.summary import write_summary


def rerun_command(args: argparse.Namespace) -> int:
    """Fork a sane-prefix run from a failed one (FR29).

    By default seeds the last-good prefix and finalizes. With ``--continue`` it
    re-executes the strategy on the fork (5.6 mid-flight re-exec), resuming work
    from the sane state instead of merely finalizing.
    """
    runs_root = getattr(args, "runs_root", None)
    at_seq = getattr(args, "at_seq", None)
    try:
        run = rerun_from(args.run_id, at_seq=at_seq, runs_root=runs_root)
    except RunError as e:
        print(str(e), file=sys.stderr)
        return ExitCode.FAILED

    if getattr(args, "continue_", False):
        run = asyncio.run(continue_run(run, strategy=DeterministicStrategy()))
        print(f"re-run {run.run_id} {run.status} (continued from {args.run_id})")
        return status_to_exit_code(run.status)

    # Seed the last-good prefix into a new run (seq preserved) and finalize.
    run.complete()
    write_summary(run.events_path, run.root_dir / "summary.json")
    print(f"re-run {run.run_id} {run.status} (from {args.run_id}) ({run.root_dir})")
    return ExitCode.SUCCESS
