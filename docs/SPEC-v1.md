# SPEC: CLI-agent-memory — Autonomous Coding Agent

> **NOTE**: Original name "Ruffae CLI". Renamed to "CLI-agent-memory" on 2026-04-19.
> This spec is historical. See SPEC-v5.md for the current version.

**Version**: 1.0 (historical)
**Date**: 2026-04-19
**Status**: SUPERSEDED by SPEC-v5

---

## 0. INVARIANTES

```
INV-1: 0 acoplamiento con PROJECT-MCP-memory-server (comunicación solo via MCP)
INV-2: Cada archivo < 150 líneas (SRP estricto)
INV-3: Todas las dependencias externas via interfaces (DIP)
INV-4: Zero mock/demo/fake data — siempre producción
INV-5: TDD obligatorio — tests antes que código
INV-6: Python 3.12+ con type hints en todo
INV-7: Un solo entry point: `ruffae` (CLI) o `python -m ruffae`
INV-8: Configuración via archivo TOML + env vars (12-factor)
```

---

## 1. DEFINICIÓN DEL PRODUCTO

### 1.1 Qué es Ruffae

Ruffae es un CLI que toma una descripción de tarea (PRD, issue, o texto libre),
la aísla en un git worktree, y ejecuta un loop autónomo de planificación →
codificación → verificación hasta completarla o fallar explícitamente.

### 1.2 Qué NO es

- No es un memory server (eso es PROJECT-MCP-memory-server)
- No es un LLM (usa LM Studio, Ollama, o APIs externas)
- No es un IDE (no tiene UI)
- No es un reemplazo de herramientas como Aider/Cursor (es complementario)

### 1.3 Relación con el ecosistema

```
┌──────────────────────────────────────────────┐
│  Usuario                                     │
│  ruffae run "Implementa auth" --repo ./app   │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  RUFFAE CLI (este proyecto)                  │
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
│ (LLM local)   │  │ (memoria/RAG)      │
└───────────────┘  └────────────────────┘
```

---

## 2. ARQUITECTURA — SOLID

### 2.1 Estructura de archivos

```
src/ruffae/
├── __init__.py              # Versión + metadata
├── __main__.py              # Entry point: python -m ruffae
├── cli.py                   # Argumentos CLI (argparse)
├── config.py                # Settings (pydantic-settings, TOML + env)
│
├── domain/                  # Lógica de negocio PURA (0 dependencias externas)
│   ├── __init__.py
│   ├── interfaces.py        # ABCs: LLMClient, MemoryClient, WorkspaceProvider
│   ├── types.py             # Enums, dataclasses, Pydantic models del dominio
│   ├── loop.py              # RalphLoop (máquina de estados)
│   ├── stagnation.py        # StagnationMonitor (detección de bucles)
│   └── state.py             # TaskContext (estado persistido de la tarea)
│
├── infra/                   # Implementaciones concretas (dependencias externas)
│   ├── __init__.py
│   ├── llm/
│   │   ├── __init__.py      # Factory: create_llm_client(config)
│   │   ├── base.py          # BaseLLMClient (código compartido)
│   │   ├── lmstudio.py      # LM Studio (:1234)
│   │   ├── ollama.py        # Ollama (:11434)
│   │   └── openai_compat.py # Cualquier API OpenAI-compatible
│   │
│   ├── memory/
│   │   ├── __init__.py      # Factory: create_memory_client(config)
│   │   ├── mcp_http.py      # Cliente HTTP al gateway MCP (:3050)
│   │   └── null.py          # No-op para testing/offline
│   │
│   └── workspace/
│       ├── __init__.py      # Factory: create_workspace(config)
│       └── git_worktree.py  # WorktreeManager (git worktree)
│
└── prompts/
    ├── __init__.py
    └── templates.py         # Templates de prompt por fase (system, planning, coding, verification)
```

### 2.2 Principios SOLID aplicados

#### S — Single Responsibility

| Archivo | Una responsabilidad |
|---------|---------------------|
| `loop.py` | Orquestar fases (PLANNING→CODING→VERIFICATION) |
| `stagnation.py` | Detectar estancamiento |
| `state.py` | Persistir estado de tarea |
| `cli.py` | Parsear argumentos del usuario |
| `config.py` | Cargar configuración |
| `lmstudio.py` | Hablar con LM Studio |
| `mcp_http.py` | Hablar con MCP Memory Server |
| `git_worktree.py` | Gestionar git worktrees |
| `templates.py` | Generar prompts |

#### O — Open/Closed

- Añadir nuevo LLM backend → nuevo archivo en `infra/llm/`, cero cambios en `loop.py`
- Añadir nuevo tipo de workspace → nuevo archivo en `infra/workspace/`, cero cambios
- Añadir nuevo cliente de memoria → nuevo archivo en `infra/memory/`, cero cambios
- Añadir nuevo comando CLI → nuevo handler, cero cambios en existentes

#### L — Liskov Substitution

- Cualquier `LLMClient` puede sustituir a otro: misma firma, mismo comportamiento
- Cualquier `MemoryClient` puede sustituir a otro
- Cualquier `WorkspaceProvider` puede sustituir a otro

#### I — Interface Segregation

```python
# NO: una interfaz gorda
class AgentClient:
    def generate(self, prompt, history): ...
    def recall(self, query): ...
    def create_worktree(self, branch): ...

# SÍ: interfaces pequeñas y enfocadas
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
loop.py (domain) depende de:
  ├── LLMClient (abstracción)     ← NO de lmstudio.py (implementación)
  ├── MemoryClient (abstracción)  ← NO de mcp_http.py (implementación)
  └── WorkspaceProvider (abstracción) ← NO de git_worktree.py (implementación)

cli.py (presentation) ensambla:
  loop = RalphLoop(
      llm=create_llm_client(config),       # inyección
      memory=create_memory_client(config),  # inyección
      workspace=create_workspace(config),   # inyección
  )
```

### 2.3 DRY — Don't Repeat Yourself

| Necesidad | ¿Duplicar? | Solución |
|-----------|-----------|----------|
| Embeddings | ❌ | Pedir al Memory Server via MCP |
| classify_intent | ❌ | Pedir al Memory Server via MCP |
| Code maps | ❌ | Pedir al Memory Server via MCP |
| Model packs | ❌ | Consultar via MCP |
| Almacenamiento | ❌ | Enviar al Memory Server |
| Git operations | ✅ (local) | `git worktree` es operación local |
| LLM calls | ✅ (propio) | Ruffae llama al LLM directamente |
| Prompt templates | ✅ (propio) | Prompts de ejecución ≠ prompts de memoria |

**Principio**: El Memory Server es el cerebro (memoria). Ruffae es las manos (ejecución).

---

## 3. SPEC: Domain Layer (Lógica pura)

### SPEC-D1: Tipos del dominio

**Archivo**: `domain/types.py`
**Dependencias**: Solo stdlib + pydantic

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

#### Criterios de aceptación

```
AC-D1.1: Todos los tipos son Pydantic models o Enums
AC-D1.2: 0 dependencias externas (solo pydantic + stdlib)
AC-D1.3: Tipos usados en domain/ y infra/ (compartidos)
AC-D1.4: Serializable a JSON (model_dump_json / model_validate_json)
```

---

### SPEC-D2: Interfaces (ABCs)

**Archivo**: `domain/interfaces.py`
**Dependencias**: Solo `domain/types.py`

```python
from typing import Protocol

class LLMClient(Protocol):
    """Abstracción de cualquier backend LLM."""
    async def generate(
        self,
        prompt: str,
        history: list[Message],
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse: ...

    def is_available(self) -> bool: ...

class MemoryClient(Protocol):
    """Abstracción del backend de memoria (MCP Memory Server)."""
    async def recall(self, query: str, max_tokens: int = 4000) -> ContextPack: ...
    async def store(self, event_type: str, content: str, tags: str = "") -> str: ...
    async def ingest(self, event_type: str, content: str) -> None: ...
    async def consolidate(self) -> str: ...

class WorkspaceProvider(Protocol):
    """Abstracción del workspace de ejecución."""
    def create(self, branch_name: str, base_ref: str = "HEAD") -> Path: ...
    def remove(self, branch_name: str, force: bool = False) -> bool: ...
    def run_command(self, worktree_path: Path, command: str) -> CommandResult: ...
    def read_file(self, worktree_path: Path, file_path: str) -> str | None: ...
    def write_file(self, worktree_path: Path, file_path: str, content: str) -> None: ...
    def list_files(self, worktree_path: Path, pattern: str = "**/*.py") -> list[str]: ...
```

#### Criterios de aceptación

```
AC-D2.1: Todas las interfaces usan Protocol (structural subtyping)
AC-D2.2: 0 lógica de negocio — solo firmas
AC-D2.3: Los tipos de retorno son del domain/types.py
AC-D2.4: Una interfaz por responsabilidad (ISP)
```

---

### SPEC-D3: RalphLoop (Máquina de estados)

**Archivo**: `domain/loop.py`
**Dependencias**: `domain/interfaces.py`, `domain/types.py`, `domain/stagnation.py`, `domain/state.py`

#### Comportamiento

```
start(task_description)
    │
    ├─ workspace.create("ralph/{task_id}")
    ├─ state = TaskContext(worktree_path, PLANNING)
    │
    └─ while state not in (DONE, FAILED):
         │
         ├─ PLANNING:
         │    ├─ memory.recall(task) → contexto RAG
         │    ├─ llm.generate(planning_prompt, history) → PLAN.md
         │    ├─ workspace.write_file("PLAN.md", plan)
         │    └─ si PLAN.md existe → transition(CODING)
         │
         ├─ CODING:
         │    ├─ memory.recall(task + plan) → contexto actualizado
         │    ├─ llm.generate(coding_prompt, history) → código
         │    ├─ stagnation.record(files_edited)
         │    │    └─ si stagnant → reset historial + intervention prompt
         │    └─ si "DONE CODING" → transition(VERIFICATION)
         │
         └─ VERIFICATION:
              ├─ workspace.run_command(test_command)
              ├─ si tests pasan → transition(DONE)
              │    └─ memory.store("task_completed", result)
              └─ si tests fallan → transition(CODING)
                   ├─ stagnation.record(error)
                   └─ memory.ingest("test_failure", error)
```

#### Funciones públicas

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
        """Ejecutar el loop completo. Retorna cuando DONE o FAILED."""

    async def resume(self, task_id: str) -> TaskResult:
        """Retomar una tarea pausada (lee .ralph_state.json)."""

    def get_status(self) -> TaskResult:
        """Estado actual sin ejecutar."""
```

#### Criterios de aceptación

```
AC-D3.1: RalphLoop depende SOLO de interfaces (DIP), no de implementaciones
AC-D3.2: Nunca excede max_iterations (default: 50)
AC-D3.3: State persiste en .ralph_state.json tras cada transición
AC-D3.4: Stagnation detecta ≥3 turns sin editar y ≥3 mismo error
AC-D3.5: En estancamiento, historial se trunca a últimos 2 mensajes
AC-D3.6: Al completar, memory.store recibe el resultado
AC-D3.7: Al fallar, memory.ingest recibe el error
AC-D3.8: Testable sin LLM real (usando MockLLMClient)
AC-D3.9: < 150 líneas
```

---

### SPEC-D4: StagnationMonitor

**Archivo**: `domain/stagnation.py`
**Dependencias**: Solo stdlib

```python
@dataclass
class StagnationResult:
    is_stagnant: bool
    reason: str = ""          # "no_edits" | "same_error" | ""
    intervention: str = ""    # Prompt de intervención

class StagnationMonitor:
    def __init__(self, max_failures: int = 3): ...

    def record_turn(self, files_edited: int, current_error: str = "") -> StagnationResult: ...
    def reset(self) -> None: ...
```

#### Criterios de aceptación

```
AC-D4.1: record_turn retorna StagnationResult (no bool suelto)
AC-D4.2: Intervention prompts son configurables (no hardcoded)
AC-D4.3: < 80 líneas
AC-D4.4: 0 dependencias
```

---

### SPEC-D5: TaskContext (Estado persistido)

**Archivo**: `domain/state.py`
**Dependencias**: `domain/types.py`

```python
class TaskContext:
    def __init__(self, worktree_path: Path): ...

    # Estado
    state: AgentState
    task_description: str
    plan: str
    progress: str
    iteration: int
    task_id: str              # UUID generado al crear

    # Persistencia
    def save(self) -> None: ...       # Escribe .ralph_state.json
    def load(self) -> bool: ...       # Lee .ralph_state.json, True si existe
    def transition(self, to: AgentState) -> None: ...  # Cambia estado + save

    @staticmethod
    def find_in_worktree(worktree_path: Path) -> TaskContext | None: ...
```

#### Criterios de aceptación

```
AC-D5.1: JSON serializable/deserializable sin pérdida
AC-D5.2: transition() siempre llama a save()
AC-D5.3: task_id es UUID4 determinístico (seed = branch_name)
AC-D5.4: < 60 líneas
```

---

## 4. SPEC: Infrastructure Layer (Implementaciones)

### SPEC-I1: LM Studio Client

**Archivo**: `infra/llm/lmstudio.py`
**Dependencias**: `httpx`, `domain/types.py`

```python
class LMStudioClient:
    """LLM via LM Studio (OpenAI-compatible API)."""

    def __init__(self, base_url: str = "http://localhost:1234", model: str = ""): ...
    async def generate(self, prompt, history, temperature, max_tokens) -> LLMResponse: ...
    def is_available(self) -> bool: ...
```

#### Comportamiento

```
1. POST /v1/chat/completions
2. Si model="" → usar primer modelo disponible (GET /v1/models)
3. Parsear response: content + reasoning_content (si thinking model)
4. Estimar files_edited contando ocurrencias de tool_calls tipo write/edit
5. Timeout: 120s por defecto, configurable
```

#### Criterios de aceptación

```
AC-I1.1: Funciona con cualquier modelo cargado en LM Studio
AC-I1.2: Maneja modelos thinking (reasoning_content separado de content)
AC-I1.3: is_available() responde en <2s
AC-I1.4: Timeout configurable (default 120s)
AC-I1.5: Retry 1 vez en connection refused
AC-I1.6: < 80 líneas
```

---

### SPEC-I2: Ollama Client

**Archivo**: `infra/llm/ollama.py`
**Dependencias**: `httpx`, `domain/types.py`

```python
class OllamaClient:
    """LLM via Ollama API."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen3:8b"): ...
    async def generate(self, prompt, history, temperature, max_tokens) -> LLMResponse: ...
    def is_available(self) -> bool: ...
```

#### Criterios de aceptación

```
AC-I2.1: POST /api/chat con formato Ollama
AC-I2.2: Maneja streaming (optionally)
AC-I2.3: < 60 líneas
```

---

### SPEC-I3: OpenAI-Compatible Client

**Archivo**: `infra/llm/openai_compat.py`
**Dependencias**: `httpx`, `domain/types.py`

```python
class OpenAICompatClient:
    """LLM via any OpenAI-compatible API (z.ai, OpenRouter, etc.)."""

    def __init__(self, base_url: str, api_key: str, model: str): ...
    async def generate(self, prompt, history, temperature, max_tokens) -> LLMResponse: ...
    def is_available(self) -> bool: ...
```

#### Criterios de aceptación

```
AC-I3.1: Funciona con z.ai (glm-5.1), OpenRouter, o cualquier OpenAI-compatible
AC-I3.2: api_key en header Authorization: Bearer
AC-I3.3: < 60 líneas
```

---

### SPEC-I4: LLM Factory

**Archivo**: `infra/llm/__init__.py`

```python
def create_llm_client(config: LLMConfig) -> LLMClient:
    """
    Factory que retorna el LLMClient correcto segun config.backend:
      "lmstudio"     → LMStudioClient
      "ollama"        → OllamaClient
      "openai_compat" → OpenAICompatClient
    """
```

#### Criterios de aceptación

```
AC-I4.1: Añadir un nuevo backend = 0 cambios en factory (registry pattern)
AC-I4.2: Si backend no disponible → raise con mensaje claro
AC-I4.3: < 30 líneas
```

---

### SPEC-I5: MCP Memory Client (HTTP)

**Archivo**: `infra/memory/mcp_http.py`
**Dependencias**: `httpx`, `domain/types.py`

```python
class MCPMemoryClient:
    """Cliente HTTP al MCP Memory Server gateway (:3050)."""

    def __init__(self, gateway_url: str = "http://127.0.0.1:3050"): ...

    async def recall(self, query: str, max_tokens: int = 4000) -> ContextPack: ...
    async def store(self, event_type: str, content: str, tags: str = "") -> str: ...
    async def ingest(self, event_type: str, content: str) -> None: ...
    async def consolidate(self) -> str: ...
```

#### Protocolo MCP via HTTP

```
El gateway 1MCP expone herramientas MCP via HTTP/SSE.
Cada tool se llama como:

POST /mcp
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "engram_1mcp_recall",  # {server}_1mcp_{tool}
        "arguments": { "query": "...", "max_tokens": 4000 }
    },
    "id": 1
}

Tools mapeadas:
  recall     → engram_1mcp_recall / automem_1mcp_memorize
  store      → automem_1mcp_memorize
  ingest     → automem_1mcp_ingest_event
  consolidate → autodream_1mcp_consolidate
```

#### Criterios de aceptación

```
AC-I5.1: Funciona con gateway corriendo en :3050
AC-I5.2: Si gateway no disponible → fallback graceful (no crash)
AC-I5.3: Timeout: 30s para recall, 10s para store/ingest
AC-I5.4: < 100 líneas
AC-I5.5: Los nombres de tools son configurables (diferentes deployments)
```

---

### SPEC-I6: Null Memory Client

**Archivo**: `infra/memory/null.py`

```python
class NullMemoryClient:
    """No-op client para testing o uso sin Memory Server."""

    async def recall(...) → ContextPack(context_text="", sources=[], token_count=0): ...
    async def store(...) → "null": ...
    async def ingest(...) → None: ...
    async def consolidate(...) → "skipped": ...
```

#### Criterios de aceptación

```
AC-I6.1: 0 side effects
AC-I6.2: < 20 líneas
AC-I6.3: Usado automáticamente si gateway no disponible
```

---

### SPEC-I7: Git Worktree Workspace

**Archivo**: `infra/workspace/git_worktree.py`
**Dependencias**: `subprocess`, `domain/types.py`

```python
class GitWorktreeProvider:
    """Workspace aislado via git worktrees."""

    def __init__(self, repo_root: Path): ...

    def create(self, branch_name: str, base_ref: str = "HEAD") -> Path: ...
    def remove(self, branch_name: str, force: bool = False) -> bool: ...
    def run_command(self, worktree_path: Path, command: str) -> CommandResult: ...
    def read_file(self, worktree_path: Path, file_path: str) -> str | None: ...
    def write_file(self, worktree_path: Path, file_path: str, content: str) -> None: ...
    def list_files(self, worktree_path: Path, pattern: str = "**/*.py") -> list[str]: ...
```

#### Criterios de aceptación

```
AC-I7.1: Worktrees se crean en .worktrees/ dentro del repo
AC-I7.2: Si branch existe, reutiliza sin error
AC-I7.3: run_command ejecuta con shell=True (permite pipes)
AC-I7.4: Valida que repo_root tenga .git antes de operar
AC-I7.5: < 100 líneas
```

---

## 5. SPEC: Prompts

### SPEC-P1: Templates de Prompt

**Archivo**: `prompts/templates.py`
**Dependencias**: Solo stdlib

```python
def system_prompt(role: str, config: PromptConfig) -> str:
    """Genera system prompt según el rol y fase."""

def planning_prompt(task: str, context: ContextPack) -> str:
    """Prompt para fase PLANNING."""

def coding_prompt(plan: str, context: ContextPack, files: list[str]) -> str:
    """Prompt para fase CODING."""

def verification_prompt(test_output: str, plan: str) -> str:
    """Prompt para reintentar tras test failure."""

def intervention_prompt(reason: str) -> str:
    """Prompt de intervención por estancamiento."""
```

#### Principios de prompting

```
1. Temperature 0.1 para coding (determinismo)
2. Temperature 0.5 para planning (creatividad limitada)
3. Nunca "confía en mí" — siempre verificar con tool calls
4. Instrucciones en el idioma del usuario (configurable)
5. Formato de salida esperado claramente especificado
```

#### Criterios de aceptación

```
AC-P1.1: Cada prompt < 2000 tokens
AC-P1.2: Los prompts son templates con placeholders (no strings hardcoded)
AC-P1.3: < 120 líneas
AC-P1.4: Los textos de intervención son los del StagnationMonitor actual
```

---

## 6. SPEC: CLI

### SPEC-C1: Argumentos y comandos

**Archivo**: `cli.py`
**Dependencias**: `argparse`, todo lo demás

```
Comandos:

  ruffae run <description>
    --repo PATH          Repo target (default: .)
    --from-file PATH     Leer descripción de archivo
    --llm BACKEND        Backend: lmstudio | ollama | openai_compat (default: lmstudio)
    --model MODEL        Modelo específico (default: auto-detect)
    --memory URL         Memory Server URL (default: http://127.0.0.1:3050)
    --no-memory          Deshabilitar Memory Server
    --test-cmd CMD       Comando de test (default: auto-detect)
    --max-iter N         Máximo iteraciones (default: 50)
    --base-ref REF       Git ref base del worktree (default: HEAD)
    --dry-run            Simular sin ejecutar

  ruffae resume <task-id>
    --repo PATH

  ruffae status
    --repo PATH

  ruffae cleanup
    --repo PATH
    --older-than HOURS   (default: 168 = 7 días)

  ruffae config
    --show               Mostrar configuración actual
    --init               Crear ruffae.toml con defaults
```

#### Auto-detección de test command

```
Si existe pyproject.toml  → "python -m pytest"
Si existe package.json    → "npm test"
Si existe Makefile        → "make test"
Si existe Cargo.toml      → "cargo test"
Si existe go.mod          → "go test ./..."
Default                   → "echo 'No test command detected'"
```

#### Criterios de aceptación

```
AC-C1.1: run sin argumentos muestra help (no crash)
AC-C1.2: Auto-detección de test command funciona para 5+ ecosystems
AC-C1.3: --dry-run muestra qué haría sin ejecutar
AC-C1.4: config --init crea ruffae.toml válido
AC-C1.5: < 150 líneas
```

---

### SPEC-C2: Configuración

**Archivo**: `config.py`
**Dependencias**: `pydantic-settings`, `tomllib` (stdlib 3.11+)

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

    # Model settings: ConfigDict con toml_file y env_prefix
    model_config = ConfigDict(
        env_prefix="RUFFAE_",
        toml_file="ruffae.toml",
    )
```

#### Jerarquía de configuración (mayor prioridad primero)

```
1. CLI arguments (--llm, --model, etc.)
2. Environment variables (RUFFAE_LLM_BACKEND, etc.)
3. ruffae.toml en directorio actual
4. ~/.config/ruffae/ruffae.toml (global)
5. Defaults hardcoded
```

#### Criterios de aceptación

```
AC-C2.1: Carga desde TOML, env vars, y CLI args
AC-C2.2: Valida tipos (pydantic)
AC-C2.3: Muestra config completa con --show
AC-C2.4: < 60 líneas
```

---

## 7. SPEC: Tests

### SPEC-T1: Unit tests del dominio

```
tests/
├── domain/
│   ├── test_stagnation.py       # 7 tests
│   ├── test_state.py            # 5 tests
│   ├── test_loop.py             # 10 tests (con MockLLMClient)
│   └── test_types.py            # 3 tests
├── infra/
│   ├── test_lmstudio.py         # 3 tests (con mock HTTP)
│   ├── test_ollama.py           # 3 tests
│   ├── test_mcp_client.py       # 5 tests (con mock HTTP)
│   ├── test_git_worktree.py     # 8 tests (con repo temporal)
│   └── test_null_client.py      # 2 tests
├── test_cli.py                  # 5 tests
├── test_config.py               # 4 tests
└── conftest.py                  # Fixtures compartidas
```

### Test de integración (spec-t2)

```
tests/integration/
└── test_full_loop.py
    # Requiere: LM Studio corriendo + Memory Server corriendo
    # 1. Crear repo temporal con un bug conocido
    # 2. ruffae run "Fix the bug in calculator.py"
    # 3. Verificar: worktree creado, PLAN.md generado, bug corregido, tests pasan
    # 4. Verificar: Memory Server recibió store/ingest
    # 5. Cleanup
```

#### Criterios de aceptación

```
AC-T1.1: Todos los unit tests pasan sin servicios externos
AC-T1.2: Test loop con MockLLMClient verifica máquina de estados completa
AC-T1.3: Test stagnation verifica intervención correcta
AC-T1.4: Test worktree crea y destruye repo temporal
AC-T1.5: Coverage > 80% en domain/
```

---

## 8. PLAN DE EJECUCIÓN

### Dependencias entre specs

```
SPEC-D1 (types) ────── sin dependencias
SPEC-D2 (interfaces) ── depende de D1
SPEC-D4 (stagnation) ── depende de D1
SPEC-D5 (state) ────── depende de D1

SPEC-P1 (prompts) ──── depende de D1

SPEC-D3 (loop) ─────── depende de D2, D4, D5, P1

SPEC-C2 (config) ───── sin dependencias
SPEC-I1 (lmstudio) ─── depende de D2
SPEC-I2 (ollama) ───── depende de D2
SPEC-I3 (openai) ───── depende de D2
SPEC-I4 (llm factory) ─ depende de I1, I2, I3
SPEC-I5 (mcp client) ── depende de D2
SPEC-I6 (null client) ── depende de D2
SPEC-I7 (worktree) ──── depende de D2

SPEC-C1 (cli) ──────── depende de todo

SPEC-T1 (unit tests) ── depende de cada spec
SPEC-T2 (integration) ── depende de todo
```

### Orden de implementación (TDD: test → spec → code)

```
Sprint 1: Foundation (sin infra externa)
  [1] SPEC-D1: types.py         → test_types.py
  [2] SPEC-D2: interfaces.py    → (solo firmas)
  [3] SPEC-D4: stagnation.py    → test_stagnation.py
  [4] SPEC-D5: state.py         → test_state.py
  [5] SPEC-C2: config.py        → test_config.py
  [6] SPEC-P1: templates.py     → (verificación manual)

Sprint 2: Loop core
  [7] SPEC-D3: loop.py          → test_loop.py (con mocks)
  [8] SPEC-T1: todos los unit tests del dominio

Sprint 3: Infrastructure
  [9]  SPEC-I1: lmstudio.py     → test_lmstudio.py
  [10] SPEC-I2: ollama.py       → test_ollama.py
  [11] SPEC-I3: openai_compat.py → test_openai.py
  [12] SPEC-I4: llm factory
  [13] SPEC-I5: mcp_http.py     → test_mcp_client.py
  [14] SPEC-I6: null.py         → test_null_client.py
  [15] SPEC-I7: git_worktree.py → test_git_worktree.py

Sprint 4: CLI y ensamblaje
  [16] SPEC-C1: cli.py          → test_cli.py
  [17] pyproject.toml + entry point
  [18] SPEC-T2: test de integración

Sprint 5: Extracción desde Memory Server
  [19] Mover código de src/steering/ y src/workspace/
  [20] Actualizar PROJECT-MCP-memory-server (eliminar Ralph)
  [21] Docs: README.md, ARCHITECTURE.md
```

### Estimación por sprint

| Sprint | Especificaciones | Líneas (est.) | Tiempo |
|--------|-----------------|---------------|--------|
| 1 | D1, D2, D4, D5, C2, P1 | ~400 | 2h |
| 2 | D3, T1-domain | ~250 | 1.5h |
| 3 | I1-I7 | ~500 | 3h |
| 4 | C1, pyproject, T2 | ~300 | 2h |
| 5 | Extracción, docs | ~200 | 1.5h |
| **Total** | **18 specs** | **~1,650 líneas** | **~10h** |

---

## 9. DEPENDENCIAS EXTERNAS

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

**Solo 3 dependencias de runtime.** Todo lo demás es stdlib.

---

## 10. MIGRACIÓN DESDE MEMORY SERVER

### Qué se mueve

```
PROJECT-MCP-memory-server/src/steering/loop.py
  → PROJECT-CLI-Ruffae/src/ruffae/domain/loop.py (refactorizado con DI)

PROJECT-MCP-memory-server/src/steering/stagnation.py
  → PROJECT-CLI-Ruffae/src/ruffae/domain/stagnation.py (limpio)

PROJECT-MCP-memory-server/src/steering/state.py
  → PROJECT-CLI-Ruffae/src/ruffae/domain/state.py (limpio)

PROJECT-MCP-memory-server/src/workspace/worktree.py
  → PROJECT-CLI-Ruffae/src/ruffae/infra/workspace/git_worktree.py (refactorizado)

PROJECT-MCP-memory-server/docs/RALPH-LOOP-DESIGN.md
  → PROJECT-CLI-Ruffae/docs/REFERENCE-RALPH-LOOP-DESIGN.md (histórico)
```

### Qué se elimina del Memory Server

```
src/steering/           # Todo el directorio
src/workspace/          # Todo el directorio
```

### Qué se queda en el Memory Server

```
docs/FUSION-DESIGN-v2.md     # Diseño de fusión (referencia)
docs/FUSION-SPEC-v3.md       # Specs de fusión (code maps, model packs, etc.)
docs/VISION-PLATAFORMA-AGENTICA.md  # Visión general (Ralph ya no está ahí)
data/memory/engram/model-packs/     # Ruffae los consulta via MCP
```

### Actualizaciones al Memory Server

```
1. docs/VISION-PLATAFORMA-AGENTICA.md: Actualizar Fase 5 → "Ruffae CLI externo"
2. docs/SESSION-STATE.md: Añadir nota "Ralph externalizado a PROJECT-CLI-Ruffae"
3. README.md: Quitar mención de steering/workspace
4. Eliminar src/steering/ y src/workspace/
```

---

## 11. RIESGOS

| Riesgo | Prob. | Impacto | Mitigación |
|--------|-------|---------|------------|
| MCP gateway API cambia | Baja | Alto | MemoryClient con retry + fallback null |
| LM Studio no tiene tool calling | Media | Medio | LLM que genera diffs como texto (no tool calls) |
| Worktree falla en Windows | Baja | Bajo | Ruffae es macOS/Linux first |
| Tests flaky con repos temporales | Media | Bajo | Cleanup agresivo en fixtures |
| Tokens agotados en contexto | Alta | Alto | Truncar historial + reset en estancamiento |

---

## 12. CRITERIOS DE ÉXITO GLOBAL

```
SUCCESS-1: ruffae run "Fix bug in X" completa sin intervención humana
SUCCESS-2: 0 dependencia de código con PROJECT-MCP-memory-server
SUCCESS-3: Testable al 100% sin servicios externos (mockeable)
SUCCESS-4: Añadir nuevo LLM = 1 archivo nuevo, 0 cambios existentes
SUCCESS-5: Añadir nuevo comando CLI = 1 función nueva, 0 cambios existentes
SUCCESS-6: < 1,650 líneas totales
SUCCESS-7: Coverage > 80% en domain/
```
