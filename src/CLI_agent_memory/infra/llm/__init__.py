"""LLM factory — creates the right client based on config."""

from __future__ import annotations

from CLI_agent_memory.config import AgentMemoryConfig
from CLI_agent_memory.domain.protocols import LLMClient


def create_llm_client(backend: str, config: AgentMemoryConfig, model: str = "") -> LLMClient:
    if backend == "llama_cpp":
        from CLI_agent_memory.infra.llm.llama_cpp import LlamaCppClient
        return LlamaCppClient(base_url=config.llm_base_url, model=model, timeout=config.llm_timeout)
    else:
        raise ValueError(f"Unknown LLM backend: {backend}. Only supported: llama_cpp")
