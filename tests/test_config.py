"""Tests for config.py — SPEC-CLI-02."""

import os

from CLI_agent_memory.config import AgentMemoryConfig


def test_default_values():
    """Config has correct defaults."""
    cfg = AgentMemoryConfig()
    assert cfg.llm_backend == "lmstudio"
    assert cfg.mcp_server_dir == ""
    assert cfg.max_iterations == 50
    assert cfg.force_local is False


def test_env_prefix():
    """Config loads from AGENT_MEMORY_ env vars."""
    os.environ["AGENT_MEMORY_LLM_BACKEND"] = "ollama"
    try:
        cfg = AgentMemoryConfig()
        assert cfg.llm_backend == "ollama"
    finally:
        del os.environ["AGENT_MEMORY_LLM_BACKEND"]


def test_config_model_fields():
    """All expected fields exist."""
    cfg = AgentMemoryConfig()
    assert hasattr(cfg, "llm_backend")
    assert hasattr(cfg, "llm_model")
    assert hasattr(cfg, "llm_base_url")
    assert hasattr(cfg, "mcp_server_dir")
    assert hasattr(cfg, "memory_enabled")
    assert hasattr(cfg, "force_local")
    assert hasattr(cfg, "max_iterations")
    assert hasattr(cfg, "worktree_dir")
    assert hasattr(cfg, "vault_dir")
    assert hasattr(cfg, "db_path")
