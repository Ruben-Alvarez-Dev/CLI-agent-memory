"""TaskContext — persisted task state."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from CLI_agent_memory.domain.types import AgentState

STATE_FILE = ".agent-memory-state.json"


class TaskContext:
    def __init__(self, worktree_path: Path):
        self.worktree_path = worktree_path
        self.state: AgentState = AgentState.PLANNING
        self.task_description: str = ""
        self.plan: str = ""
        self.progress: str = ""
        self.iteration: int = 0
        self.task_id: str = ""

    def save(self) -> None:
        path = self.worktree_path / STATE_FILE
        data = {
            "state": self.state.value,
            "task_description": self.task_description,
            "plan": self.plan,
            "progress": self.progress,
            "iteration": self.iteration,
            "task_id": self.task_id,
            "worktree_path": str(self.worktree_path),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self) -> bool:
        path = self.worktree_path / STATE_FILE
        if not path.exists():
            return False
        data = json.loads(path.read_text(encoding="utf-8"))
        self.state = AgentState(data["state"])
        self.task_description = data["task_description"]
        self.plan = data.get("plan", "")
        self.progress = data.get("progress", "")
        self.iteration = data.get("iteration", 0)
        self.task_id = data.get("task_id", "")
        return True

    def transition(self, to: AgentState) -> None:
        self.state = to
        self.save()

    @staticmethod
    def find_in_worktree(worktree_path: Path) -> TaskContext | None:
        ctx = TaskContext(worktree_path)
        if ctx.load():
            return ctx
        return None

    def generate_task_id(self, branch_name: str) -> str:
        self.task_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, branch_name))
        return self.task_id
