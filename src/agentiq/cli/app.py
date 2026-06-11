"""``agentiq`` command-line entrypoint.

``--version``/``--help`` and ``agentiq run`` (story 1.7, headless) are functional.
The remaining subcommands (replay/runs/vault/config/resume) are registered so the
command surface is discoverable, but are stubs implemented in their own later
stories. Nothing here assumes a TTY.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from agentiq import __version__
from agentiq.cli.compare import compare_command
from agentiq.cli.completion import (
    SHELLS,
    complete_command,
    completion_command,
)
from agentiq.cli.replay import replay_command
from agentiq.cli.rerun import rerun_command
from agentiq.cli.resume import resume_command
from agentiq.cli.run import run_command
from agentiq.cli.runs import runs_command
from agentiq.cli.vault import vault_command
from agentiq.cli.web import DEFAULT_PORT, web_command

# Exit code 64 == EX_USAGE-style "command not yet implemented".
_NOT_IMPLEMENTED = 64

_STUB_SUBCOMMANDS = ("config",)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser for ``agentiq``."""
    parser = argparse.ArgumentParser(
        prog="agentiq",
        description=(
            "agentiq: orchestrate Claude multi-agent work with a legible, "
            "replayable spatial scene."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"agentiq {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    run_p = subparsers.add_parser("run", help="start a headless orchestration run")
    run_p.add_argument("goal", help="the goal to hand off to the agents")
    run_p.add_argument("--project", default=None, help="project directory (default: .)")
    run_p.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="run unattended (default)",
    )
    run_p.add_argument(
        "--watch", action="store_true", help="open the live animated scene (TTY)"
    )
    run_p.add_argument("--policy", default=None, help="autonomy policy file (unused)")
    run_p.add_argument(
        "--live",
        action="store_true",
        help="drive real Claude agents (needs ANTHROPIC_API_KEY)",
    )
    run_p.add_argument(
        "--web",
        action="store_true",
        help="open the browser factory view and answer decisions there",
    )

    subparsers.add_parser("runs", help="list past runs (newest first)")

    replay_p = subparsers.add_parser("replay", help="replay a past run")
    replay_p.add_argument("run_id", help="the run id to replay")
    replay_p.add_argument(
        "--timeline", action="store_true", default=True, help="plain timeline (default)"
    )
    replay_p.add_argument(
        "--scene", action="store_true", help="spatial scene (TTY; else timeline)"
    )
    replay_p.add_argument(
        "--ascii", action="store_true", help="force ASCII glyphs (no wide Unicode)"
    )
    replay_p.add_argument(
        "--no-anim", action="store_true", help="reduced motion (no auto-play timer)"
    )
    replay_p.add_argument(
        "--web", action="store_true", help="open the browser factory view"
    )

    vault_p = subparsers.add_parser("vault", help="validate or inspect a vault")
    vault_p.add_argument("vault_action", choices=["validate", "info"])
    vault_p.add_argument("path", help="path to the harness vault")

    resume_p = subparsers.add_parser("resume", help="resume a paused/blocked run")
    resume_p.add_argument("run_id", help="the run id to resume")

    rerun_p = subparsers.add_parser(
        "rerun", help="re-run a failed run from its last-good state"
    )
    rerun_p.add_argument("run_id", help="the failed run id to re-run")
    rerun_p.add_argument(
        "--at-seq",
        type=int,
        default=None,
        dest="at_seq",
        help="pin the checkpoint to this prior seq (default: before the failure)",
    )
    rerun_p.add_argument(
        "--continue",
        action="store_true",
        dest="continue_",
        help="re-execute from the checkpoint instead of just finalizing",
    )

    compare_p = subparsers.add_parser(
        "compare", help="compare two runs (decisions, outcomes, cost) side by side"
    )
    compare_p.add_argument("run_a", help="first run id")
    compare_p.add_argument("run_b", help="second run id")

    web_p = subparsers.add_parser(
        "web", help="serve the browser factory view (replay any run)"
    )
    web_p.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help=f"port (default {DEFAULT_PORT})"
    )
    web_p.add_argument(
        "--no-browser", action="store_true", help="don't auto-open the browser"
    )

    completion_p = subparsers.add_parser(
        "completion", help="print a shell completion script (bash/zsh/fish)"
    )
    completion_p.add_argument("shell", choices=list(SHELLS), help="target shell")

    # Hidden dynamic-completion callback invoked by the generated scripts.
    complete_p = subparsers.add_parser("__complete", help=argparse.SUPPRESS)
    complete_p.add_argument("words", nargs=argparse.REMAINDER)

    for name in _STUB_SUBCOMMANDS:
        subparsers.add_parser(name, help=f"{name} (not yet implemented)")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns a process exit code; never assumes a TTY."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        # No subcommand: show usage on stderr, exit non-zero (nothing to do).
        parser.print_help(sys.stderr)
        return _NOT_IMPLEMENTED

    if args.command == "run":
        return run_command(args)
    if args.command == "runs":
        return runs_command(args)
    if args.command == "replay":
        return replay_command(args)
    if args.command == "vault":
        return vault_command(args)
    if args.command == "resume":
        return resume_command(args)
    if args.command == "rerun":
        return rerun_command(args)
    if args.command == "compare":
        return compare_command(args)
    if args.command == "web":
        return web_command(args)
    if args.command == "completion":
        return completion_command(args)
    if args.command == "__complete":
        return complete_command(args)

    print(f"`agentiq {args.command}` is not implemented yet.", file=sys.stderr)
    return _NOT_IMPLEMENTED


if __name__ == "__main__":
    raise SystemExit(main())
