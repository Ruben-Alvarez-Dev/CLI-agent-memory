"""File operations — parsing LLM output and detecting changes."""

from __future__ import annotations
import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_and_write_files(worktree_path: Path, text: str) -> int:
    """Parse files from LLM response using multiple formats. Returns count written."""
    files_edited = 0

    # Format 1: **File: path**\n```lang\n...\n```
    for match in re.finditer(r"\*\*File:\s*(.*?)\*\*\s*```[a-z]*\n(.*?)```", text, re.DOTALL):
        path, content = match.group(1).strip(), match.group(2).strip()
        if path and content:
            write_safe(worktree_path, path, content + "\n")
            files_edited += 1

    # Format 2: ```lang\n# path: file.py\n...\n```
    if files_edited == 0:
        for match in re.finditer(r"```[a-z]*\n#\s*path:\s*(\S+)\n(.*?)```", text, re.DOTALL):
            path, content = match.group(1), match.group(2).strip()
            if path and content:
                write_safe(worktree_path, path, content + "\n")
                files_edited += 1

    # Format 3: ```\nFILE: path\n...\n```
    if files_edited == 0:
        for match in re.finditer(r"```\nFILE:\s*(\S+)\n(.*?)```", text, re.DOTALL):
            path, content = match.group(1), match.group(2).strip()
            if path and content:
                write_safe(worktree_path, path, content + "\n")
                files_edited += 1

    return files_edited


def detect_git_changes(worktree_path: Path) -> list[str]:
    """Detect files changed via git diff (fallback when parsing fails)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=worktree_path, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return [f for f in result.stdout.strip().split("\n") if f]
    except (subprocess.TimeoutExpired, Exception):
        pass
    return []


def write_safe(worktree_path: Path, file_path: str, content: str) -> None:
    """Write a file, ensuring parent dirs exist. Rejects paths outside worktree."""
    full = (worktree_path / file_path).resolve()
    if not str(full).startswith(str(worktree_path.resolve())):
        logger.warning("Rejected path traversal: %s", file_path)
        return
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


def trim_history(history: list, keep_last: int = 6) -> None:
    """Trim message history keeping system prompt + last N messages."""
    if len(history) <= keep_last + 1:
        return
    system = history[0] if history and history[0].role == "system" else None
    tail = history[-keep_last:] if len(history) >= keep_last else history[1:]
    history.clear()
    if system:
        history.append(system)
    history.extend(tail)
