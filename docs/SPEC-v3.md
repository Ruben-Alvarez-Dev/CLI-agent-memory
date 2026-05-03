# SPEC v3: — Universal Autonomous Coding Orchestrator (v3)

> **NOTE**: Historical spec under old name. Renamed to "CLI-agent-memory" on 2026-04-19.
> SUPERSEDED by SPEC-v5.

**Version**: 3.0  
**Date**: 2026-04-19  
**Status**: DRAFT  
**Principle**: Agent-agnostic + Agent Protocol compatible + Real competitive advantage

---

## 0. INVARIANTS

```
INV-1: domain/ has zero knowledge of any specific agent
INV-2: New agent = 1 new file, 0 changes in domain/
INV-3: Compatible con Agent Protocol (agentprotocol.ai)
INV-4: Memoria es opcional (funciona sin ella)
INV-5: Each file < 150 lines
INV-6: Python 3.12+ with type hints
INV-7: Spec first, code later, TDD
INV-8: 0 hardcoded paths, 0 hardcoded agent names
```

---

## 1. WHAT IS RUFFAE

An **autonomous coding orchestrator** that isolates, controls, protects and verifies
tareas ejecutadas por CUALQUIER agente de coding.

### Analogy

```
Ruffae : Autonomous Coding :: CI/CD : Deployment

CI/CD does not compile code — it orchestrates builds, tests, deploys.
Ruffae does not think code — it orchestrates agents, worktrees, verifications.
```

### Los 3 problemas que Ruffae resuelve

| # | Problem | Ruffae Solution |
|---|----------|----------------|
| 1 | **Agentes se van de las manos** — tocan archivos que no deben, borran cosas | Worktree aislado + Guardrails + Scope limitado |
| 2 | **Agents get stuck** — repeat errors, do not know when to stop | Stagnation detection + Context reset + Max iterations |
| 3 | **No reproducibility** — you do not know what happened, what changed, why it failed | Audit trail + Snapshots + Artifacts |

---

## 2. ALIGNMENT WITH STANDARDS

### 2.1 Agent Protocol (agentprotocol.ai)

The **Agent Protocol** defines a standard REST API for communicating with agents:
- `POST /ap/v1/agent/tasks` → Crear tarea
- `POST /ap/v1/agent/tasks/{id}/steps` → Ejecutar un paso
- `GET /ap/v1/agent/tasks/{id}/artifacts` → Listar artefactos producidos

Ruffae implementa este protocolo. Eso significa:
- Cualquier tool que hable Agent Protocol puede usar Ruffae
- Ruffae can be compared with other agents on standard benchmarks (SWE-bench)
- Otros orquestadores pueden delegar tareas a Ruffae

### 2.2 MCP (Model Context Protocol)

Ruffae NO es un MCP server, pero puede comunicarse con MCP servers
(memory store) como cliente. Compatible con el ecosistema MCP.

### 2.3 OpenAI API

The `http_agent` adapter uses `POST /v1/chat/completions` — the de facto standard.

### 2.4 Git

Worktrees, diffs, commits, tags — de facto standard for isolation.

---

## 3. ARQUITECTURA

```
src/ruffae/
├── __init__.py
├── __main__.py
├── cli.py                   # CLI + Agent Protocol HTTP server
│
├── domain/                  # ⬅️ PURE LOGIC
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
├── guardrails/              # ⬅️ PROTECTION (NEW)
│   ├── __init__.py
│   ├── scope.py             # Limited scope (which files it can touch)
│   └── protect.py           # Archivos protegidos (nunca tocar)
│
├── quality/                 # ⬅️ VERIFICATION (NEW)
│   ├── __init__.py
│   ├── test_gate.py         # Ejecutar tests
│   ├── lint_gate.py         # Ejecutar linter
│   └── diff_gate.py         # Verificar que el diff tiene sentido
│
├── observability/           # ⬅️ AUDIT (NUEVO)
│   ├── __init__.py
│   ├── audit.py             # Log of each agent action
│   └── snapshot.py          # Git tag at each phase (easy rollback)
│
└── prompts/
    ├── __init__.py
    └── templates.py         # Templates por fase
```

---

## 4. FEATURES NUEVAS (vs v2)

### F1: GUARDRAILS — File Protection

**Problem**: An autonomous agent can delete `.env`, touch `production.config`,
or modify files it should not.

**Solution**: Two layers of protection.

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

# Can only touch these files (if defined, everything else is forbidden)
# Si no se define, puede tocar cualquier cosa no protegida
scope = [
    "src/**",
    "tests/**",
]
```

**Implementation**: After each `agent.run()`, verify `git diff --name-only`
against the rules. If the agent touched a protected file → revert + penalty.

---

### F2: QUALITY GATES — Chain Verification

**Problem**: "Tests pass" no es suficiente. Puede pasar tests y tener:
- Code that does not pass the linter
- Code with vulnerabilities
- Code unrelated to the task

**Solution**: Configurable verification chain.

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
# Check: no more than N lines changed, no binary files, etc.
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

### F3: SNAPSHOTS — Instant Rollback

**Problem**: If the agent makes a mess in iteration 5, you want to go back to 4.

**Solution**: Automatic git tag at each phase transition.

```
ralph/task-abc123/planning-1    ← After PLANNING
ralph/task-abc123/coding-3      ← After 3rd CODING iteration
ralph/task-abc123/verification-1 ← First verification
```

```bash
# Rollback manual si algo sale mal:
ruffae rollback <task-id> --to planning-1
```

---

### F4: AUDIT TRAIL — Reproducibilidad

**Problem**: You do not know what the agent did, what prompt it received, what it decided.

**Solution**: Structured log of each action.

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
- Analyze which agent is better for which task

---

### F5: AGENT PROTOCOL SERVER — Standard API

**Problem**: Si Ruffae solo es CLI, no se puede integrar con otros sistemas.

**Solution**: Modo servidor que expone Agent Protocol.

```bash
# Modo CLI (uso directo)
ruffae run "Fix bug" --repo ./app

# Server mode (integration with other systems)
ruffae serve --port 8000
# Ahora otros sistemas pueden:
#   POST /ap/v1/agent/tasks         → Crear tarea
#   POST /ap/v1/agent/tasks/{id}/steps  → Ejecutar paso
#   GET  /ap/v1/agent/tasks/{id}/artifacts → See what it produced
#   GET  /ap/v1/agent/tasks/{id}     → Ver estado
```

**Esto permite**:
- Integrar con CI/CD pipelines
- Automatic benchmarks (SWE-bench)
- Dashboard web que monitorea tareas
- Otros orquestadores que delegan sub-tareas

---

### F6: PARALLEL TASKS — Parallel Execution

**Problem**: Un PRD grande se puede descomponer en tareas independientes.

**Solution**: Execute multiple tasks in parallel in separate worktrees.

```bash
# Desde un PRD, descomponer y ejecutar en paralelo
ruffae run --from-file PRD.md --decompose --parallel 3 --repo ./app
```

```toml
# ruffae.toml
[execution]
max_parallel = 3   # Maximum simultaneous worktrees
```

El loop detecta tareas independientes del PLAN.md y las ejecuta en paralelo.

---

### F7: MULTI-AGENT STRATEGY — Agentes para cada fase

**Problem**: Un agente no es bueno para todo. Aider es bueno codeando,
Claude Code es bueno planeando, pi es bueno con tools.

**Solution**: Asignar agentes diferentes por fase.

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
| Agent-agnostic | ✅ | ✅ |
| Agent Protocol | ❌ | ✅ Standard REST API |
| Guardrails (protection) | ❌ | ✅ Scope + archivos protegidos |
| Quality Gates (verification) | ❌ Tests solo | ✅ Tests + lint + typecheck + diff sanity |
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

**File**: `guardrails/scope.py` (~50 lines), `guardrails/protect.py` (~40 lines)

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
    auto_reverted: list[str]   # Automatically reverted files
```

**AC-G1**: fnmatch para patterns. Auto-revert de violaciones. < 90 lines total.

---

### SPEC-Q1: Quality Gates

**File**: `quality/test_gate.py` (~40), `quality/lint_gate.py` (~30), `quality/diff_gate.py` (~50)

```python
class TestGate:
    def __init__(self, command: str, blocking: bool = True): ...
    async def check(self, worktree: Path) -> GateResult:
        result = subprocess.run(command, cwd=worktree, ...)
        return GateResult(passed=result.returncode == 0, ...)

class DiffGate:
    """Verifica que el diff es razonable."""
    async def check(self, worktree: Path) -> GateResult:
        # 1. No more than max_lines_changed (default: 500)
        # 2. No archivos binarios
        # 3. No archivos fuera del scope del plan
        # 4. Cada archivo changed tiene que ver con la tarea
```

**AC-Q1**: Configurable via TOML. Blocking vs warning. < 120 lines total.

---

### SPEC-O1: Audit Trail

**File**: `observability/audit.py` (~40 lines)

```python
class AuditLogger:
    def __init__(self, task_id: str, log_dir: Path): ...

    def log(self, phase: str, action: str, **kwargs): 
        """Append JSONL line to .ruffae/audit/{task_id}.jsonl"""

    def summary(self) -> AuditSummary:
        """Tokens total, files modified, duration, cost estimate."""
```

**AC-O1**: JSONL append-only. < 40 lines. Opcional (solo si log_dir configurado).

---

### SPEC-O2: Snapshots

**File**: `observability/snapshot.py` (~30 lines)

```python
def create_snapshot(worktree: Path, task_id: str, phase: str, iteration: int):
    """Git tag: ralph/{task_id}/{phase}-{iteration}"""

def list_snapshots(worktree: Path, task_id: str) -> list[Snapshot]:
    """Lista snapshots disponibles."""

def rollback_to(worktree: Path, snapshot: Snapshot):
    """git checkout al snapshot."""
```

**AC-O2**: Git tags. Listar + rollback. < 30 lines.

---

### SPEC-S1: Agent Protocol Server

**File**: `cli.py` (add serve mode) + new `server.py` (~100 lines)

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

**AC-S1**: Compatible con OpenAPI spec de agentprotocol.ai. Starlette (ya disponible). < 100 lines.

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

## 8. UPDATED EXECUTION PLAN

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

Sprint 6: Integration (1.5h)
  [19] Test E2E multi-agente
  [20] Extraction from MCP Memory Server
  [21] README.md + docs

TOTAL: ~13h, ~1,800 lines
```

---

## 9. EJEMPLOS DE USO

```bash
# ── Basic ──
ruffae run "Add JWT auth" --repo ./app

# ── With specific agent ──
ruffae run "Fix bug #42" --agent cli --command "aider" --repo ./app

# ── With protection ──
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
ruffae rollback abc123 --to planning-1        # Go back

# ── Audit ──
ruffae audit abc123 --repo ./app              # See what it did
ruffae audit abc123 --cost                    # Estimar coste

# ── Modo servidor ──
ruffae serve --port 8000                      # API Agent Protocol
curl -X POST localhost:8000/ap/v1/agent/tasks \
  -d '{"input": "Fix the auth bug"}'

# ── Dry run ──
ruffae run "Task" --dry-run --repo ./app      # See what it would do without executing
```

---

## 10. SUCCESS CRITERIA

```
SUCCESS-1:  ruffae run with AIDER completes without intervention
SUCCESS-2:  ruffae run with CLAUDE CODE completes without intervention
SUCCESS-3:  ruffae run with PI AGENT completes without intervention
SUCCESS-4:  Guardrails block modification of .env (tested)
SUCCESS-5:  Quality gate de lint falla → agente reintenta
SUCCESS-6:  Snapshot permite rollback a fase anterior
SUCCESS-7:  Audit trail records each action (JSONL)
SUCCESS-8:  Agent Protocol server responde correctamente
SUCCESS-9:  Nuevo agente = 1 archivo, 0 cambios en domain/
SUCCESS-10: domain/ tiene 0 imports de agents/, memory/, guardrails/
SUCCESS-11: < 1,800 lines totales
SUCCESS-12: Coverage > 80% en domain/
```

---

## 11. VENTAJA COMPETITIVA

Why use Ruffae instead of running an agent directly?

| Sin Ruffae | Con Ruffae |
|-----------|-----------|
| Agent touches files it should not | Guardrails block automatically |
| Agente se atasca repitiendo errores | Stagnation detecta y resetea contexto |
| Only "tests pass" as verification | Tests + lint + typecheck + diff sanity |
| If it fails, you start from scratch | Snapshots → instant rollback |
| You do not know what happened | Complete audit trail |
| Un solo agente | El mejor agente para cada fase |
| Secuencial siempre | Paralelo cuando es posible |
| Solo CLI | CLI + Agent Protocol API |
| No hay memoria | Memoria opcional (file o MCP) |
| Repositorio expuesto | Worktree aislado (repo intacto) |

**Ruffae turns any coding agent into a safe, verifiable, and reproducible autonomous agent.**
