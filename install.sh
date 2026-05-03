#!/usr/bin/env bash
# Thin wrapper installer for CLI-agent-memory using CLI-agent-installer v2.0
#
# This script:
# 1. Auto-bootstraps source code from GitHub if not present
# 2. Delegates installation to CLI-agent-installer
#
# Usage:
#   bash install.sh                    # Install or update
#   bash install.sh --dry-run          # Preview changes
#   bash install.sh --verbose          # Verbose output
#   bash install.sh --no-checklist     # Run without checklist (legacy mode)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="CLI-agent-memory"
REPO="Ruben-Alvarez-Dev/CLI-agent-memory"

# Check if CLI-agent-installer is installed
if ! command -v installer &> /dev/null; then
    log_info "CLI-agent-installer not found. Installing..."

    # Create temp directory
    TMPDIR=$(mktemp -d)
    cd "$TMPDIR"

    # Clone and install
    if ! git clone https://github.com/Ruben-Alvarez-Dev/CLI-agent-installer.git; then
        log_error "Failed to clone CLI-agent-installer"
        exit 1
    fi

    cd CLI-agent-installer

    # Install with pip (try pip3 first, then pip)
    if command -v pip3 &> /dev/null; then
        PIP_CMD=pip3
    elif command -v pip &> /dev/null; then
        PIP_CMD=pip
    else
        log_error "Neither pip nor pip3 found"
        exit 1
    fi

    if ! $PIP_CMD install --break-system-packages -e .; then
        log_error "Failed to install CLI-agent-installer"
        exit 1
    fi

    log_success "CLI-agent-installer installed"
    cd "$SCRIPT_DIR"
    rm -rf "$TMPDIR"
fi

# Check if running from within the repo (dev mode) or standalone (user mode)
if [ -d "$SCRIPT_DIR/.git" ]; then
    # Dev mode: running from within the repo
    log_info "Running in dev mode (within repo)"
    INSTALL_DIR="$SCRIPT_DIR"
else
    # User mode: running standalone
    log_info "Running in user mode (standalone)"

    # Check if we need to bootstrap source code
    if [ ! -f "$SCRIPT_DIR/pyproject.toml" ]; then
        log_info "Bootstrapping source code from GitHub..."

        # Create temp directory for download
        TMPDIR=$(mktemp -d)
        cd "$TMPDIR"

        # Download tarball from main branch
        if ! curl -fsSL "https://github.com/${REPO}/archive/refs/heads/main.tar.gz" -o main.tar.gz; then
            log_error "Failed to download source code"
            exit 1
        fi

        # Extract
        if ! tar -xzf main.tar.gz; then
            log_error "Failed to extract source code"
            exit 1
        fi

        # Copy files
        EXTRACTED_DIR="${REPO##*/}-main"
        if [ -d "$EXTRACTED_DIR" ]; then
            # Copy all files except .git
            if ! rsync -av --exclude='.git' "$EXTRACTED_DIR/" "$SCRIPT_DIR/"; then
                log_warn "rsync not available, using cp..."
                cp -r "$EXTRACTED_DIR/"* "$SCRIPT_DIR/"
            fi
            log_success "Source code bootstrapped"
        else
            log_error "Failed to find extracted directory"
            exit 1
        fi

        cd "$SCRIPT_DIR"
        rm -rf "$TMPDIR"
    fi

    INSTALL_DIR="$SCRIPT_DIR"
fi

# Check if manifest exists
if [ ! -f "$INSTALL_DIR/install/manifest.json" ]; then
    log_error "install/manifest.json not found. Run 'installer init .' first"
    exit 1
fi

# Run installer
log_info "Running CLI-agent-installer..."
installer run "$INSTALL_DIR" "$@"
