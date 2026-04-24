#!/bin/bash
# CLI-agent-memory — Post-install verification script
# Run after: pip install git+https://github.com/Ruben-Alvarez-Dev/CLI-agent-memory.git
# Or:        pip install . (from inside the repo)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'
pass() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; ERRORS=$((ERRORS+1)); }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; WARNINGS=$((WARNINGS+1)); }
info() { echo -e "  ${CYAN}→${NC} $1"; }
ERRORS=0; WARNINGS=0

echo ""
echo -e "${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   CLI-agent-memory — Verification                       ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Package installed ────────────────────────────────────────
echo -e "${BOLD}[1/6] Package installation${NC}"
echo "────────────────────────────────────────────────────────────"

if command -v CLI-agent-memory &>/dev/null; then
    VERSION=$(CLI-agent-memory version 2>/dev/null | head -1 || echo "unknown")
    pass "CLI-agent-memory found: $VERSION"
else
    # Try module execution
    if python3 -m CLI_agent_memory.cli version 2>/dev/null | grep -q "CLI-agent-memory"; then
        pass "CLI-agent-memory importable (use: python3 -m CLI_agent_memory.cli)"
    else
        fail "CLI-agent-memory not found. Install: pip install git+https://github.com/Ruben-Alvarez-Dev/CLI-agent-memory.git"
    fi
fi
echo ""

# ── 2. Dependencies ─────────────────────────────────────────────
echo -e "${BOLD}[2/6] Dependencies${NC}"
echo "────────────────────────────────────────────────────────────"

for pkg in pydantic pydantic_settings httpx mcp; do
    if python3 -c "import ${pkg//-/_}" 2>/dev/null; then
        VER=$(python3 -c "import ${pkg//-/_}; print(getattr(${pkg//-/_},'__version__','ok'))" 2>/dev/null)
        pass "$pkg ($VER)"
    else
        fail "$pkg missing"
    fi
done
echo ""

# ── 3. Architecture ─────────────────────────────────────────────
echo -e "${BOLD}[3/6] Architecture integrity${NC}"
echo "────────────────────────────────────────────────────────────"

CHECKS=(
    "CLI_agent_memory.cli:CLI entry point"
    "CLI_agent_memory.config:Configuration"
    "CLI_agent_memory.domain.loop:Loop engine"
    "CLI_agent_memory.domain.protocols:Protocol interfaces"
    "CLI_agent_memory.domain.types:Domain types"
    "CLI_agent_memory.domain.stagnation:Stagnation monitor"
    "CLI_agent_memory.infra.adapters.protocol_factory:Protocol factory"
    "CLI_agent_memory.infra.adapters.mcp.memory_stdio:Memory stdio adapter"
    "CLI_agent_memory.infra.adapters.mcp.thinking_stdio:Thinking stdio adapter"
    "CLI_agent_memory.infra.adapters.mcp.vault_stdio:Vault stdio adapter"
    "CLI_agent_memory.infra.adapters.mcp.stdio_manager:Subprocess manager"
    "CLI_agent_memory.infra.adapters.null.memory_null:Null memory adapter"
    "CLI_agent_memory.infra.llm.ollama:Ollama client"
    "CLI_agent_memory.prompts.templates:Prompt templates"
)

for check in "${CHECKS[@]}"; do
    module="${check%%:*}"
    label="${check##*:}"
    if python3 -c "import $module" 2>/dev/null; then
        pass "$label ($module)"
    else
        fail "$label ($module)"
    fi
done
echo ""

# ── 4. Tests ────────────────────────────────────────────────────
echo -e "${BOLD}[4/6] Unit tests${NC}"
echo "────────────────────────────────────────────────────────────"

TEST_DIR="$SCRIPT_DIR/tests"
if [ -d "$TEST_DIR" ]; then
    RESULT=$(python3 -m pytest "$TEST_DIR" -q --tb=no 2>/dev/null | tail -1) || true
    if echo "$RESULT" | grep -q "passed"; then
        pass "$RESULT"
    else
        fail "$RESULT"
    fi
else
    warn "Tests directory not found"
fi
echo ""

# ── 5. MCP-agent-memory connectivity ────────────────────────────
echo -e "${BOLD}[5/6] MCP-agent-memory connectivity${NC}"
echo "────────────────────────────────────────────────────────────"

# Auto-discover MCP-agent-memory installation (same logic as stdio_manager.py)
MCP_BASE="${MCP_SERVER_DIR:-}"
if [ -z "$MCP_BASE" ] || [ ! -f "$MCP_BASE/.venv/bin/python3" ]; then
    if [ -f "$HOME/MCP-servers/MCP-agent-memory/.venv/bin/python3" ]; then
        MCP_BASE="$HOME/MCP-servers/MCP-agent-memory"
    elif [ -f "$HOME/MCP-agent-memory/.venv/bin/python3" ]; then
        MCP_BASE="$HOME/MCP-agent-memory"
    else
        MCP_BASE="$HOME/MCP-servers/MCP-agent-memory"  # default for error message
    fi
fi
MCP_PYTHON="$MCP_BASE/.venv/bin/python3"
MCP_SCRIPT="$MCP_BASE/src/unified/server/main.py"

if [ -f "$MCP_PYTHON" ] && [ -f "$MCP_SCRIPT" ]; then
    pass "MCP-agent-memory found at $MCP_BASE"

    # Test subprocess spawn (Python-native timeout — macOS + Linux compatible)
    if python3 -c "
import asyncio, sys
from CLI_agent_memory.infra.adapters.mcp.stdio_manager import MCPSessionManager
async def test():
    mgr = MCPSessionManager()
    await mgr.start()
    tools = await mgr.list_tools()
    await mgr.close()
    return len(tools)
try:
    count = asyncio.run(asyncio.wait_for(test(), timeout=15))
    print(f'subprocess_ok tools={count}')
except asyncio.TimeoutError:
    print('subprocess_timeout'); sys.exit(1)
except Exception as e:
    print(f'subprocess_error: {e}'); sys.exit(1)
" 2>/dev/null | grep -q "subprocess_ok"; then
        TOOL_COUNT=$(python3 -c "
import asyncio, sys
from CLI_agent_memory.infra.adapters.mcp.stdio_manager import MCPSessionManager
async def test():
    mgr = MCPSessionManager()
    await mgr.start()
    tools = await mgr.list_tools()
    await mgr.close()
    return len(tools)
try:
    count = asyncio.run(asyncio.wait_for(test(), timeout=15))
    print(count)
except Exception:
    print('?')
" 2>/dev/null)
        pass "MCP subprocess works ($TOOL_COUNT tools available)"
    else
        fail "MCP subprocess failed to start"
    fi
else
    warn "MCP-agent-memory not found at $MCP_BASE"
    info "Install with: curl -fsSL https://raw.githubusercontent.com/Ruben-Alvarez-Dev/MCP-agent-memory/main/install.sh | bash"
    info "Or set MCP_SERVER_DIR env var to the correct path"
fi
echo ""

# ── 6. Integration smoke test ───────────────────────────────────
echo -e "${BOLD}[6/6] Integration smoke test${NC}"
echo "────────────────────────────────────────────────────────────"

if [ -f "$MCP_PYTHON" ] && [ -f "$MCP_SCRIPT" ]; then
    INTEGRATION=$(python3 -c "
import asyncio, sys
from CLI_agent_memory.infra.adapters.mcp.memory_stdio import MCPMemoryStdioAdapter
from CLI_agent_memory.infra.adapters.mcp.vault_stdio import MCPVaultStdioAdapter

async def test():
    mem = MCPMemoryStdioAdapter()
    vlt = MCPVaultStdioAdapter()
    mid = await mem.store('fact', 'verify-install-test', tags=['verify'])
    items = await mem.list(limit=5)
    found = any('verify-install-test' in m.content for m in items)
    entry = await vlt.write('Inbox', 'verify-install', 'verification test')
    content = await vlt.read('Inbox', 'verify-install')
    from CLI_agent_memory.infra.adapters.mcp.stdio_manager import _global_manager
    if _global_manager: await _global_manager.close()
    return f'store={bool(mid)} list={found} vault_write={bool(entry.path)} vault_read={content is not None}'

try:
    result = asyncio.run(asyncio.wait_for(test(), timeout=30))
    print(result)
except Exception as e:
    print(f'error: {e}'); sys.exit(1)
" 2>/dev/null || echo "error")

    if echo "$INTEGRATION" | grep -q "store=True"; then pass "Memory store"; else fail "Memory store"; fi
    if echo "$INTEGRATION" | grep -q "list=True"; then pass "Memory list (store→list consistency)"; else fail "Memory list"; fi
    if echo "$INTEGRATION" | grep -q "vault_write=True"; then pass "Vault write"; else fail "Vault write"; fi
    if echo "$INTEGRATION" | grep -q "vault_read=True"; then pass "Vault read"; else fail "Vault read"; fi
else
    warn "MCP-agent-memory not available — integration tests skipped"
fi
echo ""

# ── Summary ─────────────────────────────────────────────────────
echo -e "${BOLD}════════════════════════════════════════════════════════════${NC}"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}${BOLD}  ✅ All checks passed${NC}"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}${BOLD}  ⚠  Verified with $WARNINGS warning(s)${NC}"
else
    echo -e "${RED}${BOLD}  ✗ $ERRORS error(s) and $WARNINGS warning(s)${NC}"
fi
echo -e "${BOLD}════════════════════════════════════════════════════════════${NC}"
echo ""
