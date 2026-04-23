# CLI-agent-memory

Autonomous coding agent with hexagonal architecture. Connects to [MCP-agent-memory](https://github.com/Ruben-Alvarez-Dev/MCP-agent-memory) for persistent memory, reasoning, and vault management.

## Quick Start

### Installation

#### One-liner

```bash
curl -fsSL https://raw.githubusercontent.com/Ruben-Alvarez-Dev/CLI-agent-memory/main/install.sh | bash
```

#### Manual

```bash
git clone https://github.com/Ruben-Alvarez-Dev/CLI-agent-memory.git
cd CLI-agent-memory
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Usage

```bash
# Run a task with MCP memory
CLI-agent-memory run "Implement user authentication" --repo ./my-project

# Run with Ollama
CLI-agent-memory run "Fix test failures" --llm ollama --repo ./my-project

# Dry run (preview without execution)
CLI-agent-memory run "Refactor auth module" --dry-run

# Show configuration
CLI-agent-memory config
```

## Architecture

Hexagonal Architecture (Ports & Adapters). Domain layer has zero external dependencies.

```
┌─────────────────────────────────────────────┐
│                  CLI Entry                   │
│              (argparse, config)              │
├─────────────────────────────────────────────┤
│               Domain Layer                   │
│  LoopEngine │ Protocols │ Types │ Stagnation│
├─────────────────────────────────────────────┤
│             Infrastructure                   │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │  MCP     │  │   LLM    │  │ Workspace │  │
│  │  stdio   │  │ ollama/  │  │  git      │  │
│  │ adapters │  │ lmstudio │  │ worktree  │  │
│  └──────────┘  └──────────┘  └───────────┘  │
└─────────────────────────────────────────────┘
```

### Domain Layer (`domain/`)

Pure business logic. No external dependencies.

| Module | Purpose |
|--------|---------|
| `loop.py` | State machine: PLANNING → CODING → VERIFICATION → DONE/FAILED |
| `protocols.py` | 8 Protocol interfaces (Memory, Thinking, Vault, LLM, Workspace, etc.) |
| `types.py` | Pydantic models and enums |
| `stagnation.py` | Detects and handles agent stagnation loops |
| `state.py` | Task state persistence |
| `schema.py` | SQLite schema management |
| `exit_codes.py` | Standardized exit codes |

### Infrastructure Layer (`infra/`)

Concrete implementations of domain protocols.

| Module | Purpose |
|--------|---------|
| `adapters/mcp/` | Stdio adapters for MCP-agent-memory (memory, thinking, vault) |
| `adapters/null/` | Null adapters for offline/testing mode |
| `llm/ollama.py` | Ollama LLM client |
| `llm/lmstudio.py` | LM Studio LLM client |
| `workspace/git_worktree.py` | Git worktree provider for isolated execution |

### MCP Integration

CLI-agent-memory connects to MCP-agent-memory via **stdio subprocess transport**. The CLI spawns the MCP server as a child process and communicates via stdin/stdout JSON-RPC.

```
CLI Process (Python)
  │
  └─ MCPSessionManager (singleton)
       │
       └─ subprocess.Popen(MCP-agent-memory)
            │
            ├─ Qdrant (vector storage)
            ├─ llama-server (embeddings)
            └─ Ollama (LLM)
```

Supported MCP protocols:
- **MemoryProtocol**: `recall`, `store`, `ingest`, `search`, `list`
- **ThinkingProtocol**: `think`, `get_session`
- **VaultProtocol**: `write`, `read`, `search`, `list`, `append`

## Configuration

Configuration via environment variables with `AGENT_MEMORY_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_MEMORY_LLM_BACKEND` | `lmstudio` | LLM backend: lmstudio, ollama |
| `AGENT_MEMORY_LLM_BASE_URL` | `http://localhost:1234` | LLM API base URL |
| `AGENT_MEMORY_MEMORY_ENABLED` | `true` | Enable MCP memory connection |
| `AGENT_MEMORY_FORCE_LOCAL` | `false` | Force null adapters (no MCP) |
| `AGENT_MEMORY_MAX_ITERATIONS` | `50` | Max loop iterations |
| `AGENT_MEMORY_MAX_STAGNATION` | `3` | Max consecutive stagnation turns |
| `AGENT_MEMORY_TEST_COMMAND` | `""` | Test command for verification phase |

## Agent Loop

The core execution loop follows a state machine:

```
PLANNING ──→ CODING ──→ VERIFICATION
    │           │            │
    │           │            ├── Tests pass → DONE
    │           │            └── Tests fail → CODING
    │           │
    │           └── Stagnation detected → Intervention → CODING
    │
    └── Max iterations → FAILED
```

Each phase:
1. **PLANNING**: Recall context, generate plan, save to vault
2. **CODING**: Generate file changes, parse output, apply edits
3. **VERIFICATION**: Run test command, ingest failures, retry or mark done

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/domain/test_loop.py -v

# With coverage
pytest tests/ --cov=CLI_agent_memory --cov-report=term-missing
```

30 tests across:
- `test_loop.py` — Loop engine, worktree, stagnation, result
- `test_schema.py` — Database init, tables, idempotent
- `test_stagnation.py` — Edit detection, error tracking, reset
- `test_state.py` — State save/load, transitions, task ID
- `test_types.py` — Pydantic models, JSON serialization
- `test_config.py` — Defaults, env prefix, fields

## License

MIT
