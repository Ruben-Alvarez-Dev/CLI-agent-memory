"""SQLite schema — init_db() creates all tables idempotently."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    content TEXT NOT NULL,
    tags TEXT,
    scope TEXT DEFAULT 'session',
    importance REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content, tags,
    content='memories',
    content_rowid='rowid'
);

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
    title, body, tags,
    content='decisions',
    content_rowid='rowid'
);

CREATE TABLE IF NOT EXISTS thinking_sessions (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    problem TEXT NOT NULL,
    conclusion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS thinking_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES thinking_sessions(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    thought TEXT NOT NULL,
    next_needed BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    task_id TEXT,
    goal TEXT NOT NULL,
    steps TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    thread_id TEXT NOT NULL,
    summary TEXT,
    messages TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
    summary,
    content='conversations',
    content_rowid='rowid'
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    agent TEXT,
    repo_path TEXT,
    branch TEXT,
    plan TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds REAL,
    iterations INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    tests_passed BOOLEAN,
    error TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT REFERENCES tasks(id),
    event_type TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(db_path: str | Path) -> sqlite3.Connection:
    """Create all tables idempotently and return connection."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
