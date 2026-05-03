#!/bin/bash
# CLI-agent-memory — Installer (Thin Wrapper)
#
# Usage (one-liner, no clone needed):
#   curl -fsSL https://raw.githubusercontent.com/Ruben-Alvarez-Dev/CLI-agent-memory/main/install.sh | bash
#   curl -fsSL ... | bash -s -- ~/my-custom-path
#
# Or from inside the cloned repo:
#   bash install.sh
#   bash install.sh ~/my-custom-path
#
# This installer delegates all heavy lifting to modular scripts in install/
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
INSTALL_DIR="${1:-$HOME/CLI-agent-memory}"
INSTALL_SCRIPT="${SCRIPT_DIR}/install/update.sh"

# ── Auto-bootstrap: download source via tarball if not inside repo ─────────────
if [ ! -f "$SCRIPT_DIR/src/CLI_agent_memory/cli.py" ]; then
    REPO_URL="https://github.com/Ruben-Alvarez-Dev/CLI-agent-memory"
    echo "⬇  Downloading CLI-agent-memory source..."

    TMPDIR=$(mktemp -d -t cli-mem.XXXXXX)
    cleanup() { rm -rf "$TMPDIR"; }
    trap cleanup EXIT

    if ! curl -fsSL "${REPO_URL}/archive/refs/heads/main.tar.gz" -o "$TMPDIR/src.tar.gz"; then
        echo "  ✗ Download failed. Check your internet connection."
        exit 1
    fi

    mkdir -p "$TMPDIR/repo"
    tar -xzf "$TMPDIR/src.tar.gz" -C "$TMPDIR/repo" --strip-components=1
    rm -rf "$TMPDIR/repo/.git"
    echo "  ✓ Source downloaded ($(du -sh "$TMPDIR/repo" | awk '{print $1}'))"

    # Extract install/ dir to check for updates even before full install
    mkdir -p "$INSTALL_DIR/install"
    cp -a "$TMPDIR/repo/install/." "$INSTALL_DIR/install/" 2>/dev/null || mkdir -p "$INSTALL_DIR/install"

    # Check for updates immediately after bootstrap
    if bash "$INSTALL_DIR/install/version.sh" check "$INSTALL_DIR" 2>/dev/null | grep -q "UPDATE_AVAILABLE"; then
        bash "$INSTALL_DIR/install/version.sh" check "$INSTALL_DIR"
        echo ""
        read -p "Update available. Continue with installation? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled."
            exit 0
        fi
    fi

    # Copy payload to install dir (using sync.sh for clean install)
    if [ -f "$TMPDIR/repo/install/sync.sh" ]; then
        bash "$TMPDIR/repo/install/sync.sh" "$TMPDIR/repo" "$INSTALL_DIR"
    else
        # Fallback if sync.sh doesn't exist in downloaded source
        mkdir -p "$INSTALL_DIR"
        for item in src install tests pyproject.toml README.md install.sh .python-version; do
            [ -e "$TMPDIR/repo/$item" ] && cp -a "$TMPDIR/repo/$item" "$INSTALL_DIR/"
        done
    fi

    echo "  ✓ Source installed at $INSTALL_DIR ($(du -sh "$INSTALL_DIR" | awk '{print $1}'))"

    # Now run the actual installation using update.sh script
    exec bash "$INSTALL_DIR/install/update.sh" "$INSTALL_DIR" "$TMPDIR/repo"
fi

# ── Running from inside the repo: delegate to install/update.sh ──────────────
if [ -f "$INSTALL_SCRIPT" ]; then
    exec bash "$INSTALL_SCRIPT" "$INSTALL_DIR" "$SCRIPT_DIR"
else
    echo "✗ Installation script not found at $INSTALL_SCRIPT"
    exit 1
fi
