"""LLM factory — creates the right client based on config."""

from __future__ import annotations

from CLI_agent_memory.config import AgentMemoryConfig
from CLI_agent_memory.domain.protocols import LLMClient
from CLI_agent_memory.infra.llm.lmstudio import LMStudioClient
from CLI_agent_memory.infra.llm.ollama import OllamaClient


def create_llm_client(backend: str, config: AgentMemoryConfig) -> LLMClient:
    if backend == "lmstudio":
        return LMStudioClient(base_url=config.llm_base_url, timeout=config.llm_timeout)
    elif backend == "ollama":
        return OllamaClient(base_url=config.llm_base_url, model=config.llm_model or "llama3")
    else:
        raise ValueError(f"Unknown LLM backend: {backend}")
