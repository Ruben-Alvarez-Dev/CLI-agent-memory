"""MCP environment loading — read .env from MCP-agent-memory config."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "QDRANT_URL": "http://127.0.0.1:6333",
    "EMBEDDING_BACKEND": "llama_server",
    "LLAMA_SERVER_URL": "http://127.0.0.1:8081",
    "EMBEDDING_MODEL": "bge-m3",
    "EMBEDDING_DIM": "1024",
    "LLM_BACKEND": "ollama",
    "LLM_MODEL": "qwen2.5:7b",
}


def load_mcp_env(base_dir: Path) -> dict[str, str]:
    """Load environment from MCP-agent-memory's config/.env file."""
    env: dict[str, str] = {
        "PYTHONPATH": str(base_dir / "src"),
        "MEMORY_SERVER_DIR": str(base_dir),
    }
    env_file = base_dir / "config" / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                if key and value:
                    env[key] = value
            logger.debug("Loaded %d env vars from %s", len(env) - 2, env_file)
        except OSError as e:
            logger.warning("Failed to read %s: %s", env_file, e)
    else:
        logger.warning("MCP-agent-memory config/.env not found at %s", env_file)
        env.update(_DEFAULTS)
    return env
