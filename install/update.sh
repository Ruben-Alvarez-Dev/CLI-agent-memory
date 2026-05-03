#!/bin/bash
# update.sh - Orchestrate installation/update/repair for CLI-agent-memory
# This script coordinates: detect, version, backup, sync, deps, verify
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname $0)" && pwd)"
INSTALL_DIR="${1:-$HOME/CLI-agent-memory}"
SOURCE_DIR="${2:-$(dirname "$SCRIPT_DIR")}"
ERRORS=0; WARNINGS=0

# Colors
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
pass() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; ERRORS=$((ERRORS+1)); }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; WARNINGS=$((WARNINGS+1)); }
info() { echo -e "  ${CYAN}→${NC} $1"; }

# ── Step 0: Detect mode and metadata ─────────────────────────────────────
echo -e "${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   CLI-agent-memory — Installer/Updater                        ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Source detect.sh to get MODE and metadata
DETECT_OUTPUT="$($SCRIPT_DIR/detect.sh "$INSTALL_DIR" "$@")"
eval "$DETECT_OUTPUT"
MODE="${MODE:-install}"
DETECT_HAS_DATA="${DETECT_HAS_DATA:-false}"
DETECT_HAS_VAULT="${DETECT_HAS_VAULT:-false}"
DETECT_HAS_MODELS="${DETECT_HAS_MODELS:-false}"
DETECT_PREV_VERSION="${DETECT_PREV_VERSION:-unknown}"
echo -e "${BOLD}[0/4] Detection${NC}"
echo "────────────────────────────────────────────────────────────"
echo "  Mode:      $MODE"
echo "  Install:   $INSTALL_DIR"
echo "  Previous:   $DETECT_PREV_VERSION"
echo ""

# ── Step 1: Version check (only for update mode) ───────────────────────────
if [ "$MODE" = "update" ]; then
    echo -e "${BOLD}[1/4] Version Check${NC}"
    echo "────────────────────────────────────────────────────────────"
    eval "$($SCRIPT_DIR/version.sh check "$INSTALL_DIR" | tail -1)"  # Capture UP_TO_DATE/UPDATE_AVAILABLE
    if [[ "$($SCRIPT_DIR/version.sh check "$INSTALL_DIR" | tail -1)" == *"UPDATE_AVAILABLE"* ]]; then
        $SCRIPT_DIR/version.sh check "$INSTALL_DIR"
        echo ""
        read -p "Continue with update? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo "Update cancelled."
            exit 0
        fi
    else
        $SCRIPT_DIR/version.sh check "$INSTALL_DIR"
    fi
    echo ""
fi

# ── Step 2: Backup (if data exists) ────────────────────────────────────────
echo -e "${BOLD}[2/4] Backup${NC}"
echo "────────────────────────────────────────────────────────────"
if [ "$DETECT_HAS_DATA" = true ]; then
    if bash "$SCRIPT_DIR/backup.sh" "$INSTALL_DIR"; then
        pass "Backup completed successfully"
    else
        warn "Backup failed — continuing anyway"
    fi
else
    info "No data to preserve — skipping backup"
fi
echo ""

# ── Step 3: Sync code (clean update) ────────────────────────────────────────
echo -e "${BOLD}[3/4] Sync Code${NC}"
echo "────────────────────────────────────────────────────────────"
if [ -f "$SOURCE_DIR/install/sync.sh" ]; then
    # Use sync.sh for clean, zombie-free updates
    if bash "$SOURCE_DIR/install/sync.sh" "$SOURCE_DIR" "$INSTALL_DIR"; then
        pass "Code synced successfully"
    else
        fail "Sync failed — aborting"
        exit 1
    fi
else
    # Fallback to simple copy if sync.sh not available
    warn "sync.sh not found in source — using simple copy"
    if [ -d "$SOURCE_DIR/src" ]; then
        cp -a "$SOURCE_DIR/src" "$INSTALL_DIR/"
        pass "src/ copied"
    fi
    if [ -d "$SOURCE_DIR/install" ]; then
        mkdir -p "$INSTALL_DIR/install"
        for f in detect.sh backup.sh update.sh deps.sh manifest.json sync.sh version.sh; do
            [ -f "$SOURCE_DIR/install/$f" ] && cp "$SOURCE_DIR/install/$f" "$INSTALL_DIR/install/"
        done
        pass "install/ copied"
    fi
fi
echo ""

# ── Step 4: Dependencies (pip install) ────────────────────────────────────────
echo -e "${BOLD}[4/4] Dependencies${NC}"
echo "────────────────────────────────────────────────────────────"

PYTHON="${PYTHON:-python3.12}"
if ! command -v "$PYTHON" &>/dev/null; then
    PYTHON="python3"
fi

# Check/create venv
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    info "Creating virtual environment..."
    $PYTHON -m venv "$INSTALL_DIR/.venv"
fi

source "$INSTALL_DIR/.venv/bin/activate"
PIP="pip"
if command -v uv &>/dev/null; then
    PIP="uv pip"
fi

# Upgrade pip
$PIP install --upgrade pip -q 2>/dev/null
pass "pip upgraded"

# Install CLI-agent-memory
if $PIP install -e "$INSTALL_DIR" -q 2>/dev/null; then
    pass "CLI-agent-memory installed"
else
    fail "Installation failed"
    ERRORS=$((ERRORS+1))
fi

# Verify installation
if CLI-agent-memory version 2>/dev/null | grep -q "CLI-agent-memory"; then
    pass "CLI-agent-memory working"
else
    warn "CLI-agent-memory installed but version check failed"
fi

# Check MCP-agent-memory (optional)
echo ""
echo "  [MCP-agent-memory Check]"
MCP_SERVER="$HOME/MCP-servers/MCP-agent-memory/src/unified/server/main.py"
if [ -f "$MCP_SERVER" ]; then
    pass "MCP-agent-memory found at $HOME/MCP-servers/MCP-agent-memory"
else
    warn "MCP-agent-memory not found. Install separately for memory features:"
    echo "    curl -fsSL https://raw.githubusercontent.com/Ruben-Alvarez-Dev/MCP-agent-memory/main/install.sh | bash"
fi

# ── Bump version in manifest ─────────────────────────────────────────────────
echo ""
if [ -f "$SOURCE_DIR/install/manifest.json" ]; then
    NEW_VERSION=$(python3 -c "import json; print(json.load(open('$SOURCE_DIR/install/manifest.json')).get('version', 'unknown'))")
    if [ "$NEW_VERSION" != "unknown" ] && [ "$NEW_VERSION" != "$DETECT_PREV_VERSION" ]; then
        $SCRIPT_DIR/version.sh bump "$NEW_VERSION" "$INSTALL_DIR"
        pass "Version bumped to $NEW_VERSION"
    fi
fi

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════════════${NC}"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}${BOLD}  ✅ Installation complete ($INSTALL_DIR)${NC}"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}${BOLD}  ⚠  Installation complete with $WARNINGS warning(s)${NC}"
else
    echo -e "${RED}${BOLD}  ✗ Installation failed with $ERRORS error(s)${NC}"
fi
echo -e "${BOLD}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Usage:"
echo "  CLI-agent-memory run \"your task description\" --repo ./my-project"
echo "  CLI-agent-memory config"
echo "  CLI-agent-memory version"
echo ""

# Exit with error count
exit $ERRORS
