"""MCP Vault stdio adapter — implements VaultProtocol via MCP subprocess."""

from __future__ import annotations
import logging
from pathlib import Path
from CLI_agent_memory.domain.protocols import VaultProtocol
from CLI_agent_memory.domain.types import VaultEntry
from .stdio_manager import get_shared_manager

logger = logging.getLogger(__name__)


class MCPVaultStdioAdapter(VaultProtocol):

    async def write(self, folder: str, filename: str, content: str) -> VaultEntry:
        try:
            mgr = await get_shared_manager()
            data = await mgr.tool("engram_vault_write", {"folder": folder, "filename": filename, "content": content})
            return VaultEntry(folder=folder, filename=filename, content=content, path=data.get("path", ""))
        except Exception as e:
            logger.error(f"vault write failed: {e}")
            return VaultEntry(folder=folder, filename=filename, content=content, path="")

    async def read(self, folder: str, filename: str) -> str | None:
        try:
            mgr = await get_shared_manager()
            data = await mgr.tool("engram_vault_read_note", {"folder": folder, "filename": filename})
            content = data.get("content")
            return content if content and data.get("status") != "not_found" else None
        except Exception as e:
            logger.error(f"vault read failed: {e}")
            return None

    async def search(self, query: str) -> list[VaultEntry]:
        try:
            mgr = await get_shared_manager()
            data = await mgr.tool("engram_vault_list_notes", {})
            notes = data.get("notes", [])
            ql = query.lower()
            return [VaultEntry(folder=Path(n.get("path","")).parent.name, filename=n.get("name",""), content="", path=n.get("path",""))
                    for n in notes if isinstance(n, dict) and (ql in n.get("name","").lower() or ql in n.get("path","").lower())]
        except Exception as e:
            logger.error(f"vault search failed: {e}")
            return []

    async def list_entries(self, folder: str = "") -> list[VaultEntry]:
        try:
            mgr = await get_shared_manager()
            data = await mgr.tool("engram_vault_list_notes", {"folder": folder} if folder else {})
            notes = data.get("notes", [])
            return [VaultEntry(folder=Path(n.get("path","")).parent.name, filename=n.get("name",""), content="", path=n.get("path",""))
                    for n in notes if isinstance(n, dict)]
        except Exception as e:
            logger.error(f"vault list failed: {e}")
            return []

    async def append(self, folder: str, filename: str, content: str) -> None:
        try:
            mgr = await get_shared_manager()
            data = await mgr.tool("engram_vault_read_note", {"folder": folder, "filename": filename})
            existing = data.get("content", "")
            if existing.startswith("---"):
                parts = existing.split("---", 2)
                combined = (parts[0] + "---" + parts[1] + "---\n\n" + parts[2].strip() + "\n\n" + content) if len(parts) >= 3 else existing + "\n\n" + content
            else:
                combined = existing + "\n\n" + content
            await mgr.tool("engram_vault_write", {"folder": folder, "filename": filename, "content": combined})
        except Exception as e:
            logger.error(f"vault append failed: {e}")

    async def close(self) -> None:
        pass
