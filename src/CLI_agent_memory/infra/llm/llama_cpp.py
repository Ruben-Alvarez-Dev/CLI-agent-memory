from CLI_agent_memory.domain.protocols import LLMClient, LLMResponse, Message
from typing import Any
import httpx


class LlamaCppClient(LLMClient):
    """Client for llama-server OpenAI-compatible API."""

    def __init__(self, base_url: str = "http://localhost:8080", model: str = "", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def generate(
        self,
        prompt: str,
        history: list,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        messages = list(history) + [{"role": "user", "content": prompt}]
        payload: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self.model:
            payload["model"] = self.model

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return LLMResponse(text=text)

    def is_available(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen(f"{self.base_url}/health", timeout=3)
            return True
        except Exception:
            return False
