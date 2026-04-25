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

    def test_cancel_parser(self):
        from CLI_agent_memory.parser import build_parser
        args = build_parser().parse_args(["cancel", "task-123", "--repo", "/tmp/test"])
        assert args.task_id == "task-123"
        assert args.repo == "/tmp/test"

    def test_plan_parser(self):
        from CLI_agent_memory.parser import build_parser
        args = build_parser().parse_args(["plan", "build API", "--save", "PLAN.md"])
        assert args.task == "build API"
        assert args.save == "PLAN.md"

    def test_db_parser(self):
        from CLI_agent_memory.parser import build_parser
        args = build_parser().parse_args(["db", "--tables"])
        assert args.tables is True
        args2 = build_parser().parse_args(["db", "--query", "SELECT 1"])
        assert args2.query == "SELECT 1"


class TestCmdCancel:
    """cancel command — mark task as FAILED."""

    def test_no_worktrees(self, tmp_path):
        from CLI_agent_memory.commands_extra import cmd_cancel
        args = FakeArgs(repo=str(tmp_path), task_id="none")
        result = cmd_cancel(args, AgentMemoryConfig())
        assert result == 1

    def test_cancel_active_task(self, tmp_path):
        from CLI_agent_memory.commands_extra import cmd_cancel
        from CLI_agent_memory.domain.state import TaskContext
        wt = tmp_path / ".worktrees" / "active-wt"
        wt.mkdir(parents=True)
        ctx = TaskContext(wt)
        ctx.generate_task_id("branch-1")
        ctx.transition(AgentState.CODING)
        args = FakeArgs(repo=str(tmp_path), task_id=ctx.task_id)
        result = cmd_cancel(args, AgentMemoryConfig())
        assert result == 0
        # Reload and verify
        ctx2 = TaskContext.find_in_worktree(wt)
        assert ctx2.state == AgentState.FAILED

    def test_cancel_not_found(self, tmp_path):
        from CLI_agent_memory.commands_extra import cmd_cancel
        from CLI_agent_memory.domain.state import TaskContext
        wt = tmp_path / ".worktrees" / "other-wt"
        wt.mkdir(parents=True)
        ctx = TaskContext(wt)
        ctx.generate_task_id("b1")
        ctx.transition(AgentState.CODING)
        args = FakeArgs(repo=str(tmp_path), task_id="nonexistent")
        result = cmd_cancel(args, AgentMemoryConfig())
        assert result == 1


class TestCmdPlan:
    """plan command — standalone planning."""

    @patch("CLI_agent_memory.infra.llm.create_llm_client")
    def test_plan_llm_unavailable(self, mock_create):
        from CLI_agent_memory.commands_extra import cmd_plan
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = False
        mock_create.return_value = mock_llm
        args = FakeArgs(task="build API", model="", save="")
        result = cmd_plan(args, AgentMemoryConfig())
        assert result == 20


class TestCmdDb:
    """db command — inspect SQLite."""

    def test_no_database(self, tmp_path):
        from CLI_agent_memory.commands_extra import cmd_db
        args = FakeArgs(repo=str(tmp_path), tables=False, query="")
        result = cmd_db(args, AgentMemoryConfig())
        assert result == 1

    def test_db_info(self, tmp_path):
        from CLI_agent_memory.commands_extra import cmd_db
        from CLI_agent_memory.domain.db.schema import init_db
        db_path = tmp_path / ".agent-memory" / "agent-memory.db"
        init_db(db_path)
        args = FakeArgs(repo=str(tmp_path), tables=False, query="")
        result = cmd_db(args, AgentMemoryConfig())
        assert result == 0

    def test_db_tables(self, tmp_path):
        from CLI_agent_memory.commands_extra import cmd_db
        from CLI_agent_memory.domain.db.schema import init_db
        db_path = tmp_path / ".agent-memory" / "agent-memory.db"
        init_db(db_path)
        args = FakeArgs(repo=str(tmp_path), tables=True, query="")
        result = cmd_db(args, AgentMemoryConfig())
        assert result == 0

    def test_db_query(self, tmp_path):
        from CLI_agent_memory.commands_extra import cmd_db
        from CLI_agent_memory.domain.db.schema import init_db
        db_path = tmp_path / ".agent-memory" / "agent-memory.db"
        init_db(db_path)
        args = FakeArgs(repo=str(tmp_path), tables=False, query="SELECT 1 AS ok")
        result = cmd_db(args, AgentMemoryConfig())
        assert result == 0
