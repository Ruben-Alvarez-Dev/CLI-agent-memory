"""Argparse definitions for all CLI subcommands."""

from __future__ import annotations
import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build the full CLI argument parser."""
    p = argparse.ArgumentParser(prog="CLI-agent-memory", description="Autonomous coding agent")
    p.add_argument("--json", action="store_true", help="JSON output")
    sub = p.add_subparsers(dest="command")
    _add_run(sub)
    _add_resume(sub)
    _add_status(sub)
    _add_cleanup(sub)
    _add_think(sub)
    _add_recall(sub)
    _add_remember(sub)
    _add_decisions(sub)
    _add_cancel(sub)
    _add_plan(sub)
    _add_db(sub)
    sub.add_parser("version", help="Show version")
    sub.add_parser("doctor", help="System health check")
    _add_config(sub)
    return p


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse args, supporting --json before or after subcommand."""
    if argv is None:
        import sys as _sys
        argv = list(_sys.argv[1:])
    else:
        argv = list(argv)
    json_flag = "--json" in argv
    cleaned = [a for a in argv if a != "--json"]
    args = build_parser().parse_args(cleaned)
    args.json = json_flag or args.json
    return args


def _add_run(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("run", help="Run an autonomous task")
    p.add_argument("description", nargs="?", help="Task description")
    p.add_argument("--repo", default=".", help="Target repo (default: .)")
    p.add_argument("--from-file", dest="from_file", default="", help="Read description from file")
    p.add_argument("--llm", default="lmstudio", help="LLM backend: lmstudio | ollama")
    p.add_argument("--model", default="", help="LLM model (default: auto-detect)")
    p.add_argument("--mcp-dir", default="", help="MCP-agent-memory install dir")
    p.add_argument("--max-iter", type=int, default=0, help="Max iterations (default: config)")
    p.add_argument("--test-cmd", dest="test_cmd", default="", help="Test command (default: auto)")
    p.add_argument("--base-ref", default="HEAD", help="Git base ref (default: HEAD)")
    p.add_argument("--force-local", action="store_true", help="Force local adapters (no MCP)")
    p.add_argument("--dry-run", action="store_true", help="Simulate")


def _add_resume(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("resume", help="Resume a paused task")
    p.add_argument("task_id", help="Task ID to resume")
    p.add_argument("--repo", default=".", help="Target repo (default: .)")
    p.add_argument("--mcp-dir", default="", help="MCP-agent-memory install dir")
    p.add_argument("--force-local", action="store_true", help="Force local adapters")


def _add_status(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("status", help="Show active tasks")
    p.add_argument("--repo", default=".", help="Target repo (default: .)")
    p.add_argument("-v", "--verbose", action="store_true", help="Show descriptions")


def _add_cleanup(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("cleanup", help="Remove completed/failed worktrees")
    p.add_argument("--repo", default=".", help="Target repo (default: .)")
    p.add_argument("--all", action="store_true", help="Remove all worktrees")
    p.add_argument("--dry-run", action="store_true", help="Simulate")


def _add_think(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("think", help="Run a thinking chain")
    p.add_argument("problem", help="Problem to think through")
    p.add_argument("--steps", type=int, default=5, help="Max steps (default: 5)")


def _add_recall(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("recall", help="Search memories")
    p.add_argument("query", help="Search query")
    p.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")


def _add_remember(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("remember", help="Store a memory")
    p.add_argument("content", help="Content to remember")
    p.add_argument("--tags", default="", help="Comma-separated tags")


def _add_decisions(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("decisions", help="List/search decisions")
    p.add_argument("query", nargs="?", default="", help="Search query (optional)")
    p.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")


def _add_config(sub: argparse._SubParsersAction) -> None:
    sub.add_parser("config", help="Show configuration")


def _add_cancel(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("cancel", help="Cancel an active task")
    p.add_argument("task_id", help="Task ID to cancel")
    p.add_argument("--repo", default=".", help="Target repo (default: .)")


def _add_plan(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("plan", help="Generate a plan (no execution)")
    p.add_argument("task", help="Task description to plan")
    p.add_argument("--model", default="", help="LLM model (default: auto-detect)")
    p.add_argument("--save", default="", help="Save plan to file")


def _add_db(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("db", help="Inspect local SQLite database")
    p.add_argument("--repo", default=".", help="Target repo (default: .)")
    p.add_argument("--tables", action="store_true", help="List tables with row counts")
    p.add_argument("--query", default="", help="Run a SQL query")
