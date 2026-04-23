"""MCP Server Manager — spawns and manages MCP-agent-memory as a subprocess.

Uses subprocess directly (no MCP SDK context managers) for persistent process
lifecycle. Singleton pattern: one shared process across all adapters.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

_MCP_ENV = {
    "PYTHONPATH": "/Users/ruben/MCP-servers/MCP-agent-memory/src",
    "MEMORY_SERVER_DIR": "/Users/ruben/MCP-servers/MCP-agent-memory",
    "QDRANT_URL": "http://127.0.0.1:6333",
    "EMBEDDING_BACKEND": "llama_server",
    "LLAMA_SERVER_URL": "http://127.0.0.1:8081",
    "EMBEDDING_MODEL": "bge-m3",
    "EMBEDDING_DIM": "1024",
    "LLM_BACKEND": "ollama",
    "LLM_MODEL": "qwen2.5:7b",
}

_MCP_PYTHON = "/Users/ruben/MCP-servers/MCP-agent-memory/.venv/bin/python3"
_MCP_SCRIPT = "/Users/ruben/MCP-servers/MCP-agent-memory/src/unified/server/main.py"


class MCPSessionManager:
    """Long-lived MCP subprocess. Call tool() directly after start()."""

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._req_id = 0
        self._read_task: asyncio.Task | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        env = {**os.environ, **_MCP_ENV}
        self._proc = subprocess.Popen(
            [_MCP_PYTHON, "-u", _MCP_SCRIPT],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env,
        )
        self._started = True
        loop = asyncio.get_event_loop()
        self._read_task = loop.create_task(self._reader())
        # MCP initialize handshake
        await self._send_json({"jsonrpc": "2.0", "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "cli-agent-memory", "version": "0.1.0"}}, "id": self._next_id()})
        await self._send_json({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        logger.info("MCP-agent-memory subprocess started (pid=%s)", self._proc.pid)

    async def tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._started:
            raise RuntimeError("MCPSessionManager not started")
        req_id = self._next_id()
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future
        await self._send_json({"jsonrpc": "2.0", "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}}, "id": req_id})
        try:
            data = await asyncio.wait_for(future, timeout=60.0)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            return {}
        result = data.get("result", data)
        if isinstance(result, dict) and "content" in result:
            for block in result["content"]:
                if block.get("type") == "text":
                    try:
                        return json.loads(block["text"])
                    except (json.JSONDecodeError, TypeError):
                        return {"_raw": block.get("text", "")}
            return {}
        return result if isinstance(result, dict) else {}

    async def list_tools(self) -> list[str]:
        if not self._started:
            raise RuntimeError("MCPSessionManager not started")
        req_id = self._next_id()
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future
        await self._send_json({"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": req_id})
        try:
            data = await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            return []
        tools = data.get("result", {}).get("tools", [])
        return [t["name"] for t in tools]

    async def close(self) -> None:
        if not self._started:
            return
        if self._read_task:
            self._read_task.cancel()
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
        self._started = False
        logger.info("MCP-agent-memory subprocess stopped")

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def _send_json(self, msg: dict) -> None:
        line = json.dumps(msg) + "\n"
        if self._proc and self._proc.stdin:
            self._proc.stdin.write(line.encode())
            await asyncio.get_event_loop().run_in_executor(None, self._proc.stdin.flush)

    async def _reader(self) -> None:
        loop = asyncio.get_event_loop()
        try:
            while self._proc and self._proc.stdout:
                line = await loop.run_in_executor(None, self._proc.stdout.readline)
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                req_id = data.get("id")
                if req_id is not None and req_id in self._pending:
                    future = self._pending.pop(req_id)
                    if not future.done():
                        future.set_result(data)
        except Exception as e:
            logger.error("MCP reader error: %s", e)
            for future in self._pending.values():
                if not future.done():
                    future.cancel()
            self._pending.clear()


# ── Global singleton ─────────────────────────────────────────────

_global_manager: MCPSessionManager | None = None
_global_lock = asyncio.Lock()


async def get_shared_manager() -> MCPSessionManager:
    global _global_manager
    async with _global_lock:
        if _global_manager is None:
            _global_manager = MCPSessionManager()
            await _global_manager.start()
    return _global_manager
