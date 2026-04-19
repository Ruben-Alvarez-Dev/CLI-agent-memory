"""Tests for domain/stagnation.py — SPEC-D4."""

from CLI_agent_memory.domain.stagnation import StagnationMonitor, StagnationResult


def test_no_stagnation_on_edits():
    """Normal operation with edits — not stagnant."""
    mon = StagnationMonitor(max_failures=3)
    result = mon.record_turn(files_edited=2)
    assert not result.is_stagnant


def test_stagnation_no_edits():
    """AC-D4.3: Detects >= 3 turns without edits."""
    mon = StagnationMonitor(max_failures=3)
    mon.record_turn(files_edited=0)
    mon.record_turn(files_edited=0)
    result = mon.record_turn(files_edited=0)
    assert result.is_stagnant
    assert result.reason == "no_edits"
    assert result.intervention != ""


def test_stagnation_same_error():
    """AC-D4.4: Detects >= 3 same errors."""
    mon = StagnationMonitor(max_failures=3)
    mon.record_turn(files_edited=1, current_error="TypeError: x")
    mon.record_turn(files_edited=1, current_error="TypeError: x")
    result = mon.record_turn(files_edited=1, current_error="TypeError: x")
    assert result.is_stagnant
    assert result.reason == "same_error"


def test_no_stagnation_different_errors():
    """Different errors should not trigger stagnation."""
    mon = StagnationMonitor(max_failures=3)
    mon.record_turn(files_edited=1, current_error="Error A")
    mon.record_turn(files_edited=1, current_error="Error B")
    result = mon.record_turn(files_edited=1, current_error="Error C")
    assert not result.is_stagnant


def test_reset_clears_counters():
    """reset() should clear all counters."""
    mon = StagnationMonitor(max_failures=3)
    mon.record_turn(files_edited=0)
    mon.record_turn(files_edited=0)
    mon.reset()
    result = mon.record_turn(files_edited=0)
    assert not result.is_stagnant


def test_stagnation_result_is_dataclass():
    """AC-D4.1: record_turn returns StagnationResult."""
    mon = StagnationMonitor()
    result = mon.record_turn(files_edited=1)
    assert isinstance(result, StagnationResult)
    assert hasattr(result, "is_stagnant")
    assert hasattr(result, "reason")
    assert hasattr(result, "intervention")


def test_custom_interventions():
    """AC-D4.2: Intervention prompts are configurable."""
    custom = {"no_edits": "Custom intervention"}
    mon = StagnationMonitor(max_failures=1, interventions=custom)
    result = mon.record_turn(files_edited=0)
    assert result.intervention == "Custom intervention"
