"""Tests for the ``agentiq vault`` command (story 3.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.cli.app import main

_FIXTURE = str(Path(__file__).parent.parent / "fixtures" / "vault")


def test_vault_info(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["vault", "info", _FIXTURE])
    assert rc == 0
    out = capsys.readouterr().out
    assert "test-vault" in out
    assert "api-design" in out


def test_vault_validate_ok(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["vault", "validate", _FIXTURE])
    assert rc == 0
    assert "valid" in capsys.readouterr().out


def test_vault_validate_missing_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["vault", "validate", str(tmp_path)])
    assert rc != 0
    assert "invalid" in capsys.readouterr().err
