# Release 1 — CLI-agent-memory Core

## SPEC-DRIVEN CHECKLIST

> Rule: NOTHING is done until it's checked here.
> Every checkbox maps to a SPEC acceptance criterion.

---

## Sprint 1: Foundations (no infra)

### SPEC-D1: Domain Types (`domain/types.py`)

- [ ] D1.1 AgentState enum defined (PLANNING, CODING, VERIFICATION, DONE, FAILED)
- [ ] D1.2 Message model defined (role, content)
- [ ] D1.3 LLMResponse model defined (text, files_edited, tool_calls, finish_reason)
- [ ] D1.4 CommandResult model defined (success, stdout, stderr, exit_code)
- [ ] D1.5 ContextPack model defined (context_text, sources, token_count)
- [ ] D1.6 Memory model defined (id, content, tags, scope, importance, created_at)
- [ ] D1.7 Decision model defined (id, title, body, tags, created_at)
- [ ] D1.8 ThinkingStep model defined (step_number, thought, next_needed)
- [ ] D1.9 ThinkingResult model defined (session_id, problem, steps, conclusion)
- [ ] D1.10 Plan model defined (id, task_id, goal, steps, status)
- [ ] D1.11 VaultEntry model defined (folder, filename, content, path)
- [ ] D1.12 TaskResult model defined (task_id, status, worktree_path, plan, files_modified, tests_passed, error, duration_seconds)
- [ ] D1.13 HealthStatus model defined (status, service, uptime_seconds, connections)
- [ ] D1.14 ServiceMetrics model defined (tasks_completed, failed, in_progress, tool_calls, errors, uptime)
- [ ] D1.15 All types are Pydantic models or Enums
- [ ] D1.16 0 external dependencies (pydantic + stdlib only)
- [ ] D1.17 All types serializable to JSON (model_dump_json / model_validate_json)

### SPEC-D2: Protocol Interfaces (`domain/protocols.py`)

- [ ] D2.1 MemoryProtocol defined (recall, store, ingest, search, list)
- [ ] D2.2 ThinkingProtocol defined (think, get_session)
- [ ] D2.3 EngramProtocol defined (save_decision, search_decisions, save_entity, search_entities)
- [ ] D2.4 PlanningProtocol defined (create_plan, get_plan)
- [ ] D2.5 ConversationProtocol defined (save, search)
- [ ] D2.6 VaultProtocol defined (write, read, search, list_entries, append)
- [ ] D2.7 WorkspaceProtocol defined (create, remove, run_command, read_file, write_file, list_files)
- [ ] D2.8 LLMClient defined (generate, is_available)
- [ ] D2.9 FederationProtocol defined (register, discover, publish_event, subscribe)
- [ ] D2.10 GovernanceProtocol defined (check_permission, validate_task, write_audit)
- [ ] D2.11 ObservabilityProtocol defined (health, metrics, record_task_start, record_task_complete, record_task_failure)
- [ ] D2.12 All interfaces use @runtime_checkable Protocol
- [ ] D2.13 0 business logic — only signatures
- [ ] D2.14 Return types from domain/types.py
- [ ] D2.15 One interface per responsibility (ISP)

### SPEC-D4: StagnationMonitor (`domain/stagnation.py`)

- [ ] D4.1 StagnationResult dataclass defined (is_stagnant, reason, intervention)
- [ ] D4.2 StagnationMonitor class defined (max_failures, record_turn, reset)
- [ ] D4.3 Detects >= 3 turns without edits
- [ ] D4.4 Detects >= 3 same errors
- [ ] D4.5 Intervention prompts are configurable
- [ ] D4.6 < 80 lines
- [ ] D4.7 0 dependencies (stdlib only)

### SPEC-D5: TaskContext (`domain/state.py`)

- [ ] D5.1 TaskContext class defined (state, task_description, plan, progress, iteration, task_id)
- [ ] D5.2 save() writes .agent-memory-state.json
- [ ] D5.3 load() reads .agent-memory-state.json
- [ ] D5.4 transition() changes state AND calls save()
- [ ] D5.5 JSON serializable/deserializable without loss
- [ ] D5.6 task_id is deterministic UUID4 (seed = branch_name)
- [ ] D5.7 < 60 lines

### SPEC-D7: Exit Codes (`domain/exit_codes.py`)

- [ ] D7.1 EXIT_OK = 0
- [ ] D7.2 EXIT_ERROR = 1
- [ ] D7.3 EXIT_USAGE = 2
- [ ] D7.4 EXIT_TASK_FAILED = 10
- [ ] D7.5 EXIT_STAGNATION = 11
- [ ] D7.6 EXIT_CANCELLED = 12
- [ ] D7.7 EXIT_LLM_UNAVAILABLE = 20
- [ ] D7.8 EXIT_MEMORY_UNAVAILABLE = 21
- [ ] D7.9 EXIT_WORKTREE_ERROR = 22
- [ ] D7.10 EXIT_SIGINT = 130
- [ ] D7.11 EXIT_SIGTERM = 143

### SPEC-D6: SQLite Schema (`domain/db/schema.py`)

- [ ] D6.1 memories table created
- [ ] D6.2 memories_fts FTS5 virtual table created
- [ ] D6.3 decisions table created
- [ ] D6.4 decisions_fts FTS5 virtual table created
- [ ] D6.5 thinking_sessions table created
- [ ] D6.6 thinking_steps table created (FK with CASCADE)
- [ ] D6.7 plans table created
- [ ] D6.8 conversations table created
- [ ] D6.9 conversations_fts FTS5 virtual table created
- [ ] D6.10 tasks table created
- [ ] D6.11 audit_events table created
- [ ] D6.12 agent_metrics table created
- [ ] D6.13 init_db() creates all tables idempotently
- [ ] D6.14 < 100 lines

### SPEC-CLI-02: Configuration (`config.py`)

- [ ] C2.1 AgentMemoryConfig class (pydantic-settings BaseSettings)
- [ ] C2.2 llm_backend, llm_model, llm_base_url, llm_api_key, llm_timeout
- [ ] C2.3 memory_url, memory_enabled, force_local
- [ ] C2.4 max_iterations, max_stagnation, test_command
- [ ] C2.5 worktree_dir, vault_dir, db_path
- [ ] C2.6 jart_os_enabled, nats_url, redis_url, a2a_enabled, a2a_port
- [ ] C2.7 env_prefix = "AGENT_MEMORY_"
- [ ] C2.8 toml_file = "agent-memory.toml"
- [ ] C2.9 Loads: CLI args > env vars > agent-memory.toml > defaults
- [ ] C2.10 < 60 lines

### SPEC-P-01: Prompt Templates (`prompts/templates.py`)

- [ ] P1.1 system_prompt() generates system prompt per role/phase
- [ ] P1.2 planning_prompt() generates planning prompt with context
- [ ] P1.3 coding_prompt() generates coding prompt with plan + files
- [ ] P1.4 verification_prompt() generates retry prompt on test failure
- [ ] P1.5 intervention_prompt() generates stagnation intervention
- [ ] P1.6 Each prompt < 2000 tokens
- [ ] P1.7 Templates use placeholders (not hardcoded strings)
- [ ] P1.8 < 120 lines

---

## Sprint 2: Loop Core

### SPEC-D3: LoopEngine (`domain/loop.py`)

- [ ] D3.1 LoopEngine class with __init__(llm, memory, thinking, workspace, vault, config)
- [ ] D3.2 run() executes full loop (PLANNING → CODING → VERIFICATION → DONE/FAILED)
- [ ] D3.3 PLANNING: memory.recall → llm.generate → workspace.write_file("PLAN.md")
- [ ] D3.4 CODING: memory.recall → llm.generate → stagnation.record
- [ ] D3.5 VERIFICATION: workspace.run_command(test) → if pass → DONE, if fail → CODING
- [ ] D3.6 State persists in .agent-memory-state.json after each transition
- [ ] D3.7 Never exceeds max_iterations
- [ ] D3.8 On stagnation: truncate history to last 2 messages + intervention prompt
- [ ] D3.9 On completion: memory.store + vault.write
- [ ] D3.10 On failure: memory.ingest
- [ ] D3.11 Depends ONLY on protocols (DIP), not implementations
- [ ] D3.12 Testable with MockLLMClient
- [ ] D3.13 < 150 lines

### SPEC-LOC-07: Null Adapters (`infra/adapters/null/`)

- [ ] N7.1 NullMemoryAdapter implements MemoryProtocol, returns empty
- [ ] N7.2 NullThinkingAdapter implements ThinkingProtocol, returns empty
- [ ] N7.3 NullEngramAdapter implements EngramProtocol, returns empty
- [ ] N7.4 NullFederationAdapter implements FederationProtocol, no-ops
- [ ] N7.5 NullGovernanceAdapter implements GovernanceProtocol, allows all
- [ ] N7.6 All null adapters < 20 lines each
- [ ] N7.7 0 side effects

### Gateway (`gateway.py`)

- [ ] GW1 ProtocolFactory.create_memory() selects correct adapter
- [ ] GW2 ProtocolFactory.create_thinking() selects correct adapter
- [ ] GW3 Resolution order: --force-local → mcp_stdio → mcp_http → local
- [ ] GW4 Federation resolution: jart-os → null

---

## Sprint 3: Local Infra

### SPEC-LOC-01: Local Memory SQLite (`infra/adapters/local/memory_sqlite.py`)

- [ ] L1.1 Implements MemoryProtocol
- [ ] L1.2 recall(): FTS5 search → ContextPack
- [ ] L1.3 store(): INSERT into memories + FTS5
- [ ] L1.4 ingest(): INSERT into audit_events
- [ ] L1.5 search(): FTS5 search → list[Memory]
- [ ] L1.6 list(): SELECT from memories with tag filter
- [ ] L1.7 Graceful on DB errors (no crash)

### SPEC-LOC-02: Local Thinking (`infra/adapters/local/thinking_local.py`)

- [ ] L2.1 Implements ThinkingProtocol
- [ ] L2.2 think(): recursive loop with LLM → thinking_sessions + thinking_steps
- [ ] L2.3 get_session(): reads from SQLite

### SPEC-LOC-03: Local Engram (`infra/adapters/local/engram_sqlite.py`)

- [ ] L3.1 Implements EngramProtocol
- [ ] L3.2 save_decision(): INSERT into decisions + FTS5
- [ ] L3.3 search_decisions(): FTS5 search → list[Decision]

### SPEC-LOC-04: Local Planning (`infra/adapters/local/planning_local.py`)

- [ ] L4.1 Implements PlanningProtocol
- [ ] L4.2 create_plan(): LLM generates plan → SQLite plans
- [ ] L4.3 get_plan(): SELECT from plans

### SPEC-LOC-05: Local Vault (`infra/adapters/local/vault_local.py`)

- [ ] L5.1 Implements VaultProtocol
- [ ] L5.2 write(): writes .md file in .agent-memory/vault/{folder}/
- [ ] L5.3 read(): reads .md file
- [ ] L5.4 search(): grep across vault
- [ ] L5.5 list_entries(): lists files in folder
- [ ] L5.6 append(): appends to existing file
- [ ] L5.7 Creates Decisions, Patterns, Notes, Inbox dirs on init

### SPEC-LOC-06: Local Conversation (`infra/adapters/local/conversation_local.py`)

- [ ] L6.1 Implements ConversationProtocol
- [ ] L6.2 save(): INSERT into conversations
- [ ] L6.3 search(): FTS5 search

### SPEC-LLM-01: LM Studio Client (`infra/llm/lmstudio.py`)

- [ ] LM1.1 Implements LLMClient
- [ ] LM1.2 POST /v1/chat/completions
- [ ] LM1.3 Timeout configurable (default 120s)
- [ ] LM1.4 1 retry on connection refused
- [ ] LM1.5 is_available() responds in < 2s
- [ ] LM1.6 < 80 lines

### SPEC-LLM-02: Ollama Client (`infra/llm/ollama.py`)

- [ ] O2.1 Implements LLMClient
- [ ] O2.2 POST /api/chat
- [ ] O2.3 < 60 lines

### SPEC-LLM-03: OpenAI-Compatible Client (`infra/llm/openai_compat.py`)

- [ ] OA3.1 Implements LLMClient
- [ ] OA3.2 Works with any OpenAI-compatible API
- [ ] OA3.3 Bearer auth in header
- [ ] OA3.4 < 60 lines

### SPEC-LLM-04: LLM Factory (`infra/llm/__init__.py`)

- [ ] F4.1 create_llm_client(config) → correct client by config.backend
- [ ] F4.2 Raises clear error if backend unavailable
- [ ] F4.3 < 30 lines

### SPEC-WS-01: Git Worktree (`infra/workspace/git_worktree.py`)

- [ ] W1.1 Implements WorkspaceProtocol
- [ ] W1.2 Worktrees created in .worktrees/ inside repo
- [ ] W1.3 Reuses existing branch without error
- [ ] W1.4 run_command with shell=True (allows pipes)
- [ ] W1.5 Validates repo has .git before operating
- [ ] W1.6 < 100 lines

---

## Sprint 4: MCP Infra + CLI

### SPEC-MCP-01: MCP Memory HTTP (`infra/adapters/mcp/memory_http.py`)

- [ ] MH1.1 Implements MemoryProtocol
- [ ] MH1.2 recall → engram_1mcp_recall
- [ ] MH1.3 store → automem_1mcp_memorize
- [ ] MH1.4 ingest → automem_1mcp_ingest_event
- [ ] MH1.5 Timeout: 30s recall, 10s store/ingest
- [ ] MH1.6 Graceful fallback if gateway unreachable
- [ ] MH1.7 < 100 lines

### SPEC-MCP-02: MCP Thinking (`infra/adapters/mcp/thinking_mcp.py`)

- [ ] MT2.1 Implements ThinkingProtocol
- [ ] MT2.2 think → sequential_thinking_1mcp_*

### SPEC-MCP-03: MCP Engram (`infra/adapters/mcp/engram_mcp.py`)

- [ ] ME3.1 Implements EngramProtocol
- [ ] ME3.2 save_decision → engram_1mcp_save_decision
- [ ] ME3.3 search_decisions → engram_1mcp_search_decisions

### SPEC-MCP-04: MCP Vault (`infra/adapters/mcp/vault_mcp.py`)

- [ ] MV4.1 Implements VaultProtocol
- [ ] MV4.2 write → engram_1mcp_memory_vault_write

### SPEC-MCP-05: MCP Stdio (`infra/adapters/mcp/memory_stdio.py`)

- [ ] MS5.1 Implements MemoryProtocol
- [ ] MS5.2 Communication via stdin/stdout subprocess

### SPEC-CLI-01: Commands (`cli.py`)

- [ ] C1.1 run command with all options
- [ ] C1.2 resume command
- [ ] C1.3 cancel command
- [ ] C1.4 status command (--json)
- [ ] C1.5 cleanup command
- [ ] C1.6 think command
- [ ] C1.7 plan command (--show)
- [ ] C1.8 recall command
- [ ] C1.9 remember command (--tags)
- [ ] C1.10 decisions command (--list, --add)
- [ ] C1.11 db command (--tasks, --stats)
- [ ] C1.12 config command (--show, --init, --validate)
- [ ] C1.13 doctor command
- [ ] C1.14 version command
- [ ] C1.15 --json on every command
- [ ] C1.16 POSIX exit codes on every path
- [ ] C1.17 SIGINT/SIGTERM handled gracefully
- [ ] C1.18 < 150 lines

### SPEC-CLI-03: Output Formatters

- [ ] C3.1 output/human.py — colored, table format
- [ ] C3.2 output/json.py — stdlib json, always available

---

## Sprint 5: Integration

### SPEC-PKG-01: Packaging (`pyproject.toml`)

- [ ] PK1.1 name = "CLI-agent-memory"
- [ ] PK1.2 version = "0.1.0"
- [ ] PK1.3 requires-python = ">=3.12"
- [ ] PK1.4 dependencies: pydantic, pydantic-settings, httpx
- [ ] PK1.5 scripts entry: CLI-agent-memory = "CLI_agent_memory.cli:main"
- [ ] PK1.6 optional-dependencies: dev, tui, server, jart-os, all

### SPEC-T-01: Domain Tests

- [ ] T1.1 test_types.py — 3 tests
- [ ] T1.2 test_stagnation.py — 7 tests
- [ ] T1.3 test_state.py — 5 tests
- [ ] T1.4 test_loop.py — 10 tests (with MockLLMClient)
- [ ] T1.5 test_schema.py — 3 tests

### SPEC-T-02: MCP Tests

- [ ] T2.1 test_memory_http.py — 5 tests
- [ ] T2.2 test_thinking_mcp.py — 3 tests
- [ ] T2.3 test_engram_mcp.py — 3 tests

### SPEC-T-03: Local Tests

- [ ] T3.1 test_memory_sqlite.py — 5 tests
- [ ] T3.2 test_thinking_local.py — 3 tests
- [ ] T3.3 test_engram_sqlite.py — 3 tests
- [ ] T3.4 test_vault_local.py — 3 tests

### SPEC-T-04: LLM Tests

- [ ] T4.1 test_lmstudio.py — 3 tests
- [ ] T4.2 test_ollama.py — 3 tests

### SPEC-T-05: Workspace + Null Tests

- [ ] T5.1 test_git_worktree.py — 8 tests
- [ ] T5.2 test_null_adapters.py — 5 tests

### SPEC-T-06: CLI Tests

- [ ] T6.1 test_cli.py — 12 tests

### SPEC-T-07: Config Tests

- [ ] T7.1 test_config.py — 6 tests

### SPEC-T-08: Integration Tests

- [ ] T8.1 test_full_loop.py — end-to-end

### Documentation

- [ ] DOC1 README.md
- [ ] DOC2 ARCHITECTURE.md

---

## GLOBAL VERIFICATION

- [ ] ALL tests pass (pytest -v)
- [ ] Coverage > 80% on domain/
- [ ] --json works on every command
- [ ] Exit codes correct on every path
- [ ] CLI-agent-memory --help works
- [ ] CLI-agent-memory --version works
- [ ] CLI-agent-memory doctor works
- [ ] Works standalone (no MCP)
- [ ] Works connected to MCP-agent-memory
- [ ] Each file < 150 lines
- [ ] 0 direct imports from infra/ in domain/
- [ ] git add -A && git commit && git push

---

**TOTAL CHECKPOINTS: ~160**
**CHECKED: 0 / ~160**
