"""Configuration — Environment + Settings."""

from __future__ import annotations

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class AgentMemoryConfig(BaseSettings):
    # LLM
    llm_backend: str = "lmstudio"
    llm_model: str = ""
    llm_base_url: str = "http://localhost:1234"
    llm_api_key: str = ""
    llm_timeout: int = 120

    # Memory
    memory_url: str = "http://127.0.0.1:3050"
    memory_enabled: bool = True
    force_local: bool = False

    # Loop
    max_iterations: int = 50
    max_stagnation: int = 3
    test_command: str = ""

    # Workspace
    worktree_dir: str = ".worktrees"

    # Vault
    vault_dir: str = ".agent-memory/vault"

    # Database
    db_path: str = ".agent-memory/agent-memory.db"

    model_config = ConfigDict(
        env_prefix="AGENT_MEMORY_",
        toml_file="agent-memory.toml",
    )
