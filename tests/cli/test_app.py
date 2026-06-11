"""Tests for the ``agentiq`` CLI entrypoint (story 1.1 scaffold)."""

from __future__ import annotations

import pytest

from agentiq import __version__
from agentiq.cli.app import main


def test_version_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """`agentiq --version` prints the version and exits 0 (AC #1)."""
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """`agentiq --help` exits 0 and shows usage (AC #1)."""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "agentiq" in capsys.readouterr().out


def test_no_command_returns_nonzero() -> None:
    """Invoking with no subcommand is a no-op that returns non-zero."""
    assert main([]) != 0


def test_subcommand_stub_returns_nonzero() -> None:
    """A registered-but-unimplemented subcommand returns the not-implemented code."""
    assert main(["config"]) != 0
