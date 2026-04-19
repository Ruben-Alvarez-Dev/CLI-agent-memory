# SPEC v3: — Universal Autonomous Coding Orchestrator (v3)

> **NOTE**: Historical spec under old name. Renamed to "CLI-agent-memory" on 2026-04-19.
> SUPERSEDED by SPEC-v5.

**Versión**: 3.0  
**Fecha**: 2026-04-19  
**Estado**: DRAFT  
**Principio**: Agente-agnóstico + Agent Protocol compatible + Ventaja competitiva real

---

## 0. INVARIANTES

```
INV-1: domain/ tiene 0 conocimiento de cualquier agente específico
INV-2: Nuevo agente = 1 archivo nuevo, 0 cambios en domain/
INV-3: Compatible con Agent Protocol (agentprotocol.ai)
INV-4: Memoria es opcional (funciona sin ella)
INV-5: Cada archivo < 150 líneas
INV-6: Python 3.12+ con type hints
INV-7: Spec primero, código después, TDD
INV-8: 0 hardcoded paths, 0 hardcoded agent names
```

---

## 1. QUÉ ES RUFFAE

Un **orquestador de coding autónomo** que aísla, controla, protege y verifica
tareas ejecutadas por CUALQUIER agente de coding.

### Analogía

```
Ruffae : Coding Autónomo :: CI/CD : Deployment

CI/CD no compila código — orquesta builds, tests, deploys.
Ruffae no piensa código — orquesta agents, worktrees, verificaciones.
```

### Los 3 problemas que Ruffae resuelve

| # | Problema | Solución Ruffae |
|---|----------|----------------|
| 1 | **Agentes se van de las manos** — tocan archivos que no deben, borran cosas | Worktree aislado + Guardrails + Scope limitado |
| 2 | **Agentes se atascan** — repiten errores, no saben cuándo parar | Stagnation detection + Context reset + Max iterations |
| 3 | **No hay reproducibilidad** — no sabes qué pasó, qué cambió, por qué falló | Audit trail + Snapshots + Artifacts |

---

## 2. ALINEACIÓN CON ESTÁNDARES

### 2.1 Agent Protocol (agentprotocol.ai)

El **Agent Protocol** define una API REST estándar para comunicarse con agentes:
- `POST /ap/v1/agent/tasks` → Crear tarea
- `POST /ap/v1/agent/tasks/{id}/steps` → Ejecutar un paso
- `GET /ap/v1/agent/tasks/{id}/artifacts` → Listar artefactos producidos

Ruffae implementa este protocolo. Eso significa:
- Cualquier tool que hable Agent Protocol puede usar Ruffae
- Ruffae puede compararse con otros agentes en benchmarks estándar (SWE-bench)
- Otros orquestadores pueden delegar tareas a Ruffae

### 2.2 MCP (Model Context Protocol)

Ruffae NO es un MCP server, pero puede comunicarse con MCP servers
(memory store) como cliente. Compatible con el ecosistema MCP.

### 2.3 OpenAI API

El adapter `http_agent` usa `POST /v1/chat/completions` — el estándar de facto.

### 2.4 Git

Worktrees, diffs, commits, tags — estándar de facto para aislamiento.

---

## 3. ARQUITECTURA

```
src/ruffae/
├── __init__.py
├── __main__.py
├── cli.py                   # CLI + Agent Protocol HTTP server
│
├── domain/                  # ⬅️ LÓGICA PURA
│   ├── types.py             # Task, Step, Artifact, AgentResult
│   ├── protocol.py          # Agent + MemoryStore + QualityGate interfaces
│   ├── loop.py              # RalphLoop (state machine)
│   ├── stagnation.py        # StagnationMonitor
│   ├── state.py             # TaskContext
│   └── quality.py           # QualityGate chain (lint, test, security)
│
├── agents/                  # ⬅️ ADAPTERS
│   ├── __init__.py          # Factory
│   ├── cli_agent.py         # Cualquier CLI subprocess
│   ├── http_agent.py        # OpenAI-compatible HTTP
│   └── pi_agent.py          # Pi RPC mode
│
├── memory/                  # ⬅️ OPCIONAL
│   ├── __init__.py          # Factory
│   ├── null_store.py        # No-op
│   ├── file_store.py        # JSON local
│   └── mcp_store.py         # MCP Memory Server
│
├── workspace/               # ⬅️ AISLAMIENTO
│   ├── __init__.py
│   └── git_worktree.py      # Git worktree + snapshots + guardrails
│
├── guardrails/              # ⬅️ PROTECCIÓN (NUEVO)
│   ├── __init__.py
│   ├── scope.py             # Scope limitado (qué archivos puede tocar)
│   └── protect.py           # Archivos protegidos (nunca tocar)
│
├── quality/                 # ⬅️ VERIFICACIÓN (NUEVO)
│   ├── __init__.py
│   ├── test_gate.py         # Ejecutar tests
│   ├── lint_gate.py         # Ejecutar linter
│   └── diff_gate.py         # Verificar que el diff tiene sentido
│
├── observability/           # ⬅️ AUDIT (NUEVO)
│   ├── __init__.py
│   ├── audit.py             # Log de cada acción del agente
│   └── snapshot.py          # Git tag en cada fase (rollback fácil)
│
└── prompts/
    ├── __init__.py
    └── templates.py         # Templates por fase
```

---

## 4. FEATURES NUEVAS (vs v2)

### F1: GUARDRAILS — Protección de archivos

**Problema**: Un agente autónomo puede borrar `.env`, tocar `production.config`,
o modificar archivos que no debería.

**Solución**: Dos capas de protección.

```toml
# ruffae.toml

[guardrails]
# Archivos que NUNCA se pueden tocar (wildcards soportadas)
protected = [
    ".env*",
    "*.secret",
    "production.*",
    "docker-compose.prod.yml",
    "**/migrations/**",
]

# Solo puede tocar estos archivos (si se define, todo lo demás está prohibido)
# Si no se define, puede tocar cualquier cosa no protegida
scope = [
    "src/**",
    "tests/**",
]
```

**Implementación**: Después de cada `agent.run()`, verificar `git diff --name-only`
contra las reglas. Si el agente tocó un archivo protegido → revert + penalty.

---

### F2: QUALITY GATES — Verificación en cadena

**Problema**: "Tests pass" no es suficiente. Puede pasar tests y tener:
- Código que no pasa el linter
- Código con vulnerabilidades
- Código que no tiene nada que ver con la tarea

**Solución**: Cadena de verificación configurable.

```python
class QualityGate(Protocol):
    """Un check de calidad."""
    async def check(self, worktree: Path) -> GateResult: ...

class GateResult(BaseModel):
    passed: bool
    name: str           # "tests" | "lint" | "typecheck" | "security"
    message: str        # Detalle del resultado
    severity: str       # "blocking" | "warning" | "info"
```

```toml
# ruffae.toml

[[quality_gates]]
name = "tests"
command = "pytest --tb=short"
blocking = true         # Si falla, no avanza

[[quality_gates]]
name = "lint"
command = "ruff check ."
blocking = true

[[quality_gates]]
name = "typecheck"
command = "mypy src/"
blocking = false        # Warning, no bloquea

[[quality_gates]]
name = "diff_sanity"
blocking = true         # Verifica que el diff es razonable
# Check: no más de N líneas cambiadas, no archivos binarios, etc.
```

**Flujo**:

```
VERIFICATION phase:
  for gate in quality_gates:
    result = gate.check(worktree)
    if result.passed:
      continue
    elif result.blocking:
      → back to CODING with error message
    else:
      → warning logged, continue
  all passed → DONE
```

---

### F3: SNAPSHOTS — Rollback instantáneo

**Problema**: Si el agente hace un desastre en iteración 5, quieres volver a 4.

**Solución**: Git tag automático en cada transición de fase.

```
ralph/task-abc123/planning-1    ← Después de PLANNING
ralph/task-abc123/coding-3      ← Después de 3ra iteración de CODING
ralph/task-abc123/verification-1 ← Primera verificación
```

```bash
# Rollback manual si algo sale mal:
ruffae rollback <task-id> --to planning-1
```

---

### F4: AUDIT TRAIL — Reproducibilidad

**Problema**: No sabes qué hizo el agente, qué prompt recibió, qué decidió.

**Solución**: Log estructurado de cada acción.

```
.ruffae/audit/{task-id}.jsonl
```

```jsonl
{"ts":"2026-04-19T12:00:01","phase":"PLANNING","agent":"aider","prompt":"...","tokens_in":1500,"tokens_out":800}
{"ts":"2026-04-19T12:00:05","phase":"PLANNING","artifact":"PLAN.md","action":"created"}
{"ts":"2026-04-19T12:00:06","phase":"CODING","agent":"aider","prompt":"...","files_modified":["src/auth.py"],"tokens_in":2000,"tokens_out":1500}
{"ts":"2026-04-19T12:00:10","phase":"CODING","guardrail":"check","result":"pass","diff_files":["src/auth.py"]}
{"ts":"2026-04-19T12:00:11","phase":"VERIFICATION","gate":"tests","command":"pytest","result":"pass","duration_ms":3200}
```

Esto permite:
- Debuggear fallos
- Medir coste (tokens por tarea)
- Reproducir problemas
- Analizar qué agente es mejor para qué tarea

---

### F5: AGENT PROTOCOL SERVER — API estándar

**Problema**: Si Ruffae solo es CLI, no se puede integrar con otros sistemas.

**Solución**: Modo servidor que expone Agent Protocol.

```bash
# Modo CLI (uso directo)
ruffae run "Fix bug" --repo ./app

# Modo servidor (integración con otros sistemas)
ruffae serve --port 8000
# Ahora otros sistemas pueden:
#   POST /ap/v1/agent/tasks         → Crear tarea
#   POST /ap/v1/agent/tasks/{id}/steps  → Ejecutar paso
#   GET  /ap/v1/agent/tasks/{id}/artifacts → Ver qué produjo
#   GET  /ap/v1/agent/tasks/{id}     → Ver estado
```

**Esto permite**:
- Integrar con CI/CD pipelines
- Benchmarks automáticos (SWE-bench)
- Dashboard web que monitorea tareas
- Otros orquestadores que delegan sub-tareas

---

### F6: PARALLEL TASKS — Ejecución paralela

**Problema**: Un PRD grande se puede descomponer en tareas independientes.

**Solución**: Ejecutar múltiples tareas en paralelo en worktrees separados.

```bash
# Desde un PRD, descomponer y ejecutar en paralelo
ruffae run --from-file PRD.md --decompose --parallel 3 --repo ./app
```

```toml
# ruffae.toml
[execution]
max_parallel = 3   # Máximo worktrees simultáneos
```

El loop detecta tareas independientes del PLAN.md y las ejecuta en paralelo.

---

### F7: MULTI-AGENT STRATEGY — Agentes para cada fase

**Problema**: Un agente no es bueno para todo. Aider es bueno codeando,
Claude Code es bueno planeando, pi es bueno con tools.

**Solución**: Asignar agentes diferentes por fase.

```toml
# ruffae.toml

[agent]                          # Default para todo
type = "cli"
command = "aider"

[agent.planning]                 # Override para planning
type = "cli"
command = "claude"
prompt_flag = "-p"

[agent.coding]                   # Override para coding
type = "pi"                      # Usa pi (tiene tools)

[agent.review]                   # Override para review
type = "http"
base_url = "http://localhost:1234"
model = "qwen3.5:9b"
```

---

## 5. COMPARATIVA: v2 vs v3

| Feature | v2 | v3 |
|---------|----|----|
| Agent-agnóstico | ✅ | ✅ |
| Agent Protocol | ❌ | ✅ API REST estándar |
| Guardrails (protección) | ❌ | ✅ Scope + archivos protegidos |
| Quality Gates (verificación) | ❌ Tests solo | ✅ Tests + lint + typecheck + diff sanity |
| Snapshots (rollback) | ❌ | ✅ Git tags por fase |
| Audit trail | ❌ | ✅ JSONL completo |
| Modo servidor | ❌ | ✅ `ruffae serve` |
| Paralelismo | ❌ | ✅ Multi-worktree |
| Multi-agent | ❌ | ✅ Agente por fase |
| Memoria opcional | ✅ | ✅ |
| Stagnation detection | ✅ | ✅ |

---

## 6. SPECS ADICIONALES (NUEVAS)

### SPEC-G1: Guardrails

**Archivo**: `guardrails/scope.py` (~50 líneas), `guardrails/protect.py` (~40 líneas)

```python
class Guardrails:
    def __init__(self, protected: list[str], scope: list[str] | None): ...

    def check_diff(self, worktree: Path) -> GuardrailResult:
        """Verifica que el diff respeta las reglas.
        
        1. git diff --name-only en el worktree
        2. Cada archivo contra protected patterns (fnmatch)
        3. Si scope definido, cada archivo debe matchear scope
        4. Retorna violaciones + sugerencia de revert
        """

class GuardrailResult(BaseModel):
    ok: bool
    violations: list[str]      # ["MODIFIED .env.production (protected)"]
    auto_reverted: list[str]   # Archivos revertidos automáticamente
```

**AC-G1**: fnmatch para patterns. Auto-revert de violaciones. < 90 líneas total.

---

### SPEC-Q1: Quality Gates

**Archivo**: `quality/test_gate.py` (~40), `quality/lint_gate.py` (~30), `quality/diff_gate.py` (~50)

```python
class TestGate:
    def __init__(self, command: str, blocking: bool = True): ...
    async def check(self, worktree: Path) -> GateResult:
        result = subprocess.run(command, cwd=worktree, ...)
        return GateResult(passed=result.returncode == 0, ...)

class DiffGate:
    """Verifica que el diff es razonable."""
    async def check(self, worktree: Path) -> GateResult:
        # 1. No más de max_lines_changed (default: 500)
        # 2. No archivos binarios
        # 3. No archivos fuera del scope del plan
        # 4. Cada archivo changed tiene que ver con la tarea
```

**AC-Q1**: Configurable via TOML. Blocking vs warning. < 120 líneas total.

---

### SPEC-O1: Audit Trail

**Archivo**: `observability/audit.py` (~40 líneas)

```python
class AuditLogger:
    def __init__(self, task_id: str, log_dir: Path): ...

    def log(self, phase: str, action: str, **kwargs): 
        """Append JSONL line to .ruffae/audit/{task_id}.jsonl"""

    def summary(self) -> AuditSummary:
        """Tokens total, files modified, duration, cost estimate."""
```

**AC-O1**: JSONL append-only. < 40 líneas. Opcional (solo si log_dir configurado).

---

### SPEC-O2: Snapshots

**Archivo**: `observability/snapshot.py` (~30 líneas)

```python
def create_snapshot(worktree: Path, task_id: str, phase: str, iteration: int):
    """Git tag: ralph/{task_id}/{phase}-{iteration}"""

def list_snapshots(worktree: Path, task_id: str) -> list[Snapshot]:
    """Lista snapshots disponibles."""

def rollback_to(worktree: Path, snapshot: Snapshot):
    """git checkout al snapshot."""
```

**AC-O2**: Git tags. Listar + rollback. < 30 líneas.

---

### SPEC-S1: Agent Protocol Server

**Archivo**: `cli.py` (añadir modo serve) + nuevo `server.py` (~100 líneas)

```bash
ruffae serve --port 8000
```

```python
# Endpoints:
POST   /ap/v1/agent/tasks              → Crear tarea (equivale a `ruffae run`)
GET    /ap/v1/agent/tasks              → Listar tareas
GET    /ap/v1/agent/tasks/{id}         → Estado de tarea
POST   /ap/v1/agent/tasks/{id}/steps   → Ejecutar paso manualmente
GET    /ap/v1/agent/tasks/{id}/artifacts → Archivos producidos
DELETE /ap/v1/agent/tasks/{id}         → Cancelar tarea
```

**AC-S1**: Compatible con OpenAPI spec de agentprotocol.ai. Starlette (ya disponible). < 100 líneas.

---

## 7. RUFFAE.TOML COMPLETO

```toml
# ============================================================
# Ruffae Configuration
# ============================================================

[agent]
type = "cli"                # "cli" | "http" | "pi"
command = "aider"           # Para type="cli"
prompt_flag = "--message"   # Para type="cli"
# base_url = ""             # Para type="http"
# model = ""                # Para type="http"
# api_key = ""              # Para type="http" (o env var)
# pi_path = "pi"            # Para type="pi"

# Agente diferente por fase (override)
[agent.planning]
type = "cli"
command = "claude"
prompt_flag = "-p"

[agent.coding]
type = "pi"

[workspace]
test_command = "pytest"       # "" = auto-detect
worktree_dir = ".worktrees"

[loop]
max_iterations = 50
max_stagnation = 3
auto_snapshot = true          # Git tag en cada fase

[guardrails]
protected = [".env*", "*.secret", "docker-compose.prod.yml"]
# scope = ["src/**", "tests/**"]  # Si no se define = todo permitido

[[quality_gates]]
name = "tests"
command = "pytest --tb=short -q"
blocking = true

[[quality_gates]]
name = "lint"
command = "ruff check ."
blocking = true

[[quality_gates]]
name = "diff_sanity"
max_lines = 500
blocking = true

[memory]
type = "null"                 # "mcp" | "file" | "null"
# gateway_url = "http://127.0.0.1:3050"
# store_dir = ".ruffae/memory"

[execution]
max_parallel = 1              # 1 = secuencial, N = paralelo

[audit]
enabled = true
log_dir = ".ruffae/audit"

[server]
# Solo para `ruffae serve`
host = "127.0.0.1"
port = 8000
```

---

## 8. PLAN DE EJECUCIÓN ACTUALIZADO

```
Sprint 1: Domain Core (2h)
  [1] types.py, protocol.py
  [2] stagnation.py, state.py
  [3] quality.py (QualityGate interface)
  [4] conftest.py + tests domain

Sprint 2: Loop + Guardrails + Quality (2.5h)
  [5] loop.py (state machine mejorada)
  [6] templates.py
  [7] guardrails/scope.py + protect.py + tests
  [8] quality/test_gate.py + lint_gate.py + diff_gate.py + tests

Sprint 3: Agents + Memory (3h)
  [9]  cli_agent.py + tests
  [10] http_agent.py + tests
  [11] pi_agent.py + tests
  [12] agents/__init__.py factory
  [13] file_store.py + mcp_store.py + null_store.py + tests

Sprint 4: Workspace + Observability (2h)
  [14] git_worktree.py + tests
  [15] audit.py + snapshot.py + tests

Sprint 5: CLI + Server (2h)
  [16] cli.py + config
  [17] server.py (Agent Protocol)
  [18] pyproject.toml + entry point

Sprint 6: Integración (1.5h)
  [19] Test E2E multi-agente
  [20] Extracción desde MCP Memory Server
  [21] README.md + docs

TOTAL: ~13h, ~1,800 líneas
```

---

## 9. EJEMPLOS DE USO

```bash
# ── Básico ──
ruffae run "Add JWT auth" --repo ./app

# ── Con agente específico ──
ruffae run "Fix bug #42" --agent cli --command "aider" --repo ./app

# ── Con protección ──
ruffae run "Refactor DB" --repo ./app \
  --protect ".env*,migrations/**" \
  --scope "src/db/**,tests/db/**"

# ── Con quality gates ──
ruffae run "Add feature X" --repo ./app \
  --gate "pytest" \
  --gate "ruff check ." \
  --gate-blocking true,true,false

# ── Multi-agente ── (configurado en ruffae.toml)
ruffae run "Implement OAuth2" --repo ./app
# Planning → claude code
# Coding → pi agent
# Review → LM Studio qwen3.5

# ── Rollback ──
ruffae status --repo ./app                    # Ver tareas
ruffae rollback abc123 --to planning-1        # Volver atrás

# ── Audit ──
ruffae audit abc123 --repo ./app              # Ver qué hizo
ruffae audit abc123 --cost                    # Estimar coste

# ── Modo servidor ──
ruffae serve --port 8000                      # API Agent Protocol
curl -X POST localhost:8000/ap/v1/agent/tasks \
  -d '{"input": "Fix the auth bug"}'

# ── Dry run ──
ruffae run "Task" --dry-run --repo ./app      # Ver qué haría sin ejecutar
```

---

## 10. CRITERIOS DE ÉXITO

```
SUCCESS-1:  ruffae run con AIDER completa sin intervención
SUCCESS-2:  ruffae run con CLAUDE CODE completa sin intervención
SUCCESS-3:  ruffae run con PI AGENT completa sin intervención
SUCCESS-4:  Guardrails bloquean modificación de .env (probado)
SUCCESS-5:  Quality gate de lint falla → agente reintenta
SUCCESS-6:  Snapshot permite rollback a fase anterior
SUCCESS-7:  Audit trail registra cada acción (JSONL)
SUCCESS-8:  Agent Protocol server responde correctamente
SUCCESS-9:  Nuevo agente = 1 archivo, 0 cambios en domain/
SUCCESS-10: domain/ tiene 0 imports de agents/, memory/, guardrails/
SUCCESS-11: < 1,800 líneas totales
SUCCESS-12: Coverage > 80% en domain/
```

---

## 11. VENTAJA COMPETITIVA

¿Por qué usar Ruffae en vez de correr un agente directamente?

| Sin Ruffae | Con Ruffae |
|-----------|-----------|
| Agente toca archivos que no debe | Guardrails bloquean automáticamente |
| Agente se atasca repitiendo errores | Stagnation detecta y resetea contexto |
| Solo "tests pass" como verificación | Tests + lint + typecheck + diff sanity |
| Si falla, empiezas de cero | Snapshots → rollback instantáneo |
| No sabes qué pasó | Audit trail completo |
| Un solo agente | El mejor agente para cada fase |
| Secuencial siempre | Paralelo cuando es posible |
| Solo CLI | CLI + Agent Protocol API |
| No hay memoria | Memoria opcional (file o MCP) |
| Repositorio expuesto | Worktree aislado (repo intacto) |

**Ruffae convierte cualquier agente de coding en un agente autónomo seguro, verificable y reproducible.**
