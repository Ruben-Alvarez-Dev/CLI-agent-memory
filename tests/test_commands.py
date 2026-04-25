"""Tests for new CLI commands — status, cleanup, think, recall, remember, decisions."""

from __future__ import annotations
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from CLI_agent_memory.config import AgentMemoryConfig
from CLI_agent_memory.domain.types import AgentState


class FakeArgs:
    """Minimal argparse.Namespace stand-in."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


async def _coro(val=None):
    """Return a coroutine that resolves to val."""
    return val


def _async_mock(return_value=None):
    """Create a mock that returns a coroutine."""
    m = AsyncMock(return_value=return_value)
    return m


class TestCmdStatus:
    """status command — show active tasks."""

    def test_no_worktrees(self, tmp_path):
        from CLI_agent_memory.commands import cmd_status
        args = FakeArgs(repo=str(tmp_path), verbose=False)
        result = cmd_status(args, AgentMemoryConfig())
        assert result == 0

    def test_with_tasks(self, tmp_path):
        """Status finds tasks in worktrees."""
        from CLI_agent_memory.commands import cmd_status
        from CLI_agent_memory.domain.state import TaskContext
        # Create a fake worktree with state
        wt = tmp_path / ".worktrees" / "test-wt"
        wt.mkdir(parents=True)
        ctx = TaskContext(wt)
        ctx.task_description = "Build something"
        ctx.generate_task_id("test-branch")
        ctx.transition(AgentState.CODING)
        args = FakeArgs(repo=str(tmp_path), verbose=True)
        result = cmd_status(args, AgentMemoryConfig())
        assert result == 0


class TestCmdCleanup:
    """cleanup command — remove worktrees."""

    def test_no_worktrees(self, tmp_path):
        from CLI_agent_memory.commands import cmd_cleanup
        args = FakeArgs(repo=str(tmp_path), dry_run=False, all=False)
        result = cmd_cleanup(args, AgentMemoryConfig())
        assert result == 0

    def test_dry_run_no_delete(self, tmp_path):
        """Dry run should not delete anything."""
        from CLI_agent_memory.commands import cmd_cleanup
        from CLI_agent_memory.domain.state import TaskContext
        wt = tmp_path / ".worktrees" / "done-wt"
        wt.mkdir(parents=True)
        ctx = TaskContext(wt)
        ctx.generate_task_id("done-branch")
        ctx.transition(AgentState.DONE)
        assert wt.exists()
        args = FakeArgs(repo=str(tmp_path), dry_run=True, all=False)
        cmd_cleanup(args, AgentMemoryConfig())
        assert wt.exists()  # dry run preserves


class TestCmdRecall:
    """recall command — search memories."""

    @patch("CLI_agent_memory.infra.adapters.protocol_factory.ProtocolFactory")
    def test_recall_returns_results(self, mock_factory):
        from CLI_agent_memory.commands import cmd_recall
        mock_memory = MagicMock()
        mock_memory.search = AsyncMock(return_value=["memory about X", "memory about Y"])
        mock_factory.return_value.create_memory.return_value = mock_memory
        args = FakeArgs(query="test", limit=5)
        result = cmd_recall(args, AgentMemoryConfig())
        assert result == 0

    @patch("CLI_agent_memory.infra.adapters.protocol_factory.ProtocolFactory")
    def test_recall_no_results(self, mock_factory):
        from CLI_agent_memory.commands import cmd_recall
        mock_memory = MagicMock()
        mock_memory.search = AsyncMock(return_value=[])
        mock_factory.return_value.create_memory.return_value = mock_memory
        args = FakeArgs(query="nothing", limit=10)
        result = cmd_recall(args, AgentMemoryConfig())
        assert result == 0


class TestCmdRemember:
    """remember command — store a memory."""

    @patch("CLI_agent_memory.infra.adapters.protocol_factory.ProtocolFactory")
    def test_remember_stores(self, mock_factory):
        from CLI_agent_memory.commands import cmd_remember
        mock_memory = MagicMock()
        mock_memory.store = AsyncMock()
        mock_factory.return_value.create_memory.return_value = mock_memory
        args = FakeArgs(content="Important fact", tags="test,important")
        result = cmd_remember(args, AgentMemoryConfig())
        assert result == 0

    @patch("CLI_agent_memory.infra.adapters.protocol_factory.ProtocolFactory")
    def test_remember_no_tags(self, mock_factory):
        from CLI_agent_memory.commands import cmd_remember
        mock_memory = MagicMock()
        mock_memory.store = AsyncMock()
        mock_factory.return_value.create_memory.return_value = mock_memory
        args = FakeArgs(content="Simple fact", tags="")
        result = cmd_remember(args, AgentMemoryConfig())
        assert result == 0


class TestCmdThink:
    """think command — run thinking chain."""

    @patch("CLI_agent_memory.infra.adapters.protocol_factory.ProtocolFactory")
    def test_think_with_steps(self, mock_factory):
        from CLI_agent_memory.commands import cmd_think
        from CLI_agent_memory.domain.types import ThinkingStep, ThinkingResult
        mock_thinking = MagicMock()
        mock_thinking.think = AsyncMock(return_value=ThinkingResult(
            session_id="s1", problem="what is 2+2",
            steps=[ThinkingStep(step_number=1, thought="add numbers", next_needed=False)],
            conclusion="4",
        ))
        mock_factory.return_value.create_thinking.return_value = mock_thinking
        args = FakeArgs(problem="what is 2+2", steps=3)
        result = cmd_think(args, AgentMemoryConfig())
        assert result == 0


class TestCmdDecisions:
    """decisions command — list/search decisions."""

    @patch("CLI_agent_memory.infra.adapters.protocol_factory.ProtocolFactory")
    def test_decisions_returns(self, mock_factory):
        from CLI_agent_memory.commands import cmd_decisions
        mock_memory = MagicMock()
        mock_memory.search = AsyncMock(return_value=["decision about auth", "decision about caching"])
        mock_factory.return_value.create_memory.return_value = mock_memory
        args = FakeArgs(query="auth", limit=10)
        result = cmd_decisions(args, AgentMemoryConfig())
        assert result == 0

    @patch("CLI_agent_memory.infra.adapters.protocol_factory.ProtocolFactory")
    def test_decisions_empty_query(self, mock_factory):
        from CLI_agent_memory.commands import cmd_decisions
        mock_memory = MagicMock()
        mock_memory.search = AsyncMock(return_value=["all decisions"])
        mock_factory.return_value.create_memory.return_value = mock_memory
        args = FakeArgs(query="", limit=20)
        result = cmd_decisions(args, AgentMemoryConfig())
        assert result == 0


class TestParserAllCommands:
    """parser.py builds all expected subcommands."""

    def test_all_commands_exist(self):
        from CLI_agent_memory.parser import build_parser
        p = build_parser()
        # Commands without required positional args
        for cmd in ["run", "version", "doctor", "status", "cleanup", "config"]:
            parsed = p.parse_args([cmd])
            assert parsed.command == cmd, f"Command '{cmd}' not recognized"
        # Commands with required positional args — use fake values
        for cmd, extra in [("resume", ["fake-id"]), ("think", ["problem"]), ("recall", ["q"]),
                           ("remember", ["content"]), ("decisions", [])]:
            parsed = p.parse_args([cmd] + extra)
            assert parsed.command == cmd, f"Command '{cmd}' not recognized"

    def test_status_verbose_flag(self):
        from CLI_agent_memory.parser import build_parser
        args = build_parser().parse_args(["status", "-v"])
        assert args.verbose is True

    def test_cleanup_dry_run(self):
        from CLI_agent_memory.parser import build_parser
        args = build_parser().parse_args(["cleanup", "--dry-run", "--all"])
        assert args.dry_run is True
        assert args.all is True

    def test_recall_limit(self):
        from CLI_agent_memory.parser import build_parser
        args = build_parser().parse_args(["recall", "test query", "--limit", "5"])
        assert args.limit == 5
        assert args.query == "test query"

    def test_remember_tags(self):
        from CLI_agent_memory.parser import build_parser
        args = build_parser().parse_args(["remember", "some content", "--tags", "a,b,c"])
        assert args.content == "some content"
        assert args.tags == "a,b,c"

    def test_decisions_optional_query(self):
        from CLI_agent_memory.parser import build_parser
        args = build_parser().parse_args(["decisions"])
        assert args.query == ""
        args2 = build_parser().parse_args(["decisions", "auth"])
        assert args2.query == "auth"
