# CLI-agent-memory

Autonomous coding agent with Hexagonal Architecture. Designed to work standalone or connected to `MCP-agent-memory`.

## 🚀 Quick Start

### 1. Installation (Development mode)
```bash
# Clone the repo
git clone <url>
cd PROJECT-CLI-agent-memory

# Install in editable mode with all dependencies
pip install -e ".[all]"
```

### 2. Usage
```bash
# Run a task using LM Studio (default) and MCP memory
CLI-agent-memory run "Implement a login form" --repo ./my-project

# Force local mode (autonomous)
CLI-agent-memory run "Fix bug X" --force-local
```

## 🏗 Architecture

The project follows **Hexagonal Architecture (Ports & Adapters)**:
- `domain/`: Pure business logic (LoopEngine, Stagnation, State). 0 external dependencies.
- `infra/adapters/`: Concrete implementations for MCP, Local SQLite, and Null adapters.
- `infra/llm/`: Clients for LM Studio and Ollama.
- `prompts/`: Managed templates for agent phases.

## 🛠 Tech Stack
- **Python 3.12+**
- **Pydantic v2**: Type safety and settings.
- **HTTPX**: Async communication with MCP and LLMs.
- **Pytest**: Full suite of unit and integration tests.

## 🧪 Testing
```bash
PYTHONPATH=src pytest
```
