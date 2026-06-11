"""``agentiq compare`` — show two runs' decisions, outcomes, and cost side by side."""

from __future__ import annotations

import argparse
import sys

from agentiq.core.exit_codes import ExitCode
from agentiq.core.run import find_run_dir
from agentiq.events.reader import read_events
from agentiq.replay.compare import RunComparison, facts, render_comparison


def compare_command(args: argparse.Namespace) -> int:
    """Compare two runs by id (FR30)."""
    runs_root = getattr(args, "runs_root", None)
    dir_a = find_run_dir(args.run_a, runs_root)
    dir_b = find_run_dir(args.run_b, runs_root)
    if dir_a is None or dir_b is None:
        missing = args.run_a if dir_a is None else args.run_b
        print(f"no run found with id {missing!r}", file=sys.stderr)
        return ExitCode.FAILED

    fa = facts(read_events(dir_a / "events.jsonl"))
    fb = facts(read_events(dir_b / "events.jsonl"))
    print(render_comparison(RunComparison(fa, fb)))
    return ExitCode.SUCCESS
