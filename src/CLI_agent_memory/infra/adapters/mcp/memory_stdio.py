"""MCP Memory stdio adapter — implements MemoryProtocol via MCP subprocess."""

from __future__ import annotations
import logging
from CLI_agent_memory.domain.protocols import MemoryProtocol
from CLI_agent_memory.domain.types import ContextPack, Memory
from .stdio_manager import get_shared_manager

logger = logging.getLogger(__name__)


class MCPMemoryStdioAdapter(MemoryProtocol):

    async def recall(self, query: str, max_tokens: int = 4000) -> ContextPack:
        try:
            mgr = await get_shared_manager()
            data = await mgr.tool("vk_cache_request_context", {
                "query": query, "agent_id": "cli-agent-memory",
                "intent": "answer", "token_budget": max_tokens,
            })
            injection = data.get("injection_text", "")
            pack = data.get("context_pack", {})
            return ContextPack(
                context_text=injection or pack.get("summary", ""),
                sources=[s.get("scope", "") if isinstance(s, dict) else str(s)
                         for s in pack.get("sources", [])],
                token_count=pack.get("token_estimate", 0),
            )
        except Exception as e:
            logger.error(f"recall failed: {e}")
            return ContextPack()

    async def store(self, event_type: str, content: str, tags: list[str] | None = None) -> str:
        try:
            mgr = await get_shared_manager()
            data = await mgr.tool("mem0_add_memory", {
                "content": f"[{event_type}] {content}", "user_id": "cli-agent-memory",
            })
            return data.get("memory_id", "")
        except Exception as e:
            logger.error(f"store failed: {e}")
            return ""

    async def ingest(self, event_type: str, content: str) -> None:
        try:
            mgr = await get_shared_manager()
            await mgr.tool("automem_ingest_event", {
                "event_type": event_type, "source": "cli-agent-memory",
                "content": content, "actor_id": "cli-agent-memory",
            })
        except Exception as e:
            logger.error(f"ingest failed: {e}")

    async def search(self, query: str, limit: int = 10) -> list[Memory]:
        try:
            mgr = await get_shared_manager()
            data = await mgr.tool("mem0_search_memory", {
                "query": query, "user_id": "cli-agent-memory", "limit": limit,
            })
            results = data.get("results", [])
            return [Memory(id=r.get("memory_id", r.get("id", "")), content=r.get("content", ""),
                           tags=r.get("topic_ids", [])) for r in results if isinstance(r, dict)]
        except Exception as e:
            logger.error(f"search failed: {e}")
            return []

    async def list(self, tags: list[str] | None = None, limit: int = 50) -> list[Memory]:
        try:
            mgr = await get_shared_manager()
            data = await mgr.tool("mem0_get_all_memories", {
                "user_id": "cli-agent-memory", "limit": limit,
            })
            memories = data.get("memories", [])
            return [Memory(id=m.get("memory_id", m.get("id", "")), content=m.get("content", ""),
                           tags=m.get("topic_ids", []), scope=m.get("scope_type", "session"),
                           importance=m.get("importance", 0.5), created_at=m.get("created_at", ""))
                    for m in memories if isinstance(m, dict)]
        except Exception as e:
            logger.error(f"list failed: {e}")
            return []

    async def close(self) -> None:
        pass
