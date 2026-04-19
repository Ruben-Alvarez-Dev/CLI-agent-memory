"""Tests for domain/db/schema.py — SPEC-D6."""

import tempfile
from pathlib import Path

from CLI_agent_memory.domain.db.schema import init_db


def test_init_db_creates_file():
    """init_db creates the database file."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = init_db(db_path)
        assert db_path.exists()
        conn.close()


def test_init_db_creates_all_tables():
    """All tables are created."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = init_db(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        expected = {
            "memories", "decisions", "thinking_sessions", "thinking_steps",
            "plans", "conversations", "tasks", "audit_events", "agent_metrics",
        }
        assert expected.issubset(tables)
        conn.close()


def test_init_db_idempotent():
    """init_db can be called multiple times without error."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn1 = init_db(db_path)
        conn1.close()
        conn2 = init_db(db_path)
        conn2.close()
