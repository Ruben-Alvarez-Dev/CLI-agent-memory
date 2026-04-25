# CLI-agent-memory

> Autonomous coding agent CLI. Hexagonal architecture. Zero enterprise dependencies.

Connects to [MCP-agent-memory](https://github.com/Ruben-Alvarez-Dev/MCP-agent-memory) for persistent memory, reasoning, and vault — or runs fully standalone with local SQLite adapters.

## Install

```bash
uv pip install --system git+ssh://git@github.com/Ruben-Alvarez-Dev/CLI-agent-memory.git
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
cli-agent-memory run "Fix the failing auth tests" --llm ollama --model llama3.2:3b --repo ./my-app

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
| `--llm lmstudio\|ollama` | LLM backend |
| `--model <name>` | LLM model (default: auto-detect) |
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
│  │  stdio    │  │ SQLite   │  │  LM Studio   │   │
│  │  transport│  │ filesystem│  │  Ollama      │   │
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
| `AGENT_MEMORY_LLM_BACKEND` | `lmstudio` | `lmstudio` or `ollama` |
| `AGENT_MEMORY_LLM_BASE_URL` | `http://localhost:1234` | LLM API URL |
| `AGENT_MEMORY_LLM_MODEL` | *(auto)* | LLM model name |
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
- **LLM model** from LM Studio's `GET /v1/models` endpoint
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

## License

MIT
