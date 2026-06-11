"""Shell completion for ``agentiq`` (story 5.7 / FR-completion).

Two pieces:

- ``complete(words, runs_root=...)`` — the pure completion engine. Given the
  tokens typed after ``agentiq`` (last token = the current partial), it returns the
  candidate completions: subcommands, per-subcommand flags, and — for commands
  that take a run id (``replay``/``resume``/``rerun``) — existing run ids from the
  store.
- ``completion_script(shell)`` — emits a bash/zsh/fish script that wires Tab to
  call ``agentiq __complete`` (a hidden subcommand), so completions stay dynamic (new
  run ids appear without reinstalling the script).

Keeping the engine pure makes it unit-testable without a real shell.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from agentiq.core.exit_codes import ExitCode
from agentiq.core.run import list_runs


@dataclass(frozen=True)
class _Spec:
    flags: list[str] = field(default_factory=list)
    run_id: bool = False  # first positional completes to an existing run id


# Mirrors the parser in ``cli/app.py``; kept in sync by a test.
SUBCOMMANDS: dict[str, _Spec] = {
    "run": _Spec(["--project", "--headless", "--watch", "--policy", "--live", "--web"]),
    "runs": _Spec(),
    "replay": _Spec(
        ["--timeline", "--scene", "--ascii", "--no-anim", "--web"], run_id=True
    ),
    "vault": _Spec(),
    "resume": _Spec(run_id=True),
    "rerun": _Spec(["--at-seq"], run_id=True),
    "compare": _Spec(run_id=True),
    "completion": _Spec(),
    "config": _Spec(),
    "web": _Spec(["--port", "--no-browser"]),
}

SHELLS = ("bash", "zsh", "fish")


def _positional_filled(words: list[str]) -> bool:
    """True if a positional arg was already given before the current partial."""
    return any(not t.startswith("-") for t in words[1:-1])


def complete(words: list[str], *, runs_root: str | Path | None = None) -> list[str]:
    """Return completion candidates for the tokens typed after ``agentiq``.

    ``words`` is the argument list; its last element is the current partial token
    ("" right after a space). Earlier elements are already-typed tokens.
    """
    if len(words) <= 1:
        prefix = words[0] if words else ""
        return [c for c in sorted(SUBCOMMANDS) if c.startswith(prefix)]

    spec = SUBCOMMANDS.get(words[0])
    if spec is None:
        return []
    partial = words[-1]
    if partial.startswith("-"):
        return [f for f in spec.flags if f.startswith(partial)]
    if spec.run_id and not _positional_filled(words):
        ids = [r.run_id for r in list_runs(runs_root)]
        return [i for i in ids if i.startswith(partial)]
    return [f for f in spec.flags if f.startswith(partial)]


_BASH = """\
# agentiq bash completion — source this or drop it in your bash completion dir.
_agentiq_complete() {
    local cur words
    cur="${COMP_WORDS[COMP_CWORD]}"
    words=("${COMP_WORDS[@]:1}")
    local IFS=$'\\n'
    COMPREPLY=( $(agentiq __complete "${words[@]}") )
}
complete -F _agentiq_complete agentiq
"""

_ZSH = """\
#compdef agentiq
# agentiq zsh completion — put this on your $fpath as _agentiq.
_agentiq() {
    local -a candidates
    candidates=("${(@f)$(agentiq __complete ${words[2,$CURRENT]})}")
    compadd -- $candidates
}
_agentiq "$@"
"""

_FISH = """\
# agentiq fish completion — source this or drop it in
# ~/.config/fish/completions/agentiq.fish
complete -c agentiq -f \\
    -a '(agentiq __complete (commandline -opc)[2..-1] (commandline -ct))'
"""

_SCRIPTS = {"bash": _BASH, "zsh": _ZSH, "fish": _FISH}


def completion_script(shell: str) -> str:
    """Return the completion script for ``shell`` (bash/zsh/fish)."""
    try:
        return _SCRIPTS[shell]
    except KeyError:
        raise ValueError(f"unsupported shell: {shell!r} (choose {SHELLS})") from None


# --- CLI command handlers ---------------------------------------------------


def completion_command(args: argparse.Namespace) -> int:
    """``agentiq completion <shell>`` — print the shell completion script."""
    try:
        sys.stdout.write(completion_script(args.shell))
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return ExitCode.FAILED
    return ExitCode.SUCCESS


def complete_command(args: argparse.Namespace) -> int:
    """``agentiq __complete <words...>`` — print candidates (one per line)."""
    words = list(getattr(args, "words", None) or [])
    for candidate in complete(words):
        print(candidate)
    return ExitCode.SUCCESS
