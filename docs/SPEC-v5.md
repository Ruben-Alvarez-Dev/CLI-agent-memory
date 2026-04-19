# SPEC v5: CLI-agent-memory — Autonomous Coding Agent

**Version**: 5.0
**Date**: 2026-04-19
**Status**: DRAFT — Pending approval
**Principle**: Spec first, code after. SOLID + DRY + TDD + Hexagonal Architecture.

---

## 0. INVARIANTES

```
INV-01: 0 direct coupling with MCP-agent-memory (communication only via ports)
INV-02: Each file < 150 lines (strict SRP)
INV-03: All external dependencies via interfaces (DIP)
INV-04: Zero mock/demo/fake data — always production
INV-05: TDD mandatory — tests before code
INV-06: Python 3.12+ with complete type hints
INV-07: Single entry point: CLI-agent-memory (CLI) or python -m CLI_agent_memory
INV-08: Configuration via TOML + env vars (12-factor)
INV-09: --json output always available (universality)
INV-10: "jart" forbidden — always "jart-os"
INV-11: Package name: CLI-agent-memory (non-negotiable)
INV-12: Install path: /Users/XXXX/MCP-servers/CLI-agent-memory
INV-13: All documentation, specs, code and comments in English
```

---

## 1. PRODUCT DEFINITION

### 1.1 What CLI-agent-memory is

CLI-agent-memory is a CLI that takes a task description (PRD, issue, or free text),
isolates it in a git worktree, and executes an autonomous loop of
planning → coding → verification until completion or explicit failure.

It complements MCP-agent-memory. When MCP is available, it delegates memory/thinking
to the memory server. When MCP is not available, it operates autonomously
with local SQLite + FTS5 + JSONL storage.

### 1.2 What CLI-agent-memory is NOT

- It is not a memory server (that is MCP-agent-memory)
- It is not an LLM (it uses LM Studio, Ollama, or external APIs)
- It is not an IDE (it has no UI in Release 1)
- It is not a replacement for tools like Aider/Cursor (it is complementary)

### 1.3 Ecosystem relationship

```
┌──────────────────────────────────────────────────┐
│  User                                            │
│  CLI-agent-memory run "Implement auth" --repo .  │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│  CLI-agent-memory (this project)                 │
│                                                  │
│  ┌─────────┐  ┌──────────┐  ┌────────────────┐  │
│  │  Loop    │  │ Stagna-  │  │  Workspace     │  │
│  │  Engine  │  │ tion     │  │  (git wt)      │  │
│  └────┬─────┘  └──────────┘  └─────┬──────────┘  │
│       │                            │             │
│  ┌────┴─────┐              ┌───────┴──────────┐  │
│  │  LLM     │              │  Filesystem      │  │
│  │  Client  │              │  (worktree)      │  │
│  └────┬─────┘              └──────────────────┘  │
│       │                                          │
│  ┌────┴──────────┐                               │
│  │  Memory       │                               │
│  │  (MCP or      │                               │
│  │   local)      │                               │
│  └────┬──────────┘                               │
└───────┼──────────────────────────────────────────┘
        │                    │
        ▼                    ▼
┌───────────────┐  ┌────────────────────┐
│ LM Studio     │  │ MCP-agent-memory   │
│ :1234         │  │ :3050              │
│ (local LLM)   │  │ (memory/RAG)       │
└───────────────┘  └────────────────────┘
```

---

## 2. ARCHITECTURE — HEXAGONAL (PORTS & ADAPTERS)

### 2.1 File structure

```
src/CLI_agent_memory/
├── __init__.py                  # Version + metadata
├── __main__.py                  # Entry point: python -m CLI_agent_memory
├── cli.py                       # CLI arguments (argparse) — 0 business logic
├── config.py                    # Settings (pydantic-settings, TOML + env)
├── gateway.py                   # ProtocolFactory: selects correct adapters
│
├── domain/                      # PURE business logic (0 external dependencies)
│   ├── __init__.py
│   ├── types.py                 # Enums, dataclasses, Pydantic models
│   ├── protocols.py             # ALL Protocol interfaces (ports)
│   ├── loop.py                  # LoopEngine (state machine)
│   ├── stagnation.py            # StagnationMonitor
│   ├── state.py                 # TaskContext (persisted state)
│   ├── exit_codes.py            # POSIX exit codes
│   └── db/
│       ├── __init__.py
│       ├── schema.py            # SQLite schema + init_db()
│       └── migrations/          # Versioned migrations
│
├── infra/                       # Concrete implementations (adapters)
│   ├── __init__.py
│   │
│   ├── adapters/
│   │   ├── mcp/                 # MCP-agent-memory adapters
│   │   │   ├── __init__.py
│   │   │   ├── memory_http.py   # MCPMemoryAdapter (HTTP JSON-RPC)
│   │   │   ├── memory_stdio.py  # MCPStdioAdapter (subprocess stdio)
│   │   │   ├── thinking_mcp.py  # MCPThinkingAdapter
│   │   │   ├── engram_mcp.py    # MCPEngramAdapter
│   │   │   └── vault_mcp.py     # MCPVaultAdapter
│   │   │
│   │   ├── a2a/                 # A2A protocol (Release 5)
│   │   │   ├── __init__.py
│   │   │   ├── server.py        # A2A server (JSON-RPC 2.0)
│   │   │   └── client.py        # A2A client
│   │   │
│   │   ├── jart-os/             # Jart-OS adapters (Release 5-6)
│   │   │   ├── __init__.py
│   │   │   ├── federation_nats.py
│   │   │   ├── federation_redis.py
│   │   │   ├── governance_jart_os.py
│   │   │   └── observability_jart_os.py
│   │   │
│   │   ├── local/               # Autonomous adapters (fallback)
│   │   │   ├── __init__.py
│   │   │   ├── memory_sqlite.py # LocalMemoryAdapter (SQLite + FTS5)
│   │   │   ├── thinking_local.py
│   │   │   ├── engram_sqlite.py
│   │   │   ├── planning_local.py
│   │   │   ├── vault_local.py   # Obsidian vault
│   │   │   ├── conversation_local.py
│   │   │   └── null/            # No-op (testing)
│   │   │       ├── __init__.py
│   │   │       ├── memory_null.py
│   │   │       ├── thinking_null.py
│   │   │       ├── federation_null.py
│   │   │       └── governance_null.py
│   │   │
│   │   └── protocol_factory.py  # THE DECISION BRAIN
│   │
│   ├── llm/                     # LLM clients
│   │   ├── __init__.py          # Factory: create_llm_client()
│   │   ├── base.py              # BaseLLMClient (shared code)
│   │   ├── lmstudio.py          # LM Studio (:1234)
│   │   ├── ollama.py            # Ollama (:11434)
│   │   └── openai_compat.py     # Any OpenAI-compatible API
│   │
│   └── workspace/
│       ├── __init__.py
│       └── git_worktree.py      # GitWorktreeProvider
│
├── prompts/
│   ├── __init__.py
│   └── templates.py             # Prompt templates per phase
│
├── output/                      # Output formatting (SRP)
│   ├── __init__.py
│   ├── human.py                 # Human-readable (colored, tables)
│   └── json.py                  # Machine-readable JSON
│
├── vault/                       # Obsidian vault operations
│   ├── __init__.py
│   └── operations.py            # High-level vault operations
│
├── integrations/                # External integrations (Release 4)
│   ├── __init__.py
│   ├── pr.py                    # PR auto-generation
│   ├── github.py                # GitHub Issues
│   ├── notifications.py         # Webhooks (Slack, Discord)
│   └── sync.py                  # Vault sync with MCP-agent-memory
│
├── server/                      # API server (Release 3)
│   ├── __init__.py
│   ├── app.py                   # FastAPI app
│   ├── routes/
│   │   ├── agent.py             # Agent Protocol endpoints
│   │   ├── tasks.py             # CRUD tasks
│   │   ├── config.py            # Config API
│   │   ├── data.py              # Data API (memories, decisions, stats)
│   │   ├── vault.py             # Vault API
│   │   └── health.py            # Health/metrics (Jart-OS compatible)
│   └── static/                  # Frontend SPA (Release 3)
│
├── tui/                         # TUI panel (Release 2)
│   ├── __init__.py
│   ├── app.py                   # Textual app
│   ├── widgets/
│   │   ├── task_table.py
│   │   ├── log_panel.py
│   │   └── progress.py
│   └── screens/
│       ├── dashboard.py
│       ├── config.py
│       └── task_detail.py
│
├── plugins/                     # Plugin system (Release 4)
│   ├── __init__.py
│   ├── system.py                # Plugin loader + hooks
│   └── secrets.py               # Secret scanning
│
└── compliance/                  # Governance (Release 6)
    ├── __init__.py
    ├── audit.py                 # Audit trail
    └── export.py                # Compliance export
```

### 2.2 SOLID applied

#### S — Single Responsibility

| File | One responsibility |
|------|-------------------|
| `loop.py` | Orchestrate phases (PLANNING→CODING→VERIFICATION) |
| `stagnation.py` | Detect stagnation |
| `state.py` | Persist task state |
| `cli.py` | Parse user arguments |
| `config.py` | Load configuration |
| `lmstudio.py` | Talk to LM Studio |
| `memory_http.py` | Talk to MCP-agent-memory via HTTP |
| `memory_sqlite.py` | Talk to local SQLite |
| `git_worktree.py` | Manage git worktrees |
| `templates.py` | Generate prompts |
| `vault_local.py` | Write to local Obsidian vault |

#### O — Open/Closed

- Add new LLM backend → new file in `infra/llm/`, zero changes in `loop.py`
- Add new workspace type → new file in `infra/workspace/`, zero changes
- Add new memory backend → new file in `infra/adapters/`, zero changes
- Add new CLI command → new handler, zero changes in existing ones

#### L — Liskov Substitution

- Any `MemoryProtocol` implementation can substitute another
- Any `ThinkingProtocol` implementation can substitute another
- Any `WorkspaceProtocol` implementation can substitute another
- Any `LLMClient` implementation can substitute another

#### I — Interface Segregation

```python
# NO: fat interface
class AgentClient:
    def generate(self, prompt, history): ...
    def recall(self, query): ...
    def create_worktree(self, branch): ...

# YES: small, focused interfaces
class LLMClient(Protocol):
    async def generate(self, prompt: str, history: list[Message]) -> LLMResponse: ...

class MemoryProtocol(Protocol):
    async def recall(self, query: str, max_tokens: int = 4000) -> ContextPack: ...
    async def store(self, event_type: str, content: str, tags: list[str] = []) -> str: ...
    async def search(self, query: str, limit: int = 10) -> list[Memory]: ...

class WorkspaceProtocol(Protocol):
    def create(self, branch_name: str, base_ref: str = "HEAD") -> Path: ...
    def remove(self, branch_name: str, force: bool = False) -> bool: ...
    def run_command(self, worktree_path: Path, command: str) -> CommandResult: ...
```

#### D — Dependency Inversion

```
loop.py (domain) depends on:
  ├── MemoryProtocol (abstraction)     ← NOT memory_sqlite.py (implementation)
  ├── ThinkingProtocol (abstraction)   ← NOT thinking_local.py
  ├── LLMClient (abstraction)          ← NOT lmstudio.py
  └── WorkspaceProtocol (abstraction)  ← NOT git_worktree.py

cli.py (presentation) assembles:
  factory = ProtocolFactory(config)
  loop = LoopEngine(
      llm=create_llm_client(config),
      memory=factory.create_memory(),
      thinking=factory.create_thinking(),
      workspace=create_workspace(config),
  )
```

### 2.3 Protocol Abstraction Layer (THE ASEPTIC INTERFACE)

```
                    ┌──────────────────────┐
                    │   domain/loop.py     │  ← KNOWS NOTHING ABOUT PROTOCOLS
                    └──────────┬───────────┘
                               │ uses
                    ┌──────────▼───────────┐
                    │ domain/protocols.py  │  ← Pure interfaces (Protocol)
                    │                      │
                    │  MemoryProtocol      │
                    │  ThinkingProtocol    │
                    │  EngramProtocol      │
                    │  PlanningProtocol    │
                    │  ConversationProtocol│
                    │  VaultProtocol       │
                    │  WorkspaceProtocol   │
                    │  LLMClient           │
                    │  FederationProtocol  │
                    │  GovernanceProtocol  │
                    │  ObservabilityProtocol│
                    └──────────┬───────────┘
                               │ implements
           ┌───────────────────┼───────────────────┐
           │                   │                   │
    ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
    │  mcp/       │    │  local/     │    │  jart-os/   │
    │  adapters   │    │  adapters   │    │  adapters   │
    │  (MCP-agent │    │  (SQLite    │    │  (Jart-OS   │
    │   memory)   │    │   fallback) │    │   federation)│
    └─────────────┘    └─────────────┘    └─────────────┘
```

### 2.4 Four supported protocols

| Protocol | When | Transport | Example |
|----------|------|-----------|---------|
| **MCP stdio** | CLI-agent-memory is subprocess of an agent | stdin/stdout | Claude Code invokes CLI-agent-memory |
| **MCP HTTP** | 1MCP gateway at :3050 | HTTP/SSE | Any HTTP client |
| **A2A JSON-RPC** | Agent-to-Agent (Jart-OS or standalone) | HTTP | IDE, another agent |
| **NATS JetStream** | Jart-OS federation | TCP | Events, state sync |
| **Local** | No infrastructure | SQLite direct | Standalone |

### 2.5 Protocol Factory (decision brain)

```python
"""
Resolution order:
1. Flag --force-local → local/
2. MCP stdio available (stdin is not tty) → mcp/stdio
3. MCP HTTP responds (:3050) → mcp/http
4. A2A endpoint configured → a2a/
5. Jart-OS federation active → jart-os/
6. Fallback → local/
"""
```

---

## 3. SPECS — DOMAIN LAYER (Pure Logic)

### SPEC-D1: Domain Types

**File**: `domain/types.py`
**Dependencies**: pydantic only

```python
class AgentState(str, Enum):
    PLANNING = "PLANNING"
    CODING = "CODING"
    VERIFICATION = "VERIFICATION"
    DONE = "DONE"
    FAILED = "FAILED"

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class LLMResponse(BaseModel):
    text: str
    files_edited: int = 0
    tool_calls: list[dict] = Field(default_factory=list)
    finish_reason: str = "stop"

class CommandResult(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1

class ContextPack(BaseModel):
    context_text: str = ""
    sources: list[str] = Field(default_factory=list)
    token_count: int = 0

class Memory(BaseModel):
    id: str
    content: str
    tags: list[str] = Field(default_factory=list)
    scope: str = "session"
    importance: float = 0.5
    created_at: str = ""

class Decision(BaseModel):
    id: str
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""

class ThinkingStep(BaseModel):
    step_number: int
    thought: str
    next_needed: bool = True

class ThinkingResult(BaseModel):
    session_id: str
    problem: str
    steps: list[ThinkingStep] = Field(default_factory=list)
    conclusion: str = ""

class Plan(BaseModel):
    id: str
    task_id: str
    goal: str
    steps: list[str] = Field(default_factory=list)
    status: str = "active"

class VaultEntry(BaseModel):
    folder: str
    filename: str
    content: str
    path: str

class TaskResult(BaseModel):
    task_id: str
    status: AgentState
    worktree_path: str
    plan: str = ""
    files_modified: list[str] = Field(default_factory=list)
    tests_passed: bool = False
    error: str = ""
    duration_seconds: float = 0.0

class HealthStatus(BaseModel):
    status: str  # "healthy" | "degraded"
    service: str
    uptime_seconds: float
    connections: dict[str, str] = Field(default_factory=dict)

class ServiceMetrics(BaseModel):
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_in_progress: int = 0
    total_tool_calls: int = 0
    total_errors: int = 0
    uptime_seconds: float = 0.0
```

**Acceptance Criteria**:
```
AC-D1.1: All types are Pydantic models or Enums
AC-D1.2: 0 external dependencies (pydantic + stdlib only)
AC-D1.3: Types used in both domain/ and infra/ (shared)
AC-D1.4: JSON serializable (model_dump_json / model_validate_json)
```

---

### SPEC-D2: Protocol Interfaces (Ports)

**File**: `domain/protocols.py`
**Dependencies**: `domain/types.py`

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class MemoryProtocol(Protocol):
    """Abstraction of any memory backend (MCP or local)."""
    async def recall(self, query: str, max_tokens: int = 4000) -> ContextPack: ...
    async def store(self, event_type: str, content: str, tags: list[str] = []) -> str: ...
    async def ingest(self, event_type: str, content: str) -> None: ...
    async def search(self, query: str, limit: int = 10) -> list[Memory]: ...
    async def list(self, tags: list[str] = [], limit: int = 50) -> list[Memory]: ...

@runtime_checkable
class ThinkingProtocol(Protocol):
    """Abstraction of sequential thinking backend."""
    async def think(self, problem: str, depth: int = 5) -> ThinkingResult: ...
    async def get_session(self, session_id: str) -> ThinkingResult | None: ...

@runtime_checkable
class EngramProtocol(Protocol):
    """Abstraction of engram (decisions + entities) backend."""
    async def save_decision(self, title: str, body: str, tags: list[str] = []) -> str: ...
    async def search_decisions(self, query: str) -> list[Decision]: ...
    async def save_entity(self, name: str, kind: str, data: dict) -> str: ...
    async def search_entities(self, query: str) -> list[dict]: ...

@runtime_checkable
class PlanningProtocol(Protocol):
    """Abstraction of planning backend."""
    async def create_plan(self, goal: str, context: str) -> Plan: ...
    async def get_plan(self, plan_id: str) -> Plan | None: ...

@runtime_checkable
class ConversationProtocol(Protocol):
    """Abstraction of conversation persistence."""
    async def save(self, thread_id: str, messages: list[dict], summary: str) -> str: ...
    async def search(self, query: str) -> list[dict]: ...

@runtime_checkable
class VaultProtocol(Protocol):
    """Abstraction of Obsidian vault operations."""
    async def write(self, folder: str, filename: str, content: str) -> VaultEntry: ...
    async def read(self, folder: str, filename: str) -> str | None: ...
    async def search(self, query: str) -> list[VaultEntry]: ...
    async def list_entries(self, folder: str = "") -> list[VaultEntry]: ...
    async def append(self, folder: str, filename: str, content: str) -> None: ...

@runtime_checkable
class WorkspaceProtocol(Protocol):
    """Abstraction of workspace (git worktree)."""
    def create(self, branch_name: str, base_ref: str = "HEAD") -> Path: ...
    def remove(self, branch_name: str, force: bool = False) -> bool: ...
    def run_command(self, worktree_path: Path, command: str) -> CommandResult: ...
    def read_file(self, worktree_path: Path, file_path: str) -> str | None: ...
    def write_file(self, worktree_path: Path, file_path: str, content: str) -> None: ...
    def list_files(self, worktree_path: Path, pattern: str = "**/*.py") -> list[str]: ...

@runtime_checkable
class LLMClient(Protocol):
    """Abstraction of any LLM backend."""
    async def generate(
        self,
        prompt: str,
        history: list[Message],
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse: ...
    def is_available(self) -> bool: ...

@runtime_checkable
class FederationProtocol(Protocol):
    """Abstraction of Jart-OS federation (Release 5)."""
    async def register(self, service_info: dict) -> None: ...
    async def discover(self, service_name: str) -> dict | None: ...
    async def publish_event(self, subject: str, data: dict) -> None: ...
    async def subscribe(self, subject: str, handler) -> None: ...

@runtime_checkable
class GovernanceProtocol(Protocol):
    """Abstraction of Jart-OS governance (Release 6)."""
    async def check_permission(self, action: str, resource: str) -> bool: ...
    async def validate_task(self, task: dict) -> tuple[bool, str]: ...
    async def write_audit(self, task_id: str, event: str, data: dict) -> None: ...

@runtime_checkable
class ObservabilityProtocol(Protocol):
    """Abstraction of Jart-OS observability (Release 6)."""
    async def health(self) -> HealthStatus: ...
    async def metrics(self) -> ServiceMetrics: ...
    def record_task_start(self, task_id: str) -> None: ...
    def record_task_complete(self) -> None: ...
    def record_task_failure(self) -> None: ...
```

**Acceptance Criteria**:
```
AC-D2.1: All interfaces use Protocol (structural subtyping)
AC-D2.2: 0 business logic — only signatures
AC-D2.3: Return types are from domain/types.py
AC-D2.4: One interface per responsibility (ISP)
AC-D2.5: All interfaces are @runtime_checkable
```

---

### SPEC-D3: LoopEngine (State Machine)

**File**: `domain/loop.py`
**Dependencies**: `domain/protocols.py`, `domain/types.py`, `domain/stagnation.py`, `domain/state.py`

#### Behavior

```
start(task_description)
    │
    ├─ workspace.create("agent-memory/{task_id}")
    ├─ state = TaskContext(worktree_path, PLANNING)
    │
    └─ while state not in (DONE, FAILED):
         │
         ├─ PLANNING:
         │    ├─ memory.recall(task) → RAG context
         │    ├─ llm.generate(planning_prompt, history) → PLAN.md
         │    ├─ workspace.write_file("PLAN.md", plan)
         │    ├─ vault.write("Decisions", task_id, plan_summary)
         │    └─ if PLAN.md exists → transition(CODING)
         │
         ├─ CODING:
         │    ├─ memory.recall(task + plan) → updated context
         │    ├─ llm.generate(coding_prompt, history) → code
         │    ├─ stagnation.record(files_edited)
         │    │    └─ if stagnant → truncate history + intervention prompt
         │    └─ if "DONE CODING" → transition(VERIFICATION)
         │
         └─ VERIFICATION:
              ├─ workspace.run_command(test_command)
              ├─ if tests pass → transition(DONE)
              │    └─ memory.store("task_completed", result)
              │    └─ vault.write("Decisions", task_id + "-result", result)
              └─ if tests fail → transition(CODING)
                   ├─ stagnation.record(error)
                   └─ memory.ingest("test_failure", error)
```

#### Public API

```python
class LoopEngine:
    def __init__(
        self,
        llm: LLMClient,
        memory: MemoryProtocol,
        thinking: ThinkingProtocol,
        workspace: WorkspaceProtocol,
        vault: VaultProtocol,
        config: LoopConfig,
    ): ...

    async def run(self, task_description: str, repo_path: Path) -> TaskResult:
        """Execute the full loop. Returns when DONE or FAILED."""

    async def resume(self, task_id: str) -> TaskResult:
        """Resume a paused task (reads .agent-memory-state.json)."""

    def get_status(self) -> TaskResult:
        """Current state without executing."""
```

**Acceptance Criteria**:
```
AC-D3.1: LoopEngine depends ONLY on protocols (DIP), not implementations
AC-D3.2: Never exceeds max_iterations (default: 50)
AC-D3.3: State persists in .agent-memory-state.json after each transition
AC-D3.4: Stagnation detects ≥3 turns without edits and ≥3 same error
AC-D3.5: On stagnation, history truncates to last 2 messages
AC-D3.6: On completion, memory.store + vault.write receive result
AC-D3.7: On failure, memory.ingest receives the error
AC-D3.8: Testable without real LLM (using MockLLMClient)
AC-D3.9: < 150 lines
```

---

### SPEC-D4: StagnationMonitor

**File**: `domain/stagnation.py`
**Dependencies**: stdlib only

```python
@dataclass
class StagnationResult:
    is_stagnant: bool
    reason: str = ""          # "no_edits" | "same_error" | ""
    intervention: str = ""    # Intervention prompt

class StagnationMonitor:
    def __init__(self, max_failures: int = 3): ...
    def record_turn(self, files_edited: int, current_error: str = "") -> StagnationResult: ...
    def reset(self) -> None: ...
```

**Acceptance Criteria**:
```
AC-D4.1: record_turn returns StagnationResult (not bare bool)
AC-D4.2: Intervention prompts are configurable (not hardcoded)
AC-D4.3: < 80 lines
AC-D4.4: 0 dependencies
```

---

### SPEC-D5: TaskContext (Persisted State)

**File**: `domain/state.py`
**Dependencies**: `domain/types.py`

```python
class TaskContext:
    def __init__(self, worktree_path: Path): ...
    state: AgentState
    task_description: str
    plan: str
    progress: str
    iteration: int
    task_id: str
    def save(self) -> None: ...
    def load(self) -> bool: ...
    def transition(self, to: AgentState) -> None: ...
    @staticmethod
    def find_in_worktree(worktree_path: Path) -> TaskContext | None: ...
```

**Acceptance Criteria**:
```
AC-D5.1: JSON serializable/deserializable without loss
AC-D5.2: transition() always calls save()
AC-D5.3: task_id is deterministic UUID4 (seed = branch_name)
AC-D5.4: < 60 lines
```

---

### SPEC-D6: SQLite Schema

**File**: `domain/db/schema.py`
**Dependencies**: stdlib (sqlite3)

Tables: `memories`, `memories_fts`, `decisions`, `decisions_fts`, `thinking_sessions`, `thinking_steps`, `plans`, `conversations`, `conversations_fts`, `tasks`, `audit_events`, `agent_metrics`.

**Acceptance Criteria**:
```
AC-D6.1: FTS5 virtual tables for memories, decisions, conversations
AC-D6.2: Foreign keys with ON DELETE CASCADE
AC-D6.3: init_db() creates all tables idempotently
AC-D6.4: < 100 lines
```

---

### SPEC-D7: Exit Codes

**File**: `domain/exit_codes.py`
**Dependencies**: stdlib

```python
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_TASK_FAILED = 10
EXIT_STAGNATION = 11
EXIT_CANCELLED = 12
EXIT_LLM_UNAVAILABLE = 20
EXIT_MEMORY_UNAVAILABLE = 21
EXIT_WORKTREE_ERROR = 22
EXIT_SIGINT = 130  # 128 + 2
EXIT_SIGTERM = 143  # 128 + 15
```

---

## 4. SPECS — INFRASTRUCTURE LAYER (Adapters)

### 4a. MCP Adapters

#### SPEC-MCP-01: MCP Memory HTTP Adapter

**File**: `infra/adapters/mcp/memory_http.py`
**Dependencies**: httpx, `domain/protocols.py`

Protocol via HTTP JSON-RPC to MCP-agent-memory gateway (:3050):
- `recall` → `engram_1mcp_recall`
- `store` → `automem_1mcp_memorize`
- `ingest` → `automem_1mcp_ingest_event`
- `search` → `engram_1mcp_search`
- `list` → `engram_1mcp_list`

Timeouts: 30s recall, 10s store/ingest.
Fallback: graceful (returns empty results, no crash).

**AC**: Works with gateway at :3050. < 100 lines.

#### SPEC-MCP-02: MCP Thinking Adapter
**File**: `infra/adapters/mcp/thinking_mcp.py`
→ `sequential_thinking_1mcp_*`

#### SPEC-MCP-03: MCP Engram Adapter
**File**: `infra/adapters/mcp/engram_mcp.py`
→ `engram_1mcp_save_decision`, `engram_1mcp_search_decisions`

#### SPEC-MCP-04: MCP Vault Adapter
**File**: `infra/adapters/mcp/vault_mcp.py`
→ `engram_1mcp_memory_vault_write`

#### SPEC-MCP-05: MCP Stdio Adapter
**File**: `infra/adapters/mcp/memory_stdio.py`
Communication via stdin/stdout subprocess.

### 4b. Local Adapters (Autonomous)

#### SPEC-LOC-01: Local Memory SQLite Adapter
**File**: `infra/adapters/local/memory_sqlite.py`
SQLite + FTS5 for recall/store/search/list.

#### SPEC-LOC-02: Local Thinking Adapter
**File**: `infra/adapters/local/thinking_local.py`
Recursive loop with LLM → SQLite thinking_sessions + thinking_steps.

#### SPEC-LOC-03: Local Engram Adapter
**File**: `infra/adapters/local/engram_sqlite.py`
SQLite decisions + FTS5 search.

#### SPEC-LOC-04: Local Planning Adapter
**File**: `infra/adapters/local/planning_local.py`
LLM generates plan → SQLite plans.

#### SPEC-LOC-05: Local Vault Adapter
**File**: `infra/adapters/local/vault_local.py`
Writes to `.agent-memory/vault/` (Decisions, Patterns, Notes, Inbox).

#### SPEC-LOC-06: Local Conversation Adapter
**File**: `infra/adapters/local/conversation_local.py`
JSONL + SQLite.

#### SPEC-LOC-07: Null Adapters
**File**: `infra/adapters/null/*.py`
0 side effects. < 20 lines each.

### 4c. LLM Clients

#### SPEC-LLM-01: LM Studio Client
**File**: `infra/llm/lmstudio.py`
POST /v1/chat/completions. Timeout configurable. 1 retry on connection refused.

#### SPEC-LLM-02: Ollama Client
**File**: `infra/llm/ollama.py`
POST /api/chat.

#### SPEC-LLM-03: OpenAI-Compatible Client
**File**: `infra/llm/openai_compat.py`
Any OpenAI-compatible API (z.ai, OpenRouter, etc.).

#### SPEC-LLM-04: LLM Factory
**File**: `infra/llm/__init__.py`
`create_llm_client(config) → LLMClient` based on config.backend.

### 4d. Workspace

#### SPEC-WS-01: Git Worktree Provider
**File**: `infra/workspace/git_worktree.py`
create/remove/run_command/read_file/write_file/list_files.
Worktrees in `.worktrees/` inside the repo.

---

## 5. SPECS — CLI LAYER

### SPEC-CLI-01: Commands and Arguments

**File**: `cli.py`
**Dependencies**: argparse, everything else

```
Commands:
  CLI-agent-memory run <description> [options]
  CLI-agent-memory resume <task-id>
  CLI-agent-memory cancel <task-id>
  CLI-agent-memory status [--json]
  CLI-agent-memory cleanup [--older-than HOURS]

  CLI-agent-memory think "<problem>" [--depth N]
  CLI-agent-memory plan <task-id> --show
  CLI-agent-memory recall "<query>"
  CLI-agent-memory remember "<fact>" [--tags ...]
  CLI-agent-memory decisions --list|--add "Title" "Body"

  CLI-agent-memory db --tasks|--stats
  CLI-agent-memory config --show|--init|--validate
  CLI-agent-memory doctor
  CLI-agent-memory version

Options:
  --repo PATH          Target repo (default: .)
  --from-file PATH     Read description from file
  --llm BACKEND        lmstudio | ollama | openai_compat (default: lmstudio)
  --model MODEL        Specific model (default: auto-detect)
  --memory URL         MCP-agent-memory URL (default: http://127.0.0.1:3050)
  --no-memory          Disable MCP-agent-memory
  --force-local        Force local adapters
  --test-cmd CMD       Test command (default: auto-detect)
  --max-iter N         Max iterations (default: 50)
  --base-ref REF       Git base ref (default: HEAD)
  --dry-run            Simulate without executing
  --json               JSON output (always available)
```

**AC**: POSIX compliant (--json, exit codes, signals). < 150 lines.

### SPEC-CLI-02: Configuration

**File**: `config.py`
**Dependencies**: pydantic-settings, tomllib

```python
class AgentMemoryConfig(BaseSettings):
    # LLM
    llm_backend: str = "lmstudio"
    llm_model: str = ""
    llm_base_url: str = "http://localhost:1234"
    llm_api_key: str = ""
    llm_timeout: int = 120

    # Memory
    memory_url: str = "http://127.0.0.1:3050"
    memory_enabled: bool = True
    force_local: bool = False

    # Loop
    max_iterations: int = 50
    max_stagnation: int = 3
    test_command: str = ""

    # Workspace
    worktree_dir: str = ".worktrees"

    # Vault
    vault_dir: str = ".agent-memory/vault"

    # Database
    db_path: str = ".agent-memory/agent-memory.db"

    # Jart-OS
    jart_os_enabled: bool = False
    nats_url: str = "nats://nats:4222"
    redis_url: str = "redis://redis:6379"
    a2a_enabled: bool = False
    a2a_port: int = 0

    model_config = ConfigDict(
        env_prefix="AGENT_MEMORY_",
        toml_file="agent-memory.toml",
    )
```

Hierarchy: CLI args → env vars (AGENT_MEMORY_*) → agent-memory.toml → ~/.config/CLI-agent-memory/ → defaults.

**AC**: < 60 lines.

### SPEC-CLI-03: Output Formatters

**File**: `output/human.py` — Rich-based, colored, tables
**File**: `output/json.py` — stdlib json, always available

---

## 6. SPECS — PROMPTS

### SPEC-P-01: Prompt Templates

**File**: `prompts/templates.py`
**Dependencies**: stdlib

Templates: system_prompt, planning_prompt, coding_prompt, verification_prompt, intervention_prompt.
Temperature 0.1 for coding, 0.5 for planning. Each prompt < 2000 tokens.

**AC**: < 120 lines.

---

## 7. SPECS — TESTS

### SPEC-T-01: Domain Unit Tests
```
tests/domain/
├── test_types.py          # 3 tests
├── test_stagnation.py     # 7 tests
├── test_state.py          # 5 tests
├── test_loop.py           # 10 tests (with MockLLMClient)
└── test_schema.py         # 3 tests
```

### SPEC-T-02: MCP Adapter Tests
```
tests/infra/mcp/
├── test_memory_http.py    # 5 tests (mock HTTP)
├── test_thinking_mcp.py   # 3 tests
└── test_engram_mcp.py     # 3 tests
```

### SPEC-T-03: Local Adapter Tests
```
tests/infra/local/
├── test_memory_sqlite.py      # 5 tests (temp DB)
├── test_thinking_local.py     # 3 tests
├── test_engram_sqlite.py      # 3 tests
└── test_vault_local.py        # 3 tests (temp dir)
```

### SPEC-T-04: LLM Client Tests
```
tests/infra/llm/
├── test_lmstudio.py       # 3 tests (mock HTTP)
└── test_ollama.py         # 3 tests
```

### SPEC-T-05: Workspace + Null Tests
```
tests/infra/
├── test_git_worktree.py   # 8 tests (temp repo)
└── test_null_adapters.py  # 5 tests
```

### SPEC-T-06: CLI Tests
```
tests/test_cli.py          # 12 tests (args, exit codes, JSON output)
```

### SPEC-T-07: Config Tests
```
tests/test_config.py       # 6 tests (TOML, env, defaults)
```

### SPEC-T-08: Integration Tests
```
tests/integration/
└── test_full_loop.py      # temp repo → run → plan → code → verify → done
```

**AC**: > 80% coverage on domain/. All unit tests pass without external services.

---

## 8. PACKAGING

### SPEC-PKG-01: pyproject.toml

```toml
[project]
name = "CLI-agent-memory"
version = "0.1.0"
requires-python = ">=3.12"
license = {text = "MIT"}
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.27",
]

[project.scripts]
CLI-agent-memory = "CLI_agent_memory.cli:main"

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "pytest-cov>=5.0"]
tui = ["textual>=0.50"]
server = ["fastapi>=0.100", "uvicorn>=0.24"]
jart-os = ["nats-py>=2.0", "redis>=5.0"]
all = ["CLI-agent-memory[dev,tui,server,jart-os]"]
```

---

## 9. RELEASE ROADMAP

```
RELEASE 1 — CLI Core (autonomous foundation)
  Specs: D1-D7, MCP-01..05, LOC-01..07, LLM-01..04, WS-01,
         CLI-01..03, P-01, T-01..T-08, PKG-01
  Total: ~38 specs
  Estimated: ~12h
  Runtime deps: 3 (pydantic, pydantic-settings, httpx)

RELEASE 2 — TUI Panel
  Specs: TUI-01..TUI-08 (textual-based terminal dashboard)
  Total: 8 specs
  Estimated: ~6h

RELEASE 3 — API Server + GUI Web
  Specs: SRV-01..SRV-08, GUI-01..GUI-05
  Total: 13 specs
  Estimated: ~10h

RELEASE 4 — Ecosystem
  Specs: ECO-01..ECO-09 (PR gen, GitHub, notifications, Docker,
         plugins, secret scanning, MCP mode, vault sync)
  Total: 9 specs
  Estimated: ~8h

RELEASE 5 — Jart-OS Federation
  Specs: JOS-01..JOS-07 (NATS, Redis, A2A server/client)
  Total: 7 specs
  Estimated: ~6h

RELEASE 6 — Governance + Compliance
  Specs: GOV-01..GOV-05 (spec/quality gates, audit, export)
  Total: 5 specs
  Estimated: ~6h

═══════════════════════════════════════
TOTAL: ~80 specs, ~48h, 3 runtime deps
═══════════════════════════════════════
```

---

## 10. IMPLEMENTATION ORDER (Release 1, TDD)

```
Sprint 1: Foundations (no infra)
  [1]  D1  types.py           → T-01 test_types
  [2]  D2  protocols.py       → (interfaces only)
  [3]  D4  stagnation.py      → T-01 test_stagnation
  [4]  D5  state.py           → T-01 test_state
  [5]  D7  exit_codes.py      → (constants only)
  [6]  D6  schema.py          → T-01 test_schema
  [7]  CLI-02 config.py       → T-07 test_config
  [8]  P-01 templates.py      → (manual verification)

Sprint 2: Loop core
  [9]  D3  loop.py            → T-01 test_loop (with mocks)
  [10] LOC-07 null adapters   → T-05 test_null
  [11] gateway.py             → (factory, no own tests)

Sprint 3: Local infra
  [12] LOC-01 memory_sqlite   → T-03 test_memory_sqlite
  [13] LOC-02 thinking_local  → T-03 test_thinking_local
  [14] LOC-03 engram_sqlite   → T-03 test_engram_sqlite
  [15] LOC-04 planning_local  → (uses LLM, manual test)
  [16] LOC-05 vault_local     → T-03 test_vault_local
  [17] LOC-06 conversation_local → T-03 (if time)
  [18] LLM-01 lmstudio        → T-04 test_lmstudio
  [19] LLM-02 ollama          → T-04 test_ollama
  [20] LLM-03 openai_compat   → (similar to LLM-01)
  [21] LLM-04 factory         → (uses LLM-01..03)
  [22] WS-01 git_worktree     → T-05 test_git_worktree

Sprint 4: MCP infra + CLI
  [23] MCP-01 memory_http     → T-02 test_memory_http
  [24] MCP-02 thinking_mcp    → T-02 test_thinking_mcp
  [25] MCP-03 engram_mcp      → T-02 test_engram_mcp
  [26] MCP-04 vault_mcp       → (similar to MCP-01)
  [27] MCP-05 memory_stdio    → (manual test)
  [28] CLI-01 cli.py          → T-06 test_cli
  [29] CLI-03 output/human    → (manual verification)
  [30] CLI-04 output/json     → T-06 test_json_output

Sprint 5: Integration
  [31] D6  migrations         → (manual verification)
  [32] T-08 integration test  → test_full_loop
  [33] pyproject.toml + entry point
  [34] README.md + ARCHITECTURE.md
```

---

## 11. RISKS

| Risk | Prob. | Impact | Mitigation |
|------|-------|--------|------------|
| MCP gateway API changes | Low | High | MemoryProtocol with retry + null fallback |
| LM Studio lacks tool calling | Medium | Medium | LLM generates diffs as text (no tool calls) |
| Worktree fails on Windows | Low | Low | CLI-agent-memory is macOS/Linux first |
| Flaky tests with temp repos | Medium | Low | Aggressive cleanup in fixtures |
| Context token exhaustion | High | High | Truncate history + reset on stagnation |

---

## 12. SUCCESS CRITERIA

```
SUCCESS-1: CLI-agent-memory run "Fix bug in X" completes without human intervention
SUCCESS-2: 0 code dependency with MCP-agent-memory (communication via ports only)
SUCCESS-3: 100% testable without external services (mockable)
SUCCESS-4: Adding new LLM = 1 new file, 0 changes in existing
SUCCESS-5: Adding new command = 1 new function, 0 changes in existing
SUCCESS-6: < 1,650 lines total (Release 1)
SUCCESS-7: > 80% coverage on domain/
SUCCESS-8: Works standalone AND connected to MCP-agent-memory
SUCCESS-9: --json available on every command
SUCCESS-10: POSIX compliant (exit codes, signals, pipes)
```
