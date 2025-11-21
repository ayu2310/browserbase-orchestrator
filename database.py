"""SQLite helpers for persisting deterministic flowState + execution logs."""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

from config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    """Ensure required tables exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS flow_states (
            cache_key TEXT PRIMARY KEY,
            prompt TEXT NOT NULL,
            flow_state TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key TEXT NOT NULL,
            prompt TEXT NOT NULL,
            summary TEXT,
            history TEXT,
            status TEXT NOT NULL DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_flow_state(cache_key: str, prompt: str, flow_state: Dict[str, Any]) -> None:
    """Persist the latest flowState snapshot."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO flow_states (cache_key, prompt, flow_state)
        VALUES (?, ?, ?)
        ON CONFLICT(cache_key)
        DO UPDATE SET
            prompt = excluded.prompt,
            flow_state = excluded.flow_state,
            updated_at = CURRENT_TIMESTAMP
        """,
        (cache_key, prompt, json.dumps(flow_state)),
    )
    conn.commit()
    conn.close()


def get_flow_state(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retrieve stored flowState by cache key."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flow_states WHERE cache_key = ?", (cache_key,))
    row = cursor.fetchone()
    conn.close()
    if not row:
    return None
    return {
        "cache_key": row["cache_key"],
        "prompt": row["prompt"],
        "flow_state": json.loads(row["flow_state"]),
        "updated_at": row["updated_at"],
    }


def list_flow_states(limit: int = 20) -> List[Dict[str, Any]]:
    """List cached flows for quick inspection."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT cache_key, prompt, updated_at FROM flow_states ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_flow_state(cache_key: str) -> None:
    """Remove a cached flowState."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM flow_states WHERE cache_key = ?", (cache_key,))
    conn.commit()
    conn.close()


def record_execution(
    cache_key: str,
    prompt: str,
    summary: str,
    history: List[Dict[str, Any]],
    status: str = "completed",
) -> int:
    """Persist an execution log for observability."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO executions (cache_key, prompt, summary, history, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (cache_key, prompt, summary, json.dumps(history), status),
    )
    execution_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return execution_id


def list_executions(limit: int = 20) -> List[Dict[str, Any]]:
    """Return the most recent execution summaries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, cache_key, prompt, summary, status, created_at FROM executions ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def clear_all_data() -> None:
    """Clear all flow states and executions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM flow_states")
    cursor.execute("DELETE FROM executions")
    conn.commit()
    conn.close()

