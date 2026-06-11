"""Tests for the ``agentiq run`` command's error handling (code-review hardening)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from agentiq.cli.run import run_command


def test_run_reports_bad_config_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # A malformed config in the cwd must surface as a clean stderr message +
    # non-zero exit, never a raw ConfigError traceback to the user.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "agentiq.config.toml").write_text(
        "[project\npath = '.'", encoding="utf-8"
    )

    rc = run_command(
        argparse.Namespace(goal="g", project=None, watch=False, live=False)
    )
    assert rc != 0
    err = capsys.readouterr().err
    assert "invalid TOML" in err
    assert "Traceback" not in err
