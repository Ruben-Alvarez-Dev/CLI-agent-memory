"""Tests for file_ops, prompts, cli_helpers, and doctor."""

from __future__ import annotations
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from CLI_agent_memory.domain.file_ops import parse_and_write_files, write_safe, trim_history
from CLI_agent_memory.domain.types import Message, ContextPack
from CLI_agent_memory.prompts.templates import (
    is_done_signal, DONE_SIGNALS, coding_prompt, verification_prompt,
    system_prompt, planning_prompt, intervention_prompt,
)
from CLI_agent_memory.cli_helpers import auto_detect_test_command


# ── file_ops ──────────────────────────────────────────────────────


class TestParseAndWriteFiles:
    """parse_and_write_files — 3 format support."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.wt = Path(self.tmp)

    def test_format1_bold_file(self):
        """Format 1: **File: path** ```lang ... ```"""
        text = "**File: src/main.py**\n```python\nprint('hello')\n```\n"
        count = parse_and_write_files(self.wt, text)
        assert count == 1
        assert (self.wt / "src" / "main.py").read_text() == "print('hello')\n"

    def test_format2_path_comment(self):
        """Format 2: ```lang\n# path: file.py\n...```"""
        text = "```\n# path: lib/helpers.py\ndef helper(): pass\n```\n"
        count = parse_and_write_files(self.wt, text)
        assert count == 1
        assert (self.wt / "lib" / "helpers.py").read_text().strip() == "def helper(): pass"

    def test_format3_file_directive(self):
        """Format 3: ```\nFILE: path\n...```"""
        text = "```\nFILE: README.md\n# My Project\n```\n"
        count = parse_and_write_files(self.wt, text)
        assert count == 1
        assert (self.wt / "README.md").read_text() == "# My Project\n"

    def test_multiple_files(self):
        """Parse multiple files in one response."""
        text = (
            "**File: a.py**\n```python\na = 1\n```\n"
            "**File: b.py**\n```python\nb = 2\n```\n"
        )
        count = parse_and_write_files(self.wt, text)
        assert count == 2

    def test_no_files_returns_zero(self):
        """No parsable files → returns 0."""
        count = parse_and_write_files(self.wt, "Just some text, no files here.")
        assert count == 0

    def test_empty_text(self):
        count = parse_and_write_files(self.wt, "")
        assert count == 0


class TestWriteSafe:
    """write_safe — path traversal protection."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.wt = Path(self.tmp)

    def test_normal_write(self):
        write_safe(self.wt, "src/app.py", "content")
        assert (self.wt / "src" / "app.py").read_text() == "content"

    def test_creates_parent_dirs(self):
        write_safe(self.wt, "a/b/c/deep.py", "deep")
        assert (self.wt / "a" / "b" / "c" / "deep.py").exists()

    def test_path_traversal_rejected(self):
        """Rejects ../ escaping worktree."""
        write_safe(self.wt, "../etc/passwd", "evil")
        # No file outside worktree should be created
        parent = Path(self.tmp).parent
        assert not (parent / "etc" / "passwd").exists()

    def test_absolute_path_rejected(self):
        """Rejects absolute paths."""
        write_safe(self.wt, "/tmp/evil.py", "evil")
        assert not Path("/tmp/evil.py").exists()


class TestTrimHistory:
    """trim_history — sliding window."""

    def _msgs(self, n: int) -> list[Message]:
        return [Message(role="system", content="sys")] + [
            Message(role="user" if i % 2 == 0 else "assistant", content=f"msg{i}")
            for i in range(n)
        ]

    def test_short_history_untouched(self):
        """History shorter than window → no change."""
        history = self._msgs(3)
        original_len = len(history)
        trim_history(history, keep_last=6)
        assert len(history) == original_len

    def test_trimming_keeps_system_and_tail(self):
        """Trims middle, keeps system + last N."""
        history = self._msgs(10)  # system + 10 = 11 total
        trim_history(history, keep_last=4)
        assert history[0].role == "system"
        assert len(history) == 5  # system + 4 tail
        assert history[-1].content == "msg9"

    def test_empty_history(self):
        trim_history([])
        assert len([]) == 0

    def test_no_system_prompt(self):
        """History without system prompt — just keep tail."""
        history = [Message(role="user", content=f"m{i}") for i in range(10)]
        trim_history(history, keep_last=3)
        assert len(history) == 3


# ── prompts/templates ────────────────────────────────────────────


class TestIsDoneSignal:
    """is_done_signal — multi-pattern detection."""

    def test_done_coding(self):
        assert is_done_signal("I finished. DONE CODING") is True

    def test_all_steps_complete(self):
        assert is_done_signal("Everything is ready. ALL STEPS COMPLETE") is True

    def test_implementation_complete(self):
        assert is_done_signal("Done. IMPLEMENTATION COMPLETE") is True

    def test_all_changes_applied(self):
        assert is_done_signal("ALL CHANGES APPLIED") is True

    def test_task_complete(self):
        assert is_done_signal("TASK COMPLETE") is True

    def test_case_insensitive(self):
        assert is_done_signal("done coding") is True
        assert is_done_signal("Done Coding") is True

    def test_signal_in_long_response_tail(self):
        """Signal at the end of a 500-char response is still detected."""
        text = "x" * 400 + "I'm done now. DONE CODING"
        assert is_done_signal(text) is True

    def test_signal_buried_in_middle_long(self):
        """Signal in middle of 500+ char response — tail doesn't contain it."""
        text = "x" * 250 + "DONE CODING" + "y" * 250
        assert is_done_signal(text) is False

    def test_no_signal(self):
        assert is_done_signal("I'll keep working on this...") is False

    def test_empty_string(self):
        assert is_done_signal("") is False


class TestPromptGeneration:
    """Template functions return expected strings."""

    def test_system_prompt(self):
        assert "coding" in system_prompt()
        assert "autonomous" in system_prompt()

    def test_planning_prompt(self):
        ctx = ContextPack(context_text="some context")
        result = planning_prompt("build a thing", ctx)
        assert "build a thing" in result
        assert "PLAN.md" in result

    def test_coding_prompt_with_files(self):
        ctx = ContextPack(context_text="ctx")
        result = coding_prompt("plan text", ctx, files=["a.py", "b.py"])
        assert "plan text" in result
        assert "a.py" in result
        assert "Format 1" in result
        assert "DONE CODING" in result

    def test_verification_prompt(self):
        result = verification_prompt("FAIL: test_foo", "plan text", files_changed=["a.py"])
        assert "FAIL: test_foo" in result
        assert "a.py" in result
        assert "minimal change" in result

    def test_intervention_prompt_no_edits(self):
        result = intervention_prompt("no_edits")
        assert "no file changes" in result.lower()

    def test_intervention_prompt_same_error(self):
        result = intervention_prompt("same_error")
        assert "same error" in result.lower()

    def test_intervention_prompt_with_context(self):
        result = intervention_prompt("no_edits", recent_context="tried X, tried Y")
        assert "tried X" in result


# ── cli_helpers ───────────────────────────────────────────────────


class TestAutoDetectTestCommand:
    """auto_detect_test_command — file-based detection."""

    def test_python_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").touch()
        assert auto_detect_test_command(tmp_path) == "python -m pytest"

    def test_python_setup(self, tmp_path):
        (tmp_path / "setup.py").touch()
        assert auto_detect_test_command(tmp_path) == "python -m pytest"

    def test_node(self, tmp_path):
        (tmp_path / "package.json").touch()
        assert auto_detect_test_command(tmp_path) == "npm test"

    def test_makefile(self, tmp_path):
        (tmp_path / "Makefile").touch()
        assert auto_detect_test_command(tmp_path) == "make test"

    def test_rust(self, tmp_path):
        (tmp_path / "Cargo.toml").touch()
        assert auto_detect_test_command(tmp_path) == "cargo test"

    def test_go(self, tmp_path):
        (tmp_path / "go.mod").touch()
        assert auto_detect_test_command(tmp_path) == "go test ./..."

    def test_java(self, tmp_path):
        (tmp_path / "pom.xml").touch()
        assert auto_detect_test_command(tmp_path) == "mvn test"

    def test_no_match(self, tmp_path):
        assert auto_detect_test_command(tmp_path) == ""

    def test_empty_dir(self, tmp_path):
        assert auto_detect_test_command(tmp_path) == ""
