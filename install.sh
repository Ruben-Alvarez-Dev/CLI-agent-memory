#!/bin/bash
# CLI-agent-memory — One-liner installer
# Usage: curl -fsSL <url>/install.sh | bash
# Or:    bash install.sh [install_dir]
set -euo pipefail

INSTALL_DIR="${1:-$HOME/CLI-agent-memory}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Auto-bootstrap (curl | bash) ──
if [ ! -f "$SCRIPT_DIR/src/CLI_agent_memory/cli.py" ]; then
    REPO_URL="https://github.com/Ruben-Alvarez-Dev/CLI-agent-memory.git"
    TMPDIR=$(mktemp -d -t cli-mem.XXXXXX)
    echo "⬇  Downloading CLI-agent-memory..."
    git clone --depth 1 "$REPO_URL" "$TMPDIR/repo" 2>/dev/null
    bash "$TMPDIR/repo/install.sh" "$@"
    rm -rf "$TMPDIR"
    exit $?
fi

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║   CLI-agent-memory — Installer                    ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# ── 1. Check Python ──
PYTHON="${PYTHON:-python3.12}"
if ! command -v "$PYTHON" &>/dev/null; then
    PYTHON="python3"
    if ! command -v "$PYTHON" &>/dev/null; then
        echo "  ✗ Python 3.12+ required. Install from https://python.org"
        exit 1
    fi
fi
PYVER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  ✓ Python $PYVER found"

# ── 2. Virtual environment ──
echo "1/4 Creating virtual environment..."
$PYTHON -m venv "$SCRIPT_DIR/.venv"
source "$SCRIPT_DIR/.venv/bin/activate"
pip install --upgrade pip -q 2>/dev/null
echo "  ✓ venv created"

# ── 3. Install package ──
echo "2/4 Installing CLI-agent-memory..."
pip install -e "$SCRIPT_DIR" -q 2>/dev/null
echo "  ✓ CLI-agent-memory installed"

# ── 4. Verify ──
echo "3/4 Verifying installation..."
if CLI-agent-memory version 2>/dev/null | grep -q "CLI-agent-memory"; then
    echo "  ✓ CLI-agent-memory working"
else
    echo "  ⚠ CLI-agent-memory installed but version check failed"
fi

# ── 5. Check MCP-agent-memory (optional) ──
echo "4/4 Checking MCP-agent-memory..."
MCP_SERVER="$HOME/MCP-servers/MCP-agent-memory/src/unified/server/main.py"
if [ -f "$MCP_SERVER" ]; then
    echo "  ✓ MCP-agent-memory found at $HOME/MCP-servers/MCP-agent-memory"
    echo "    (CLI will connect to it via stdio subprocess)"
else
    echo "  ⚠ MCP-agent-memory not found at $MCP_SERVER"
    echo "    Install it separately for memory features:"
    echo "    curl -fsSL https://raw.githubusercontent.com/Ruben-Alvarez-Dev/MCP-agent-memory/main/install.sh | bash"
fi

# ── Done ──
echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║   ✅ Installation complete                         ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""
echo "Usage:"
echo "  CLI-agent-memory run \"your task description\" --repo ./my-project"
echo "  CLI-agent-memory config"
echo "  CLI-agent-memory version"
