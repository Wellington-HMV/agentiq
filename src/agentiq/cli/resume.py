"""``agentiq resume`` — reopen a paused/blocked run and bring it to a terminal state."""

from __future__ import annotations

import argparse
import sys

from agentiq.core.exit_codes import ExitCode
from agentiq.core.run import RunError, resume_run
from agentiq.replay.summary import write_summary


def resume_command(args: argparse.Namespace) -> int:
    """Resume a non-terminal run, finalize it, and re-project its summary."""
    runs_root = getattr(args, "runs_root", None)
    try:
        run = resume_run(args.run_id, runs_root=runs_root)
    except RunError as e:
        print(str(e), file=sys.stderr)
        return ExitCode.FAILED

    # MVP: reopening continues the same append-only log (seq preserved); finalize
    # the previously-open run. Full mid-flight continuation is a follow-on.
    run.complete()
    write_summary(run.events_path, run.root_dir / "summary.json")
    print(f"run {run.run_id} {run.status} ({run.root_dir})")
    return ExitCode.SUCCESS
