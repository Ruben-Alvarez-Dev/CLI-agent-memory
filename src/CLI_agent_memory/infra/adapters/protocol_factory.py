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
    """Resolves adapters based on config.

    Resolution order:
      1. MCP stdio adapters (default): spawn MCP-agent-memory subprocess
      2. Local adapters (force_local=True): SQLite + filesystem
      3. Null adapters (fallback): empty stubs for testing
    """

    def __init__(self, config: AgentMemoryConfig):
        self.config = config

    def create_memory(self) -> MemoryProtocol:
        if self.config.force_local:
            from CLI_agent_memory.infra.adapters.local.memory_local import LocalMemoryAdapter
            return LocalMemoryAdapter(self.config.db_path or ".agent-memory/agent-memory.db")
        if self.config.memory_enabled:
            from CLI_agent_memory.infra.adapters.mcp.memory_stdio import MCPMemoryStdioAdapter
            return MCPMemoryStdioAdapter()
        return NullMemoryAdapter()

    def create_thinking(self) -> ThinkingProtocol:
        if self.config.force_local:
            from CLI_agent_memory.infra.adapters.local.thinking_local import LocalThinkingAdapter
            return LocalThinkingAdapter(self.config.db_path or ".agent-memory/agent-memory.db")
        if self.config.memory_enabled:
            from CLI_agent_memory.infra.adapters.mcp.thinking_stdio import MCPThinkingStdioAdapter
            return MCPThinkingStdioAdapter()
        return NullThinkingAdapter()

    def create_vault(self) -> VaultProtocol:
        if self.config.force_local:
            from CLI_agent_memory.infra.adapters.local.vault_local import LocalVaultAdapter
            return LocalVaultAdapter(self.config.vault_dir or ".agent-memory/vault")
        if self.config.memory_enabled:
            from CLI_agent_memory.infra.adapters.mcp.vault_stdio import MCPVaultStdioAdapter
            return MCPVaultStdioAdapter()
        return NullVaultAdapter()

    def create_engram(self) -> EngramProtocol | None:
        return None
