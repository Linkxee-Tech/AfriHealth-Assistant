"""
Local SQLite persistence layer for AfriHealth Assistant.

Tables:
  - chat_sessions     : archived conversation sessions
  - chat_messages     : individual messages per session
  - health_logs       : health metric entries (with notes field, per data model spec)
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "afrihealth.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at  TEXT NOT NULL,
                topic       TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                source      TEXT,
                msg_time    TEXT,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS health_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_type TEXT NOT NULL,
                value       TEXT NOT NULL,
                unit        TEXT,
                notes       TEXT,
                logged_at   TEXT NOT NULL
            )
        """)


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
def save_session(messages, session_id=None):
    if not messages:
        return None
    topic = messages[0]["content"][:80]
    with get_conn() as conn:
        if session_id:
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            conn.execute("UPDATE chat_sessions SET topic = ? WHERE id = ?", (topic, session_id))
        else:
            cur = conn.execute(
                "INSERT INTO chat_sessions (started_at, topic) VALUES (?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M"), topic),
            )
            session_id = cur.lastrowid
        for m in messages:
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, source, msg_time) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, m["role"], m["content"], m.get("source"), m.get("time")),
            )
    return session_id


def list_sessions(limit=20):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.id, s.started_at, s.topic, COUNT(m.id) as msg_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY s.id DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def load_session(session_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, source, msg_time FROM chat_messages "
            "WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"], "source": r["source"], "time": r["msg_time"]}
            for r in rows]


def delete_session(session_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))


# ---------------------------------------------------------------------------
# Health metric logging  (notes field added per data model spec)
# ---------------------------------------------------------------------------
def add_health_entry(metric_type, value, unit, notes=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO health_logs (metric_type, value, unit, notes, logged_at) VALUES (?, ?, ?, ?, ?)",
            (metric_type, value, unit, notes, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )


def get_health_entries(metric_type=None, limit=200):
    with get_conn() as conn:
        if metric_type:
            rows = conn.execute(
                "SELECT * FROM health_logs WHERE metric_type = ? ORDER BY id DESC LIMIT ?",
                (metric_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM health_logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


def delete_health_entry(entry_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM health_logs WHERE id = ?", (entry_id,))
