"""CLI entry point — argparse, 0 business logic."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from CLI_agent_memory.config import AgentMemoryConfig
from CLI_agent_memory.domain.exit_codes import EXIT_OK, EXIT_USAGE
from CLI_agent_memory.cli_helpers import auto_detect_test_command, resolve_description

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="CLI-agent-memory", description="Autonomous coding agent")
    sub = p.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run an autonomous task")
    run_p.add_argument("description", nargs="?", help="Task description")
    run_p.add_argument("--repo", default=".", help="Target repo (default: .)")
    run_p.add_argument("--from-file", dest="from_file", default="", help="Read description from file")
    run_p.add_argument("--llm", default="lmstudio", help="LLM backend: lmstudio | ollama")
    run_p.add_argument("--model", default="", help="LLM model (default: auto-detect)")
    run_p.add_argument("--mcp-dir", default="", help="MCP-agent-memory install dir")
    run_p.add_argument("--max-iter", type=int, default=0, help="Max iterations (default: config)")
    run_p.add_argument("--test-cmd", dest="test_cmd", default="", help="Test command (default: auto)")
    run_p.add_argument("--base-ref", default="HEAD", help="Git base ref (default: HEAD)")
    run_p.add_argument("--force-local", action="store_true", help="Force local adapters (no MCP)")
    run_p.add_argument("--dry-run", action="store_true", help="Simulate")
    run_p.add_argument("--json", action="store_true", help="JSON output")

    sub.add_parser("version", help="Show version")

    resume_p = sub.add_parser("resume", help="Resume a paused task")
    resume_p.add_argument("task_id", help="Task ID to resume")
    resume_p.add_argument("--repo", default=".", help="Target repo (default: .)")
    resume_p.add_argument("--mcp-dir", default="", help="MCP-agent-memory install dir")
    resume_p.add_argument("--force-local", action="store_true", help="Force local adapters")
    resume_p.add_argument("--json", action="store_true", help="JSON output")

    sub.add_parser("doctor", help="System health check")

    cfg_p = sub.add_parser("config", help="Show configuration")
    cfg_p.add_argument("--json", action="store_true", help="JSON output")

    return p

def _assemble_engine(repo: Path, config: AgentMemoryConfig, *,
                     llm_backend: str = "", model: str = "", test_cmd: str = ""):
    """Build LoopEngine with all adapters (used by run and resume)."""
    from CLI_agent_memory.infra.llm import create_llm_client
    from CLI_agent_memory.infra.workspace.git_worktree import GitWorktreeProvider
    from CLI_agent_memory.infra.adapters.protocol_factory import ProtocolFactory
    from CLI_agent_memory.domain.loop import LoopEngine
    from CLI_agent_memory.config import LoopConfig
    factory = ProtocolFactory(config)
    cmd = test_cmd or config.test_command
    return LoopEngine(
        llm=create_llm_client(llm_backend or config.llm_backend, config, model=model or ""),
        memory=factory.create_memory(), thinking=factory.create_thinking(),
        vault=factory.create_vault(), workspace=GitWorktreeProvider(repo),
        config=LoopConfig(max_iterations=config.max_iterations, max_stagnation=config.max_stagnation,
                       test_command=cmd),
    )
    return EXIT_OK if result.status.value == "DONE" else 10

def cmd_resume(args: argparse.Namespace, config: AgentMemoryConfig) -> int:
    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        print(f"Error: {repo} is not a git repo", file=sys.stderr)
        return 1
    if args.mcp_dir:
        config.mcp_server_dir = args.mcp_dir
    if args.force_local:
        config.force_local = True
    engine = _assemble_engine(repo, config)
    result = __import__("asyncio").run(engine.resume(args.task_id, repo))
    if result is None:
        print(f"Error: no active task found with ID '{args.task_id}'", file=sys.stderr)
        return 1
    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        msg = f"Task {result.task_id}: {result.status.value} (resumed)"
        print(msg + (f"\nError: {result.error}" if result.error else ""))
    return EXIT_OK if result.status.value == "DONE" else 10


def cmd_version() -> int:
    from CLI_agent_memory import __version__
    print(f"CLI-agent-memory v{__version__}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_USAGE
    config = AgentMemoryConfig()
    if args.command == "run":
        return cmd_run(args, config)
    if args.command == "resume":
        return cmd_resume(args, config)
    if args.command == "doctor":
        from CLI_agent_memory.doctor import run_doctor
        repo = Path(args.repo).resolve() if hasattr(args, "repo") else Path(".")
        return run_doctor(repo, config)
    if args.command == "version":
        return cmd_version()
    if args.command == "config":
        print(config.model_dump_json(indent=2) if args.json else
              "\n".join(f"  {k}: {v}" for k, v in config.model_dump().items()))
        return EXIT_OK
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
