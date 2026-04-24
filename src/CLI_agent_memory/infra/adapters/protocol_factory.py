"""Protocol factory — resolves adapters for memory, thinking, vault, etc."""

from __future__ import annotations

from CLI_agent_memory.config import AgentMemoryConfig
from CLI_agent_memory.domain.protocols import (
    MemoryProtocol, ThinkingProtocol, VaultProtocol, EngramProtocol,
)
from CLI_agent_memory.infra.adapters.null.memory_null import NullMemoryAdapter
from CLI_agent_memory.infra.adapters.null.thinking_null import NullThinkingAdapter
from CLI_agent_memory.infra.adapters.null.vault_null import NullVaultAdapter


class ProtocolFactory:
    """Decides which adapter to use based on config.

    Stdio adapters (default): CLI spawns MCP-agent-memory as a subprocess.
    Null adapters (fallback): for offline/testing mode.
    """

    def __init__(self, config: AgentMemoryConfig):
        self.config = config

    def create_memory(self) -> MemoryProtocol:
        if self.config.memory_enabled and not self.config.force_local:
            from CLI_agent_memory.infra.adapters.mcp.memory_stdio import MCPMemoryStdioAdapter
            return MCPMemoryStdioAdapter()
        return NullMemoryAdapter()

    def create_thinking(self) -> ThinkingProtocol:
        if self.config.memory_enabled and not self.config.force_local:
            from CLI_agent_memory.infra.adapters.mcp.thinking_stdio import MCPThinkingStdioAdapter
            return MCPThinkingStdioAdapter()
        return NullThinkingAdapter()

    def create_vault(self) -> VaultProtocol:
        if self.config.memory_enabled and not self.config.force_local:
            from CLI_agent_memory.infra.adapters.mcp.vault_stdio import MCPVaultStdioAdapter
            return MCPVaultStdioAdapter()
        return NullVaultAdapter()

    def create_engram(self) -> EngramProtocol | None:
        # Engram adapter not yet implemented — returns None (use force_local if needed)
        return None
