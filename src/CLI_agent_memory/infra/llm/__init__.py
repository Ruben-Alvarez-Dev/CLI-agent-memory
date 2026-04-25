"""LLM factory — creates the right client based on config."""

from __future__ import annotations

from CLI_agent_memory.config import AgentMemoryConfig
from CLI_agent_memory.domain.protocols import LLMClient
from CLI_agent_memory.infra.llm.lmstudio import LMStudioClient
from CLI_agent_memory.infra.llm.ollama import OllamaClient


def create_llm_client(backend: str, config: AgentMemoryConfig, model: str = "") -> LLMClient:
    if backend == "lmstudio":
        return LMStudioClient(base_url=config.llm_base_url, model=model, timeout=config.llm_timeout)
    elif backend == "ollama":
        # Ollama default port is 11434, ignore config.llm_base_url (which is LM Studio's 1234)
        return OllamaClient(base_url="http://localhost:11434", model=model or config.llm_model or "llama3")
    else:
        raise ValueError(f"Unknown LLM backend: {backend}")
