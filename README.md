# CLI-agent-memory

> Autonomous coding agent CLI. Hexagonal architecture. Zero enterprise dependencies. 100% local LLM.

Connects to [MCP-agent-memory](https://github.com/Ruben-Alvarez-Dev/MCP-agent-memory) for persistent memory, reasoning, and vault — or runs fully standalone with local SQLite adapters. Uses **llama.cpp** for all LLM inference — no cloud APIs, no external services.

## Install

```bash
uv pip install --system git+https://github.com/Ruben-Alvarez-Dev/CLI-agent-memory.git
```

Requires **Python ≥ 3.12** and [uv](https://docs.astral.sh/uv/).

Verify everything works:

```bash
cli-agent-memory version
cli-agent-memory doctor
```

## Quick Start

```bash
# Run a coding task (auto-detects LLM and test command)
cli-agent-memory run "Add input validation to the login form" --repo ./my-app

# Plan without executing
cli-agent-memory plan "Refactor database layer to use repository pattern" --repo ./my-app

# Use a specific model
cli-agent-memory run "Fix the failing auth tests" --llm llama_cpp --model qwen2.5-7b-instruct-Q4_K_M --repo ./my-app

# Run offline (local SQLite, no MCP required)
cli-agent-memory run "Implement pagination" --repo ./my-app --force-local
```

## Commands

### Core

| Command | Description |
|---------|-------------|
| `run` | Run an autonomous coding task |
| `resume <id>` | Resume a paused task |
| `plan <task>` | Generate a plan (no execution) |
| `status` | Show active tasks in a repo |
| `cancel <id>` | Cancel an active task |
| `cleanup` | Remove completed/failed worktrees |

### Memory & Reasoning

| Command | Description |
|---------|-------------|
| `recall <query>` | Search memories |
| `remember <content>` | Store a memory (`--tags=a,b`) |
| `think <problem>` | Run a thinking chain (`--steps=N`) |
| `decisions [query]` | List/search architectural decisions |

### Utilities

| Command | Description |
|---------|-------------|
| `doctor` | System health check (git, LLM, MCP, uv) |
| `config` | Show configuration (`--json`) |
| `db [--tables] [--query]` | Inspect local SQLite database |
| `version` | Show installed version |

All commands support `--json` for structured output.

## Options

| Flag | Description |
|------|-------------|
| `--repo .` | Target git repository (default: `.`) |
| `--llm llama_cpp` | LLM backend (only llama.cpp supported) |
| `--model <name>` | LLM model (default: auto-detect from `models/`) |
| `--force-local` | Use SQLite instead of MCP |
| `--max-iter N` | Max loop iterations (default: 50) |
| `--test-cmd "..."` | Test command for verification |
| `--dry-run` | Preview without executing |
| `--json` | Structured JSON output |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                    CLI Layer                    │
│  cli.py · parser.py · commands.py · output.py  │
├─────────────────────────────────────────────────┤
│                  Domain Layer                    │
│  Zero external dependencies. Pure business logic  │
│                                                  │
│  loop.py     State machine:                     │
│  protocols.py  8 interfaces (ports)              │
│  types.py     Pydantic models + enums            │
│  stagnation.py  Anti-loop detection               │
│  file_ops.py  Multi-format file parsing          │
│  state.py     Task persistence                  │
│  schema.py    SQLite DDL                         │
│  templates.py  LLM prompts                      │
├─────────────────────────────────────────────────┤
│               Infrastructure Layer                 │
│  Adapters implement domain protocols             │
│                                                  │
│  ┌───────────┐  ┌──────────┐  ┌───────────────┐   │
│  │ MCP       │  │  Local   │  │     LLM      │   │
│  │  stdio    │  │ SQLite   │  │  llama.cpp   │   │
│  │  transport│  │ filesystem│  │  (local)     │   │
│  └───────────┘  └──────────┘  └───────────────┘   │
└─────────────────────────────────────────────────┘
```

### Adapter Resolution (ProtocolFactory)

```
1. MCP stdio  → if memory_enabled=True (default)
2. Local      → if force_local=True
3. Null       → if memory_enabled=False (offline/testing)
```

### Domain Protocols

| Protocol | Methods |
|----------|---------|
| `MemoryProtocol` | `recall`, `store`, `ingest`, `search`, `list` |
| `ThinkingProtocol` | `think`, `get_session` |
| `VaultProtocol` | `write`, `read`, `search`, `list_entries`, `append` |
| `WorkspaceProtocol` | `create`, `remove`, `run_command`, `read_file`, `write_file`, `list_files` |
| `LLMClient` | `generate`, `is_available` |

## Agent Loop

```
PLANNING ──→ CODING ──→ VERIFICATION
    │           │            │
    │           │            ├── Tests pass → DONE
    │           │            └── Tests fail → CODING
    │           │
    │           ├── Stagnation → Intervention → CODING
    │           └── DONE signal detected → VERIFICATION
    │
    └── Max iterations / SIGINT → FAILED
```

- **File parsing**: 3 formats with git diff fallback
- **DONE detection**: 5 signals checked in last 200 chars of LLM output
- **History**: Sliding window (MAX_HISTORY=30) with stagnation reset
- **Stagnation**: 3 turns without edits or 3 identical errors triggers intervention

## Configuration

Environment variables with `AGENT_MEMORY_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_MEMORY_LLM_BACKEND` | `llama_cpp` | Only `llama_cpp` supported |
| `AGENT_MEMORY_LLM_BASE_URL` | `http://localhost:8080` | LLM API URL (llama.cpp server) |
| `AGENT_MEMORY_LLM_MODEL` | *(auto)* | LLM model name (auto-detected from `models/`) |
| `AGENT_MEMORY_LLM_TIMEOUT` | `120` | Request timeout in seconds |
| `AGENT_MEMORY_MEMORY_ENABLED` | `true` | Enable MCP memory |
| `AGENT_MEMORY_MCP_SERVER_DIR` | *(auto)* | MCP-agent-memory path |
| `AGENT_MEMORY_FORCE_LOCAL` | `false` | Use local adapters |
| `AGENT_MEMORY_MAX_ITERATIONS` | `50` | Max loop iterations |
| `AGENT_MEMORY_MAX_STAGNATION` | `3` | Max stagnation turns |
| `AGENT_MEMORY_TEST_COMMAND` | *(auto)* | Test command (auto-detected) |
| `AGENT_MEMORY_WORKTREE_DIR` | `.worktrees` | Git worktrees directory |
| `AGENT_MEMORY_VAULT_DIR` | `.agent-memory/vault` | Local vault directory |
| `AGENT_MEMORY_DB_PATH` | `.agent-memory/agent-memory.db` | Local SQLite path |

## Auto-Detection

The CLI automatically detects:

- **Test command** from project files: `pyproject.toml` → `pytest`, `package.json` → `npm test`, `Cargo.toml` → `cargo test`, `go.mod` → `go test ./...`, `Makefile` → `make test`, `pom.xml` → `mvn test`, `setup.py` → `pytest`
- **LLM model** from `models/` directory (`.gguf` files) or running llama.cpp server
- **MCP-agent-memory** installation at `~/MCP-servers/MCP-agent-memory`

## Testing

```bash
pytest tests/ -v            # Run all 117 tests
pytest tests/ --cov=CLI_agent_memory  # With coverage
```

## Invariants

| ID | Rule |
|----|------|
| INV-01 | Domain layer has 0 infra imports |
| INV-02 | Every file ≤ 150 lines (SRP) |
| INV-03 | All types are Pydantic models or Enums |
| INV-04 | Protocols use `@runtime_checkable` |
| INV-05 | Every adapter handles exceptions gracefully |

## Adapters for Other CLIs

CLI-agent-memory is the **active orchestration layer** (the tractor head) of "La Mochila" — the backpack system. The MCP-agent-memory server is the passive memory engine. CLI-specific plugins live in `adapters/` so any tool can connect:

| Adapter | Status | Description |
|---------|--------|-------------|
| `opencode/` | ✅ Active | TypeScript plugin with 6 hooks — auto-capture, context injection, enforcement gates |
| `claude-code/` | 🔜 Planned | Claude Code hooks via `.claude/` config |
| `aider/` | 🔜 Planned | Aider config + scripting |
| `cursor/` | 🔜 Planned | `.cursorrules` + MCP config |

All adapters talk to the same MCP-agent-memory HTTP sidecar on `:8890`. The adapter pattern means adding a new CLI is a matter of writing hooks for that CLI's event system — the memory backend stays identical.

### OpenCode Plugin (backpack-orchestrator)

The OpenCode adapter is the most advanced. It provides:

- **Auto-capture**: Every user prompt, tool call, and file edit → stored as raw events
- **Auto-context**: Fetches relevant memories on every user message, injects into system prompt
- **Enforcement gates**: Blocks `write`/`edit` until memory context is verified, blocks non-conventional commits
- **Compaction recovery**: Saves conversation + triggers consolidation before context is lost
- **Background verification** (roadmap v1.4): Verifies stale memories during session idle time

## Roadmap Integration

CLI-agent-memory and MCP-agent-memory share a unified roadmap. See [MCP-agent-memory ROADMAP](https://github.com/Ruben-Alvarez-Dev/MCP-agent-memory/blob/main/docs/ROADMAP.md) for the full plan.

| Version | Focus | Status |
|---------|-------|--------|
| v1.0 | CLI MVP — autonomous coding agent | ✅ 115/115 checkpoints |
| v1.2 | Backpack enforcement layer | ✅ Shipped |
| v1.3 | Smart context injection + enforcement gates | ✅ Shipped |
| v1.4 | Continuous knowledge verification (freshness scoring) | 🔜 Next |
| v1.5 | Expanded enforcement (env guards, blind write blocks) | Planned |
| v2.0 | Multi-agent orchestration with shared memory | Future |

**Research foundation**: [Verification of Continuous Knowledge](https://github.com/Ruben-Alvarez-Dev/MCP-agent-memory/blob/main/docs/research/verificacion-continua-conocimiento.md) — neuroscientific basis for freshness tracking, reconsolidation, and background verification.

## License

MIT
