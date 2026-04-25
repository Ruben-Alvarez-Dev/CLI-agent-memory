"""LM Studio LLM client — POST /v1/chat/completions."""

from __future__ import annotations

import logging

import httpx

from CLI_agent_memory.domain.protocols import LLMClient
from CLI_agent_memory.domain.types import LLMResponse, Message

logger = logging.getLogger(__name__)


class LMStudioClient(LLMClient):
    def __init__(self, base_url: str = "http://localhost:1234", model: str = "", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def generate(
        self, prompt: str, history: list[Message], temperature: float = 0.1, max_tokens: int = 4096,
    ) -> LLMResponse:
        messages = [{"role": m.role, "content": m.content} for m in history]
        model = self._resolve_model()
        try:
            resp = await self._client.post(
                f"{self.base_url}/v1/chat/completions",
                json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            return LLMResponse(text=choice["message"]["content"], finish_reason=choice.get("finish_reason", "stop"))
        except httpx.ConnectError:
            logger.warning("LM Studio connection refused, retrying...")
            return await self._retry_generate(messages, temperature, max_tokens)
        except Exception as e:
            logger.error("LM Studio generate error: %s", e)
            return LLMResponse(text=str(e), finish_reason="error")

    async def _retry_generate(self, messages, temperature, max_tokens) -> LLMResponse:
        """Retry once on connection refused (SPEC-LLM-01)."""
        try:
            import asyncio
            await asyncio.sleep(1)
            model = self._resolve_model()
            resp = await self._client.post(
                f"{self.base_url}/v1/chat/completions",
                json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            )
            resp.raise_for_status()
            data = resp.json()
            return LLMResponse(text=data["choices"][0]["message"]["content"])
        except Exception as e:
            return LLMResponse(text=str(e), finish_reason="error")

    def _resolve_model(self) -> str:
        """Auto-detect model if not set (SPEC-LLM-01: GET /v1/models)."""
        if self.model:
            return self.model
        try:
            resp = httpx.get(f"{self.base_url}/v1/models", timeout=2.0)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                if models:
                    self.model = models[0]["id"]
                    return self.model
        except Exception:
            pass
        return ""

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/v1/models", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False
