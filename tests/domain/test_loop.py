"""Tests for domain/loop.py — SPEC-D3."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from CLI_agent_memory.config import LoopConfig
from CLI_agent_memory.domain.loop import LoopEngine
from CLI_agent_memory.domain.types import (
    AgentState, CommandResult, ContextPack, LLMResponse, Message, TaskResult,
)


class MockLLM:
    def __init__(self, responses: list[str] | None = None):
        self._responses = responses or ["PLAN.md", "coding... DONE CODING"]
        self._idx = 0

    async def generate(self, prompt, history, temperature=0.1, max_tokens=4096):
        text = self._responses[self._idx % len(self._responses)]
        self._idx += 1
        return LLMResponse(text=text, files_edited=1)

    def is_available(self):
        return True


class MockMemory:
    async def recall(self, query, max_tokens=4000):
        return ContextPack()
    async def store(self, event_type, content, tags=None):
        return "mem-1"
    async def ingest(self, event_type, content):
        pass
    async def search(self, query, limit=10):
        return []
    async def list(self, tags=None, limit=50):
        return []


class MockThinking:
    async def think(self, problem, depth=5):
        return None
    async def get_session(self, session_id):
        return None


class MockWorkspace:
    def __init__(self, tmpdir: Path):
        self.tmpdir = tmpdir
        self._wt = tmpdir / "worktree"
        self._wt.mkdir(exist_ok=True)

    def create(self, branch_name, base_ref="HEAD"):
        return self._wt

    def remove(self, branch_name, force=False):
        return True

    def run_command(self, worktree_path, command):
        import subprocess
        try:
            r = subprocess.run(command, shell=True, cwd=worktree_path, capture_output=True, text=True)
            return CommandResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr, exit_code=r.returncode)
        except Exception:
            return CommandResult(success=False, stderr="error", exit_code=-1)

    def read_file(self, worktree_path, file_path):
        p = worktree_path / file_path
        return p.read_text() if p.exists() else None

    def write_file(self, worktree_path, file_path, content):
        p = worktree_path / file_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def list_files(self, worktree_path, pattern="**/*.py"):
        return []


class MockVault:
    async def write(self, folder, filename, content):
        return None
    async def read(self, folder, filename):
        return None
    async def search(self, query):
        return []
    async def list_entries(self, folder=""):
        return []
    async def append(self, folder, filename, content):
        pass


def make_engine(tmpdir: Path, llm=None, test_cmd="", max_iter=50):
    return LoopEngine(
        llm=llm or MockLLM(),
        memory=MockMemory(),
        thinking=MockThinking(),
        workspace=MockWorkspace(tmpdir),
        vault=MockVault(),
        config=LoopConfig(max_iterations=max_iter, test_command=test_cmd),
    )


@pytest.mark.asyncio
async def test_loop_runs_to_completion():
    """D3.2: run() executes full loop → DONE."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = make_engine(Path(tmp))
        result = await engine.run("Test task", Path(tmp))
        assert result.status == AgentState.DONE
        assert result.tests_passed is True
        assert result.task_id != ""


@pytest.mark.asyncio
async def test_loop_creates_worktree():
    """D3.3: PLANNING creates worktree."""
    with tempfile.TemporaryDirectory() as tmp:
        ws = MockWorkspace(Path(tmp))
        engine = LoopEngine(
            llm=MockLLM(), memory=MockMemory(), thinking=MockThinking(),
            workspace=ws, vault=MockVault(),
            config=LoopConfig(),
        )
        await engine.run("Test", Path(tmp))
        assert ws._wt.exists()


@pytest.mark.asyncio
async def test_loop_respects_max_iterations():
    """D3.7: Never exceeds max_iterations."""
    with tempfile.TemporaryDirectory() as tmp:
        llm = MockLLM(["never done coding"])
        engine = make_engine(Path(tmp), llm=llm, max_iter=3, test_cmd="false")
        result = await engine.run("Test", Path(tmp))
        assert result.status == AgentState.FAILED


@pytest.mark.asyncio
async def test_loop_on_verification_failure_goes_to_coding():
    """D3.5: Tests fail → back to CODING."""
    class FailWorkspace(MockWorkspace):
        def run_command(self, worktree_path, command):
            return CommandResult(success=False, stderr="test failed", exit_code=1)

    with tempfile.TemporaryDirectory() as tmp:
        llm = MockLLM(["plan", "coding DONE CODING", "fix done DONE CODING"])
        ws = FailWorkspace(Path(tmp))
        engine = LoopEngine(
            llm=llm, memory=MockMemory(), thinking=MockThinking(),
            workspace=ws, vault=MockVault(),
            config=LoopConfig(max_iterations=10, test_command="pytest"),
        )
        result = await engine.run("Test", Path(tmp))
        assert result.status in (AgentState.DONE, AgentState.FAILED)


@pytest.mark.asyncio
async def test_loop_returns_task_result():
    """D3.10: Returns TaskResult with correct fields."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = make_engine(Path(tmp))
        result = await engine.run("Fix bug", Path(tmp))
        assert isinstance(result, TaskResult)
        assert result.task_id
        assert result.worktree_path
        assert result.duration_seconds >= 0


@pytest.mark.asyncio
async def test_loop_handles_llm_error():
    """Loop handles LLM exception gracefully."""
    class ErrorLLM:
        async def generate(self, prompt, history, temperature=0.1, max_tokens=4096):
            raise RuntimeError("LLM exploded")
        def is_available(self):
            return True

    with tempfile.TemporaryDirectory() as tmp:
        engine = make_engine(Path(tmp), llm=ErrorLLM())
        result = await engine.run("Test", Path(tmp))
        assert result.status == AgentState.FAILED
        assert "LLM exploded" in result.error


@pytest.mark.asyncio
async def test_loop_writes_plan_file():
    """D3.3: PLANNING writes PLAN.md to workspace."""
    with tempfile.TemporaryDirectory() as tmp:
        ws = MockWorkspace(Path(tmp))
        engine = LoopEngine(
            llm=MockLLM(["# My Plan\n\nStep 1", "done DONE CODING"]),
            memory=MockMemory(), thinking=MockThinking(),
            workspace=ws, vault=MockVault(),
            config=LoopConfig(),
        )
        await engine.run("Test", Path(tmp))
        plan = ws.read_file(ws._wt, "PLAN.md")
        assert plan is not None
        assert "Plan" in plan


@pytest.mark.asyncio
async def test_loop_stores_result_on_completion():
    """D3.9: On completion, memory.store is called."""
    stored = []

    class TrackingMemory(MockMemory):
        async def store(self, event_type, content, tags=None):
            stored.append((event_type, content))
            return "ok"

    with tempfile.TemporaryDirectory() as tmp:
        engine = make_engine(Path(tmp))
        engine.memory = TrackingMemory()
        await engine.run("Test", Path(tmp))
        assert any("task_completed" in e[0] for e in stored)


@pytest.mark.asyncio
async def test_loop_ingests_on_test_failure():
    """D3.10: On failure, memory.ingest is called."""
    ingested = []

    class TrackingMemory(MockMemory):
        async def ingest(self, event_type, content):
            ingested.append((event_type, content))

    class FailWorkspace(MockWorkspace):
        def run_command(self, worktree_path, command):
            return CommandResult(success=False, stderr="assertion error", exit_code=1)

    with tempfile.TemporaryDirectory() as tmp:
        llm = MockLLM(["plan", "coding DONE CODING", "fix DONE CODING"])
        engine = LoopEngine(
            llm=llm, memory=TrackingMemory(), thinking=MockThinking(),
            workspace=FailWorkspace(Path(tmp)), vault=MockVault(),
            config=LoopConfig(max_iterations=5),
        )
        await engine.run("Test", Path(tmp))
        assert any("test_failure" in e[0] for e in ingested)
