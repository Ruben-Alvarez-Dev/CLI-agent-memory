#!/bin/bash
# version.sh — Version management for CLI-agent-memory
# Reads from manifest.json (single source of truth), compares with GitHub releases
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_INSTALL_DIR="$HOME/MCP-servers/CLI-agent-memory"

# Colors
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'

_get_manifest_path() {
    local dir="${1:-$DEFAULT_INSTALL_DIR}"
    echo "$dir/install/manifest.json"
}

get_local_version() {
    local manifest="$(_get_manifest_path "${1:-}")"
    if [ -f "$manifest" ]; then
        python3 -c "import json; print(json.load(open('$manifest')).get('version', '0.0.0'))" 2>/dev/null || echo "0.0.0"
    else
        echo "0.0.0"
    fi
}

get_remote_version() {
    local manifest="$(_get_manifest_path "${1:-}")"
    local repo=""
    if [ -f "$manifest" ]; then
        repo=$(python3 -c "import json; print(json.load(open('$manifest')).get('repo', ''))" 2>/dev/null || echo "")
    fi
    if [ -z "$repo" ]; then
        repo="Ruben-Alvarez-Dev/CLI-agent-memory"
    fi
    local tag=$(curl -fsSL --max-time 10 "https://api.github.com/repos/$repo/releases/latest" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('tag_name',''))" 2>/dev/null || echo "")
    echo "${tag#v}"
}

get_git_version() {
    local dir="${1:-$DEFAULT_INSTALL_DIR}"
    if [ -d "$dir/.git" ]; then
        local desc=$(cd "$dir" && git describe --tags --always 2>/dev/null || echo "")
        echo "${desc#v}"
    else
        echo ""
    fi
}

check_for_update() {
    local install_dir="${1:-$DEFAULT_INSTALL_DIR}"
    local local_ver=$(get_local_version "$install_dir")
    local remote_ver=$(get_remote_version "$install_dir")
    
    echo -e "── Version Check ──────────────────────"
    echo -e "  Local:  ${BOLD}$local_ver${NC}"
    
    if [ -z "$remote_ver" ]; then
        echo -e "  Remote: ${YELLOW}unreachable${NC}"
        echo -e "  ${YELLOW}⚠${NC}  Cannot check for updates (offline or rate-limited)"
        echo "UNKNOWN"
        return 0
    fi
    
    echo -e "  Remote: ${BOLD}v$remote_ver${NC}"
    
    if [ "$local_ver" = "$remote_ver" ]; then
        echo -e "  ${GREEN}✓${NC} Up to date ($local_ver)"
        echo "UP_TO_DATE"
    else
        echo -e "  ${YELLOW}⚠${NC}  Update available: $local_ver → $remote_ver"
        echo "UPDATE_AVAILABLE"
    fi
}

bump_manifest_version() {
    local new_version="${1:?Usage: bump_manifest_version <version> [install_dir]}"
    local manifest="$(_get_manifest_path "${2:-}")"
    if [ -f "$manifest" ]; then
        python3 -c "
import json
with open('$manifest') as f: data = json.load(f)
data['version'] = '$new_version'
with open('$manifest', 'w') as f: json.dump(data, f, indent=2)
print(data['version'])
" 2>/dev/null
    else
        echo "ERROR: manifest not found at $manifest" >&2
        return 1
    fi
}

# CLI interface
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    ACTION="${1:-check}"
    INSTALL_DIR="${2:-$DEFAULT_INSTALL_DIR}"
    
    case "$ACTION" in
        check)  check_for_update "$INSTALL_DIR" ;;
        local)  echo "$(get_local_version "$INSTALL_DIR")" ;;
        remote) echo "$(get_remote_version "$INSTALL_DIR")" ;;
        git)    echo "$(get_git_version "$INSTALL_DIR")" ;;
        bump)   bump_manifest_version "${2:?Usage: version.sh bump <version>}" "${3:-$DEFAULT_INSTALL_DIR}" ;;
        *)
            echo "Usage: version.sh [check|local|remote|git|bump] [args...]"
            echo "  check  — Compare local vs remote version"
            echo "  local  — Print local version"
            echo "  remote — Print latest GitHub release version"
            echo "  git    — Print git describe version (if in repo)"
            echo "  bump   — Update manifest.json version"
            exit 1
            ;;
    esac
fi
