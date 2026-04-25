"""CLI helpers — auto-detection, description resolution.""" 

from __future__ import annotations
import sys
from pathlib import Path

# Test command detectors: (filename, command) — SPEC-CLI-01
_TEST_DETECTORS = [
    ("pyproject.toml", "python -m pytest"),
    ("setup.py", "python -m pytest"),
    ("package.json", "npm test"),
    ("Makefile", "make test"),
    ("Cargo.toml", "cargo test"),
    ("go.mod", "go test ./..."),
    ("pom.xml", "mvn test"),
]


def auto_detect_test_command(repo: Path) -> str:
    """"Auto-detect test command from repo files (SPEC-CLI-01)."""
    for filename, cmd in _TEST_DETECTORS:
        if (repo / filename).exists():
            return cmd
    return ""


def resolve_description(args) -> str:
    """Resolve task description from args or --from-file."""
    from_file = getattr(args, "from_file", "")
    desc = getattr(args, "description", None)

    if from_file:
        path = Path(from_file)
        if not path.exists():
            print(f"Error: file not found: {from_file}", file=sys.stderr)
            sys.exit(2)
        return path.read_text(encoding="utf-8").strip()
    if desc:
        return desc
    print("Error: provide a task description or --from-file", file=sys.stderr)
    sys.exit(2)
