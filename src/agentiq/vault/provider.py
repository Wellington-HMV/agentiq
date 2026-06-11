"""VaultProvider interface — the seam between agents and a knowledge vault.

The rest of the system depends on this ABC, never on a concrete vault format
(NFR16), so alternative harness-standard sources can be swapped in.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class VaultError(Exception):
    """Raised when a vault is malformed, invalid, or a ref cannot be read."""


@dataclass(frozen=True)
class VaultEntry:
    """Index entry for one vault note."""

    id: str
    title: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    type: str = "doc"
    rel_path: str = ""


@dataclass(frozen=True)
class VaultDocument:
    """A read entry plus its markdown body."""

    entry: VaultEntry
    body: str


class VaultProvider(ABC):
    """Abstract knowledge-vault source."""

    @abstractmethod
    def validate(self) -> None:
        """Raise VaultError if the vault is missing, malformed, or inconsistent."""

    @abstractmethod
    def entries(self) -> list[VaultEntry]:
        """All indexed entries."""

    @abstractmethod
    def read(self, ref: str) -> VaultDocument:
        """Read one entry by id or relative path. Raises VaultError if unknown."""

    @abstractmethod
    def search(
        self, query: str | None = None, tags: list[str] | None = None
    ) -> list[VaultEntry]:
        """Entries matching a text query and/or tags."""

    @abstractmethod
    def metadata(self) -> dict[str, object]:
        """Vault-level metadata (name, description, schema_version, entry count)."""
