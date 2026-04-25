# Architecture

## Overview

CLI-agent-memory uses **Hexagonal Architecture** (Ports & Adapters). The domain layer contains all business logic with zero external dependencies. Infrastructure adapters implement domain protocols to connect to LLMs, MCP servers, and local storage.

```
src/CLI_agent_memory/
├── cli.py              # Entry point — argparse dispatch, signal handling
├── parser.py           # Argparse definitions for all 14 commands
├── commands.py         # Command handlers (status, cleanup, think, recall, remember, decisions)
├── commands_extra.py   # Command handlers (cancel, plan, db)
├── output.py           # JSON/text output formatters
├── cli_helpers.py      # Auto-detection, description resolution
├── doctor.py           # System health check
├── config.py           # Pydantic Settings (env vars with AGENT_MEMORY_ prefix)
│
├── domain/             # PURE BUSINESS LOGIC — 0 external imports
│   ├── types.py        # Pydantic models, enums (AgentState, Message, TaskResult, ...)
│   ├── protocols.py    # 8 Protocol interfaces (@runtime_checkable)
│   ├── loop.py         # LoopEngine — state machine (PLANNING→CODING→VERIFICATION→DONE/FAILED)
│   ├── file_ops.py     # Multi-format file parsing, git diff fallback, trim_history
│   ├── stagnation.py   # StagnationMonitor — detects agent loops
│   ├── state.py        # TaskContext — state persistence to .agent-memory-state.json
│   ├── prompts/        # LLM prompt templates
│   │   └── templates.py
│   ├── db/
│   │   └── schema.py   # SQLite DDL — 10 tables, 3 FTS5 virtual tables
│   └── exit_codes.py   # POSIX exit codes (0, 1, 2, 10-22, 130, 143)
│
└── infra/              # ADAPTERS — implements domain protocols
    ├── adapters/
    │   ├── protocol_factory.py  # 3-tier resolution (MCP → local → null)
    │   ├── mcp/               # MCP stdio transport
    │   │   ├── discovery.py     # Auto-discover MCP-agent-memory path
    │   │   ├── mcp_env.py       # Load .env from MCP config
    │   │   ├── session.py       # MCPSessionManager (JSON-RPC subprocess)
    │   │   ├── stdio_manager.py # Backward-compatible re-export
    │   │   ├── memory_stdio.py  # MemoryProtocol → MCP tools
    │   │   ├── thinking_stdio.py # ThinkingProtocol → MCP tools
    │   │   └── vault_stdio.py   # VaultProtocol → MCP tools
    │   ├── local/             # SQLite + filesystem adapters
    │   │   ├── memory_local.py  # MemoryProtocol → SQLite + FTS5
    │   │   ├── thinking_local.py# ThinkingProtocol → SQLite
    │   │   └── vault_local.py   # VaultProtocol → filesystem
    │   └── null/              # Offline/testing stubs
    │       ├── memory_null.py
    │       ├── thinking_null.py
    │       └── vault_null.py
    ├── llm/
    │   ├── __init__.py       # Factory: create_llm_client(backend, config, model)
    │   ├── lmstudio.py       # LM Studio: auto-detect model, retry on ConnectError
    │   └── ollama.py         # Ollama: POST /api/chat
    └── workspace/
        └── git_worktree.py  # WorkspaceProtocol → git worktrees
```

## Layers

### CLI Layer

**Responsibility**: Parse arguments, dispatch to commands, handle signals.

- `cli.py` — Main entry point. Dispatches commands, manages SIGINT/SIGTERM in `run`.
- `parser.py` — Argparse definitions for all 14 subcommands. Each command has its own `_add_*` function.
- `commands.py` — Handlers for 6 memory/management commands (status, cleanup, think, recall, remember, decisions).
- `commands_extra.py` — Handlers for 3 task commands (cancel, plan, db).
- `output.py` — `json_output()` and `text_output()` formatters.
- `cli_helpers.py` — Auto-detect test command from project files, resolve description from `--from-file`.
- `doctor.py` — System health check: git, python, LLM, MCP, uv, test command.

### Domain Layer

**Responsibility**: Business logic, state management, file parsing, prompts.

**Invariant: 0 imports from `infra/` or `CLI_agent_memory.cli_helpers`.**

| Module | Lines | Purpose |
|--------|-------|---------|
| `types.py` | 101 | 12 Pydantic models + AgentState enum |
| `protocols.py` | 84 | 8 Protocol interfaces (Memory, Thinking, Vault, LLM, Workspace, Engram, Planning, Conversation) |
| `loop.py` | 150 | LoopEngine state machine, resume(), get_status(), _execute_loop() |
| `file_ops.py` | 75 | parse_and_write_files (3 formats), write_safe (path traversal protection), trim_history |
| `stagnation.py` | 68 | StagnationMonitor: detect no-edits loops and repeated errors |
| `state.py` | 63 | TaskContext: save/load .agent-memory-state.json, UUID5 task IDs |
| `templates.py` | 121 | 5 DONE signals, is_done_signal(), multi-format coding instructions |
| `schema.py` | 113 | SQLite DDL: 10 tables + 3 FTS5 virtual tables |
| `exit_codes.py` | 16 | 11 exit codes (0, 1, 2, 10-22, 130, 143) |

### Infrastructure Layer

**Responsibility**: Concrete implementations of domain protocols.

**Adapter Resolution** (`ProtocolFactory`):
1. **MCP stdio** — if `memory_enabled=True` (default). Spawns MCP-agent-memory subprocess.
2. **Local** — if `force_local=True`. SQLite + filesystem.
3. **Null** — if `memory_enabled=False`. Returns empty stubs for testing.

#### MCP Transport

```
CLI Process
  └── MCPSessionManager (singleton subprocess.Popen)
        │
        └── stdin/stdout JSON-RPC ──→ MCP-agent-memory
                                       ├── Qdrant (vector DB)
                                       ├── llama-server (embeddings)
                                       └── Ollama (LLM for embedding model)
```

Split into 3 modules for INV-02 compliance:
- `discovery.py` (44 lines) — Auto-discover MCP-agent-memory installation path
- `mcp_env.py` (44 lines) — Load `.env` with defaults
- `session.py` (149 lines) — MCPSessionManager, JSON-RPC, reader, singleton

#### Local Adapters

- `memory_local.py` — SQLite + FTS5 for full-text search across stored memories
- `thinking_local.py` — SQLite for thinking session persistence
- `vault_local.py` — Filesystem-based vault entries (folder/file.md)

#### LLM Clients

- `lmstudio.py` — Auto-detect model via `GET /v1/models`, retry once on `ConnectError`
- `ollama.py` — `POST /api/chat`, independent port (11434, not shared with LM Studio)

## Data Flow

### Run Command Flow

```
cli run "Fix auth" --repo ./app --llm ollama
  │
  ├─ create_llm_client("ollama", config)
  ├─ ProtocolFactory(config).create_memory/thinking/vault()
  ├─ LoopEngine(llm, memory, thinking, vault, workspace, config)
  │
  └─ engine.run("Fix auth", ./app)
       │
       ├─ workspace.create("agent-memory/TIMESTAMP")
       │     └── git worktree add -b agent-memory/TIMESTAMP
       │
       ├─ PLANNING:
       │     ├─ memory.recall("Fix auth")
       │     ├─ llm.generate(planning_prompt)
       │     └─ workspace.write_file("PLAN.md")
       │
       ├─ CODING (repeats):
       │     ├─ memory.recall(task + plan)
       │     ├─ llm.generate(coding_prompt + files list)
       │     ├─ file_ops.parse_and_write_files(response)
       │     ├─ stagnation.record_turn(files_edited)
       │     ├─ trim_history(history, MAX_HISTORY=30)
       │     └─ if is_done_signal → VERIFICATION
       │
       ├─ VERIFICATION:
       │     ├─ workspace.run_command(test_cmd)
       │     ├─ if pass → state = DONE
       │     └─ if fail → memory.ingest(errors) → CODING
       │
       └─ return TaskResult(task_id, status, files_modified, ...)
```

### DONE Signal Detection

The loop checks the **last 200 characters** of the LLM response for:
- `DONE CODING`
- `ALL STEPS COMPLETE`
- `IMPLEMENTATION COMPLETE`
- `ALL CHANGES APPLIED`
- `TASK COMPLETE`

Case-insensitive. Only checked in the tail of the response to avoid false positives from mid-reasoning mentions.

## Design Decisions

### Why stdio instead of HTTP for MCP?

MCP-agent-memory runs a local Qdrant + embedding model that doesn't expose HTTP. Stdio subprocess is the most universal transport — works regardless of network configuration.

### Why 3 adapter tiers?

Production → MCP (rich memory, embeddings, vault).
Offline/dev → Local (SQLite works without network).
Testing → Null (fast, deterministic, no side effects).

### Why FTS5 for local search?

SQLite FTS5 provides full-text search without any external dependency. The `memories_fts` virtual table is content-synced with the `memories` table via rowid references.

### Why sliding window history?

Brutally truncating history after N messages causes the LLM to lose context about what it's done. A sliding window (keep system prompt + last N messages) preserves recent context while staying within token limits. Stagnation resets use a smaller window (keep last 6) to break out of loops more aggressively.
