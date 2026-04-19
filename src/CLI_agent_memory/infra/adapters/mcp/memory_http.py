"""MCP Memory HTTP adapter — connects to MCP-agent-memory gateway."""

from __future__ import annotations

import httpx

from CLI_agent_memory.domain.protocols import MemoryProtocol
from CLI_agent_memory.domain.types import ContextPack, Memory


class MCPMemoryAdapter(MemoryProtocol):
    """Talks to MCP-agent-memory gateway via HTTP JSON-RPC."""

    def __init__(self, base_url: str = "http://127.0.0.1:3050/mcp"):
        self.base_url = base_url.rstrip("/")
        if self.base_url.startswith("http") and not self.base_url.endswith("/mcp"):
             self.base_url += "/mcp"
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _call(self, method: str, params: dict) -> dict | None:
        try:
            resp = await self._client.post(
                self.base_url,
                json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("result")
        except Exception:
            return None

    async def recall(self, query: str, max_tokens: int = 4000) -> ContextPack:
        result = await self._call("engram_1mcp_recall", {"query": query, "max_tokens": max_tokens})
        if not result:
            return ContextPack()
        return ContextPack(
            context_text=result.get("context_text", ""),
            sources=result.get("sources", []),
            token_count=result.get("token_count", 0),
        )

    async def store(self, event_type: str, content: str, tags: list[str] | None = None) -> str:
        result = await self._call(
            "automem_1mcp_memorize",
            {"event_type": event_type, "content": content, "tags": tags or []},
        )
        return result.get("id", "") if result else ""

    async def ingest(self, event_type: str, content: str) -> None:
        await self._call("automem_1mcp_ingest_event", {"event_type": event_type, "content": content})

    async def search(self, query: str, limit: int = 10) -> list[Memory]:
        result = await self._call("engram_1mcp_search", {"query": query, "limit": limit})
        if not result:
            return []
        return [Memory(**m) for m in result.get("memories", [])]

    async def list(self, tags: list[str] | None = None, limit: int = 50) -> list[Memory]:
        result = await self._call("engram_1mcp_list", {"tags": tags or [], "limit": limit})
        if not result:
            return []
        return [Memory(**m) for m in result.get("memories", [])]

    async def close(self) -> None:
        await self._client.aclose()
