# SPEC v4: — Enterprise Coding Orchestrator (v4)

> **NOTE**: Historical spec under old name "Ruffae". Renamed to "CLI-agent-memory" on 2026-04-19.
> SUPERSEDED by SPEC-v5.

**Versión**: 4.0  
**Fecha**: 2026-04-19  
**Estado**: DRAFT — Full Feature Set  
**Principio**: El orquestador de coding autónomo más completo del ecosistema open source.

---

## 0. FEATURE MATRIX

```
TIER 1 — CORE (Sprint 1-3)         Estado    Horas
──────────────────────────────────────────────────
Agent-agnóstico (CLI/HTTP/RPC)      SPEC      3h
State machine (PLANNING→DONE)       SPEC      2h
Git worktree isolation              SPEC      1.5h
Stagnation detection                SPEC      1h
Quality gates (test/lint/diff)      SPEC      2h
Guardrails (scope + protected)      SPEC      1.5h
── SUBTOTAL CORE:                              ~11h

TIER 2 — INTELLIGENCE (Sprint 4-5)
──────────────────────────────────────────────────
Audit trail (JSONL)                 SPEC      1h
Snapshots + rollback                SPEC      1h
Agent Protocol server               SPEC      2h
Multi-agent (agente por fase)       SPEC      1.5h
Task decomposition from PRD         SPEC      2h
Human-in-the-loop approval          SPEC      1.5h
── SUBTOTAL INTELLIGENCE:                      ~9h

TIER 3 — COLLABORATION (Sprint 6-7)
──────────────────────────────────────────────────
PR auto-generation                  SPEC      1.5h
Commit messages (conventional)      SPEC      1h
GitHub Issues integration           SPEC      2h
Slack/Discord notifications         SPEC      1.5h
Webhook events                      SPEC      1h
Dashboard web UI                    SPEC      3h
── SUBTOTAL COLLABORATION:                     ~10h

TIER 4 — ADVANCED (Sprint 8-10)
──────────────────────────────────────────────────
Parallel execution                  SPEC      2h
Agent benchmarking/ranking          SPEC      2h
Dynamic agent selection             SPEC      1.5h
Cost tracking (tokens/$)            SPEC      1h
Replay mode                         SPEC      1.5h
Secret scanning                     SPEC      1h
Docker sandbox                      SPEC      2h
Plugin system                       SPEC      2h
── SUBTOTAL ADVANCED:                          ~13h

TOTAL ESTIMADO: ~43h, ~3,500 líneas
```

---

## TIER 1: CORE — Sin esto, no existe

*(Mantiene todo de SPEC v3 — agentes, state machine, worktrees, guardrails, quality gates, stagnation. Ver SPEC-v3.md para detalles.)*

---

## TIER 2: INTELLIGENCE — Lo que te hace diferente

### F-INT-1: Task Decomposition — Descomponer PRDs

**Problema**: Un PRD grande ("Rebuild the auth system") es imposible para un agente en una sesión.

**Solución**: Ruffae descompone automáticamente un PRD en subtareas ejecutables.

```bash
ruffae decompose --from-file PRD.md --repo ./app
```

**Output**:

```
Task: "Rebuild auth system"
├── Subtask 1: "Create User model with password hashing"     [scope: src/models/]
├── Subtask 2: "Implement JWT token generation/validation"   [scope: src/auth/]
├── Subtask 3: "Add login/logout endpoints"                  [scope: src/routes/]
├── Subtask 4: "Write auth middleware"                       [scope: src/middleware/]
├── Subtask 5: "Add tests for auth flow"                     [scope: tests/auth/]
│
│ Dependencies:
│   2 depends on 1
│   3 depends on 2
│   4 depends on 2
│   5 depends on 3, 4
│
│ Execution plan:
│   Phase A: [1]                    (sequential)
│   Phase B: [2]                    (sequential, needs 1)
│   Phase C: [3, 4]                 (PARALLEL, both need 2)
│   Phase D: [5]                    (sequential, needs 3+4)
```

**Implementación**: El `decompose` usa el agente configurado para generar la descomposición. Luego ejecuta el DAG de dependencias.

```python
class TaskGraph:
    """DAG de subtareas con dependencias."""
    
    def add_task(self, task: SubTask, depends_on: list[str] = []) -> None: ...
    def get_ready_tasks(self, completed: set[str]) -> list[SubTask]: ...
    def is_complete(self) -> bool: ...
    
    def to_mermaid(self) -> str:
        """Genera diagrama Mermaid del DAG."""
```

**AC-F-INT-1**:
- Genera subtareas con scope (archivos que puede tocar)
- Detecta dependencias entre subtareas
- Ejecuta en paralelo cuando es posible
- Cada subtarea tiene su propio worktree
- < 150 líneas para TaskGraph

---

### F-INT-2: Human-in-the-Loop — Aprobación humana

**Problema**: No siempre quieres que corra 100% autónomo. A veces quieres aprobar antes de ciertas acciones.

**Solución**: Modo interactivo con puntos de aprobación configurables.

```toml
# ruffae.toml

[hil]
# Puntos donde Ruffae se detiene y pregunta
approval_points = [
    "after_planning",      # Mostrar PLAN.md y preguntar: ¿continuar?
    "before_verification", # Mostrar diff y preguntar: ¿ejecutar tests?
    "on_stagnation",       # Preguntar qué hacer cuando se atasca
]

# Límites que requieren aprobación
max_lines_without_approval = 200   # Si el diff > 200 líneas → preguntar
max_files_without_approval = 10   # Si toca > 10 archivos → preguntar
```

```bash
# Modo interactivo (pide aprobación en puntos configurados)
ruffae run "Add OAuth" --interactive --repo ./app

# Modo fully autonomous (sin preguntar nada)
ruffae run "Add OAuth" --repo ./app

# Modo dry-run (solo planifica, no ejecuta)
ruffae run "Add OAuth" --plan-only --repo ./app
```

**Comportamiento en modo interactivo**:

```
╭─────────────────────────────────────────────────────╮
│  RUFFAE — Phase: PLANNING                          │
│                                                     │
│  Task: "Add OAuth2 authentication"                 │
│  Agent: aider                                       │
│  Worktree: .worktrees/ralph/abc123                  │
│                                                     │
│  PLAN.md generated:                                 │
│  1. Add oauth2 dependencies to requirements.txt     │
│  2. Create OAuth2 service class                     │
│  3. Add OAuth2 routes                               │
│  4. Update User model for OAuth2 fields             │
│  5. Add tests                                       │
│                                                     │
│  Estimated scope: 4 files, ~300 lines               │
│                                                     │
│  [a] Approve plan  [e] Edit plan  [r] Reject       │
│  [s] Skip to coding  [q] Quit                      │
╰─────────────────────────────────────────────────────╯
```

**AC-F-INT-2**:
- Puntos de aprobación configurables
- Mostrar diff antes/después de cada fase
- Opciones: approve, reject, edit plan, skip, quit
- Funciona en terminal con input() y en API con callback
- < 100 líneas adicionales en loop.py

---

### F-INT-3: Multi-Agent Strategy — Agentes por fase

(De SPEC v3, sin cambios)

```toml
[agent]                  # Default
type = "cli"
command = "aider"

[agent.planning]         # Claude Code para planificar
type = "cli"
command = "claude"
prompt_flag = "-p"

[agent.coding]           # Pi para codificar (tiene tools)
type = "pi"

[agent.review]           # LM Studio para review (barato, local)
type = "http"
base_url = "http://localhost:1234"
model = "qwen3.5:9b"
```

---

## TIER 3: COLLABORATION — Para equipos

### F-COL-1: PR Auto-Generation

**Problema**: Después de que Ruffae completa una tarea, tienes un worktree con cambios. Falta crear el PR.

**Solución**: Auto-generar PR con título, descripción, y labels.

```bash
ruffae pr <task-id> --repo ./app --platform github
```

**Genera automáticamente**:

```markdown
## PR: Add JWT authentication to auth module

### Task
Implement JWT-based authentication for the API endpoints.

### Changes
- `src/auth/jwt_handler.py` (NEW) — JWT token generation and validation
- `src/auth/middleware.py` (MODIFIED) — Added auth middleware
- `src/routes/login.py` (MODIFIED) — Login/logout endpoints
- `tests/test_jwt.py` (NEW) — 12 tests, all passing

### Quality Gates
✅ Tests: 12/12 passed
✅ Lint: 0 errors
✅ Type check: passed
✅ Diff sanity: 4 files, 247 lines

### Audit
- Agent: aider (planning), pi (coding), qwen3.5 (review)
- Iterations: 4 (2 coding, 1 verification fix, 1 final)
- Duration: 3m 42s
- Tokens: ~15,000 input, ~8,000 output

### Screenshots
(If applicable)
```

**AC-F-COL-1**:
- Soporta GitHub (`gh pr create`) y GitLab (`mr create`)
- Descripción generada del audit trail
- Labels automáticos del scope de archivos
- Assignee configurable
- < 100 líneas

---

### F-COL-2: Commit Messages

**Problema**: Los agentes generan commits horribles ("fix", "update", "changes").

**Solución**: Generar conventional commits con contexto.

```bash
ruffae commit <task-id> --repo ./app
```

**Genera**:

```
feat(auth): add JWT token generation and validation

- Implement JWTHandler class with HS256 signing
- Add auth middleware for protected routes
- Create login/logout endpoints with token refresh
- Add 12 tests covering auth flow

Task: abc123 | Agent: aider → pi | 4 iterations
```

**AC-F-COL-2**: Conventional commits. Scope del path. Body del audit. < 60 líneas.

---

### F-COL-3: GitHub Issues Integration

**Problema**: Las tareas vienen de issues. Tienes que copiar/pegar.

**Solución**: Ruffae lee issues y escribe resultados.

```bash
# Ejecutar tarea desde un issue
ruffae run --from-issue 42 --repo ./app

# Al completar, auto-comenta en el issue:
# "✅ Task completed by ruffae. PR #123 created. 4 files changed, all tests passing."
```

```toml
[integrations.github]
repo = "owner/repo"
auto_comment = true        # Comentar en issue al completar
auto_close = false         # Cerrar issue al completar
auto_label = ["ruffae", "auto-generated"]
```

**AC-F-COL-3**: GitHub API via `gh` CLI. Leer issue, comentar, label. < 80 líneas.

---

### F-COL-4: Notifications

**Problema**: No sabes cuándo termina una tarea larga.

**Solución**: Notificaciones configurables.

```toml
[notifications]
# Slack
[[notifications.channels]]
type = "slack"
webhook = "https://hooks.slack.com/..."
events = ["task_started", "task_completed", "task_failed", "stagnation_detected"]

# Discord
[[notifications.channels]]
type = "discord"
webhook = "https://discord.com/api/webhooks/..."
events = ["task_completed", "task_failed"]

# Email (SMTP)
[[notifications.channels]]
type = "email"
to = "dev@company.com"
smtp_host = "smtp.gmail.com"
events = ["task_completed", "task_failed"]

# Custom webhook
[[notifications.channels]]
type = "webhook"
url = "https://internal.example.com/ruffae"
events = ["*"]
```

**Payload estándar**:

```json
{
  "event": "task_completed",
  "task_id": "abc123",
  "task": "Add JWT auth",
  "agent": "aider",
  "duration_s": 222,
  "iterations": 4,
  "files_changed": 4,
  "tests_passed": true,
  "gates": {"tests": "pass", "lint": "pass"},
  "repo": "owner/repo",
  "branch": "ralph/abc123"
}
```

**AC-F-COL-4**: Genérico — Slack, Discord, email, webhook custom. Template de mensaje configurable. < 80 líneas.

---

### F-COL-5: Web Dashboard

**Problema**: CLI es genial para devs, pero managers/teams quieren ver estado.

**Solución**: Dashboard web minimalista.

```bash
ruffae dashboard --port 8080
```

```
╔══════════════════════════════════════════════════════╗
║  RUFFAE DASHBOARD                          :8080    ║
╠══════════════════════════════════════════════════════╣
║                                                       ║
║  ACTIVE TASKS                        COMPLETED: 12    ║
║  ┌──────────┬─────────┬────────┬──────┬──────────┐   ║
║  │ Task     │ Agent   │ Phase  │ Iter │ Duration │   ║
║  ├──────────┼─────────┼────────┼──────┼──────────┤   ║
║  │ OAuth2   │ aider   │ CODING │ 3/50 │ 2m 15s   │   ║
║  │ Fix #42  │ pi      │ VERIFY │ 1/50 │ 45s      │   ║
║  │ DB refac │ claude  │ PLAN   │ 0/50 │ 10s      │   ║
║  └──────────┴─────────┴────────┴──────┴──────────┘   ║
║                                                       ║
║  AGENT STATS                                          ║
║  aider:  ████████░░ 80% success, avg 3m per task     ║
║  pi:     █████████░ 90% success, avg 2m per task     ║
║  claude: ████████░░ 85% success, avg 4m per task     ║
║                                                       ║
║  RECENT COMPLETED                                      ║
║  ✅ "Add rate limiting" (aider) — 3m 22s, 3 files    ║
║  ✅ "Fix login bug" (pi) — 1m 05s, 1 file            ║
║  ❌ "Refactor API" (claude) — FAILED after 15 iter   ║
║                                                       ║
╚══════════════════════════════════════════════════════╝
```

**AC-F-COL-5**: HTML + SSE para real-time. Mismo puerto que Agent Protocol. < 200 líneas.

---

## TIER 4: ADVANCED — Lo que te pone en otro nivel

### F-ADV-1: Agent Benchmarking & Ranking

**Problema**: No sabes qué agente es mejor para qué tipo de tarea.

**Solución**: Ruffae trackea métricas por agente y genera rankings.

```bash
ruffae stats --repo ./app
```

```
AGENT PERFORMANCE (last 30 days)
─────────────────────────────────────────────────
Agent       Tasks  Success  Avg Iter  Avg Time  Avg Tokens
aider       15     87%      3.2       2m 45s    12K in / 6K out
pi          12     92%      2.8       1m 55s    18K in / 9K out
claude      8      75%      4.1       3m 30s    25K in / 12K out

BY TASK TYPE:
"bug_fix"       → pi (95% success, 1.5 min avg)
"feature"       → aider (90% success, 3 min avg)
"refactor"      → claude (80% success, 4 min avg)
"tests"         → aider (95% success, 2 min avg)

RECOMMENDATION:
  For "Fix auth bug" → use pi (95% success on bug_fix)
```

**Datos almacenados**:

```json
{
  "agent": "aider",
  "task_type": "bug_fix",
  "success": true,
  "iterations": 3,
  "duration_s": 165,
  "tokens_in": 12000,
  "tokens_out": 6000,
  "files_changed": 2,
  "gates_passed": ["tests", "lint"],
  "timestamp": "2026-04-19T12:00:00Z"
}
```

**AC-F-ADV-1**: SQLite local para stats. Ranking por tipo de tarea. Recomendación automática. < 120 líneas.

---

### F-ADV-2: Dynamic Agent Selection

**Problema**: Tienes que elegir el agente manualmente.

**Solución**: Ruffae elige automáticamente el mejor agente para cada tarea.

```toml
[agent]
type = "auto"  # ← NUEVO: selección automática
```

**Algoritmo**:

```python
def select_best_agent(task_description: str, stats: AgentStats) -> Agent:
    # 1. Clasificar tipo de tarea
    task_type = classify_task(task_description)
    # "bug_fix" | "feature" | "refactor" | "tests" | "docs" | "config"
    
    # 2. Buscar en stats qué agente tiene mejor success rate para ese tipo
    best = stats.get_best_agent(task_type)
    
    # 3. Si no hay datos suficientes (< 3 tasks), usar default
    if best.confidence < 0.7:
        return default_agent
    
    return best.agent
```

**Clasificación de tarea** (sin LLM, heurística):

```python
TASK_PATTERNS = {
    "bug_fix":    ["fix", "bug", "error", "crash", "broken", "fallo"],
    "feature":    ["add", "implement", "create", "new", "support"],
    "refactor":   ["refactor", "rewrite", "restructure", "clean", "optimize"],
    "tests":      ["test", "coverage", "spec", "verify"],
    "docs":       ["document", "readme", "comment", "docstring"],
    "config":     ["config", "setup", "install", "deploy", "ci"],
}
```

**AC-F-ADV-2**: Sin LLM para clasificar (heurística < 1ms). Stats de F-ADV-1. Fallback a default. < 80 líneas.

---

### F-ADV-3: Cost Tracking

**Problema**: No sabes cuánto cuesta cada tarea en tokens/dinero.

**Solución**: Tracking automático con costos estimados.

```bash
ruffae cost --repo ./app --period 7d
```

```
COST REPORT (last 7 days)
──────────────────────────────────────────────
Task               Agent    Tokens(I/O)    Est. Cost
"Add OAuth2"       aider    15K / 8K       $0.12
"Fix login bug"    pi       22K / 11K      $0.18
"Refactor DB"      claude   45K / 22K      $0.55
──────────────────────────────────────────────
TOTAL: 82K / 41K tokens                  $0.85

BY AGENT:
aider:   $0.12 (14%)
pi:      $0.18 (21%)
claude:  $0.55 (65%)  ← Consider switching to aider for refactors
```

**Modelo de costos**: Configurable por agente.

```toml
[agent.coding]
type = "pi"
cost_per_1k_input = 0.003     # $0.003 per 1K input tokens
cost_per_1k_output = 0.015    # $0.015 per 1K output tokens
```

**AC-F-ADV-3**: SQLite. Reporte por tarea, agente, periodo. Recomendaciones de ahorro. < 80 líneas.

---

### F-ADV-4: Replay Mode

**Problema**: Una tarea falló y quieres entender paso a paso qué pasó.

**Solución**: Reproducir la ejecución desde el audit trail.

```bash
# Replay interactivo (avanza paso a paso)
ruffae replay <task-id> --repo ./app

# Replay con diffs en cada paso
ruffae replay <task-id> --show-diffs --repo ./app
```

```
╭──────────────────────────────────────────────────────╮
│  REPLAY: Task abc123 — "Add JWT auth"               │
│                                                       │
│  Step 1/4 — PLANNING (aider, 12s)                   │
│  ─────────────────────────────────────────            │
│  Prompt: "Analyze the codebase and write a plan..."  │
│  Response: Created PLAN.md with 5 steps              │
│  Files: PLAN.md (NEW)                                │
│  Tokens: 1,500 in / 800 out                          │
│                                                       │
│  [Enter] Next step  [d] Show diff  [s] Skip to end  │
╰──────────────────────────────────────────────────────╯
```

**AC-F-ADV-4**: Lee audit JSONL. Muestra cada paso con diff. < 100 líneas.

---

### F-ADV-5: Secret Scanning

**Problema**: Los agentes pueden introducir secrets en el código (API keys, passwords).

**Solución**: Escanear automáticamente después de cada iteración.

```python
SECRET_PATTERNS = [
    r'(?i)(api_key|apikey|api_secret)\s*[:=]\s*["\'][\w-]{20,}',
    r'(?i)(password|passwd|pwd)\s*[:=]\s*["\'][^"\']{8,}',
    r'(?i)(secret|token|bearer)\s*[:=]\s*["\'][\w-]{20,}',
    r'sk-[a-zA-Z0-9]{20,}',           # OpenAI
    r'ghp_[a-zA-Z0-9]{36}',           # GitHub PAT
    r'AKIA[0-9A-Z]{16}',              # AWS
    r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
]
```

**AC-F-ADV-5**: Regex scanning post-diff. Auto-revert si detecta secret. < 50 líneas.

---

### F-ADV-6: Docker Sandbox

**Problema**: Worktrees aíslan el código, pero el agente puede ejecutar comandos peligrosos (`rm -rf /`, `curl malware`).

**Solución**: Ejecutar el agente dentro de un container.

```toml
[sandbox]
type = "docker"               # "native" | "docker"
image = "ruffae/agent-runner:latest"
memory_limit = "2g"
cpu_limit = 2
network = "none"              # Sin internet para el agente
readonly_mounts = ["/usr", "/lib"]
```

```bash
# El worktree se monta en el container
# El agente corre aislado: sin red, sin acceso al host
ruffae run "Fix bug" --sandbox docker --repo ./app
```

**AC-F-ADV-6**: Docker SDK Python. Volúmenes read-write solo para worktree. Sin red. < 100 líneas.

---

### F-ADV-7: Plugin System

**Problema**: Cada equipo tiene necesidades diferentes. No puedes meter todo en core.

**Solución**: Sistema de plugins como pi.

```python
# plugins/my_plugin.py

class MyPlugin(RuffaePlugin):
    """Plugin custom para mi equipo."""
    
    @hook("after_coding")
    async def run_custom_checks(self, worktree: Path, ctx: HookContext):
        """Correr checks custom después de cada iteración de coding."""
        result = subprocess.run(["my-custom-linter", worktree])
        if result.returncode != 0:
            return HookResult(block=True, message="Custom linter failed")
        return HookResult(block=False)

    @hook("task_completed")
    async def notify_team(self, ctx: HookContext):
        """Notificar al equipo cuando una tarea completa."""
        requests.post("https://internal.example.com/notify", json=ctx.to_dict())
```

**Hooks disponibles**:

| Hook | Cuando | Puede bloquear? |
|------|--------|----------------|
| `before_planning` | Antes de planificar | Sí |
| `after_planning` | Después de planificar | Sí |
| `before_coding` | Antes de cada iteración | Sí |
| `after_coding` | Después de cada iteración | Sí |
| `before_verification` | Antes de tests | Sí |
| `after_verification` | Después de tests | Sí |
| `on_stagnation` | Cuando detecta estancamiento | No |
| `on_guardrail_violation` | Cuando viola guardrails | No |
| `task_completed` | Tarea completada | No |
| `task_failed` | Tarea fallida | No |

```toml
# ruffae.toml
[plugins]
dirs = ["./ruffae-plugins/", "~/.ruffae/plugins/"]
```

**AC-F-ADV-7**: Protocol-based. 10 hooks. Blocking vs informational. < 80 líneas core.

---

### F-ADV-8: Parallel Execution

(De SPEC v3, mejorado con TaskGraph de F-INT-1)

```bash
# Desde un PRD, descomponer y ejecutar en paralelo
ruffae run --from-file PRD.md --decompose --parallel 4 --repo ./app

# O manualmente:
ruffae parallel \
  --task "Fix auth bug" \
  --task "Add rate limiter" \
  --task "Update docs" \
  --parallel 3 \
  --repo ./app
```

```toml
[execution]
max_parallel = 4          # Max worktrees simultáneos
merge_strategy = "rebase" # "rebase" | "merge" | "manual"
```

**AC-F-ADV-8**: asyncio semaphore para paralelismo. Merge automático o manual. < 80 líneas.

---

## RUFFAE.TOML COMPLETO (Enterprise)

```toml
# ═══════════════════════════════════════════════════
# RUFFAE — Enterprise Configuration
# ═══════════════════════════════════════════════════

# ── Agent ──────────────────────────────────────────
[agent]
type = "auto"                    # "cli" | "http" | "pi" | "auto"
command = "aider"
prompt_flag = "--message"

[agent.planning]
type = "cli"
command = "claude"
prompt_flag = "-p"

[agent.coding]
type = "pi"

[agent.review]
type = "http"
base_url = "http://localhost:1234"
model = "qwen3.5:9b"
cost_per_1k_input = 0.0
cost_per_1k_output = 0.0

# ── Workspace ─────────────────────────────────────
[workspace]
test_command = "pytest"
worktree_dir = ".worktrees"
auto_commit = true              # Auto-commit después de cada iteración
commit_style = "conventional"   # "conventional" | "simple" | "detailed"

# ── Loop ──────────────────────────────────────────
[loop]
max_iterations = 50
max_stagnation = 3
auto_snapshot = true

# ── Guardrails ────────────────────────────────────
[guardrails]
protected = [".env*", "*.secret", "*.key", "docker-compose.prod.yml"]
scope = []                      # Vacío = todo permitido (excepto protected)
scan_secrets = true             # Escanear secrets en diffs

# ── Quality Gates ─────────────────────────────────
[[quality_gates]]
name = "tests"
command = "pytest --tb=short -q"
blocking = true

[[quality_gates]]
name = "lint"
command = "ruff check ."
blocking = true

[[quality_gates]]
name = "typecheck"
command = "mypy src/ --ignore-missing-imports"
blocking = false

[[quality_gates]]
name = "diff_sanity"
max_lines = 500
max_files = 20
blocking = true

# ── Human-in-the-Loop ────────────────────────────
[hil]
enabled = false                 # true para modo interactivo
approval_points = ["after_planning", "before_verification"]
max_lines_without_approval = 200

# ── Memory ────────────────────────────────────────
[memory]
type = "null"                   # "mcp" | "file" | "null"
# gateway_url = "http://127.0.0.1:3050"
# store_dir = ".ruffae/memory"

# ── Execution ─────────────────────────────────────
[execution]
max_parallel = 4
merge_strategy = "rebase"

# ── Audit ─────────────────────────────────────────
[audit]
enabled = true
log_dir = ".ruffae/audit"

# ── Sandbox ───────────────────────────────────────
[sandbox]
type = "native"                 # "native" | "docker"
# image = "ruffae/agent-runner:latest"
# memory_limit = "2g"

# ── Integrations ──────────────────────────────────
[integrations.github]
repo = ""                       # "owner/repo"
auto_comment = false
auto_close = false

# ── Notifications ────────────────────────────────
[[notifications.channels]]
type = "webhook"
url = ""
events = ["task_completed", "task_failed"]

# ── Stats ─────────────────────────────────────────
[stats]
enabled = true
db = ".ruffae/stats.db"         # SQLite
agent_ranking = true             # Auto-rankear agentes

# ── Plugins ───────────────────────────────────────
[plugins]
dirs = ["./ruffae-plugins/"]

# ── Server (Agent Protocol) ───────────────────────
[server]
host = "127.0.0.1"
port = 8000
dashboard = true                # Servir dashboard web
cors_origins = ["*"]
```

---

## COMANDOS CLI COMPLETOS

```bash
# ── Ejecución ──
ruffae run <description> [options]
ruffae run --from-file <path>
ruffae run --from-issue <number>
ruffae run --decompose [--parallel N]
ruffae run --plan-only          # Solo planifica, no ejecuta
ruffae run --interactive        # Human-in-the-loop
ruffae run --dry-run            # Simular sin ejecutar

# ── Gestión ──
ruffae resume <task-id>
ruffae status [--repo <path>]
ruffae rollback <task-id> --to <snapshot>
ruffae cancel <task-id>
ruffae cleanup [--older-than HOURS]

# ── Post-tarea ──
ruffae pr <task-id> [--platform github|gitlab]
ruffae commit <task-id>
ruffae diff <task-id>           # Ver diff completo

# ── Análisis ──
ruffae stats [--period 30d]
ruffae cost [--period 7d]
ruffae replay <task-id>
ruffae audit <task-id> [--format json|text]

# ── Benchmarking ──
ruffae bench <task-id> --agents "aider,pi,claude"  # Ejecutar con múltiples agentes
ruffae rank                      # Ver ranking de agentes

# ── Config ──
ruffae config --init
ruffae config --show
ruffae config --validate

# ── Server ──
ruffae serve [--port 8000] [--dashboard]

# ── Utilidades ──
ruffae version
ruffae doctor                    # Health check del sistema
```

---

## `ruffae doctor` — Health Check

```bash
$ ruffae doctor

RUFFAE SYSTEM CHECK
═════════════════════════════════════════════════════
✅ Git:             2.47.0 (/usr/bin/git)
✅ Python:          3.12.13
✅ ruffae.toml:     Found (project)
✅ Worktrees:       Git worktrees supported
✅ Agent (default): aider — available in PATH
✅ Agent (planning): claude — available in PATH
✅ Agent (coding):  pi — available in PATH
✅ Agent (review):  LM Studio — http://localhost:1234 (4 models loaded)
⚠️  Memory (MCP):   http://127.0.0.1:3050 — NOT reachable (fallback to null)
✅ Quality gate:    pytest — available
✅ Quality gate:    ruff — available
⚠️  Quality gate:   mypy — not found (skipping)
✅ Sandbox:         native (docker available if needed)
✅ Stats DB:        .ruffae/stats.db (42 tasks tracked)

⚠️  2 warnings (non-blocking)
```

---

## VENTAJA COMPETITIVA — Ruffae vs El Mundo

| Feature | Ruffae | Devin ($500/mes) | SWE-agent | Aider | Claude Code |
|---------|--------|-------------------|-----------|-------|-------------|
| Agent-agnóstico | ✅ Cualquiera | ❌ Propio | ❌ Propio | ❌ Propio | ❌ Propio |
| Worktree isolation | ✅ | ✅ Docker | ❌ | ❌ | ❌ |
| Guardrails | ✅ | ✅ | ❌ | ❌ | ❌ |
| Quality gates chain | ✅ | ✅ | Parcial | ❌ | ❌ |
| Stagnation detection | ✅ | ❓ | ❌ | ❌ | ❌ |
| Multi-agent | ✅ | ❌ | ❌ | ❌ | ❌ |
| Agent Protocol API | ✅ | ❌ | ✅ | ❌ | ❌ |
| Parallel tasks | ✅ | ✅ | ❌ | ❌ | ❌ |
| Task decomposition | ✅ | ✅ | ❌ | ❌ | ❌ |
| Agent benchmarking | ✅ | ❌ | ❌ | ❌ | ❌ |
| Dynamic agent selection | ✅ | ❌ | ❌ | ❌ | ❌ |
| Cost tracking | ✅ | ✅ | ❌ | ❌ | ❌ |
| PR generation | ✅ | ✅ | ❌ | ❌ | ❌ |
| Secret scanning | ✅ | ✅ | ❌ | ❌ | ❌ |
| Docker sandbox | ✅ | ✅ | ❌ | ❌ | ❌ |
| Plugin system | ✅ | ❌ | ❌ | ✅ | ❌ |
| Audit trail | ✅ | ❓ | ❌ | ❌ | ❌ |
| Replay mode | ✅ | ❌ | ❌ | ❌ | ❌ |
| Human-in-the-loop | ✅ | ✅ | ❌ | ❌ | ❌ |
| Web dashboard | ✅ | ✅ | ❌ | ❌ | ❌ |
| Notifications | ✅ | ❌ | ❌ | ❌ | ❌ |
| Offline/Local | ✅ | ❌ Cloud | ✅ | ✅ | ✅ |
| Open source | ✅ | ❌ | ✅ | ✅ | ❌ |
| **Precio** | **Gratis** | **$500/mes** | Gratis | Gratis | Freemium |

**Ruffae es el único orquestador agent-agnóstico con aislamiento, verificación en cadena y benchmarking automático. Y es gratis y local.**

---

## PLAN DE EJECUCIÓN FINAL

```
Sprint 1-3: CORE (11h)
  Domain, state machine, agents, worktree, guardrails, quality gates

Sprint 4-5: INTELLIGENCE (9h)
  Audit, snapshots, Agent Protocol, multi-agent, decomposition, HIL

Sprint 6-7: COLLABORATION (10h)
  PR generation, commits, GitHub, notifications, dashboard

Sprint 8-10: ADVANCED (13h)
  Parallel, benchmarking, dynamic selection, cost, replay,
  secret scanning, Docker sandbox, plugins

TOTAL: ~43h, ~3,500 líneas
```

**Prioridad**: Core → Intelligence → Collaboration → Advanced
Cada tier es funcional por sí solo. No necesitas los 4 para tener valor.
