"""Tests for shell completion (story 5.7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.cli.app import build_parser, main
from agentiq.cli.completion import (
    SUBCOMMANDS,
    complete,
    completion_script,
)
from agentiq.core.run import start_run


def test_completes_subcommands_from_empty() -> None:
    out = complete([""])
    assert "run" in out and "replay" in out and "rerun" in out


def test_completes_subcommand_prefix() -> None:
    out = complete(["r"])
    assert out == ["rerun", "replay", "resume", "run", "runs"] or set(out) == {
        "rerun",
        "replay",
        "resume",
        "run",
        "runs",
    }


def test_completes_flags_for_subcommand() -> None:
    out = complete(["replay", "--"])
    assert "--scene" in out and "--ascii" in out
    # only flags of that subcommand, nothing from others
    assert "--watch" not in out


def test_completes_rerun_flag() -> None:
    assert complete(["rerun", "--at"]) == ["--at-seq"]


def test_completes_existing_run_ids(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    start_run("g", ".", runs_root=runs, run_id="AAA1").complete()
    start_run("g", ".", runs_root=runs, run_id="AAA2").complete()
    start_run("g", ".", runs_root=runs, run_id="BBB1").complete()
    out = complete(["replay", "AAA"], runs_root=runs)
    assert sorted(out) == ["AAA1", "AAA2"]  # prefix-filtered run ids


def test_no_run_ids_after_positional_filled(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    start_run("g", ".", runs_root=runs, run_id="AAA1").complete()
    # run id already provided -> next completes flags, not more run ids
    out = complete(["replay", "AAA1", ""], runs_root=runs)
    assert "AAA1" not in out


def test_completion_script_bash_wires_dynamic_callback() -> None:
    script = completion_script("bash")
    assert "complete -F" in script and "agentiq __complete" in script


def test_completion_script_unknown_shell_raises() -> None:
    with pytest.raises(ValueError):
        completion_script("powershell")


def test_subcommand_registry_matches_parser() -> None:
    """The completion registry must stay in sync with the real parser."""
    parser = build_parser()
    sub_action = next(
        a for a in parser._actions if hasattr(a, "choices") and a.dest == "command"
    )
    parser_subs = {c for c in (sub_action.choices or {}) if c != "__complete"}
    assert parser_subs == set(SUBCOMMANDS)


def test_completion_cli_prints_script(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["completion", "bash"])
    assert rc == 0
    assert "agentiq __complete" in capsys.readouterr().out


def test_complete_cli_prints_candidates(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["__complete", "replay", "--"])
    assert rc == 0
    out = capsys.readouterr().out.splitlines()
    assert "--scene" in out
