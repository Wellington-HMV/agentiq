"""Tests for the harness vault provider (story 3.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentiq.vault.harness import HarnessVaultProvider
from agentiq.vault.provider import VaultError

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "vault"


def _provider() -> HarnessVaultProvider:
    return HarnessVaultProvider(_FIXTURE)


def test_load_builds_index_with_frontmatter_and_fallback_id() -> None:
    entries = {e.id: e for e in _provider().entries()}
    # frontmatter id used
    assert "api-design" in entries
    assert entries["api-design"].title == "API Design"
    assert entries["api-design"].tags == ("api", "rest")
    # no-frontmatter note falls back to its relative path as id
    assert "notes/auth.md" in entries
    assert entries["notes/auth.md"].type == "doc"


def test_read_by_id_and_relpath() -> None:
    p = _provider()
    doc = p.read("api-design")
    assert "API Design" in doc.body
    doc2 = p.read("notes/auth.md")
    assert "Auth" in doc2.body


def test_read_unknown_ref_raises() -> None:
    with pytest.raises(VaultError, match="no vault entry"):
        _provider().read("does-not-exist")


def test_search_by_tag_and_query() -> None:
    p = _provider()
    assert [e.id for e in p.search(tags=["api"])] == ["api-design"]
    assert [e.id for e in p.search(query="auth")] == ["notes/auth.md"]


def test_validate_resolves_wikilinks() -> None:
    # [[auth]] resolves to the auth.md filename stem.
    _provider().validate()  # no raise


def test_metadata() -> None:
    meta = _provider().metadata()
    assert meta["name"] == "test-vault"
    assert meta["schema_version"] == 1
    assert meta["entry_count"] == 2


def test_missing_manifest_raises(tmp_path: Path) -> None:
    with pytest.raises(VaultError, match="not a harness vault"):
        HarnessVaultProvider(tmp_path).validate()


def test_unresolved_wikilink_raises(tmp_path: Path) -> None:
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "manifest.toml").write_text(
        'schema_version = 1\ninclude = ["notes/**/*.md"]\n', encoding="utf-8"
    )
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "a.md").write_text("links [[ghost]]", encoding="utf-8")
    with pytest.raises(VaultError, match="unresolved wikilink"):
        HarnessVaultProvider(tmp_path).validate()


def test_non_list_tags_raises_vault_error(tmp_path: Path) -> None:
    # A scalar (non-string) `tags` must fail with VaultError, not a raw TypeError.
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "manifest.toml").write_text(
        'schema_version = 1\ninclude = ["notes/**/*.md"]\n', encoding="utf-8"
    )
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "a.md").write_text(
        "---\nid: a\ntags: 123\n---\nbody", encoding="utf-8"
    )
    with pytest.raises(VaultError, match="invalid 'tags'"):
        HarnessVaultProvider(tmp_path).validate()
