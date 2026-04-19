"""Tests for domain/types.py — SPEC-D1."""

from enum import Enum

from CLI_agent_memory.domain.types import (
    AgentState,
    CommandResult,
    ContextPack,
    Decision,
    LLMResponse,
    Memory,
    Message,
    Plan,
    TaskResult,
    ThinkingResult,
    ThinkingStep,
    VaultEntry,
)


def test_all_types_are_pydantic_or_enum():
    """AC-D1.1: All types are Pydantic models or Enums."""
    enum_types = [AgentState]
    pydantic_types = [
        Message, LLMResponse, CommandResult, ContextPack,
        Memory, Decision, ThinkingStep, ThinkingResult,
        Plan, VaultEntry, TaskResult,
    ]
    for t in enum_types:
        assert issubclass(t, Enum)
    for t in pydantic_types:
        assert hasattr(t, "model_validate"), f"{t.__name__} is not a Pydantic model"


def test_json_serialization():
    """AC-D1.4: Serializable to JSON."""
    msg = Message(role="user", content="hello")
    json_str = msg.model_dump_json()
    restored = Message.model_validate_json(json_str)
    assert restored.content == "hello"


def test_agent_state_values():
    """AC-D1.1: AgentState enum has correct values."""
    assert AgentState.PLANNING.value == "PLANNING"
    assert AgentState.CODING.value == "CODING"
    assert AgentState.VERIFICATION.value == "VERIFICATION"
    assert AgentState.DONE.value == "DONE"
    assert AgentState.FAILED.value == "FAILED"
