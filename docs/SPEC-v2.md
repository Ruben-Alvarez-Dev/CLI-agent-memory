# SPEC v2: — Universal Autonomous Coding Orchestrator (v2)

> **NOTE**: Historical spec under old name. Renamed to "CLI-agent-memory" on 2026-04-19.
> SUPERSEDED by SPEC-v5.

**Versión**: 2.0  
**Fecha**: 2026-04-19  
**Estado**: DRAFT  
**Principio**: Agente-agnóstico. Orquestador universal, no agente.

---

## 0. INVARIANTES

```
INV-1: domain/ tiene 0 conocimiento de cualquier agente específico
INV-2: Nuevo agente = 1 archivo nuevo, 0 cambios en domain/
INV-3: El agente es un plugin intercambiable (DIP estricto)
INV-4: La memoria es opcional (funciona sin ella)
INV-5: 3 protocolos soportados: CLI subprocess, HTTP API, stdin/stdout
INV-6: Cada archivo < 150 líneas
INV-7: Python 3.12+ con type hints
INV-8: Spec primero, código después, TDD
```

---

## 1. QUÉ ES RUFFAE

Ruffae es un **orquestador** que toma una tarea, la aísla en un git worktree,
y la ejecuta autónomamente usando CUALQUIER agente de coding existente o futuro.

### Qué HACE Ruffae

| Capacidad | Responsabilidad |
|-----------|----------------|
| **Aislamiento** | Git worktree — el repo principal nunca se toca |
| **Máquina de estados** | PLANNING → CODING → VERIFICATION → DONE/FAILED |
| **Prevención de bucles** | Detecta estancamiento y resetea contexto |
| **Persistencia** | Estado sobrevive a reinicios |
| **Memoria** (opcional) | Recuerda patrones entre tareas |

### Qué NO hace Ruffae

- ❌ No llama a LLMs directamente
- ❌ No tiene system prompts de agente
- ❌ No gestiona API keys de providers
- ❌ No reemplaza herramientas de coding
- ❌ No está atado a ningún agente

### Analogía

```
Ruffae es al coding como Kubernetes es a los containers:
  - No corre el código (eso lo hace el agente)
  - Lo aísla, lo orquesta, lo monitorea, lo reinicia si falla
  - Es agnóstico al runtime (container=agente)
```

---

## 2. ARQUITECTURA

```
                    ┌─────────────────┐
                    │   Usuario       │
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

### Estructura de archivos

```
src/ruffae/
├── __init__.py
├── __main__.py              # python -m ruffae
├── cli.py                   # Argumentos CLI
│
├── domain/                  # ⬅️ LÓGICA PURA — 0 conocimiento de agentes
│   ├── __init__.py
│   ├── types.py             # AgentResult, AgentState, Message, etc.
│   ├── protocol.py          # Agent + MemoryStore (Protocol classes)
│   ├── loop.py              # RalphLoop (máquina de estados)
│   ├── stagnation.py        # StagnationMonitor
│   └── state.py             # TaskContext (persistencia)
│
├── agents/                  # ⬅️ ADAPTERS — 1 archivo por agente
│   ├── __init__.py          # Factory: create_agent(config)
│   ├── cli_agent.py         # Cualquier CLI subprocess
│   ├── http_agent.py        # Cualquier HTTP OpenAI-compatible
│   └── pi_agent.py          # Pi RPC mode (stdin/stdout JSONL)
│
├── memory/                  # ⬅️ OPCIONAL — 1 archivo por backend
│   ├── __init__.py          # Factory: create_memory(config)
│   ├── mcp_store.py         # MCP Memory Server (HTTP)
│   ├── file_store.py        # Archivos JSON locales (sin servidor)
│   └── null_store.py        # No-op (default)
│
├── workspace/               # ⬅️ AISLAMIENTO
│   ├── __init__.py
│   └── git_worktree.py      # Git worktree manager
│
└── prompts/
    ├── __init__.py
    └── templates.py         # Prompt templates por fase
```

---

## 3. SPEC: Domain Layer

### SPEC-D1: Tipos

**Archivo**: `domain/types.py` (~60 líneas)

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
    """Lo que cualquier agente retorna tras una ejecución."""
    output: str                       # Texto de respuesta
    files_modified: list[str] = []    # Archivos que tocó
    success: bool = True              # Terminó sin error
    error: str = ""                   # Si success=False
    tokens_used: int = 0              # Opcional, para tracking

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

**AC-D1**: Solo pydantic + stdlib. Serializable. 0 deps externas.

---

### SPEC-D2: Protocol (interfaces)

**Archivo**: `domain/protocol.py` (~40 líneas)

```python
from typing import Protocol

class Agent(Protocol):
    """Cualquier agente de coding del mundo."""
    
    async def run(
        self,
        prompt: str,
        cwd: Path,
        history: list[Message] = [],
    ) -> AgentResult:
        """Ejecuta un prompt en un directorio de trabajo.
        
        El agente:
        1. Recibe el prompt + historial de conversación
        2. Trabaja en cwd (lee, edita, crea archivos)
        3. Retorna qué hizo y qué archivos modificó
        
        NO necesita saber nada de worktrees, estados, o memoria.
        Solo recibe un prompt y un directorio.
        """
        ...

class MemoryStore(Protocol):
    """Backend de memoria (opcional)."""
    
    async def save(self, key: str, value: str) -> None: ...
    async def recall(self, query: str, limit: int = 5) -> list[str]: ...
```

**AC-D2**: 2 interfaces. Agent tiene 1 método. MemoryStore tiene 2 métodos. Protocol (structural typing).

---

### SPEC-D3: RalphLoop

**Archivo**: `domain/loop.py` (~130 líneas)

```python
class RalphLoop:
    def __init__(
        self,
        agent: Agent,                    # Cualquier agente
        workspace: WorkspaceProvider,     # Git worktree
        memory: MemoryStore | None = None,  # Opcional
        config: LoopConfig = LoopConfig(),
    ): ...

    async def run(self, task: str, repo_path: Path) -> TaskResult:
        """Ejecutar loop completo."""
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
        # Verificar que PLAN.md existe
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
            self._history = self._history[-2:]  # Reset contexto
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
            # Inyectar error en historial
```

**AC-D3**: 
- Depende SOLO de Agent protocol y MemoryStore protocol (DIP)
- Funciona con CUALQUIER agente que implemente `Agent.run()`
- Memory es opcional (None = sin memoria)
- < 150 líneas
- Testable con MockAgent

---

### SPEC-D4: StagnationMonitor

**Archivo**: `domain/stagnation.py` (~70 líneas)

Sin cambios respecto a SPEC v1. Detecta:
- ≥3 turns sin editar archivos
- ≥3 veces el mismo error

---

### SPEC-D5: TaskContext

**Archivo**: `domain/state.py` (~50 líneas)

Sin cambios respecto a SPEC v1. Persiste en `.ralph_state.json`.

---

## 4. SPEC: Agent Adapters

### SPEC-A1: CLI Agent (universal)

**Archivo**: `agents/cli_agent.py` (~80 líneas)

```python
class CLIAgent:
    """Cualquier agente que funcione como CLI subprocess.
    
    Funciona con: aider, claude code, copilot, o cualquier tool
    que acepte un prompt por stdin/argumento y edite archivos.
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

**Configuración de ejemplo**:

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
- < 80 líneas

---

### SPEC-A2: HTTP Agent (OpenAI-compatible)

**Archivo**: `agents/http_agent.py` (~90 líneas)

```python
class HTTPAgent:
    """Cualquier agente via OpenAI-compatible HTTP API.
    
    Funciona con: LM Studio, Ollama, z.ai, OpenRouter,
    o cualquier server que hable /v1/chat/completions.
    
    NOTA: Este agente NO tiene tools (read, bash, edit).
    Solo genera texto. Útil para tareas simples o como fallback.
    Para coding real, usar cli_agent o pi_agent.
    """

    def __init__(self, base_url: str, model: str = "", api_key: str = ""): ...

    async def run(self, prompt: str, cwd: Path, history: list[Message] = []) -> AgentResult:
        # POST /v1/chat/completions
        # Parsear respuesta
        # files_modified = [] (HTTP agent no edita archivos)
```

**AC-A2**: 
- POST /v1/chat/completions estándar
- Auto-detecta modelo si model=""
- < 90 líneas

---

### SPEC-A3: Pi Agent (RPC)

**Archivo**: `agents/pi_agent.py` (~100 líneas)

```python
class PiAgent:
    """Pi coding agent via RPC mode (stdin/stdout JSONL).
    
    El agente más potente: tiene acceso a tools (read, bash, edit, write),
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
- Spawn pi subprocess por cada iteración del loop
- Parsea eventos JSONL (text_delta, tool_execution_end, agent_end)
- Detecta files_modified de tool calls (write, edit)
- Limpia subprocess correctamente
- < 100 líneas

---

### SPEC-A4: Agent Factory

**Archivo**: `agents/__init__.py` (~30 líneas)

```python
def create_agent(config: AgentConfig) -> Agent:
    match config.type:
        case "cli"    → CLIAgent(config.command, config.prompt_flag)
        case "http"   → HTTPAgent(config.base_url, config.model, config.api_key)
        case "pi"     → PiAgent(config.pi_path)
        case _        → raise ValueError(f"Unknown agent type: {config.type}")
```

**AC-A4**: Añadir agente = añadir 1 case + 1 archivo. 0 cambios en domain/.

---

## 5. SPEC: Memory Adapters (opcionales)

### SPEC-M1: File Store (sin servidor)

**Archivo**: `memory/file_store.py` (~40 líneas)

```python
class FileMemoryStore:
    """Memoria local basada en archivos JSON. Sin servidor necesario."""
    
    def __init__(self, store_dir: Path): ...

    async def save(self, key: str, value: str) -> None:
        # Escribir a store_dir/{hash(key)}.json

    async def recall(self, query: str, limit: int = 5) -> list[str]:
        # Busqueda simple por texto en todos los archivos
```

---

### SPEC-M2: MCP Store

**Archivo**: `memory/mcp_store.py` (~60 líneas)

```python
class MCPMemoryStore:
    """MCP Memory Server (HTTP gateway)."""
    
    def __init__(self, gateway_url: str = "http://127.0.0.1:3050"): ...
    async def save(self, key: str, value: str) -> None: ...
    async def recall(self, query: str, limit: int = 5) -> list[str]: ...
```

---

### SPEC-M3: Null Store

**Archivo**: `memory/null_store.py` (~15 líneas)

```python
class NullMemoryStore:
    """Sin memoria. Siempre retorna vacío."""
    async def save(self, key, value): pass
    async def recall(self, query, limit=5): return []
```

---

## 6. SPEC: Workspace

### SPEC-W1: Git Worktree

**Archivo**: `workspace/git_worktree.py` (~90 líneas)

Sin cambios respecto a SPEC v1. Aislamiento via git worktrees.

---

## 7. SPEC: CLI

### SPEC-C1: Comandos

```bash
# Comando principal
ruffae run "Fix the auth bug" --repo ./myproject
ruffae run --from-file PRD.md --repo ./myproject

# Con agente específico
ruffae run "Task" --agent cli --command "aider"
ruffae run "Task" --agent cli --command "claude" --prompt-flag "-p"
ruffae run "Task" --agent http --url http://localhost:1234 --model qwen3.5:9b
ruffae run "Task" --agent pi

# Sin memoria (offline)
ruffae run "Task" --no-memory

# Gestión
ruffae resume <task-id>
ruffae status
ruffae cleanup --older-than 168
ruffae config --init    # Crea ruffae.toml
ruffae config --show
```

### ruffae.toml (config file)

```toml
# Configuración por proyecto

[agent]
type = "cli"           # "cli" | "http" | "pi"
command = "aider"      # Solo si type="cli"
prompt_flag = "--message"
# base_url = ""        # Solo si type="http"
# model = ""           # Solo si type="http"
# api_key = ""         # Solo si type="http", o env var
# pi_path = "pi"       # Solo si type="pi"

[workspace]
test_command = "pytest"  # "" = auto-detect
worktree_dir = ".worktrees"

[loop]
max_iterations = 50
max_stagnation = 3

[memory]
type = "null"            # "mcp" | "file" | "null"
# gateway_url = "http://127.0.0.1:3050"  # Solo si type="mcp"
# store_dir = ".ruffae/memory"            # Solo si type="file"
```

**AC-C1**:
- `--agent` override config file
- Auto-detección de test_command
- `config --init` genera ruffae.toml interactivo
- < 150 líneas

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
    """Agente mock que simula editar archivos."""
    
    def __init__(self, responses: list[AgentResult]):
        self.responses = responses
        self.call_count = 0
    
    async def run(self, prompt, cwd, history=[]):
        result = self.responses[self.call_count]
        self.call_count += 1
        # Simular escritura de archivos
        if result.files_modified:
            for f in result.files_modified:
                (cwd / f).write_text("# mock content")
        return result
```

**AC-T1**: Todos los tests de domain pasan sin agentes reales. Coverage > 80%.

---

## 9. PLAN DE EJECUCIÓN

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
  [8] Tests loop con MockAgent (máquina de estados completa)

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

Sprint 5: Integración (1.5h)
  [19] Test E2E: ruffae run con aider/claude/pi
  [20] Extracción desde MCP Memory Server
  [21] README.md + docs
```

**Total: ~10h, ~1,200 líneas**

---

## 10. DEPENDENCIAS

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

**3 deps runtime**. httpx es la única "externa" real (pydantic es estándar de facto).

---

## 11. COMPARACIÓN: SPEC v1 vs v2

| Aspecto | SPEC v1 | SPEC v2 |
|---------|---------|---------|
| Agentes soportados | 1 (LLM directo) | ∞ (cualquiera) |
| Protocolos | HTTP API | CLI + HTTP + RPC |
| Acoplamiento con pi | Ninguno | Ninguno (pi = 1 adapter) |
| Domain depende de | LLMClient + MemoryClient | Agent (1 método) |
| Interfaces | 3 (LLM, Memory, Workspace) | 3 (Agent, MemoryStore, Workspace) |
| Archivos infra/llm/ | 5 archivos | ELIMINADO |
| Archivos agents/ | No existía | 3-4 archivos |
| Archivos memory/ | 2 | 3 |
| Líneas estimadas | ~1,650 | ~1,200 |
| Deps runtime | 3 | 3 |
| Testable sin servicios | Sí | Sí |
| Funciona sin servidor | Solo con LM Studio local | Sí (cli_agent + file_store) |

---

## 12. EJEMPLOS DE USO

```bash
# Con Aider (el más simple)
ruffae run "Add JWT authentication to the auth module" \
  --agent cli --command "aider" --repo ./myapp

# Con Claude Code
ruffae run "Refactor the database layer to use repositories" \
  --agent cli --command "claude" --prompt-flag "-p" --repo ./myapp

# Con Pi Agent (el más potente, tiene tools + memory)
ruffae run "Fix all failing tests" \
  --agent pi --repo ./myapp

# Con LM Studio directo (sin tools, solo texto)
ruffae run "Explain the auth flow" \
  --agent http --url http://localhost:1234 --repo ./myapp

# Con memoria MCP (recuerda patrones entre tareas)
ruffae run "Implement OAuth2" \
  --agent pi --memory mcp --repo ./myapp

# Sin memoria, sin servidor (máxima portabilidad)
ruffae run "Add logging" \
  --agent cli --command "aider" --no-memory --repo ./myapp

# Dry run (ver qué haría)
ruffae run "Fix bug #42" --dry-run --repo ./myapp
```

---

## 13. CRITERIOS DE ÉXITO

```
SUCCESS-1: ruffae run con AIDER completa sin intervención humana
SUCCESS-2: ruffae run con CLAUDE CODE completa sin intervención
SUCCESS-3: ruffae run con PI AGENT completa sin intervención
SUCCESS-4: Nuevo agente = 1 archivo nuevo, 0 cambios en domain/
SUCCESS-5: Funciona 100% offline (cli_agent + null_store)
SUCCESS-6: domain/ tiene 0 imports de agents/ o memory/
SUCCESS-7: < 1,200 líneas totales
SUCCESS-8: Coverage > 80% en domain/
```
