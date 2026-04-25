"""CLI entry point — dispatch, 0 business logic."""
from __future__ import annotations
import io
import signal
import sys
from pathlib import Path
from CLI_agent_memory.config import AgentMemoryConfig

from CLI_agent_memory.config import AgentMemoryConfig
from CLI_agent_memory.domain.exit_codes import EXIT_OK, EXIT_USAGE
from CLI_agent_memory.cli_helpers import auto_detect_test_command, resolve_description
from CLI_agent_memory.parser import build_parser


def _assemble_engine(repo: Path, config: AgentMemoryConfig, *,
                     llm_backend: str = "", model: str = "", test_cmd: str = ""):
    """Build LoopEngine with all adapters."""
    from CLI_agent_memory.infra.llm import create_llm_client
    from CLI_agent_memory.infra.workspace.git_worktree import GitWorktreeProvider
    from CLI_agent_memory.infra.adapters.protocol_factory import ProtocolFactory
    from CLI_agent_memory.domain.loop import LoopEngine
    from CLI_agent_memory.config import LoopConfig
    factory = ProtocolFactory(config)
    return LoopEngine(
        llm=create_llm_client(llm_backend or config.llm_backend, config, model=model or ""),
        memory=factory.create_memory(), thinking=factory.create_thinking(),
        vault=factory.create_vault(), workspace=GitWorktreeProvider(repo),
        config=LoopConfig(max_iterations=config.max_iterations, max_stagnation=config.max_stagnation,
                       test_command=test_cmd or config.test_command),
    )


def cmd_run(args, config: AgentMemoryConfig) -> int:
    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        print(f"Error: {repo} is not a git repo", file=sys.stderr)
        return 1
    description = resolve_description(args)
    if args.mcp_dir:
        config.mcp_server_dir = args.mcp_dir
    if args.force_local:
        config.force_local = True
    test_cmd = args.test_cmd or config.test_command or auto_detect_test_command(repo)
    if args.max_iter > 0:
        config.max_iterations = args.max_iter
    engine = _assemble_engine(repo, config, llm_backend=args.llm,
                             model=args.model or config.llm_model, test_cmd=test_cmd)
    if not engine.llm.is_available() and not args.dry_run:
        print(f"Error: LLM '{args.llm}' not available", file=sys.stderr)
        return 20
    if args.dry_run:
        print(f"[DRY RUN] {description}\n  Repo: {repo}\n  LLM: {args.llm}\n  Test: {test_cmd or 'auto'}")
        return EXIT_OK

    # SIGINT/SIGTERM → graceful exit with exit code 130/143
    _cancelled = False
    def _sig_handler(signum, _frame):
        nonlocal _cancelled
        _cancelled = True
        sig_name = signal.Signals(signum).name
        print(f"\n  Received {sig_name}, stopping gracefully...")
    original_sigint = signal.signal(signal.SIGINT, _sig_handler)
    original_sigterm = signal.signal(signal.SIGTERM, _sig_handler)
    try:
        result = __import__("asyncio").run(engine.run(description, repo))
    finally:
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)

    if _cancelled:
        from CLI_agent_memory.domain.exit_codes import EXIT_CANCELLED
        return EXIT_CANCELLED
    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        print(f"Task {result.task_id}: {result.status.value}\nDuration: {result.duration_seconds:.1f}s")
        if result.error:
            print(f"Error: {result.error}")
    return EXIT_OK if result.status.value == "DONE" else 10


def cmd_resume(args, config: AgentMemoryConfig) -> int:
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


def _json_run_dispatch(args, config, exit_code: int, captured: str) -> int:
    """Format captured text output as JSON when --json is set."""
    if not args.json:
        print(captured, end="")
        return exit_code
    from CLI_agent_memory.output import json_output
    json_output({"command": args.command, "exit_code": exit_code, "output": captured.strip()})
    return exit_code

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
        return run_doctor(Path("."), config)
    if args.command == "version":
        return cmd_version()
    if args.command == "config":
        print(config.model_dump_json(indent=2) if args.json else
              "\n".join(f"  {k}: {v}" for k, v in config.model_dump().items()))
        return EXIT_OK
    from CLI_agent_memory.commands import (cmd_status, cmd_cleanup, cmd_think, cmd_recall,
                                           cmd_remember, cmd_decisions)
    from CLI_agent_memory.commands_extra import cmd_cancel, cmd_plan, cmd_db
    handlers = {"status": cmd_status, "cleanup": cmd_cleanup, "think": cmd_think,
                "recall": cmd_recall, "remember": cmd_remember, "decisions": cmd_decisions,
                "cancel": cmd_cancel, "plan": cmd_plan, "db": cmd_db}
    handler = handlers.get(args.command)
    if handler:
        return handler(args, config)
    return EXIT_USAGE

if __name__ == "__main__":
    sys.exit(main())
