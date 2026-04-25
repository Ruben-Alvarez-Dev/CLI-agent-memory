"""Backward-compatible re-exports.

Split into:
  - discovery.py: discover_mcp_server_dir()
  - mcp_env.py: load_mcp_env()
  - session.py: MCPSessionManager, get_shared_manager
"""

from .discovery import discover_mcp_server_dir as _discover_mcp_server_dir
from .mcp_env import load_mcp_env as _load_mcp_env
from .session import MCPSessionManager, get_shared_manager

# Re-exports for backward compatibility
__all__ = [
    "MCPSessionManager",
    "discover_mcp_server_dir",
    "get_shared_manager",
    "load_mcp_env",
]

# Named aliases for old imports
discover_mcp_server_dir = _discover_mcp_server_dir
load_mcp_env = _load_mcp_env
