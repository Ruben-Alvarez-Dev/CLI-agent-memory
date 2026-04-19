"""CLI entry point — argparse, 0 business logic."""

from __future__ import annotations
import argparse
import asyncio
import sys

from CLI_agent_memory.config import AgentMemoryConfig
from CLI_agent_memory.domain.exit_codes import EXIT_OK, EXIT_USAGE


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="CLI-agent-memory", description="Autonomous coding agent")
    sub = p.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run an autonomous task")
    run_p.add_argument("description", help="Task description")
    run_p.add_argument("--repo", default=".", help="Target repo (default: .)")
    run_p.add_argument("--llm", default="lmstudio", help="LLM backend: lmstudio | ollama")
    run_p.add_argument("--memory", default="http://127.0.0.1:3050", help="MCP memory URL")
    run_p.add_argument("--max-iter", type=int, default=50, help="Max iterations")
    run_p.add_argument("--dry-run", action="store_true", help="Simulate")
    run_p.add_argument("--json", action="store_true", help="JSON output")

    sub.add_parser("version", help="Show version")

    cfg_p = sub.add_parser("config", help="Show configuration")
    cfg_p.add_argument("--json", action="store_true", help="JSON output")

    return p


def cmd_run(args: argparse.Namespace, config: AgentMemoryConfig) -> int:
    from pathlib import Path
    from CLI_agent_memory.infra.llm import create_llm_client
    from CLI_agent_memory.infra.workspace.git_worktree import GitWorktreeProvider
    from CLI_agent_memory.infra.adapters.mcp.memory_http import MCPMemoryAdapter
    from CLI_agent_memory.infra.adapters.null.memory_null import NullMemoryAdapter
    from CLI_agent_memory.infra.adapters.null.thinking_null import NullThinkingAdapter
    from CLI_agent_memory.infra.adapters.null.vault_null import NullVaultAdapter
    from CLI_agent_memory.domain.loop import LoopEngine
    from CLI_agent_memory.config import LoopConfig

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        print(f"Error: {repo} is not a git repo", file=sys.stderr)
        return 1

    llm = create_llm_client(args.llm, config)
    memory = MCPMemoryAdapter(args.memory) if args.memory else NullMemoryAdapter()
    thinking = NullThinkingAdapter()
    workspace = GitWorktreeProvider(repo)
    vault = NullVaultAdapter()

    if not llm.is_available():
        print(f"Error: LLM '{args.llm}' not available", file=sys.stderr)
        return 20

    if args.dry_run:
        print(f"[DRY RUN] {args.description}\n  Repo: {repo}\n  LLM: {args.llm}\n  Mem: {args.memory}")
        return EXIT_OK

    loop_cfg = LoopConfig(max_iterations=args.max_iter, max_stagnation=config.max_stagnation,
                          test_command=config.test_command)
    engine = LoopEngine(llm=llm, memory=memory, thinking=thinking,
                        workspace=workspace, vault=vault, config=loop_cfg)
    result = asyncio.run(engine.run(args.description, repo))

    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        print(f"Task {result.task_id}: {result.status.value}")
        if result.error:
            print(f"Error: {result.error}")
        print(f"Duration: {result.duration_seconds:.1f}s")

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
    elif args.command == "version":
        return cmd_version()
    elif args.command == "config":
        if args.json:
            print(config.model_dump_json(indent=2))
        else:
            for k, v in config.model_dump().items():
                print(f"  {k}: {v}")
        return EXIT_OK
    else:
        parser.print_help()
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
