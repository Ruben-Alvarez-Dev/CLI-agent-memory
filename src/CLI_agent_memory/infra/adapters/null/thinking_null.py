"""Null thinking adapter — returns empty results."""

from __future__ import annotations

from CLI_agent_memory.domain.protocols import ThinkingProtocol
from CLI_agent_memory.domain.types import ThinkingResult


class NullThinkingAdapter(ThinkingProtocol):
    async def think(self, problem: str, depth: int = 5) -> ThinkingResult:
        return ThinkingResult(session_id="", problem=problem)

    async def get_session(self, session_id: str) -> ThinkingResult | None:
        return None
