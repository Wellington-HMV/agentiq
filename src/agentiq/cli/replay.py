"""``agentiq replay`` — replay a past run as a plain timeline or the spatial scene."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentiq.core.exit_codes import ExitCode
from agentiq.core.run import find_run_dir
from agentiq.events.reader import read_events
from agentiq.replay.timeline import iter_timeline_lines


def _print_timeline(events_path: Path) -> int:
    for line in iter_timeline_lines(read_events(events_path)):
        print(line)
    return ExitCode.SUCCESS


def _launch_scene(
    events_path: Path, run_id: str, *, ascii_only: bool, reduced_motion: bool
) -> int:
    # Imported lazily so piping/headless never pays the Textual import.
    from agentiq.replay.transport import ReplayController
    from agentiq.tui.app import WcsApp

    controller = ReplayController(list(read_events(events_path)))
    WcsApp(
        controller=controller,
        app_title=f"replay {run_id}",
        ascii_only=ascii_only,
        reduced_motion=reduced_motion,
    ).run()
    return ExitCode.SUCCESS


def replay_command(args: argparse.Namespace) -> int:
    """Replay a run: spatial scene in a TTY, plain timeline otherwise (NFR7)."""
    runs_root = getattr(args, "runs_root", None)
    run_dir = find_run_dir(args.run_id, runs_root)
    if run_dir is None:
        print(f"no run found with id {args.run_id!r}", file=sys.stderr)
        return ExitCode.FAILED

    events_path = run_dir / "events.jsonl"

    if getattr(args, "web", False):
        from agentiq.cli.web import serve_web

        return serve_web(run_id=args.run_id)

    if getattr(args, "scene", False):
        from agentiq.tui.capabilities import from_environment

        caps = from_environment(
            ascii_only=getattr(args, "ascii", False),
            reduced_motion=getattr(args, "no_anim", False),
        )
        if sys.stdout.isatty() and caps.representation != "minimal":
            return _launch_scene(
                events_path,
                args.run_id,
                ascii_only=caps.ascii_only,
                reduced_motion=caps.reduced_motion,
            )
        reason = "terminal too small" if sys.stdout.isatty() else "scene needs a TTY"
        print(f"{reason}; showing the plain timeline instead.", file=sys.stderr)

    return _print_timeline(events_path)
