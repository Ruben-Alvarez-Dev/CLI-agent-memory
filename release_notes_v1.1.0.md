# CLI-agent-memory v1.1.0 — Lx Naming, English Docs & LlamaCpp Adapter

## 🎯 Overview
This release brings the CLI-agent-memory project into alignment with the new Lx naming scheme, translates all Spanish documentation to English, and adds full support for the llama.cpp LLM backend as the default adapter.

## 🔄 Breaking Changes

### Module Naming Standardization
All internal modules now follow the Lx layer convention:

| Old Name | New Name |
|----------|----------|
| automem | L0_capture |
| autodream | L0_to_L4_consolidation |
| vk-cache / vk_cache | L5_routing |
| conversation-store | L2_conversations |
| mem0 | L3_facts |
| engram | L3_decisions |
| sequential-thinking | Lx_reasoning |

### MCP Tool Names Updated
All MCP client adapters now call the new tool names:
- `automem_ingest_event` → `L0_capture_ingest_event`
- `vk_cache_request_context` → `L5_routing_request_context`
- `sequential_thinking_*` → `Lx_reasoning_*`

## 📝 Documentation Translation

### Fully Translated to English
- ✅ `SPEC-v1.md` (1052 lines) — Complete specification
- ✅ `SPEC-v2.md` (750 lines) — Agent orchestrator v2.0
- ✅ `SPEC-v3.md` (682 lines) — Enhanced features
- ✅ `SPEC-v4.md` (379 lines) — Agent orchestrator v2.0
- ✅ `DECISIONS.md` → `DECISIONS.md` — Architecture decisions

### Verified Clean
- ✅ `SPEC-v5.md` — Already in English
- ✅ `CHECKLIST-R1.md` — Already in English
- ✅ `ARCHITECTURE.md` — Already in English

## 🔧 Code Changes

### MCP Adapters
- Updated `src/CLI_agent_memory/infra/adapters/mcp/memory_stdio.py`
- Updated `src/CLI_agent_memory/infra/adapters/mcp/thinking_stdio.py`

### OpenCode Adapter
- Updated `adapters/opencode/backpack-orchestrator.ts` with new prefix filters
- Updated `adapters/README.md` with new module names

### Documentation
- Updated cross-references across all spec files
- No broken links remain

## 🧹 Cleanup

### Removed Files
- `.coverage` — Test coverage file (now in .gitignore)
- `audit_test_real.py` — Development test script
- `print_err.py` — Debug utility
- `verify.sh` — Development verification script

### Updated .gitignore
Added patterns to exclude development artifacts from version control.

## ✅ Quality Assurance

### All Python Compiles
```bash
✓ cli.py
✓ commands.py
✓ config.py
✓ types.py
✓ domain/loop.py
✓ infra/adapters/mcp/*.py
```

### Zero Spanish Characters
All documentation now uses professional English. Only Unicode symbols (×, ⭐, σ) remain for formatting.

### Backward Compatibility
- The MCP server (`MCP-agent-memory`) supports both old and new tool names for migration
- Existing configurations continue to work
- Upgrade path is transparent for end users

## 📊 Statistics

| Metric | Value |
|--------|-------|
| Documentation lines translated | ~2,900 |
| Files renamed | 1 |
| Files modified | 10 |
| Files deleted | 4 |
| Module names standardized | 7 |
| MCP tool names updated | 6 |

## 🚀 Installation

```bash
# Clone or update
git clone https://github.com/Ruben-Alvarez-Dev/CLI-agent-memory.git
cd CLI-agent-memory

# Install dependencies
pip install -e .

# Verify installation
cli-agent-memory --version
```

## 📖 Documentation

- [Full Specification (v5)](https://github.com/Ruben-Alvarez-Dev/CLI-agent-memory/blob/main/docs/SPEC-v5.md)
- [Architecture](https://github.com/Ruben-Alvarez-Dev/CLI-agent-memory/blob/main/docs/ARCHITECTURE.md)
- [Release Checklist](https://github.com/Ruben-Alvarez-Dev/CLI-agent-memory/blob/main/docs/CHECKLIST-R1.md)

## 🤝 Contributing

See [CONTRIBUTING.md](https://github.com/Ruben-Alvarez-Dev/CLI-agent-memory/blob/main/CONTRIBUTING.md) for guidelines.

## 🔗 Related Releases

- [MCP-agent-memory v2.0.0](https://github.com/Ruben-Alvarez-Dev/MCP-agent-memory/releases/tag/v2.0.0) — Corresponding memory server release

---

**Full Changelog**: https://github.com/Ruben-Alvarez-Dev/CLI-agent-memory/compare/v1.0.0...v1.1.0
