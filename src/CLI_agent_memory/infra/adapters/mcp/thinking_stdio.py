"""MCP Thinking stdio adapter — implements ThinkingProtocol via MCP subprocess."""

from __future__ import annotations
import logging
from CLI_agent_memory.domain.protocols import ThinkingProtocol
from CLI_agent_memory.domain.types import ThinkingResult, ThinkingStep
from .stdio_manager import get_shared_manager

logger = logging.getLogger(__name__)


class MCPThinkingStdioAdapter(ThinkingProtocol):

    async def think(self, problem: str, depth: int = 5) -> ThinkingResult:
        try:
            mgr = await get_shared_manager()
            data = await mgr.tool("Lx_reasoning_sequential_thinking", {
                "problem": problem, "context": "", "max_steps": depth,
            })
            thoughts = data.get("thoughts", [])
            return ThinkingResult(
                session_id=data.get("session_id", ""), problem=problem,
                steps=[ThinkingStep(step_number=t.get("step_number", i+1),
                        thought=t.get("thought", ""), next_needed=t.get("next_needed", True))
                       for i, t in enumerate(thoughts)] if thoughts else [],
                conclusion=data.get("summary", ""),
            )
        except Exception as e:
            logger.error(f"think failed: {e}")
            return ThinkingResult(session_id="", problem=problem)

    async def get_session(self, session_id: str) -> ThinkingResult | None:
        try:
            mgr = await get_shared_manager()
            data = await mgr.tool("Lx_reasoning_get_thinking_session", {"session_id": session_id})
            thoughts = data.get("thoughts", [])
            return ThinkingResult(
                session_id=session_id, problem=data.get("problem", ""),
                steps=[ThinkingStep(step_number=t.get("step_number", i+1), thought=t.get("thought", ""))
                       for i, t in enumerate(thoughts)],
                conclusion=data.get("summary", ""),
            )
        except Exception as e:
            logger.error(f"get_session failed: {e}")
            return None

    async def close(self) -> None:
        pass
