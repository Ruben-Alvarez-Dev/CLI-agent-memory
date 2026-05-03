# SPEC: CLI-agent-memory — Autonomous Coding Agent

> **NOTE**: Original name "Ruffae CLI". Renamed to "CLI-agent-memory" on 2026-04-19.
> This spec is historical. See SPEC-v5.md for the current version.

**Version**: 1.0 (historical)
**Date**: 2026-04-19
**Status**: SUPERSEDED by SPEC-v5

---

## 0. INVARIANTS

```
INV-1: 0 coupling with PROJECT-MCP-memory-server (communication only via MCP)
INV-2: Each file < 150 lines (strict SRP)
INV-3: All external dependencies via interfaces (DIP)
INV-4: Zero mock/demo/fake data — always production
INV-5: Mandatory TDD — tests before code
INV-6: Python 3.12+ with type hints everywhere
INV-7: Single entry point: `ruffae` (CLI) or `python -m ruffae`
INV-8: Configuration via TOML file + env vars (12-factor)
```

---

## 1. PRODUCT DEFINITION

### 1.1 What Ruffae is

Ruffae is a CLI that takes a task description (PRD, issue, or free text),
isolates it in a git worktree, and executes an autonomous loop of planning →
coding → verification until completed or explicitly failed.

### 1.2 What it is NOT

- It is not a memory server (that is PROJECT-MCP-memory-server)
- It is not an LLM (it uses LM Studio, Ollama, or external APIs)
- It is not an IDE (it has no UI)
- It is not a replacement for tools like Aider/Cursor (it is complementary)

### 1.3 Relationship with the ecosystem

```
┌──────────────────────────────────────────────┐
│  User                                        │
│  ruffae run "Implement auth" --repo ./app    │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  RUFFAE CLI (this project)                   │
│                                              │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Loop    │  │ Stagna-  │  │ Workspace  │  │
│  │  Ralph   │  │ tion     │  │ (git wt)   │  │
│  └────┬─────┘  └──────────┘  └─────┬──────┘  │
│       │                            │         │
│  ┌────┴─────┐              ┌───────┴──────┐  │
│  │  LLM     │              │  Filesystem  │  │
│  │  Client  │              │  (worktree)  │  │
│  └────┬─────┘              └──────────────┘  │
│       │                                      │
│  ┌────┴──────┐                               │
│  │  Memory   │                               │
│  │  Client   │                               │
│  └────┬──────┘                               │
└───────┼──────────────────────────────────────┘
        │                    │
        ▼                    ▼
┌───────────────┐  ┌────────────────────┐
│ LM Studio     │  │ MCP Memory Server  │
│ :1234         │  │ :3050              │
│ (local LLM)   │  │ (memory/RAG)       │
└───────────────┘  └────────────────────┘
```

---

## 2. ARCHITECTURE — SOLID

### 2.1 File structure

```
src/ruffae/
├── __init__.py              # Version + metadata
├── __main__.py              # Entry point: python -m ruffae
├── cli.py                   # CLI arguments (argparse)
├── config.py                # Settings (pydantic-settings, TOML + env)
│
├── domain/                  # PURE business logic (0 external dependencies)
│   ├── __init__.py
│   ├── interfaces.py        # ABCs: LLMClient, MemoryClient, WorkspaceProvider
│   ├── types.py             # Enums, dataclasses, Pydantic models of the domain
│   ├── loop.py              # RalphLoop (state machine)
│   ├── stagnation.py        # StagnationMonitor (loop detection)
│   └── state.py             # TaskContext (persisted task state)
│
├── infra/                   # Concrete implementations (external dependencies)
│   ├── __init__.py
│   ├── llm/
│   │   ├── __init__.py      # Factory: create_llm_client(config)
│   │   ├── base.py          # BaseLLMClient (shared code)
│   │   ├── lmstudio.py      # LM Studio (:1234)
│   │   ├── ollama.py        # Ollama (:11434)
│   │   └── openai_compat.py # Any OpenAI-compatible API
│   │
│   ├── memory/
│   │   ├── __init__.py      # Factory: create_memory_client(config)
│   │   ├── mcp_http.py      # HTTP client to MCP gateway (:3050)
│   │   └── null.py          # No-op for testing/offline
│   │
│   └── workspace/
│       ├── __init__.py      # Factory: create_workspace(config)
│       └── git_worktree.py  # WorktreeManager (git worktree)
│
└── prompts/
    ├── __init__.py
    └── templates.py         # Prompt templates by phase (system, planning, coding, verification)
```

### 2.2 SOLID principles applied

#### S — Single Responsibility

| File | One responsibility |
|---------|---------------------|
| `loop.py` | Orchestrate phases (PLANNING→CODING→VERIFICATION) |
| `stagnation.py` | Detect stagnation |
| `state.py` | Persist task state |
| `cli.py` | Parse user arguments |
| `config.py` | Load configuration |
| `lmstudio.py` | Talk to LM Studio |
| `mcp_http.py` | Talk to MCP Memory Server |
| `git_worktree.py` | Manage git worktrees |
| `templates.py` | Generate prompts |

#### O — Open/Closed

- Add new LLM backend → new file in `infra/llm/`, zero changes in `loop.py`
- Add new workspace type → new file in `infra/workspace/`, zero changes
- Add new memory client → new file in `infra/memory/`, zero changes
- Add new CLI command → new handler, zero changes in existing ones

#### L — Liskov Substitution

- Any `LLMClient` can substitute another: same signature, same behavior
- Any `MemoryClient` can substitute another
- Any `WorkspaceProvider` can substitute another

#### I — Interface Segregation

```python
# NO: a fat interface
class AgentClient:
    def generate(self, prompt, history): ...
    def recall(self, query): ...
    def create_worktree(self, branch): ...

# YES: small and focused interfaces
class LLMClient(Protocol):
    async def generate(self, prompt: str, history: list[Message]) -> LLMResponse: ...

class MemoryClient(Protocol):
    async def recall(self, query: str, max_tokens: int = 4000) -> ContextPack: ...
    async def store(self, event_type: str, content: str) -> str: ...
    async def ingest(self, event_type: str, content: str) -> None: ...

class WorkspaceProvider(Protocol):
    def create(self, branch_name: str, base_ref: str = "HEAD") -> Path: ...
    def remove(self, branch_name: str, force: bool = False) -> bool: ...
    def run_command(self, worktree_path: Path, command: str) -> CommandResult: ...
    def read_file(self, worktree_path: Path, file_path: str) -> str | None: ...
    def write_file(self, worktree_path: Path, file_path: str, content: str) -> None: ...
```

#### D — Dependency Inversion

```
loop.py (domain) depends on:
  ├── LLMClient (abstraction)     ← NOT from lmstudio.py (implementation)
  ├── MemoryClient (abstraction)  ← NOT from mcp_http.py (implementation)
  └── WorkspaceProvider (abstraction) ← NOT from git_worktree.py (implementation)

cli.py (presentation) assembles:
  loop = RalphLoop(
      llm=create_llm_client(config),       # injection
      memory=create_memory_client(config),  # injection
      workspace=create_workspace(config),   # injection
  )
```

### 2.3 DRY — Don't Repeat Yourself

| Need | Duplicate? | Solution |
|-----------|-----------|----------|
| Embeddings | ❌ | Ask Memory Server via MCP |
| classify_intent | ❌ | Ask Memory Server via MCP |
| Code maps | ❌ | Ask Memory Server via MCP |
| Model packs | ❌ | Consult via MCP |
| Storage | ❌ | Send to Memory Server |
| Git operations | ✅ (local) | `git worktree` is a local operation |
| LLM calls | ✅ (own) | Ruffae calls the LLM directly |
| Prompt templates | ✅ (own) | Execution prompts ≠ memory prompts |

**Principle**: Memory Server is the brain (memory). Ruffae is the hands (execution).

---

## 3. SPEC: Domain Layer (Pure logic)

### SPEC-D1: Domain types

**File**: `domain/types.py`
**Dependencies**: Only stdlib + pydantic

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

class TaskResult(BaseModel):
    task_id: str
    status: AgentState
    worktree_path: str
    plan: str = ""
    files_modified: list[str] = Field(default_factory=list)
    tests_passed: bool = False
    error: str = ""
    duration_seconds: float = 0.0
```

#### Acceptance criteria

```
AC-D1.1: All types are Pydantic models or Enums
AC-D1.2: 0 external dependencies (only pydantic + stdlib)
AC-D1.3: Types used in domain/ and infra/ (shared)
AC-D1.4: Serializable to JSON (model_dump_json / model_validate_json)
```

---

### SPEC-D2: Interfaces (ABCs)

**File**: `domain/interfaces.py`
**Dependencies**: Only `domain/types.py`

```python
from typing import Protocol

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

class MemoryClient(Protocol):
    """Abstraction of the memory backend (MCP Memory Server)."""
    async def recall(self, query: str, max_tokens: int = 4000) -> ContextPack: ...
    async def store(self, event_type: str, content: str, tags: str = "") -> str: ...
    async def ingest(self, event_type: str, content: str) -> None: ...
    async def consolidate(self) -> str: ...

class WorkspaceProvider(Protocol):
    """Abstraction of the execution workspace."""
    def create(self, branch_name: str, base_ref: str = "HEAD") -> Path: ...
    def remove(self, branch_name: str, force: bool = False) -> bool: ...
    def run_command(self, worktree_path: Path, command: str) -> CommandResult: ...
    def read_file(self, worktree_path: Path, file_path: str) -> str | None: ...
    def write_file(self, worktree_path: Path, file_path: str, content: str) -> None: ...
    def list_files(self, worktree_path: Path, pattern: str = "**/*.py") -> list[str]: ...
```

#### Acceptance criteria

```
AC-D2.1: All interfaces use Protocol (structural subtyping)
AC-D2.2: 0 business logic — signatures only
AC-D2.3: Return types are from domain/types.py
AC-D2.4: One interface per responsibility (ISP)
```

---

### SPEC-D3: RalphLoop (STATE MACHINE)

**File**: `domain/loop.py`
**Dependencies**: `domain/interfaces.py`, `domain/types.py`, `domain/stagnation.py`, `domain/state.py`

#### Behavior

```
start(task_description)
    │
    ├─ workspace.create("ralph/{task_id}")
    ├─ state = TaskContext(worktree_path, PLANNING)
    │
    └─ while state not in (DONE, FAILED):
         │
         ├─ PLANNING:
         │    ├─ memory.recall(task) → RAG context
         │    ├─ llm.generate(planning_prompt, history) → PLAN.md
         │    ├─ workspace.write_file("PLAN.md", plan)
         │    └─ if PLAN.md exists → transition(CODING)
         │
         ├─ CODING:
         │    ├─ memory.recall(task + plan) → updated context
         │    ├─ llm.generate(coding_prompt, history) → code
         │    ├─ stagnation.record(files_edited)
         │    │    └─ if stagnant → reset history + intervention prompt
         │    └─ if "DONE CODING" → transition(VERIFICATION)
         │
         └─ VERIFICATION:
              ├─ workspace.run_command(test_command)
              ├─ if tests pass → transition(DONE)
              │    └─ memory.store("task_completed", result)
              └─ if tests fail → transition(CODING)
                   ├─ stagnation.record(error)
                   └─ memory.ingest("test_failure", error)
```

#### Public functions

```python
class RalphLoop:
    def __init__(
        self,
        llm: LLMClient,
        memory: MemoryClient,
        workspace: WorkspaceProvider,
        config: LoopConfig,         # max_iterations, test_command, etc.
    ): ...

    async def run(self, task_description: str, repo_path: Path) -> TaskResult:
        """Execute the full loop. Returns when DONE or FAILED."""

    async def resume(self, task_id: str) -> TaskResult:
        """Resume a paused task (reads .ralph_state.json)."""

    def get_status(self) -> TaskResult:
        """Current status without executing."""
```

#### Acceptance criteria

```
AC-D3.1: RalphLoop depends ONLY on interfaces (DIP), not on implementations
AC-D3.2: Never exceeds max_iterations (default: 50)
AC-D3.3: State persisted in .ralph_state.json after each transition
AC-D3.4: Stagnation detects ≥3 turns without edits and ≥3 same error
AC-D3.5: In stagnation, history is truncated to last 2 messages
AC-D3.6: On completion, memory.store receives the result
AC-D3.7: On failure, memory.ingest receives the error
AC-D3.8: Testable without real LLM (using MockLLMClient)
AC-D3.9: < 150 lines
```

---

### SPEC-D4: StagnationMonitor

**File**: `domain/stagnation.py`
**Dependencies**: Only stdlib

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

#### Acceptance criteria

```
AC-D4.1: record_turn returns StagnationResult (not bare bool)
AC-D4.2: Intervention prompts are configurable (not hardcoded)
AC-D4.3: < 80 lines
AC-D4.4: 0 dependencies
```

---

### SPEC-D5: TaskContext (Persisted state)

**File**: `domain/state.py`
**Dependencies**: `domain/types.py`

```python
class TaskContext:
    def __init__(self, worktree_path: Path): ...

    # State
    state: AgentState
    task_description: str
    plan: str
    progress: str
    iteration: int
    task_id: str              # UUID generated on creation

    # Persistence
    def save(self) -> None: ...       # Writes .ralph_state.json
    def load(self) -> bool: ...       # Reads .ralph_state.json, True if exists
    def transition(self, to: AgentState) -> None: ...  # Changes state + save

    @staticmethod
    def find_in_worktree(worktree_path: Path) -> TaskContext | None: ...
```

#### Acceptance criteria

```
AC-D5.1: JSON serializable/deserializable without loss
AC-D5.2: transition() always calls save()
AC-D5.3: task_id is deterministic UUID4 (seed = branch_name)
AC-D5.4: < 60 lines
```

---

## 4. SPEC: Infrastructure Layer (Implementations)

### SPEC-I1: LM Studio Client

**File**: `infra/llm/lmstudio.py`
**Dependencies**: `httpx`, `domain/types.py`

```python
class LMStudioClient:
    """LLM via LM Studio (OpenAI-compatible API)."""

    def __init__(self, base_url: str = "http://localhost:1234", model: str = ""): ...
    async def generate(self, prompt, history, temperature, max_tokens) -> LLMResponse: ...
    def is_available(self) -> bool: ...
```

#### Behavior

```
1. POST /v1/chat/completions
2. If model="" → use first available model (GET /v1/models)
3. Parse response: content + reasoning_content (if thinking model)
4. Estimate files_edited by counting occurrences of tool_calls of type write/edit
5. Timeout: 120s by default, configurable
```

#### Acceptance criteria

```
AC-I1.1: Works with any model loaded in LM Studio
AC-I1.2: Handles thinking models (reasoning_content separated from content)
AC-I1.3: is_available() responds in <2s
AC-I1.4: Configurable timeout (default 120s)
AC-I1.5: Retry 1 time on connection refused
AC-I1.6: < 80 lines
```

---

### SPEC-I2: Ollama Client

**File**: `infra/llm/ollama.py`
**Dependencies**: `httpx`, `domain/types.py`

```python
class OllamaClient:
    """LLM via Ollama API."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen3:8b"): ...
    async def generate(self, prompt, history, temperature, max_tokens) -> LLMResponse: ...
    def is_available(self) -> bool: ...
```

#### Acceptance criteria

```
AC-I2.1: POST /api/chat with Ollama format
AC-I2.2: Handles streaming (optionally)
AC-I2.3: < 60 lines
```

---

### SPEC-I3: OpenAI-Compatible Client

**File**: `infra/llm/openai_compat.py`
**Dependencies**: `httpx`, `domain/types.py`

```python
class OpenAICompatClient:
    """LLM via any OpenAI-compatible API (z.ai, OpenRouter, etc.)."""

    def __init__(self, base_url: str, api_key: str, model: str): ...
    async def generate(self, prompt, history, temperature, max_tokens) -> LLMResponse: ...
    def is_available(self) -> bool: ...
```

#### Acceptance criteria

```
AC-I3.1: Works with z.ai (glm-5.1), OpenRouter, or any OpenAI-compatible
AC-I3.2: api_key in Authorization: Bearer header
AC-I3.3: < 60 lines
```

---

### SPEC-I4: LLM Factory

**File**: `infra/llm/__init__.py`

```python
def create_llm_client(config: LLMConfig) -> LLMClient:
    """
    Factory that returns the correct LLMClient according to config.backend:
      "lmstudio"     → LMStudioClient
      "ollama"        → OllamaClient
      "openai_compat" → OpenAICompatClient
    """
```

#### Acceptance criteria

```
AC-I4.1: Add a new backend = 0 changes in factory (registry pattern)
AC-I4.2: If backend not available → raise with clear message
AC-I4.3: < 30 lines
```

---

### SPEC-I5: MCP Memory Client (HTTP)

**File**: `infra/memory/mcp_http.py`
**Dependencies**: `httpx`, `domain/types.py`

```python
class MCPMemoryClient:
    """HTTP client to MCP Memory Server gateway (:3050)."""

    def __init__(self, gateway_url: str = "http://127.0.0.1:3050"): ...

    async def recall(self, query: str, max_tokens: int = 4000) -> ContextPack: ...
    async def store(self, event_type: str, content: str, tags: str = "") -> str: ...
    async def ingest(self, event_type: str, content: str) -> None: ...
    async def consolidate(self) -> str: ...
```

#### MCP protocol via HTTP

```
The gateway 1MCP exposes MCP tools via HTTP/SSE.
Each tool is called as:

POST /mcp
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "L3_decisions_1mcp_recall",  # {server}_1mcp_{tool}
        "arguments": { "query": "...", "max_tokens": 4000 }
    },
    "id": 1
}

Mapped tools:
  recall     → L3_decisions_1mcp_recall / L0_capture_1mcp_memorize
  store      → L0_capture_1mcp_memorize
  ingest     → L0_capture_1mcp_ingest_event
  consolidate → L0_to_L4_consolidation_1mcp_consolidate
```

#### Acceptance criteria

```
AC-I5.1: Works with gateway running on :3050
AC-I5.2: If gateway not available → graceful fallback (no crash)
AC-I5.3: Timeout: 30s for recall, 10s for store/ingest
AC-I5.4: < 100 lines
AC-I5.5: Tool names are configurable (different deployments)
```

---

### SPEC-I6: Null Memory Client

**File**: `infra/memory/null.py`

```python
class NullMemoryClient:
    """No-op client for testing or use without Memory Server."""

    async def recall(...) → ContextPack(context_text="", sources=[], token_count=0): ...
    async def store(...) → "null": ...
    async def ingest(...) → None: ...
    async def consolidate(...) → "skipped": ...
```

#### Acceptance criteria

```
AC-I6.1: 0 side effects
AC-I6.2: < 20 lines
AC-I6.3: Automatically used if gateway not available
```

---

### SPEC-I7: Git Worktree Workspace

**File**: `infra/workspace/git_worktree.py`
**Dependencies**: `subprocess`, `domain/types.py`

```python
class GitWorktreeProvider:
    """Isolated workspace via git worktrees."""

    def __init__(self, repo_root: Path): ...

    def create(self, branch_name: str, base_ref: str = "HEAD") -> Path: ...
    def remove(self, branch_name: str, force: bool = False) -> bool: ...
    def run_command(self, worktree_path: Path, command: str) -> CommandResult: ...
    def read_file(self, worktree_path: Path, file_path: str) -> str | None: ...
    def write_file(self, worktree_path: Path, file_path: str, content: str) -> None: ...
    def list_files(self, worktree_path: Path, pattern: str = "**/*.py") -> list[str]: ...
```

#### Acceptance criteria

```
AC-I7.1: Worktrees are created in .worktrees/ inside the repo
AC-I7.2: If branch exists, reuse without error
AC-I7.3: run_command executes with shell=True (allows pipes)
AC-I7.4: Validates that repo_root has .git before operating
AC-I7.5: < 100 lines
```

---

## 5. SPEC: Prompts

### SPEC-P1: Prompt Templates

**File**: `prompts/templates.py`
**Dependencies**: Only stdlib

```python
def system_prompt(role: str, config: PromptConfig) -> str:
    """Generates system prompt according to role and phase."""

def planning_prompt(task: str, context: ContextPack) -> str:
    """Prompt for PLANNING phase."""

def coding_prompt(plan: str, context: ContextPack, files: list[str]) -> str:
    """Prompt for CODING phase."""

def verification_prompt(test_output: str, plan: str) -> str:
    """Prompt for retrying after test failure."""

def intervention_prompt(reason: str) -> str:
    """Intervention prompt for stagnation."""
```

#### Prompting principles

```
1. Temperature 0.1 for coding (determinism)
2. Temperature 0.5 for planning (limited creativity)
3. Never "trust me" — always verify with tool calls
4. Instructions in the user's language (configurable)
5. Expected output format clearly specified
```

#### Acceptance criteria

```
AC-P1.1: Each prompt < 2000 tokens
AC-P1.2: Prompts are templates with placeholders (no hardcoded strings)
AC-P1.3: < 120 lines
AC-P1.4: Intervention texts are the ones from the current StagnationMonitor
```

---

## 6. SPEC: CLI

### SPEC-C1: Arguments and commands

**File**: `cli.py`
**Dependencies**: `argparse`, everything else

```
Commands:

  ruffae run <description>
    --repo PATH          Target repo (default: .)
    --from-file PATH     Read description from file
    --llm BACKEND        Backend: lmstudio | ollama | openai_compat (default: lmstudio)
    --model MODEL        Specific model (default: auto-detect)
    --memory URL         Memory Server URL (default: http://127.0.0.1:3050)
    --no-memory          Disable Memory Server
    --test-cmd CMD       Test command (default: auto-detect)
    --max-iter N         Maximum iterations (default: 50)
    --base-ref REF       Git base ref for worktree (default: HEAD)
    --dry-run            Simulate without executing

  ruffae resume <task-id>
    --repo PATH

  ruffae status
    --repo PATH

  ruffae cleanup
    --repo PATH
    --older-than HOURS   (default: 168 = 7 days)

  ruffae config
    --show               Show current configuration
    --init               Create ruffae.toml with defaults
```

#### Auto-detection of test command

```
If pyproject.toml exists  → "python -m pytest"
If package.json exists    → "npm test"
If Makefile exists        → "make test"
If Cargo.toml exists      → "cargo test"
If go.mod exists          → "go test ./..."
Default                   → "echo 'No test command detected'"
```

#### Acceptance criteria

```
AC-C1.1: run without arguments shows help (no crash)
AC-C1.2: Auto-detection of test command works for 5+ ecosystems
AC-C1.3: --dry-run shows what it would do without executing
AC-C1.4: config --init creates valid ruffae.toml
AC-C1.5: < 150 lines
```

---

### SPEC-C2: Configuration

**File**: `config.py`
**Dependencies**: `pydantic-settings`, `tomllib` (stdlib 3.11+)

```python
class RuffaeConfig(BaseSettings):
    # LLM
    llm_backend: str = "lmstudio"
    llm_model: str = ""
    llm_base_url: str = "http://localhost:1234"
    llm_api_key: str = ""
    llm_timeout: int = 120

    # Memory Server
    memory_url: str = "http://127.0.0.1:3050"
    memory_enabled: bool = True

    # Loop
    max_iterations: int = 50
    max_stagnation: int = 3
    test_command: str = ""          # "" = auto-detect

    # Workspace
    worktree_dir: str = ".worktrees"

    # Model settings: ConfigDict with toml_file and env_prefix
    model_config = ConfigDict(
        env_prefix="RUFFAE_",
        toml_file="ruffae.toml",
    )
```

#### Configuration hierarchy (highest priority first)

```
1. CLI arguments (--llm, --model, etc.)
2. Environment variables (RUFFAE_LLM_BACKEND, etc.)
3. ruffae.toml in current directory
4. ~/.config/ruffae/ruffae.toml (global)
5. Hardcoded defaults
```

#### Acceptance criteria

```
AC-C2.1: Loads from TOML, env vars, and CLI args
AC-C2.2: Validates types (pydantic)
AC-C2.3: Shows complete config with --show
AC-C2.4: < 60 lines
```

---

## 7. SPEC: Tests

### SPEC-T1: Domain unit tests

```
tests/
├── domain/
│   ├── test_stagnation.py       # 7 tests
│   ├── test_state.py            # 5 tests
│   ├── test_loop.py             # 10 tests (with MockLLMClient)
│   └── test_types.py            # 3 tests
├── infra/
│   ├── test_lmstudio.py         # 3 tests (with HTTP mock)
│   ├── test_ollama.py           # 3 tests
│   ├── test_mcp_client.py       # 5 tests (with HTTP mock)
│   ├── test_git_worktree.py     # 8 tests (with temporary repo)
│   └── test_null_client.py      # 2 tests
├── test_cli.py                  # 5 tests
├── test_config.py               # 4 tests
└── conftest.py                  # Shared fixtures
```

### Integration test (spec-t2)

```
tests/integration/
└── test_full_loop.py
    # Requires: LM Studio running + Memory Server running
    # 1. Create temporary repo with a known bug
    # 2. ruffae run "Fix the bug in calculator.py"
    # 3. Verify: worktree created, PLAN.md generated, bug fixed, tests pass
    # 4. Verify: Memory Server received store/ingest
    # 5. Cleanup
```

#### Acceptance criteria

```
AC-T1.1: All unit tests pass without external services
AC-T1.2: Test loop with MockLLMClient verifies full state machine
AC-T1.3: Test stagnation verifies correct intervention
AC-T1.4: Test worktree creates and destroys temporary repo
AC-T1.5: Coverage > 80% in domain/
```

---

## 8. EXECUTION PLAN

### Dependencies between specs

```
SPEC-D1 (types) ────── no dependencies
SPEC-D2 (interfaces) ── depends on D1
SPEC-D4 (stagnation) ── depends on D1
SPEC-D5 (state) ────── depends on D1

SPEC-P1 (prompts) ──── depends on D1

SPEC-D3 (loop) ─────── depends on D2, D4, D5, P1

SPEC-C2 (config) ───── no dependencies
SPEC-I1 (lmstudio) ─── depends on D2
SPEC-I2 (ollama) ───── depends on D2
SPEC-I3 (openai) ───── depends on D2
SPEC-I4 (llm factory) ─ depends on I1, I2, I3
SPEC-I5 (mcp client) ── depends on D2
SPEC-I6 (null client) ── depends on D2
SPEC-I7 (worktree) ──── depends on D2

SPEC-C1 (cli) ──────── depends on everything

SPEC-T1 (unit tests) ── depends on each spec
SPEC-T2 (integration) ── depends on everything
```

### Implementation order (TDD: test → spec → code)

```
Sprint 1: Foundation (no external infra)
  [1] SPEC-D1: types.py         → test_types.py
  [2] SPEC-D2: interfaces.py    → (signatures only)
  [3] SPEC-D4: stagnation.py    → test_stagnation.py
  [4] SPEC-D5: state.py         → test_state.py
  [5] SPEC-C2: config.py        → test_config.py
  [6] SPEC-P1: templates.py     → (manual verification)

Sprint 2: Loop core
  [7] SPEC-D3: loop.py          → test_loop.py (with mocks)
  [8] SPEC-T1: all domain unit tests

Sprint 3: Infrastructure
  [9]  SPEC-I1: lmstudio.py     → test_lmstudio.py
  [10] SPEC-I2: ollama.py       → test_ollama.py
  [11] SPEC-I3: openai_compat.py → test_openai.py
  [12] SPEC-I4: llm factory
  [13] SPEC-I5: mcp_http.py     → test_mcp_client.py
  [14] SPEC-I6: null.py         → test_null_client.py
  [15] SPEC-I7: git_worktree.py → test_git_worktree.py

Sprint 4: CLI and assembly
  [16] SPEC-C1: cli.py          → test_cli.py
  [17] pyproject.toml + entry point
  [18] SPEC-T2: integration test

Sprint 5: Extraction from Memory Server
  [19] Move code from src/steering/ and src/workspace/
  [20] Update PROJECT-MCP-memory-server (remove Ralph)
  [21] Docs: README.md, ARCHITECTURE.md
```

### Sprint estimation

| Sprint | Specifications | Lines (est.) | Time |
|--------|-----------------|---------------|--------|
| 1 | D1, D2, D4, D5, C2, P1 | ~400 | 2h |
| 2 | D3, T1-domain | ~250 | 1.5h |
| 3 | I1-I7 | ~500 | 3h |
| 4 | C1, pyproject, T2 | ~300 | 2h |
| 5 | Extraction, docs | ~200 | 1.5h |
| **Total** | **18 specs** | **~1,650 lines** | **~10h** |

---

## 9. EXTERNAL DEPENDENCIES

```toml
[project]
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
]
```

**Only 3 runtime dependencies.** Everything else is stdlib.

---

## 10. MIGRATION FROM MEMORY SERVER

### What is moving

```
PROJECT-MCP-memory-server/src/steering/loop.py
  → PROJECT-CLI-Ruffae/src/ruffae/domain/loop.py (refactored with DI)

PROJECT-MCP-memory-server/src/steering/stagnation.py
  → PROJECT-CLI-Ruffae/src/ruffae/domain/stagnation.py (clean)

PROJECT-MCP-memory-server/src/steering/state.py
  → PROJECT-CLI-Ruffae/src/ruffae/domain/state.py (clean)

PROJECT-MCP-memory-server/src/workspace/worktree.py
  → PROJECT-CLI-Ruffae/src/ruffae/infra/workspace/git_worktree.py (refactored)

PROJECT-MCP-memory-server/docs/RALPH-LOOP-DESIGN.md
  → PROJECT-CLI-Ruffae/docs/REFERENCE-RALPH-LOOP-DESIGN.md (historical)
```

### What is removed from Memory Server

```
src/steering/           # Entire directory
src/workspace/          # Entire directory
```

### What stays in Memory Server

```
docs/FUSION-DESIGN-v2.md     # Fusion design (reference)
docs/FUSION-SPEC-v3.md       # Fusion specs (code maps, model packs, etc.)
docs/VISION-PLATAFORMA-AGENTICA.md  # General vision (Ralph is no longer there)
data/memory/L3_decisions/model-packs/     # Ruffae consults them via MCP
```

### Updates to Memory Server

```
1. docs/VISION-PLATAFORMA-AGENTICA.md: Update Phase 5 → "External Ruffae CLI"
2. docs/SESSION-STATE.md: Add note "Ralph externalized to PROJECT-CLI-Ruffae"
3. README.md: Remove mention of steering/workspace
4. Remove src/steering/ and src/workspace/
```

---

## 11. RISKS

| Risk | Prob. | Impact | Mitigation |
|--------|-------|---------|------------|
| MCP gateway API changes | Low | High | MemoryClient with retry + fallback null |
| LM Studio lacks tool calling | Medium | Medium | LLM that generates diffs as text (no tool calls) |
| Worktree fails on Windows | Low | Low | Ruffae is macOS/Linux first |
| Tests flaky with temp repos | Medium | Low | Aggressive cleanup in fixtures |
| Tokens exhausted in context | High | High | Truncate history + reset on stagnation |

---

## 12. GLOBAL SUCCESS CRITERIA

```
SUCCESS-1: ruffae run "Fix bug in X" completes without human intervention
SUCCESS-2: 0 code dependency with PROJECT-MCP-memory-server
SUCCESS-3: 100% testable without external services (mockable)
SUCCESS-4: Add new LLM = 1 new file, 0 existing changes
SUCCESS-5: Add new CLI command = 1 new function, 0 existing changes
SUCCESS-6: < 1,650 total lines
SUCCESS-7: Coverage > 80% in domain/
```
