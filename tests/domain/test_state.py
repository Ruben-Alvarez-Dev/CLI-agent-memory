"""Tests for domain/state.py — SPEC-D5."""

import json
import tempfile
from pathlib import Path

from CLI_agent_memory.domain.state import TaskContext, STATE_FILE
from CLI_agent_memory.domain.types import AgentState


def test_save_creates_state_file():
    """AC-D5.2: save() writes .agent-memory-state.json."""
    with tempfile.TemporaryDirectory() as tmp:
        ctx = TaskContext(Path(tmp))
        ctx.task_description = "Test task"
        ctx.save()
        assert (Path(tmp) / STATE_FILE).exists()


def test_load_reads_state_file():
    """AC-D5.1: JSON serializable/deserializable."""
    with tempfile.TemporaryDirectory() as tmp:
        ctx = TaskContext(Path(tmp))
        ctx.task_description = "Test task"
        ctx.task_id = "test-123"
        ctx.save()

        ctx2 = TaskContext(Path(tmp))
        assert ctx2.load()
        assert ctx2.task_description == "Test task"
        assert ctx2.task_id == "test-123"


def test_transition_changes_and_saves():
    """AC-D5.2: transition() changes state AND calls save()."""
    with tempfile.TemporaryDirectory() as tmp:
        ctx = TaskContext(Path(tmp))
        ctx.transition(AgentState.CODING)
        assert ctx.state == AgentState.CODING

        ctx2 = TaskContext(Path(tmp))
        ctx2.load()
        assert ctx2.state == AgentState.CODING


def test_find_in_worktree():
    """find_in_worktree returns None if no state file."""
    with tempfile.TemporaryDirectory() as tmp:
        assert TaskContext.find_in_worktree(Path(tmp)) is None


def test_generate_task_id():
    """AC-D5.3: task_id is deterministic UUID4."""
    with tempfile.TemporaryDirectory() as tmp:
        ctx = TaskContext(Path(tmp))
        id1 = ctx.generate_task_id("test-branch")
        id2 = ctx.generate_task_id("test-branch")
        assert id1 == id2
        assert len(id1) == 36  # UUID format
