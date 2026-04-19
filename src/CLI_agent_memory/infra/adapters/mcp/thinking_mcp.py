"""MCP Thinking adapter — connects to sequential-thinking server."""

from __future__ import annotations

import httpx

from CLI_agent_memory.domain.protocols import ThinkingProtocol
from CLI_agent_memory.domain.types import ThinkingResult, ThinkingStep


class MCPThinkingAdapter(ThinkingProtocol):
    """Talks to MCP-agent-memory gateway for sequential thinking."""

    def __init__(self, base_url: str = "http://127.0.0.1:3050/mcp"):
        self.base_url = base_url.rstrip("/")
        if self.base_url.startswith("http") and not self.base_url.endswith("/mcp"):
             self.base_url += "/mcp"
        self._client = httpx.AsyncClient(timeout=60.0)

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

    async def think(self, problem: str, depth: int = 5) -> ThinkingResult:
        result = await self._call(
            "sequential-thinking_1mcp_think",
            {"problem": problem, "thought_limit": depth},
        )
        if not result:
            return ThinkingResult(session_id="err", problem=problem)

        steps = [
            ThinkingStep(
                step_number=i + 1,
                thought=s.get("thought", ""),
                next_needed=s.get("next_needed", True)
            )
            for i, s in enumerate(result.get("steps", []))
        ]
        return ThinkingResult(
            session_id=result.get("session_id", ""),
            problem=problem,
            steps=steps,
            conclusion=result.get("conclusion", "")
        )

    async def get_session(self, session_id: str) -> ThinkingResult | None:
        result = await self._call("sequential-thinking_1mcp_get_session", {"session_id": session_id})
        if not result:
            return None
        steps = [
            ThinkingStep(
                step_number=i + 1,
                thought=s.get("thought", ""),
                next_needed=s.get("next_needed", True)
            )
            for i, s in enumerate(result.get("steps", []))
        ]
        return ThinkingResult(
            session_id=session_id,
            problem=result.get("problem", ""),
            steps=steps,
            conclusion=result.get("conclusion", "")
        )

    async def close(self) -> None:
        await self._client.aclose()
