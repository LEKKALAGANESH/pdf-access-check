"""Database access: a local SQLite file by default, Postgres when DATABASE_URL is set.

Free hosts wipe their disk on every deploy, so production sets DATABASE_URL to a Supabase pooler connection
string (see DEPLOY.md). Any Postgres works the same way.
Both backends are used through the same call shape: `with connect() as conn: conn.execute(sql, params)`,
written with `?` placeholders.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import psycopg

DB_PATH = Path(__file__).parent / "leads.db"
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

SQLITE_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS audits (
      id TEXT PRIMARY KEY,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      filename TEXT NOT NULL,
      pages INTEGER NOT NULL,
      scanned_pages INTEGER NOT NULL,
      score INTEGER NOT NULL,
      quote_low REAL NOT NULL,
      quote_high REAL NOT NULL,
      failed_checks TEXT NOT NULL,
      result TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS leads (
      id INTEGER PRIMARY KEY,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      audit_id TEXT NOT NULL REFERENCES audits(id),
      name TEXT NOT NULL,
      email TEXT NOT NULL,
      organization TEXT NOT NULL,
      message TEXT NOT NULL DEFAULT ''
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS leads_audit_email ON leads(audit_id, email)",
]

POSTGRES_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS audits (
      id TEXT PRIMARY KEY,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      filename TEXT NOT NULL,
      pages INTEGER NOT NULL CHECK (pages > 0),
      scanned_pages INTEGER NOT NULL CHECK (scanned_pages >= 0),
      score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
      quote_low NUMERIC(10, 2) NOT NULL,
      quote_high NUMERIC(10, 2) NOT NULL,
      failed_checks TEXT NOT NULL,
      result TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS leads (
      id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      audit_id TEXT NOT NULL REFERENCES audits(id),
      name TEXT NOT NULL,
      email TEXT NOT NULL,
      organization TEXT NOT NULL,
      message TEXT NOT NULL DEFAULT ''
    )""",
    # Leading audit_id also serves the foreign-key lookups.
    "CREATE UNIQUE INDEX IF NOT EXISTS leads_audit_email ON leads(audit_id, email)",
    "CREATE INDEX IF NOT EXISTS leads_created_at ON leads(created_at DESC)",
    # Supabase can expose tables in `public` to its anon role through the Data API. RLS with no policies
    # hides every row from those roles; the app connects as the tables' owner, which RLS doesn't restrict.
    "ALTER TABLE audits ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE leads ENABLE ROW LEVEL SECURITY",
]

LEADS_QUERY = """
SELECT l.created_at, l.name, l.email, l.organization, a.filename, a.pages, a.scanned_pages,
       a.score, a.quote_low, a.quote_high, l.message, l.audit_id
FROM leads l JOIN audits a ON a.id = l.audit_id
ORDER BY l.created_at DESC, l.id DESC
"""


class _Postgres:
    """psycopg in the sqlite3 shape the app uses: execute(sql with ?, params) returns a cursor."""

    def __init__(self, conn: psycopg.Connection):
        self._conn = conn

    def execute(self, sql: str, params: tuple | list = ()):
        # ponytail: plain '?' -> '%s' swap; holds while no SQL text contains a literal '?'
        return self._conn.execute(sql.replace("?", "%s"), params)


@contextmanager
def connect():
    """One connection per call; commits on success, rolls back on error, always closes."""
    if DATABASE_URL:
        # ponytail: a new connection per request; add psycopg_pool when traffic needs it
        # prepare_threshold=None: Supabase's transaction pooler (port 6543) can't hold prepared statements.
        with psycopg.connect(DATABASE_URL, connect_timeout=10, prepare_threshold=None) as conn:
            yield _Postgres(conn)
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            yield conn
    finally:
        conn.close()


def migrate() -> None:
    with connect() as conn:
        for statement in POSTGRES_SCHEMA if DATABASE_URL else SQLITE_SCHEMA:
            conn.execute(statement)
        if not DATABASE_URL:  # files made before shareable reports lack the column
            if "result" not in {row[1] for row in conn.execute("PRAGMA table_info(audits)")}:
                conn.execute("ALTER TABLE audits ADD COLUMN result TEXT")
