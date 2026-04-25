# Adapters — CLI-Specific Integration Layers

The MCP-agent-memory core is tool-agnostic — it exposes an HTTP sidecar on `:8890` that any client can call. Adapters are the glue between a specific CLI/tool and that sidecar.

## Architecture

```
Any CLI/Tool → Adapter (per tool) → HTTP :8890 → MCP-agent-memory → Qdrant
```

Each adapter knows:
- How to hook into its CLI's event system
- Which sidecar endpoints to call
- How to inject context into its CLI's prompt pipeline

## Available Adapters

| Adapter | Status | CLI/Tool |
|---------|--------|----------|
| `opencode/` | ✅ Active | [OpenCode](https://opencode.ai) — TypeScript plugin with 6 hooks |
| `claude-code/` | 🔜 Planned | Claude Code — hooks via `.claude/` config |
| `aider/` | 🔜 Planned | Aider — `.aider.conf.yml` + scripting |
| `cursor/` | 🔜 Planned | Cursor — `.cursorrules` + MCP config |
| `gemini/` | 🔜 Planned | Gemini CLI — agent config |

## Setup

Each adapter directory contains its own setup instructions. For OpenCode:

```bash
# Symlink from OpenCode plugins dir to repo
ln -s $(pwd)/adapters/opencode/backpack-orchestrator.ts ~/.config/opencode/plugins/
ln -s $(pwd)/adapters/opencode/engram.ts ~/.config/opencode/plugins/
```

## Shared Contract

All adapters talk to the same HTTP sidecar endpoints:

| Endpoint | Purpose | Called by |
|----------|---------|-----------|
| `POST /api/ingest-event` | Capture raw events | Every adapter |
| `POST /api/heartbeat` | Track turns (automem) | Every adapter |
| `POST /api/heartbeat-dream` | Track turns (autodream) | Every adapter |
| `POST /api/request-context` | Fetch relevant context | Every adapter |
| `POST /api/save-conversation` | Save before compaction | Adapters with compaction |
| `POST /api/consolidate` | Trigger consolidation | Adapters with compaction |
