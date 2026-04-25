"""Doctor command — system health check for CLI-agent-memory."""

from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path

from CLI_agent_memory.config import AgentMemoryConfig


def run_doctor(repo: Path | None = None, config: AgentMemoryConfig | None = None) -> int:
    """Run system health check. Returns 0 if all critical, 1 if warnings."""
    config = config or AgentMemoryConfig()
    repo = repo or Path(".")
    checks = []

    # Git
    git_ver = _run_cmd("git --version", silent=True)
    checks.append(("Git", bool(git_ver), git_ver or "not found"))

    # Python
    checks.append(("Python", True, f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"))

    # Is a git repo?
    is_repo = (repo / ".git").exists()
    checks.append(("Git repo", is_repo, str(repo) if is_repo else "not a git repo"))

    # LLM availability
    lmstudio = _check_url(config.llm_base_url + "/v1/models", "LM Studio")
    checks.append(("LM Studio", lmstudio[0], lmstudio[1]))
    checks.append(("Ollama", _check_url("http://localhost:11434/api/tags", "Ollama")[0]))

    # MCP-agent-memory
    mcp_dir = config.mcp_server_dir
    if not mcp_dir:
        mcp_dir = str(Path.home() / "MCP-servers/MCP-agent-memory")
    mcp_python = Path(mcp_dir) / ".venv" / "bin" / "python3"
    mcp_ok = mcp_python.exists()
    checks.append(("MCP-agent-memory", mcp_ok, mcp_dir if mcp_ok else "not found"))

    # Test command auto-detection
    from CLI_agent_memory.cli_helpers import auto_detect_test_command
    test_cmd = auto_detect_test_command(repo)
    checks.append(("Test command", bool(test_cmd), test_cmd or "not detected"))

    # uv (needed for pip install on IPv6-restricted networks)
    has_uv = shutil.which("uv") is not None
    checks.append(("uv", has_uv, "available" if has_uv else "not found (pip may fail on IPv6)"))

    # Print results
    print("\nCLI-agent-memory — System Check")
    print("═" * 50)
    warnings = 0
    for name, ok, detail in checks:
        icon = "✅" if ok else "⚠️"
        print(f"  {icon} {name:<20} {detail}")
        if not ok:
            warnings += 1

    print("═" * 50)
    if warnings == 0:
        print("  All checks passed")
    else:
        print(f"  {warnings} warning(s)")
    return 0 if warnings == 0 else 1


def _check_url(url: str, name: str) -> tuple[bool, str]:
    try:
        import httpx
        resp = httpx.get(url, timeout=2.0)
        return (resp.status_code == 200, f"{url} (available)" if resp.status_code == 200 else f"{url} ({resp.status_code})")
    except Exception:
        return (False, f"{url} (unreachable)")


def _run_cmd(cmd: str, silent: bool = True) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if not silent else ""
    except Exception:
        return ""
