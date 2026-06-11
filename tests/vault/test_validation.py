"""Tests for vault fail-fast validation (story 3.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.vault.harness import HarnessVaultProvider
from agentiq.vault.provider import VaultError

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "vault"


def _make_vault(tmp_path: Path, manifest: str) -> Path:
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "manifest.toml").write_text(manifest, encoding="utf-8")
    (tmp_path / "notes").mkdir()
    return tmp_path


_MANIFEST = 'schema_version = 1\ninclude = ["notes/**/*.md"]\n'


def test_invalid_frontmatter_names_the_note(tmp_path: Path) -> None:
    v = _make_vault(tmp_path, _MANIFEST)
    # Unbalanced/invalid YAML in the frontmatter block.
    (v / "notes" / "bad.md").write_text(
        "---\ntitle: [unclosed\n---\nbody", encoding="utf-8"
    )
    with pytest.raises(VaultError, match=r"invalid YAML frontmatter in notes/bad\.md"):
        HarnessVaultProvider(v).validate()


def test_duplicate_entry_id(tmp_path: Path) -> None:
    v = _make_vault(tmp_path, _MANIFEST)
    (v / "notes" / "a.md").write_text("---\nid: dup\n---\nA", encoding="utf-8")
    (v / "notes" / "b.md").write_text("---\nid: dup\n---\nB", encoding="utf-8")
    with pytest.raises(VaultError, match="duplicate entry id 'dup'"):
        HarnessVaultProvider(v).validate()


def test_unsupported_schema_version(tmp_path: Path) -> None:
    v = _make_vault(tmp_path, 'schema_version = 2\ninclude = ["notes/**/*.md"]\n')
    with pytest.raises(VaultError, match="unsupported vault schema_version"):
        HarnessVaultProvider(v).validate()


def test_conformant_fixture_validates() -> None:
    HarnessVaultProvider(_FIXTURE).validate()  # no raise
