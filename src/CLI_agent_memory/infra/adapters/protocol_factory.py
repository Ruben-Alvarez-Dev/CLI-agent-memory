"""Protocol factory — resolves adapters for memory, thinking, vault, etc."""

from __future__ import annotations

from CLI_agent_memory.config import AgentMemoryConfig
from CLI_agent_memory.domain.protocols import (
    MemoryProtocol, ThinkingProtocol, VaultProtocol, EngramProtocol,
)
from CLI_agent_memory.infra.adapters.mcp.memory_http import MCPMemoryAdapter
from CLI_agent_memory.infra.adapters.mcp.thinking_mcp import MCPThinkingAdapter
from CLI_agent_memory.infra.adapters.null.memory_null import NullMemoryAdapter
from CLI_agent_memory.infra.adapters.null.thinking_null import NullThinkingAdapter
from CLI_agent_memory.infra.adapters.null.vault_null import NullVaultAdapter


class ProtocolFactory:
    """Decides which adapter to use based on config."""

    def __init__(self, config: AgentMemoryConfig):
        self.config = config

    def create_memory(self) -> MemoryProtocol:
        if self.config.memory_enabled and not self.config.force_local:
            return MCPMemoryAdapter(self.config.memory_url)
        return NullMemoryAdapter()

    def create_thinking(self) -> ThinkingProtocol:
        if self.config.memory_enabled and not self.config.force_local:
            return MCPThinkingAdapter(self.config.memory_url)
        return NullThinkingAdapter()

    def create_vault(self) -> VaultProtocol:
        # NOTE: VaultMCPAdapter not implemented yet
        return NullVaultAdapter()

    def create_engram(self) -> EngramProtocol | None:
        # Engram not used in loop MVP yet
        return None
