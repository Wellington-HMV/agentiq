"""Tests for per-project configuration (story 1.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.config.settings import (
    ConfigError,
    Settings,
    apply_cli_overrides,
    find_config,
    load_config,
)

_VALID = """
[project]
path = "./app"

[vault]
paths = ["../CSharp-Senior-Vault", "../React-Native-Vault"]

[autonomy]
default = "deny"

[cost]
ceiling_usd = 12.5

[isolation]
mode = "worktree"
"""


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "agentiq.config.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_valid_config_parses_all_sections(tmp_path: Path) -> None:
    s = load_config(_write(tmp_path, _VALID))
    assert s.project.path == "./app"
    assert s.vault.paths == ["../CSharp-Senior-Vault", "../React-Native-Vault"]
    assert s.autonomy.default == "deny"
    assert s.cost.ceiling_usd == 12.5
    assert s.isolation.mode == "worktree"


def test_empty_config_uses_defaults(tmp_path: Path) -> None:
    s = load_config(_write(tmp_path, ""))
    assert s.project.path == "."
    assert s.vault.paths == []
    assert s.autonomy.default == "ask"
    assert s.cost.ceiling_usd is None
    assert s.isolation.mode == "serialize"


def test_cli_override_beats_file() -> None:
    s = Settings()
    out = apply_cli_overrides(
        s, project="/tmp/proj", cost_ceiling_usd=1.0, isolation="worktree"
    )
    assert out.project.path == "/tmp/proj"
    assert out.cost.ceiling_usd == 1.0
    assert out.isolation.mode == "worktree"
    # original is untouched (copy semantics)
    assert s.project.path == "."


def test_unknown_key_fails_fast(tmp_path: Path) -> None:
    bad = "[project]\npath = '.'\nbogus = 1\n"
    with pytest.raises(ConfigError, match="invalid config"):
        load_config(_write(tmp_path, bad))


def test_wrong_type_fails_fast(tmp_path: Path) -> None:
    bad = "[cost]\nceiling_usd = 'lots'\n"
    with pytest.raises(ConfigError, match="invalid config"):
        load_config(_write(tmp_path, bad))


def test_invalid_toml_fails_fast(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config(_write(tmp_path, "[project\npath = '.'"))


def test_directory_path_is_config_error(tmp_path: Path) -> None:
    # Reading a directory -> clean ConfigError, never a raw OSError to the user.
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_invalid_utf8_is_config_error(tmp_path: Path) -> None:
    bad = tmp_path / "agentiq.config.toml"
    bad.write_bytes(b"\xff\xfe not utf-8 \x00")
    with pytest.raises(ConfigError):
        load_config(bad)


def test_find_config(tmp_path: Path) -> None:
    assert find_config(tmp_path) is None
    _write(tmp_path, _VALID)
    found = find_config(tmp_path)
    assert found is not None and found.name == "agentiq.config.toml"
