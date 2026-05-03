# SPEC v2: — Universal Autonomous Coding Orchestrator (v2)

> **NOTE**: Historical spec under old name. Renamed to "CLI-agent-memory" on 2026-04-19.
> SUPERSEDED by SPEC-v5.

**Version**: 2.0  
**Date**: 2026-04-19  
**Status**: DRAFT  
**Principle**: Agent-agnostic. Universal orchestrator, not agent.

---

## 0. INVARIANTS

```
INV-1: domain/ has zero knowledge of any specific agent
INV-2: New agent = 1 new file, 0 changes in domain/
INV-3: The agent is a swappable plugin (strict DIP)
INV-4: Memory is optional (works without it)
INV-5: 3 supported protocols: CLI subprocess, HTTP API, stdin/stdout
INV-6: Each file < 150 lines
INV-7: Python 3.12+ with type hints
INV-8: Spec first, code later, TDD
```

---

## 1. WHAT IS RUFFAE

Ruffae is an **orchestrator** that takes a task, isolates it in a git worktree,
and executes it autonomously using ANY existing or future coding agent.

### What Ruffae DOES

| Capacidad | Responsabilidad |
|-----------|----------------|
 | **Isolation** | Git worktree — the main repo is never touched |
| **State Machine** | PLANNING → CODING → VERIFICATION → DONE/FAILED |
| **Loop Prevention** | Detects stagnation and resets context |
| **Persistence** | State survives restarts |
| **Memory** (optional) | Remembers patterns across tasks |

### What Ruffae Does NOT Do

- ❌ Does not call LLMs directly
- ❌ Has no agent system prompts
- ❌ Does not manage provider API keys
- ❌ Does not replace coding tools
- ❌ Is not tied to any agent

### Analogy

```
Ruffae is to coding what Kubernetes is to containers:
  - Does not run code (the agent does that)
  - Isolates, orchestrates, monitors, and restarts if it fails
  - Is runtime-agnostic (container=agent)
```

---

## 2. ARCHITECTURE

```
                    ┌─────────────────┐
                    │   User          │
                    │ ruffae run ...  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   cli.py        │
                    │   (argparse)    │
                    └────────┬────────┘
                             │
              ┌──────────────▼──────────────┐
              │         domain/             │
              │  ┌─────────┐  ┌──────────┐  │
              │  │  Loop    │  │Stagnation│  │
              │  │  Ralph   │  │ Monitor  │  │
              │  └────┬─────┘  └──────────┘  │
              │       │                      │
              │  ┌────▼──────┐  ┌─────────┐  │
              │  │  State    │  │ Types   │  │
              │  │  Context  │  │ Models  │  │
              │  └───────────┘  └─────────┘  │
              │                              │
              │  depende de: Agent protocol  │ ← INTERFACE
              └──────────────┬───────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
   ┌──────▼─────┐   ┌───────▼──────┐   ┌──────▼──────┐
   │ cli_agent   │   │ http_agent   │   │ pi_agent    │
   │ (subprocess)│   │ (OpenAI API) │   │ (RPC JSONL) │
   │             │   │              │   │             │
   │ - aider     │   │ - LM Studio  │   │ - pi --mode │
   │ - claude    │   │ - Ollama     │   │   rpc       │
   │ - copilot   │   │ - z.ai       │   │             │
   │ - cualquier │   │ - OpenRouter │   │             │
   │   CLI tool  │   │ - cualquier  │   │             │
   └──────────────┘   └──────────────┘   └─────────────┘
```

### File Structure

```
src/ruffae/
├── __init__.py
├── __main__.py              # python -m ruffae
├── cli.py                   # Argumentos CLI
│
├── domain/                  # ⬅️ PURE LOGIC — zero agent knowledge
│   ├── __init__.py
│   ├── types.py             # AgentResult, AgentState, Message, etc.
│   ├── protocol.py          # Agent + MemoryStore (Protocol classes)
│   ├── loop.py              # RalphLoop (state machine)
│   ├── stagnation.py        # StagnationMonitor
│   └── state.py             # TaskContext (persistencia)
│
├── agents/                  # ⬅️ ADAPTERS — 1 file per agent
│   ├── __init__.py          # Factory: create_agent(config)
│   ├── cli_agent.py         # Any CLI subprocess
│   ├── http_agent.py        # Any HTTP OpenAI-compatible
│   └── pi_agent.py          # Pi RPC mode (stdin/stdout JSONL)
│
├── memory/                  # ⬅️ OPTIONAL — 1 file per backend
│   ├── __init__.py          # Factory: create_memory(config)
│   ├── mcp_store.py         # MCP Memory Server (HTTP)
│   ├── file_store.py        # Local JSON files (no server)
│   └── null_store.py        # No-op (default)
│
├── workspace/               # ⬅️ ISOLATION
│   ├── __init__.py
│   └── git_worktree.py      # Git worktree manager
│
└── prompts/
    ├── __init__.py
    └── templates.py         # Prompt templates per phase
```

---

## 3. SPEC: Domain Layer

### SPEC-D1: Types

**File**: `domain/types.py` (~60 lines)

```python
class AgentState(str, Enum):
    PLANNING = "PLANNING"
    CODING = "CODING"
    VERIFICATION = "VERIFICATION"
    DONE = "DONE"
    FAILED = "FAILED"

class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str

class AgentResult(BaseModel):
    """What any agent returns after execution."""
    output: str                       # Response text
    files_modified: list[str] = []    # Files touched
    success: bool = True              # Finished without error
    error: str = ""                   # If success=False
    tokens_used: int = 0              # Optional, for tracking

class CommandResult(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1

class TaskResult(BaseModel):
    task_id: str
    status: AgentState
    worktree_path: str
    plan: str = ""
    files_modified: list[str] = []
    tests_passed: bool = False
    iterations: int = 0
    duration_seconds: float = 0.0
    error: str = ""
```

**AC-D1**: Pydantic + stdlib only. Serializable. 0 external deps.

---

### SPEC-D2: Protocol (interfaces)

**File**: `domain/protocol.py` (~40 lines)

```python
from typing import Protocol

class Agent(Protocol):
    """Any coding agent in the world."""
    
    async def run(
        self,
        prompt: str,
        cwd: Path,
        history: list[Message] = [],
    ) -> AgentResult:
        """Executes a prompt in a working directory.
        
        The agent:
        1. Receives the prompt + conversation history
        2. Works in cwd (reads, edits, creates files)
        3. Returns what it did and which files it modified
        
        Does NOT need to know about worktrees, states, or memory.
        Only receives a prompt and a directory.
        """
        ...

class MemoryStore(Protocol):
    """Memory backend (optional)."""
    
    async def save(self, key: str, value: str) -> None: ...
    async def recall(self, query: str, limit: int = 5) -> list[str]: ...
```

**AC-D2**: 2 interfaces. Agent has 1 method. MemoryStore has 2 methods. Protocol (structural typing).

---

### SPEC-D3: RalphLoop

**File**: `domain/loop.py` (~130 lines)

```python
class RalphLoop:
    def __init__(
        self,
        agent: Agent,                    # Any agent
        workspace: WorkspaceProvider,     # Git worktree
        memory: MemoryStore | None = None,  # Opcional
        config: LoopConfig = LoopConfig(),
    ): ...

    async def run(self, task: str, repo_path: Path) -> TaskResult:
        """Execute complete loop."""
        worktree = self.workspace.create(f"ralph/{task_id}")
        state = TaskContext(worktree)
        state.task_description = task
        
        while state.state not in (DONE, FAILED):
            if state.state == PLANNING:
                await self._phase_planning(state)
            elif state.state == CODING:
                await self._phase_coding(state)
            elif state.state == VERIFICATION:
                await self._phase_verification(state)
        
        return TaskResult(...)

    async def _phase_planning(self, state):
        context = await self.memory.recall(state.task_description) if self.memory else ""
        result = await self.agent.run(
            prompt=planning_prompt(state.task_description, context),
            cwd=state.worktree_path,
        )
        # Verify that PLAN.md exists
        if (state.worktree_path / "PLAN.md").exists():
            state.transition(CODING)

    async def _phase_coding(self, state):
        result = await self.agent.run(
            prompt=coding_prompt(state.plan),
            cwd=state.worktree_path,
            history=self._history,
        )
        stagnation = self.stagnation.record(result.files_modified)
        if stagnation.is_stagnant:
            self._history = self._history[-2:]  # Reset context
            self._history.append(Message(role="system", content=stagnation.intervention))
        if "DONE CODING" in result.output:
            state.transition(VERIFICATION)

    async def _phase_verification(self, state):
        cmd_result = self.workspace.run_command(
            state.worktree_path, self.config.test_command
        )
        if cmd_result.success:
            state.transition(DONE)
            if self.memory:
                await self.memory.save(f"task:{state.task_id}", "completed")
        else:
            state.transition(CODING)
            # Inject error into history
```

**AC-D3**: 
- Depends ONLY on Agent protocol and MemoryStore protocol (DIP)
- Works with ANY agent that implements `Agent.run()`
- Memory is optional (None = no memory)
- < 150 lines
- Testable con MockAgent

---

### SPEC-D4: StagnationMonitor

**File**: `domain/stagnation.py` (~70 lines)

No changes from SPEC v1. Detects:
- ≥3 turns without editing files
- ≥3 times the same error

---

### SPEC-D5: TaskContext

**File**: `domain/state.py` (~50 lines)

No changes from SPEC v1. Persists in `.ralph_state.json`.

---

## 4. SPEC: Agent Adapters

### SPEC-A1: CLI Agent (universal)

**File**: `agents/cli_agent.py` (~80 lines)

```python
class CLIAgent:
    """Any agent that works as a CLI subprocess.
    
    Works with: aider, claude code, copilot, or any tool
    that accepts a prompt via stdin/argument and edits files.
    """

    def __init__(self, command: str, prompt_flag: str = ""):
        # command: "aider" / "claude" / "copilot" / "/path/to/agent"
        # prompt_flag: "--message" / "-p" / "" (stdin)
        ...

    async def run(self, prompt: str, cwd: Path, history: list[Message] = []) -> AgentResult:
        # 1. Construir subprocess
        # 2. Pasar prompt via flag o stdin
        # 3. Capturar stdout + stderr
        # 4. Detectar archivos modificados (git diff en cwd)
        # 5. Retornar AgentResult
```

**Example Configuration**:

```toml
# ruffae.toml

[agent]
type = "cli"
command = "aider"
prompt_flag = "--message"
# O:
# type = "cli"
# command = "claude"
# prompt_flag = "-p"

[workspace]
test_command = "pytest"

[memory]
type = "null"  # "mcp" | "file" | "null"
```

**AC-A1**: 
- Funciona con cualquier CLI que acepte prompt
- Detecta files_modified via `git diff --name-only`
- Timeout configurable (default 300s)
- < 80 lines

---

### SPEC-A2: HTTP Agent (OpenAI-compatible)

**File**: `agents/http_agent.py` (~90 lines)

```python
class HTTPAgent:
    """Any agent via OpenAI-compatible HTTP API.
    
    Works with: LM Studio, Ollama, z.ai, OpenRouter,
    or any server that speaks /v1/chat/completions.
    
    NOTA: Este agente NO tiene tools (read, bash, edit).
    Only generates text. Useful for simple tasks or as fallback.
    For real coding, use cli_agent or pi_agent.
    """

    def __init__(self, base_url: str, model: str = "", api_key: str = ""): ...

    async def run(self, prompt: str, cwd: Path, history: list[Message] = []) -> AgentResult:
        # POST /v1/chat/completions
        # Parsear respuesta
        # files_modified = [] (HTTP agent no edita archivos)
```

**AC-A2**: 
- POST /v1/chat/completions standard
- Auto-detecta modelo si model=""
- < 90 lines

---

### SPEC-A3: Pi Agent (RPC)

**File**: `agents/pi_agent.py` (~100 lines)

```python
class PiAgent:
    """Pi coding agent via RPC mode (stdin/stdout JSONL).
    
    The most powerful agent: has access to tools (read, bash, edit, write),
    extensiones, MCP servers (memory), y todos los modelos configurados.
    """

    def __init__(self, pi_path: str = "pi"): ...

    async def run(self, prompt: str, cwd: Path, history: list[Message] = []) -> AgentResult:
        # 1. Spawn pi --mode rpc --no-session --cwd {cwd}
        # 2. Send {"type": "prompt", "message": prompt}
        # 3. Collect events until agent_end
        # 4. Extract text + tool calls
        # 5. Detect files_modified from tool calls
        # 6. Send {"type": "abort"} y cerrar
```

**AC-A3**: 
- Spawn pi subprocess for each loop iteration
- Parsea eventos JSONL (text_delta, tool_execution_end, agent_end)
- Detecta files_modified de tool calls (write, edit)
- Limpia subprocess correctamente
- < 100 lines

---

### SPEC-A4: Agent Factory

**File**: `agents/__init__.py` (~30 lines)

```python
def create_agent(config: AgentConfig) -> Agent:
    match config.type:
        case "cli"    → CLIAgent(config.command, config.prompt_flag)
        case "http"   → HTTPAgent(config.base_url, config.model, config.api_key)
        case "pi"     → PiAgent(config.pi_path)
        case _        → raise ValueError(f"Unknown agent type: {config.type}")
```

**AC-A4**: Add agent = add 1 case + 1 file. 0 changes in domain/.

---

## 5. SPEC: Memory Adapters (optional)

### SPEC-M1: File Store (sin servidor)

**File**: `memory/file_store.py` (~40 lines)

```python
class FileMemoryStore:
    """Local memory based on JSON files. No server required."""
    
    def __init__(self, store_dir: Path): ...

    async def save(self, key: str, value: str) -> None:
        # Write to store_dir/{hash(key)}.json

    async def recall(self, query: str, limit: int = 5) -> list[str]:
        # Simple text search across all files
```

---

### SPEC-M2: MCP Store

**File**: `memory/mcp_store.py` (~60 lines)

```python
class MCPMemoryStore:
    """MCP Memory Server (HTTP gateway)."""
    
    def __init__(self, gateway_url: str = "http://127.0.0.1:3050"): ...
    async def save(self, key: str, value: str) -> None: ...
    async def recall(self, query: str, limit: int = 5) -> list[str]: ...
```

---

### SPEC-M3: Null Store

**File**: `memory/null_store.py` (~15 lines)

```python
class NullMemoryStore:
    """No memory. Always returns empty."""
    async def save(self, key, value): pass
    async def recall(self, query, limit=5): return []
```

---

## 6. SPEC: Workspace

### SPEC-W1: Git Worktree

**File**: `workspace/git_worktree.py` (~90 lines)

No changes from SPEC v1. Isolation via git worktrees.

---

## 7. SPEC: CLI

### SPEC-C1: Commands

```bash
# Main command
ruffae run "Fix the auth bug" --repo ./myproject
ruffae run --from-file PRD.md --repo ./myproject

# With specific agent
ruffae run "Task" --agent cli --command "aider"
ruffae run "Task" --agent cli --command "claude" --prompt-flag "-p"
ruffae run "Task" --agent http --url http://localhost:1234 --model qwen3.5:9b
ruffae run "Task" --agent pi

# Without memory (offline)
ruffae run "Task" --no-memory

# Management
ruffae resume <task-id>
ruffae status
ruffae cleanup --older-than 168
ruffae config --init    # Crea ruffae.toml
ruffae config --show
```

### ruffae.toml (config file)

```toml
# Per-project configuration

[agent]
type = "cli"           # "cli" | "http" | "pi"
command = "aider"      # Only if type="cli"
prompt_flag = "--message"
# base_url = ""        # Only if type="http"
# model = ""           # Only if type="http"
# api_key = ""         # Only if type="http", o env var
# pi_path = "pi"       # Only if type="pi"

[workspace]
test_command = "pytest"  # "" = auto-detect
worktree_dir = ".worktrees"

[loop]
max_iterations = 50
max_stagnation = 3

[memory]
type = "null"            # "mcp" | "file" | "null"
# gateway_url = "http://127.0.0.1:3050"  # Only if type="mcp"
# store_dir = ".ruffae/memory"            # Solo si type="file"
```

**AC-C1**:
- `--agent` override config file
- Auto-detection of test_command
- `config --init` genera ruffae.toml interactivo
- < 150 lines

---

## 8. SPEC: Tests

### SPEC-T1: Unit tests

```
tests/
├── domain/
│   ├── test_stagnation.py       # 7 tests — 0 mocks de agente
│   ├── test_state.py            # 5 tests
│   ├── test_loop.py             # 12 tests con MockAgent
│   └── test_types.py            # 3 tests
├── agents/
│   ├── test_cli_agent.py        # 5 tests con subprocess mock
│   ├── test_http_agent.py       # 5 tests con HTTP mock
│   └── test_pi_agent.py         # 5 tests con JSONL mock
├── memory/
│   ├── test_file_store.py       # 3 tests con tmpdir
│   ├── test_mcp_store.py        # 3 tests con HTTP mock
│   └── test_null_store.py       # 1 test
├── workspace/
│   └── test_git_worktree.py     # 8 tests con repo temporal
├── test_cli.py                  # 5 tests
├── test_config.py               # 4 tests
└── conftest.py                  # MockAgent, MockMemory, tmp repo
```

### MockAgent (conftest.py)

```python
class MockAgent:
    """Mock agent that simulates file editing."""
    
    def __init__(self, responses: list[AgentResult]):
        self.responses = responses
        self.call_count = 0
    
    async def run(self, prompt, cwd, history=[]):
        result = self.responses[self.call_count]
        self.call_count += 1
        # Simulate file writing
        if result.files_modified:
            for f in result.files_modified:
                (cwd / f).write_text("# mock content")
        return result
```

**AC-T1**: All domain tests pass without real agents. Coverage > 80%.

---

## 9. EXECUTION PLAN

```
Sprint 1: Domain (2h)
  [1] SPEC-D1: types.py
  [2] SPEC-D2: protocol.py
  [3] SPEC-D4: stagnation.py
  [4] SPEC-D5: state.py
  [5] conftest.py (MockAgent, MockMemory)
  [6] Tests domain

Sprint 2: Loop (1.5h)
  [7] SPEC-D3: loop.py + templates.py
  [8] Tests loop con MockAgent (complete state machine)

Sprint 3: Agents + Memory (3h)
  [9]  SPEC-A1: cli_agent.py + tests
  [10] SPEC-A2: http_agent.py + tests
  [11] SPEC-A3: pi_agent.py + tests
  [12] SPEC-A4: agents/__init__.py factory
  [13] SPEC-M1: file_store.py + tests
  [14] SPEC-M2: mcp_store.py + tests
  [15] SPEC-M3: null_store.py + tests

Sprint 4: Workspace + CLI (2h)
  [16] SPEC-W1: git_worktree.py + tests
  [17] SPEC-C1: cli.py + config
  [18] pyproject.toml + entry point

Sprint 5: Integration (1.5h)
  [19] E2E Test: ruffae run with aider/claude/pi
  [20] Extraction from MCP Memory Server
  [21] README.md + docs
```

**Total: ~10h, ~1,200 lines**

---

## 10. DEPENDENCIES

```toml
[project]
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.27",        # Solo para http_agent y mcp_store
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]
```

**3 runtime deps**. httpx is the only real "external" one (pydantic is a de facto standard).

---

## 11. COMPARISON: SPEC v1 vs v2

| Aspecto | SPEC v1 | SPEC v2 |
|---------|---------|---------|
| Agentes soportados | 1 (LLM directo) | ∞ (cualquiera) |
| Protocolos | HTTP API | CLI + HTTP + RPC |
| Ac coupling with pi | Ninguno | Ninguno (pi = 1 adapter) |
| Domain depends on | LLMClient + MemoryClient | Agent (1 method) |
| Interfaces | 3 (LLM, Memory, Workspace) | 3 (Agent, MemoryStore, Workspace) |
| Archivos infra/llm/ | 5 archivos | ELIMINADO |
| agents/ files | Did not exist | 3-4 files |
| memory/ | 2 | 3 |
| Estimated lines | ~1,650 | ~1,200 |
| Runtime deps | 3 | 3 |
| Testable without services | Yes | Yes |
| Works without server | Only with local LM Studio | Yes (cli_agent + file_store) |

---

## 12. USAGE EXAMPLES

```bash
# With Aider (simplest)
ruffae run "Add JWT authentication to the auth module" \
  --agent cli --command "aider" --repo ./myapp

# Con Claude Code
ruffae run "Refactor the database layer to use repositories" \
  --agent cli --command "claude" --prompt-flag "-p" --repo ./myapp

# With Pi Agent (most powerful, has tools + memory)
ruffae run "Fix all failing tests" \
  --agent pi --repo ./myapp

# Con LM Studio directo (sin tools, solo texto)
ruffae run "Explain the auth flow" \
  --agent http --url http://localhost:1234 --repo ./myapp

# Con memoria MCP (recuerda patrones entre tareas)
ruffae run "Implement OAuth2" \
  --agent pi --memory mcp --repo ./myapp

# No memory, no server (maximum portability)
ruffae run "Add logging" \
  --agent cli --command "aider" --no-memory --repo ./myapp

# Dry run (see what it would do)
ruffae run "Fix bug #42" --dry-run --repo ./myapp
```

---

## 13. SUCCESS CRITERIA

```
SUCCESS-1: ruffae run with AIDER completes without human intervention
SUCCESS-2: ruffae run with CLAUDE CODE completes without intervention
SUCCESS-3: ruffae run with PI AGENT completes without intervention
SUCCESS-4: Nuevo agente = 1 archivo nuevo, 0 cambios en domain/
SUCCESS-5: Works 100% offline (cli_agent + null_store)
SUCCESS-6: domain/ has 0 imports from agents/ or memory/
SUCCESS-7: < 1,200 total lines
SUCCESS-8: Coverage > 80% in domain/
```
