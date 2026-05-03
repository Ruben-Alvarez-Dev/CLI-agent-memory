"""CLI-agent-memory — Autonomous coding agent CLI."""
from pathlib import Path
import json

def _get_version() -> str:
    """Read version from install/manifest.json (single source of truth)."""
    for manifest_path in [
        Path(__file__).resolve().parent.parent.parent / "install" / "manifest.json",
        Path(__file__).resolve().parent.parent / "install" / "manifest.json",
    ]:
        if manifest_path.exists():
            try:
                return json.loads(manifest_path.read_text()).get("version", "0.0.0")
            except (json.JSONDecodeError, OSError):
                pass
    return "0.0.0"

__version__ = _get_version()
__name__ = "CLI-agent-memory"
