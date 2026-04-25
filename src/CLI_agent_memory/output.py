"""Output formatters — consistent JSON/text output for all commands."""

from __future__ import annotations
import json
import sys
from typing import Any


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
