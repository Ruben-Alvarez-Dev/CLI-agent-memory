"""CLI subcommands — status, cleanup, think, recall, remember, decisions."""

from __future__ import annotations
import asyncio
import shutil
import sys
from pathlib import Path

from CLI_agent_memory.config import AgentMemoryConfig


def cmd_status(args: argparse.Namespace, config: AgentMemoryConfig) -> int:
    """Show active/paused tasks in a repo."""
    # Avoid circular import — domain only depends on protocols
    from CLI_agent_memory.domain.state import TaskContext
    from CLI_agent_memory.domain.types import AgentState
    repo = Path(args.repo).resolve()
    wt_base = repo / (config.worktree_dir or ".worktrees")
    if not wt_base.exists():
        print("No active tasks.")
        return 0
    found = False
    for wt_dir in sorted(wt_base.iterdir()):
        if not wt_dir.is_dir():
            continue
        ctx = TaskContext.find_in_worktree(wt_dir)
        if ctx:
            status_icon = "🟢" if ctx.state not in (AgentState.DONE, AgentState.FAILED) else "⚫"
            print(f"  {status_icon} {ctx.task_id}  {ctx.state.value:<14}  iter={ctx.iteration}  {wt_dir.name}")
            if args.verbose and ctx.task_description:
                print(f"      {ctx.task_description[:80]}")
            found = True
    if not found:
        print("No tasks found.")
    return 0


def cmd_cleanup(args: argparse.Namespace, config: AgentMemoryConfig) -> int:
    """Remove completed/failed worktrees."""
    from CLI_agent_memory.domain.state import TaskContext
    from CLI_agent_memory.domain.types import AgentState
    repo = Path(args.repo).resolve()
    wt_base = repo / (config.worktree_dir or ".worktrees")
    if not wt_base.exists():
        print("Nothing to clean up.")
        return 0
    removed = 0
    for wt_dir in sorted(wt_base.iterdir()):
        if not wt_dir.is_dir():
            continue
        ctx = TaskContext.find_in_worktree(wt_dir)
        if ctx and ctx.state in (AgentState.DONE, AgentState.FAILED):
            if args.dry_run:
                print(f"  [DRY] Would remove {wt_dir.name} ({ctx.state.value})")
            else:
                shutil.rmtree(wt_dir, ignore_errors=True)
                print(f"  Removed {wt_dir.name} ({ctx.state.value})")
            removed += 1
    if args.all:
        for wt_dir in sorted(wt_base.iterdir()):
            if not wt_dir.is_dir():
                continue
            if args.dry_run:
                print(f"  [DRY] Would remove {wt_dir.name} (all)")
            else:
                shutil.rmtree(wt_dir, ignore_errors=True)
                print(f"  Removed {wt_dir.name} (all)")
            removed += 1
    print(f"  {removed} worktree(s) {'would be ' if args.dry_run else ''}removed.")
    return 0


def cmd_think(args: argparse.Namespace, config: AgentMemoryConfig) -> int:
    """Run a thinking chain via MCP or local adapter."""
    from CLI_agent_memory.infra.adapters.protocol_factory import ProtocolFactory
    factory = ProtocolFactory(config)
    thinking = factory.create_thinking()
    result = asyncio.run(thinking.think(args.problem, max_steps=args.steps))
    if hasattr(result, "steps") and result.steps:
        for step in result.steps:
            print(f"  Step {step.step_number}: {step.thought[:120]}")
        print(f"  Conclusion: {result.conclusion[:200]}")
    else:
        print(result)
    return 0


def cmd_recall(args: argparse.Namespace, config: AgentMemoryConfig) -> int:
    """Search memories via MCP or local adapter."""
    from CLI_agent_memory.infra.adapters.protocol_factory import ProtocolFactory
    factory = ProtocolFactory(config)
    memory = factory.create_memory()
    results = asyncio.run(memory.search(args.query, limit=args.limit))
    if not results:
        print("No memories found.")
        return 0
    for mem in results[:args.limit]:
        content = mem if isinstance(mem, str) else str(getattr(mem, "content", mem))
        print(f"  • {content[:200]}")
    return 0


def cmd_remember(args: argparse.Namespace, config: AgentMemoryConfig) -> int:
    """Store a memory via MCP or local adapter."""
    from CLI_agent_memory.infra.adapters.protocol_factory import ProtocolFactory
    factory = ProtocolFactory(config)
    memory = factory.create_memory()
    tags = args.tags.split(",") if args.tags else []
    asyncio.run(memory.store(args.content, tags=tags))
    print(f"  Stored: {args.content[:80]}")
    return 0


def cmd_decisions(args: argparse.Namespace, config: AgentMemoryConfig) -> int:
    """List or search decisions via MCP or local adapter."""
    from CLI_agent_memory.infra.adapters.protocol_factory import ProtocolFactory
    factory = ProtocolFactory(config)
    memory = factory.create_memory()
    # Decisions are stored as memories with "decision" tag
    results = asyncio.run(memory.search(args.query or "", limit=args.limit))
    if not results:
        print("No decisions found.")
        return 0
    for mem in results[:args.limit]:
        content = mem if isinstance(mem, str) else str(getattr(mem, "content", mem))
        print(f"  • {content[:200]}")
    return 0
