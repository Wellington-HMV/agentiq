"""HarnessVaultProvider — an Obsidian-style markdown vault + `.harness/manifest.toml`.

Loads the manifest (stdlib tomllib), globs the included notes, parses each note's
optional YAML frontmatter, and builds an in-memory id→entry index. `[[wikilinks]]`
resolve to an entry id or a note filename stem. Pure filesystem I/O — no events,
no orchestration (those arrive in stories 3.3 / 3.5).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

from agentiq.vault.provider import (
    VaultDocument,
    VaultEntry,
    VaultError,
    VaultProvider,
)

SUPPORTED_SCHEMA = 1
MANIFEST_REL = ".harness/manifest.toml"
_WIKILINK = re.compile(r"\[\[([^\]|#]+)")
_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER.match(text)
    if not match:
        return {}, text
    raw, body = match.group(1), match.group(2)
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        return {}, text
    return data, body


class HarnessVaultProvider(VaultProvider):
    """Loads and indexes a harness-standard vault directory."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._manifest: dict[str, Any] = {}
        self._entries: dict[str, VaultEntry] = {}
        self._bodies: dict[str, str] = {}
        self._stems: dict[str, str] = {}  # filename stem -> entry id
        self._loaded = False

    # --- loading ------------------------------------------------------------
    def _load(self) -> None:
        if self._loaded:
            return
        manifest_path = self.root / MANIFEST_REL
        if not manifest_path.is_file():
            raise VaultError(
                f"not a harness vault (missing {MANIFEST_REL}): {self.root}"
            )
        try:
            self._manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as e:
            raise VaultError(f"invalid manifest {manifest_path}: {e}") from e

        version = self._manifest.get("schema_version")
        if version != SUPPORTED_SCHEMA:
            raise VaultError(
                f"unsupported vault schema_version {version!r} "
                f"(supported: {SUPPORTED_SCHEMA})"
            )

        includes = self._manifest.get("include", ["**/*.md"])
        excludes = self._manifest.get("exclude", [])
        excluded: set[Path] = set()
        for pattern in excludes:
            excluded.update(self.root.glob(pattern))

        for pattern in includes:
            for path in sorted(self.root.glob(pattern)):
                if not path.is_file() or path in excluded:
                    continue
                self._index_note(path)
        self._loaded = True

    def _index_note(self, path: Path) -> None:
        rel = path.relative_to(self.root).as_posix()
        try:
            meta, body = _split_frontmatter(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise VaultError(f"invalid YAML frontmatter in {rel}: {e}") from e
        entry_id = str(meta.get("id") or rel)
        if entry_id in self._entries:
            other = self._entries[entry_id].rel_path
            raise VaultError(f"duplicate entry id {entry_id!r} (in {rel} and {other})")
        tags = meta.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        if not isinstance(tags, list):
            raise VaultError(
                f"invalid 'tags' in {rel}: expected a list or string, got "
                f"{type(tags).__name__}"
            )
        entry = VaultEntry(
            id=entry_id,
            title=str(meta.get("title") or path.stem),
            tags=tuple(str(t) for t in tags),
            type=str(meta.get("type") or "doc"),
            rel_path=rel,
        )
        self._entries[entry_id] = entry
        self._bodies[entry_id] = body
        self._stems[path.stem] = entry_id

    # --- VaultProvider ------------------------------------------------------
    def validate(self) -> None:
        self._load()
        for entry_id, body in self._bodies.items():
            for target in _WIKILINK.findall(body):
                target = target.strip()
                if target not in self._entries and target not in self._stems:
                    raise VaultError(
                        f"unresolved wikilink [[{target}]] in entry {entry_id!r}"
                    )

    def entries(self) -> list[VaultEntry]:
        self._load()
        return sorted(self._entries.values(), key=lambda e: e.id)

    def read(self, ref: str) -> VaultDocument:
        self._load()
        entry = self._entries.get(ref)
        if entry is None:
            # fall back to a relative-path lookup
            for candidate in self._entries.values():
                if candidate.rel_path == ref:
                    entry = candidate
                    break
        if entry is None:
            raise VaultError(f"no vault entry for ref {ref!r}")
        return VaultDocument(entry=entry, body=self._bodies[entry.id])

    def search(
        self, query: str | None = None, tags: list[str] | None = None
    ) -> list[VaultEntry]:
        self._load()
        q = (query or "").lower()
        want = set(tags or [])
        results = []
        for entry in self.entries():
            if q and q not in entry.id.lower() and q not in entry.title.lower():
                continue
            if want and not want.issubset(set(entry.tags)):
                continue
            results.append(entry)
        return results

    def metadata(self) -> dict[str, object]:
        self._load()
        return {
            "name": self._manifest.get("name", self.root.name),
            "description": self._manifest.get("description", ""),
            "schema_version": self._manifest.get("schema_version"),
            "entry_count": len(self._entries),
        }
