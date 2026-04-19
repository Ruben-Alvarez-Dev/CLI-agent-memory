"""Git worktree provider — manages isolated workspaces."""

from __future__ import annotations

import subprocess
from pathlib import Path

from CLI_agent_memory.domain.protocols import WorkspaceProtocol
from CLI_agent_memory.domain.types import CommandResult


class GitWorktreeProvider(WorkspaceProtocol):
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.worktree_dir = repo_path / ".worktrees"
        self.worktree_dir.mkdir(exist_ok=True)

    def create(self, branch_name: str, base_ref: str = "HEAD") -> Path:
        wt_path = self.worktree_dir / branch_name.replace("/", "_")
        subprocess.run(
            ["git", "worktree", "add", "-b", branch_name, str(wt_path), base_ref],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )
        return wt_path

    def remove(self, branch_name: str, force: bool = False) -> bool:
        wt_path = self.worktree_dir / branch_name.replace("/", "_")
        try:
            subprocess.run(
                ["git", "worktree", "remove", "--force" if force else "", str(wt_path)],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def run_command(self, worktree_path: Path, command: str) -> CommandResult:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return CommandResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(success=False, stderr="Command timed out", exit_code=-1)

    def read_file(self, worktree_path: Path, file_path: str) -> str | None:
        full = worktree_path / file_path
        return full.read_text(encoding="utf-8") if full.exists() else None

    def write_file(self, worktree_path: Path, file_path: str, content: str) -> None:
        full = worktree_path / file_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")

    def list_files(self, worktree_path: Path, pattern: str = "**/*.py") -> list[str]:
        return [str(p.relative_to(worktree_path)) for p in worktree_path.glob(pattern)]
