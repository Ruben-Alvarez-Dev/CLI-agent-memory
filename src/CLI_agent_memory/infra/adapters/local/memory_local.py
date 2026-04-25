"""Local SQLite memory adapter — stores/retrieves memories in SQLite."""

from __future__ import annotations
import json
import sqlite3
from pathlib import Path

from CLI_agent_memory.domain.db.schema import init_db
from CLI_agent_memory.domain.protocols import MemoryProtocol
from CLI_agent_memory.domain.types import ContextPack, Memory


class LocalMemoryAdapter(MemoryProtocol):
    """Memory adapter backed by local SQLite + FTS5."""

    def __init__(self, db_path: str | Path = ".agent-memory/agent-memory.db"):
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = init_db(self._db_path)
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    async def recall(self, query: str, max_tokens: int = 4000) -> ContextPack:
        rows = self._db().execute(
            "SELECT content, tags FROM memories ORDER BY importance DESC LIMIT 10"
        ).fetchall()
        text = "\n".join(r[0] for r in rows if r[0])
        return ContextPack(context_text=text[:max_tokens], token_count=min(len(text), max_tokens))

    async def store(self, event_type: str, content: str, tags: list[str] | None = None) -> str:
        tags_str = ",".join(tags) if tags else event_type
        db = self._db()
        db.execute("INSERT INTO memories (content, tags) VALUES (?, ?)", (content, tags_str))
        db.commit()
        row = db.execute("SELECT id FROM memories WHERE content = ? ORDER BY rowid DESC LIMIT 1", (content,)).fetchone()
        mem_id = str(row[0]) if row else ""
        # FTS uses rowid for content sync
        try:
            db.execute("INSERT INTO memories_fts (rowid, content, tags) VALUES ((SELECT rowid FROM memories WHERE id = ?), ?, ?)",
                       (mem_id, content, tags_str))
            db.commit()
        except Exception:
            pass  # FTS sync is best-effort
        return mem_id

    async def ingest(self, event_type: str, content: str) -> None:
        await self.store(event_type, content, tags=[event_type])

    async def search(self, query: str, limit: int = 10) -> list[Memory]:
        rows = self._db().execute(
            "SELECT m.id, m.content, m.tags FROM memories m "
            "JOIN memories_fts f ON f.rowid = m.rowid "
            "WHERE memories_fts MATCH ? ORDER BY f.rank LIMIT ?",
            (query, limit),
        ).fetchall()
        return [Memory(id=str(r[0]), content=r[1], tags=r[2].split(",") if r[2] else [])
                for r in rows]

    async def list(self, tags: list[str] | None = None, limit: int = 50) -> list[Memory]:
        if tags:
            like = ",".join(f"%{t}%" for t in tags)
            rows = self._db().execute(
                "SELECT id, content, tags FROM memories WHERE tags LIKE ? ORDER BY created_at DESC LIMIT ?",
                (like, limit),
            ).fetchall()
        else:
            rows = self._db().execute(
                "SELECT id, content, tags FROM memories ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [Memory(id=str(r[0]), content=r[1], tags=r[2].split(",") if r[2] else [])
                for r in rows]
