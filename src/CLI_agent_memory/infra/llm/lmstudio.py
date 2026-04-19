"""LM Studio LLM client — POST /v1/chat/completions."""

from __future__ import annotations

import httpx

from CLI_agent_memory.domain.protocols import LLMClient
from CLI_agent_memory.domain.types import LLMResponse, Message


class LMStudioClient(LLMClient):
    def __init__(self, base_url: str = "http://localhost:1234", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

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
                f"{self.base_url}/v1/chat/completions",
                json={
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            return LLMResponse(
                text=choice["message"]["content"],
                finish_reason=choice.get("finish_reason", "stop"),
            )
        except httpx.ConnectError:
            return LLMResponse(text="", finish_reason="error")
        except Exception as e:
            return LLMResponse(text=str(e), finish_reason="error")

    def is_available(self) -> bool:
        try:
            import httpx
            resp = httpx.get(f"{self.base_url}/v1/models", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False
