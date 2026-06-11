"""Vault access bridge — pairs a vault read with a `vault.read` event.

The `VaultProvider` stays pure (no event dependency); this bridge lives in
`agent/` (which already depends on both the vault and the adapter/events) and
emits `vault.read` at the consumption boundary (FR10), so reads show up in the
log and replay. Searching is a local index op and is not logged.
"""

from __future__ import annotations

from agentiq.agent.adapter import AgentAdapter
from agentiq.vault.provider import VaultDocument, VaultEntry, VaultProvider


class VaultReader:
    """Reads a vault on behalf of an agent, emitting `vault.read` events."""

    def __init__(self, provider: VaultProvider, adapter: AgentAdapter) -> None:
        self._provider = provider
        self._adapter = adapter

    def read(self, agent_id: str, ref: str) -> VaultDocument:
        """Fetch a document and log the read as a `vault.read` event."""
        document = self._provider.read(ref)
        self._adapter.vault_read(agent_id, ref)
        return document

    def search(
        self, query: str | None = None, tags: list[str] | None = None
    ) -> list[VaultEntry]:
        """Search the index (not logged — searching is not an agent action)."""
        return self._provider.search(query, tags)
