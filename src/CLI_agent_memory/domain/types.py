"""Domain types — Pydantic models and enums. Pure business logic, 0 external deps."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    PLANNING = "PLANNING"
    CODING = "CODING"
    VERIFICATION = "VERIFICATION"
    DONE = "DONE"
    FAILED = "FAILED"


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMResponse(BaseModel):
    text: str
    files_edited: int = 0
    tool_calls: list[dict] = Field(default_factory=list)
    finish_reason: str = "stop"


class CommandResult(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1


class ContextPack(BaseModel):
    context_text: str = ""
    sources: list[str] = Field(default_factory=list)
    token_count: int = 0


class Memory(BaseModel):
    id: str
    content: str
    tags: list[str] = Field(default_factory=list)
    scope: str = "session"
    importance: float = 0.5
    created_at: str = ""


class Decision(BaseModel):
    id: str
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""


class ThinkingStep(BaseModel):
    step_number: int
    thought: str
    next_needed: bool = True


class ThinkingResult(BaseModel):
    session_id: str
    problem: str
    steps: list[ThinkingStep] = Field(default_factory=list)
    conclusion: str = ""


class Plan(BaseModel):
    id: str
    task_id: str
    goal: str
    steps: list[str] = Field(default_factory=list)
    status: str = "active"


class VaultEntry(BaseModel):
    folder: str
    filename: str
    content: str
    path: str


class TaskResult(BaseModel):
    task_id: str
    status: AgentState
    worktree_path: str
    plan: str = ""
    files_modified: list[str] = Field(default_factory=list)
    tests_passed: bool = False
    error: str = ""
    duration_seconds: float = 0.0


class HealthStatus(BaseModel):
    status: str
    service: str
    uptime_seconds: float
    connections: dict[str, str] = Field(default_factory=dict)


class ServiceMetrics(BaseModel):
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_in_progress: int = 0
    total_tool_calls: int = 0
    total_errors: int = 0
    uptime_seconds: float = 0.0
