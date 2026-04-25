"""Local filesystem vault adapter — stores vault entries as files."""

from __future__ import annotations
from pathlib import Path

from CLI_agent_memory.domain.protocols import VaultProtocol
from CLI_agent_memory.domain.types import VaultEntry


class LocalVaultAdapter(VaultProtocol):
    """Vault adapter backed by local filesystem."""

    def __init__(self, vault_dir: str | Path = ".agent-memory/vault"):
        self._vault = Path(vault_dir)

    def _folder(self, folder: str) -> Path:
        p = self._vault / folder
        p.mkdir(parents=True, exist_ok=True)
        return p

    async def write(self, folder: str, filename: str, content: str) -> VaultEntry:
        p = self._folder(folder) / filename
        p.write_text(content, encoding="utf-8")
        return VaultEntry(folder=folder, filename=filename, content=content, path=str(p))

    async def read(self, folder: str, filename: str) -> str | None:
        p = self._vault / folder / filename
        if not p.exists():
            return None
        return p.read_text(encoding="utf-8")

    async def search(self, query: str) -> list[VaultEntry]:
        results = []
        if not self._vault.exists():
            return results
        ql = query.lower()
        for folder in self._vault.iterdir():
            if not folder.is_dir():
                continue
            for f in folder.iterdir():
                if not f.is_file():
                    continue
                if ql in f.name.lower() or ql in f.stem.lower():
                    results.append(VaultEntry(folder=folder.name, filename=f.name, content="", path=str(f)))
        return results

    async def list_entries(self, folder: str = "") -> list[VaultEntry]:
        results = []
        target = self._vault / folder if folder else self._vault
        if not target.exists():
            return results
        for f in target.iterdir():
            if not f.is_file():
                continue
            results.append(VaultEntry(folder=folder or f.parent.name, filename=f.name, content="", path=str(f)))
        return results

    async def append(self, folder: str, filename: str, content: str) -> None:
        existing = await self.read(folder, filename)
        combined = (existing or "") + "\n\n" + content
        await self.write(folder, filename, combined)

    def close(self) -> None:
        pass
