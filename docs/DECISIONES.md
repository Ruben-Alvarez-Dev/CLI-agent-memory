# Architecture Decisions — CLI-agent-memory

## DEC-001: Naming & Ecosystem Relationship
- **Date**: 2026-04-19
- **Name**: CLI-agent-memory (formerly CLI-ruffae)
- **Production path**: `/Users/XXXX/MCP-servers/CLI-agent-memory`
- **Development path**: `PROJECT-CLI-agent-memory` (this folder)
- **Relationship**: Complements MCP-agent-memory
- **Modes**:
  - Connected (with MCP): Delegates memory/RAG/thinking to the memory server
  - Autonomous (without MCP): Local mini-brain (SQLite + JSONL)

## DEC-002: Memory Architecture
- Ports (interfaces) in domain/
- MCP adapters (delegate to MCP-agent-memory) and local adapters (SQLite + FTS5)
- Auto-detection: if MCP responds → mcp, else → local
- Flag --force-local to force local mode
- DO NOT replicate: patterns, consolidation (dream cycle), L0-L4 layers
- DO replicate: memory (store/recall), thinking, engram (decisions), planning, conversations, vault
- Flat memory (single layer) sufficient for short sessions

## DEC-003: Nomenclature (anti-typo rules)
- **FORBIDDEN**: "jart" alone. Always "jart-os".
- **FORBIDDEN**: "ruffae" or "Ruffae". Old name, use "agent-memory".
- **CLI name**: CLI-agent-memory (not CLI-ruffae)
- **MCP companion name**: MCP-agent-memory
- **GitHub repo name**: PROJECT-CLI-agent-memory
- **Production path**: `/Users/XXXX/MCP-servers/CLI-agent-memory`
- **Adapters**: `adapters/jart-os/` (not `adapters/jart/`)
- **NATS subjects**: `jart-os.04.cli-agent-memory.*`
- **Redis prefix**: `jart-os:cli-agent-memory:*`

## DEC-004: Obsidian Vault
- CLI-agent-memory has its own Obsidian vault at `.agent-memory/vault/`
- Usage similar to MCP-agent-memory (memory_vault_write)
- Structure: Decisions, Patterns, Notes, Inbox
- Structured Markdown for persistent documentation
- FTS5 indexed for search

## DEC-005: Jart-OS Integration
- **Date**: 2026-04-19
- CLI-agent-memory is designed for final integration into **Jart-OS**
- Can run standalone (free of obligation)
- Higher releases include:
  - **Federation**: Discovery, registration, state sync with Jart-OS
  - **Governance**: Permissions, access policies, roles
  - **Compliance**: Full audit, retention, export, traceability
- Integration via adapters (do not contaminate core)
- Protocol/API consumable by Jart-OS
