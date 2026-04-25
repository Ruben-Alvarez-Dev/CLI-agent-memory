"""CLI extra commands — cancel, plan, db."""

from __future__ import annotations
import asyncio
import sqlite3
import sys
from pathlib import Path

from CLI_agent_memory.config import AgentMemoryConfig


def cmd_cancel(args: argparse.Namespace, config: AgentMemoryConfig) -> int:
    """Cancel an active task by marking it FAILED."""
    from CLI_agent_memory.domain.state import TaskContext
    from CLI_agent_memory.domain.types import AgentState
    repo = Path(args.repo).resolve()
    wt_base = repo / (config.worktree_dir or ".worktrees")
    if not wt_base.exists():
        print("No active tasks.", file=sys.stderr)
        return 1
    for wt_dir in sorted(wt_base.iterdir()):
        if not wt_dir.is_dir():
            continue
        ctx = TaskContext.find_in_worktree(wt_dir)
        if ctx and ctx.task_id == args.task_id and ctx.state not in (AgentState.DONE, AgentState.FAILED):
            ctx.transition(AgentState.FAILED)
            print(f"  Cancelled {args.task_id}")
            return 0
    print(f"Task '{args.task_id}' not found or already done.", file=sys.stderr)
    return 1


def cmd_plan(args: argparse.Namespace, config: AgentMemoryConfig) -> int:
    """Run standalone planning (LLM generates plan, no execution)."""
    from CLI_agent_memory.infra.llm import create_llm_client
    llm = create_llm_client(config.llm_backend, config, model=args.model or config.llm_model)
    if not llm.is_available():
        print(f"Error: LLM '{config.llm_backend}' not available", file=sys.stderr)
        return 20
    sys_prompt = "You are a planning agent. Create a detailed, numbered plan."
    resp = asyncio.run(llm.generate(args.task, [{"role": "system", "content": sys_prompt}], temperature=0.5))
    if args.save:
        out = Path(args.save)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(resp.text, encoding="utf-8")
        print(f"  Plan saved to {out}")
    else:
        print(resp.text)
    return 0


def cmd_db(args: argparse.Namespace, config: AgentMemoryConfig) -> int:
    """Inspect or manage the local SQLite database."""
    repo = Path(args.repo).resolve()
    db = repo / (config.db_path or ".agent-memory/agent-memory.db")
    if not db.exists():
        print(f"No database found at {db}")
        return 1
    if args.tables:
        conn = sqlite3.connect(str(db))
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        print("Tables:")
        for (name,) in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
            print(f"  {name:<25} {count} rows")
        conn.close()
    elif args.query:
        conn = sqlite3.connect(str(db))
        try:
            cursor = conn.execute(args.query)
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description] if cursor.description else []
            if cols:
                print("  " + " | ".join(f"{c:<20}" for c in cols))
                for row in rows:
                    print("  " + " | ".join(str(v)[:20] for v in row))
            else:
                print(f"  {len(rows)} row(s) affected.")
        except sqlite3.Error as e:
            print(f"SQL error: {e}", file=sys.stderr)
            return 1
        finally:
            conn.close()
    else:
        print(f"  Database: {db} ({db.stat().st_size} bytes)")
    return 0
