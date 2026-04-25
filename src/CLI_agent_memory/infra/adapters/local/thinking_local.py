"""Local SQLite thinking adapter — stores thinking chains in SQLite."""

from __future__ import annotations
import sqlite3
from pathlib import Path

from CLI_agent_memory.domain.db.schema import init_db
from CLI_agent_memory.domain.protocols import ThinkingProtocol
from CLI_agent_memory.domain.types import ThinkingResult, ThinkingStep


class LocalThinkingAdapter(ThinkingProtocol):
    """Thinking adapter backed by local SQLite."""

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

    async def think(self, problem: str, depth: int = 5) -> ThinkingResult:
        # Local adapter can't think — just record the problem
        db = self._db()
        cur = db.execute("INSERT INTO thinking_sessions (problem) VALUES (?)", (problem,))
        session_id = str(cur.lastrowid)
        db.commit()
        return ThinkingResult(session_id=session_id, problem=problem)

    async def get_session(self, session_id: str) -> ThinkingResult | None:
        row = self._db().execute(
            "SELECT id, problem, conclusion FROM thinking_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            return None
        steps_rows = self._db().execute(
            "SELECT step_number, thought, next_needed FROM thinking_steps WHERE session_id = ? ORDER BY step_number",
            (session_id,),
        ).fetchall()
        return ThinkingResult(
            session_id=str(row[0]), problem=row[1],
            steps=[ThinkingStep(step_number=r[0], thought=r[1], next_needed=bool(r[2])) for r in steps_rows],
            conclusion=row[2] or "",
        )
