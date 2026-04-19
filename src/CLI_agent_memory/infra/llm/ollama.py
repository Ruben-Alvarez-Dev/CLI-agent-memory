"""Ollama LLM client — POST /api/chat."""

from __future__ import annotations

import httpx

from CLI_agent_memory.domain.protocols import LLMClient
from CLI_agent_memory.domain.types import LLMResponse, Message


class OllamaClient(LLMClient):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(timeout=120)

    async def generate(
        self,
        prompt: str,
        history: list[Message],
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        messages = [{"role": m.role, "content": m.content} for m in history]
        try:
            resp = await self._client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "options": {"temperature": temperature},
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return LLMResponse(
                text=data["message"]["content"],
                finish_reason="stop",
            )
        except Exception as e:
            return LLMResponse(text=str(e), finish_reason="error")

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False
