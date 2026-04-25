"""Tests for local adapters — memory, thinking, vault."""

from __future__ import annotations
import tempfile
from pathlib import Path

import pytest

from CLI_agent_memory.config import AgentMemoryConfig


class TestLocalMemoryAdapter:
    """LocalMemoryAdapter — SQLite-backed memory."""

    @pytest.fixture
    def adapter(self, tmp_path):
        from CLI_agent_memory.infra.adapters.local.memory_local import LocalMemoryAdapter
        a = LocalMemoryAdapter(tmp_path / "test.db")
        yield a
        a.close()

    @pytest.mark.asyncio
    async def test_store_and_search(self, adapter):
        rid = await adapter.store("test", "Python is great", tags=["python", "lang"])
        assert rid  # non-empty string
        results = await adapter.search("Python")
        assert len(results) >= 1
        assert "Python" in results[0].content

    @pytest.mark.asyncio
    async def test_recall_returns_context(self, adapter):
        await adapter.store("fact", "The sky is blue")
        pack = await adapter.recall("sky")
        assert "blue" in pack.context_text

    @pytest.mark.asyncio
    async def test_list_all(self, adapter):
        await adapter.store("a", "first")
        await adapter.store("b", "second")
        items = await adapter.list()
        assert len(items) >= 2

    @pytest.mark.asyncio
    async def test_ingest(self, adapter):
        await adapter.ingest("event", "something happened")
        results = await adapter.search("something")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_empty(self, adapter):
        results = await adapter.search("nonexistent_xyz")
        assert results == []


class TestLocalThinkingAdapter:
    """LocalThinkingAdapter — SQLite-backed thinking."""

    @pytest.fixture
    def adapter(self, tmp_path):
        from CLI_agent_memory.infra.adapters.local.thinking_local import LocalThinkingAdapter
        a = LocalThinkingAdapter(tmp_path / "test.db")
        yield a
        a.close()

    @pytest.mark.asyncio
    async def test_think_returns_session(self, adapter):
        result = await adapter.think("What is 2+2?")
        assert result.session_id  # non-empty
        assert result.problem == "What is 2+2?"

    @pytest.mark.asyncio
    async def test_get_session(self, adapter):
        result = await adapter.think("problem x")
        fetched = await adapter.get_session(result.session_id)
        assert fetched is not None
        assert fetched.problem == "problem x"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, adapter):
        result = await adapter.get_session("nonexistent")
        assert result is None


class TestLocalVaultAdapter:
    """LocalVaultAdapter — filesystem-backed vault."""

    @pytest.fixture
    def adapter(self, tmp_path):
        from CLI_agent_memory.infra.adapters.local.vault_local import LocalVaultAdapter
        return LocalVaultAdapter(tmp_path / "vault")

    @pytest.mark.asyncio
    async def test_write_and_read(self, adapter):
        entry = await adapter.write("Plans", "plan-1.md", "# Plan\n\n1. Do stuff")
        assert entry.filename == "plan-1.md"
        content = await adapter.read("Plans", "plan-1.md")
        assert "# Plan" in content

    @pytest.mark.asyncio
    async def test_read_not_found(self, adapter):
        result = await adapter.read("Plans", "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_entries(self, adapter):
        await adapter.write("Notes", "a.md", "content a")
        await adapter.write("Notes", "b.md", "content b")
        entries = await adapter.list_entries("Notes")
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_append(self, adapter):
        await adapter.write("Log", "day1.md", "Morning")
        await adapter.append("Log", "day1.md", "Evening")
        content = await adapter.read("Log", "day1.md")
        assert "Morning" in content
        assert "Evening" in content

    @pytest.mark.asyncio
    async def test_search(self, adapter):
        await adapter.write("Decisions", "auth.md", "Use JWT")
        results = await adapter.search("auth")
        assert len(results) >= 1
        assert results[0].filename == "auth.md"


class TestProtocolFactory:
    """ProtocolFactory resolves correct adapter tier."""

    def test_force_local_uses_local_memory(self, tmp_path):
        from CLI_agent_memory.infra.adapters.protocol_factory import ProtocolFactory
        config = AgentMemoryConfig(force_local=True, db_path=str(tmp_path / "test.db"))
        factory = ProtocolFactory(config)
        mem = factory.create_memory()
        assert mem.__class__.__name__ == "LocalMemoryAdapter"

    def test_force_local_uses_local_vault(self, tmp_path):
        from CLI_agent_memory.infra.adapters.protocol_factory import ProtocolFactory
        config = AgentMemoryConfig(force_local=True, vault_dir=str(tmp_path / "vault"))
        factory = ProtocolFactory(config)
        vault = factory.create_vault()
        assert vault.__class__.__name__ == "LocalVaultAdapter"

    def test_memory_disabled_uses_null(self):
        from CLI_agent_memory.infra.adapters.protocol_factory import ProtocolFactory
        config = AgentMemoryConfig(memory_enabled=False)
        factory = ProtocolFactory(config)
        mem = factory.create_memory()
        assert mem.__class__.__name__ == "NullMemoryAdapter"

    def test_mcp_memory_when_enabled(self):
        from CLI_agent_memory.infra.adapters.protocol_factory import ProtocolFactory
        config = AgentMemoryConfig(memory_enabled=True)
        factory = ProtocolFactory(config)
        mem = factory.create_memory()
        assert mem.__class__.__name__ == "MCPMemoryStdioAdapter"

    def test_llama_cpp_uses_config_url(self):
        from CLI_agent_memory.infra.llm import create_llm_client
        from CLI_agent_memory.config import AgentMemoryConfig
        c = AgentMemoryConfig()
        client = create_llm_client("llama_cpp", c)
        assert client.base_url == "http://localhost:8081"

    def test_unknown_backend_raises(self):
        from CLI_agent_memory.infra.llm import create_llm_client
        from CLI_agent_memory.config import AgentMemoryConfig
        c = AgentMemoryConfig()
        try:
            create_llm_client("unknown", c)
            assert False, "Should have raised"
        except ValueError:
            pass
