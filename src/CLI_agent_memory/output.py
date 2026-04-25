"""Output formatters — consistent JSON/text output, capture, dispatch."""

from __future__ import annotations
import io
import json
import sys
from typing import Any

from CLI_agent_memory.config import AgentMemoryConfig
from CLI_agent_memory.domain.exit_codes import EXIT_OK


def json_output(data: Any) -> None:
    """Print data as formatted JSON to stdout."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            data = {"raw": data}
    if hasattr(data, "model_dump"):
        print(data.model_dump_json(indent=2))
    else:
        print(json.dumps(data, indent=2, default=str))


def text_output(title: str, items: list[tuple[str, str]] | None = None, message: str = "") -> None:
    """Print structured text output."""
    if title:
        print(title)
    if items:
        for key, val in items:
            print(f"  {key}: {val}")
    if message:
        print(message)


def capture_stdout(fn, args, config):
    """Run handler capturing stdout; return (exit_code, text)."""
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        code = fn(args, config)
    finally:
        sys.stdout = old
    return code, buf.getvalue()


def json_wrap(args, code: int, text: str) -> int:
    """Print text normally, or as JSON if --json is set."""
    if not args.json:
        print(text, end="")
        return code
    json_output({"command": args.command, "exit_code": code, "output": text.strip()})
    return code


def cmd_config(args, config: AgentMemoryConfig) -> int:
    """Show current configuration as text or JSON."""
    if args.json:
        print(config.model_dump_json(indent=2))
    else:
        for k, v in config.model_dump().items():
            print(f"  {k}: {v}")
    return EXIT_OK
