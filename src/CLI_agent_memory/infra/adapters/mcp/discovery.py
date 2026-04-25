"""MCP server discovery — find MCP-agent-memory installation.

Priority:
  1. MCP_SERVER_DIR env var (explicit override)
  2. ~/MCP-servers/MCP-agent-memory (default installer path)
  3. ~/MCP-agent-memory (legacy path)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_VENV_MARKER = ".venv/bin/python3"


def discover_mcp_server_dir() -> Path:
    """Auto-discover MCP-agent-memory installation directory."""
    # 1. Explicit override
    env_dir = os.environ.get("MCP_SERVER_DIR", "")
    if env_dir:
        p = Path(env_dir).expanduser()
        if (p / _VENV_MARKER).exists():
            return p
        logger.warning("MCP_SERVER_DIR=%s points to invalid installation, falling back", env_dir)

    # 2. Default installer path
    default = Path.home() / "MCP-servers" / "MCP-agent-memory"
    if (default / _VENV_MARKER).exists():
        return default

    # 3. Legacy path
    legacy = Path.home() / "MCP-agent-memory"
    if (legacy / _VENV_MARKER).exists():
        return legacy

    logger.warning(
        "MCP-agent-memory not found at ~/MCP-servers/MCP-agent-memory or ~/MCP-agent-memory. "
        "Set MCP_SERVER_DIR env var to the correct path."
    )
    return default
