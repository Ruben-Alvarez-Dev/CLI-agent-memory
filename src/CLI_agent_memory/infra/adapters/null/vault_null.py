"""Null vault adapter — returns empty results."""

from __future__ import annotations

from CLI_agent_memory.domain.protocols import VaultProtocol
from CLI_agent_memory.domain.types import VaultEntry


class NullVaultAdapter(VaultProtocol):
    async def write(self, folder: str, filename: str, content: str) -> VaultEntry:
        return VaultEntry(folder=folder, filename=filename, content=content, path="")

    async def read(self, folder: str, filename: str) -> str | None:
        return None

    async def search(self, query: str) -> list[VaultEntry]:
        return []

    async def list_entries(self, folder: str = "") -> list[VaultEntry]:
        return []

    async def append(self, folder: str, filename: str, content: str) -> None:
        pass
