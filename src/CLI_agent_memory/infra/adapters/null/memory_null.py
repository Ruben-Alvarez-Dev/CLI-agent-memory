"""Null memory adapter — returns empty results, 0 side effects."""

from __future__ import annotations

from CLI_agent_memory.domain.protocols import MemoryProtocol
from CLI_agent_memory.domain.types import ContextPack, Memory


class NullMemoryAdapter(MemoryProtocol):
    async def recall(self, query: str, max_tokens: int = 4000) -> ContextPack:
        return ContextPack()

    async def store(self, event_type: str, content: str, tags: list[str] | None = None) -> str:
        return ""

    async def ingest(self, event_type: str, content: str) -> None:
        pass

    async def search(self, query: str, limit: int = 10) -> list[Memory]:
        return []

    async def list(self, tags: list[str] | None = None, limit: int = 50) -> list[Memory]:
        return []
