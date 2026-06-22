import sqlite3
import json
from datetime import datetime
from typing import Optional
from loguru import logger

DB_PATH = "./data/voxbr.db"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the database and create tables if they don't exist."""
    import os
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transcriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'pt',
                transcript TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                key_points TEXT NOT NULL DEFAULT '[]',
                duration_seconds REAL NOT NULL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'processing',
                error_message TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    logger.info(f"Database initialized at {DB_PATH}")


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if isinstance(d.get("key_points"), str):
        try:
            d["key_points"] = json.loads(d["key_points"])
        except (json.JSONDecodeError, TypeError):
            d["key_points"] = []
    return d


def create_record(filename: str, language: str) -> dict:
    """Create a new transcription record with status 'processing'."""
    created_at = datetime.now().isoformat()
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO transcriptions (filename, language, transcript, summary, key_points, duration_seconds, status, created_at)
            VALUES (?, ?, '', '', '[]', 0.0, 'processing', ?)
            """,
            (filename, language, created_at),
        )
        conn.commit()
        record_id = cursor.lastrowid

    logger.info(f"Created transcription record id={record_id} for file={filename}")
    return get_by_id(record_id)


def update_record(
    record_id: int,
    transcript: Optional[str] = None,
    summary: Optional[str] = None,
    key_points: Optional[list] = None,
    duration_seconds: Optional[float] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Optional[dict]:
    """Update an existing transcription record."""
    fields = []
    values = []

    if transcript is not None:
        fields.append("transcript = ?")
        values.append(transcript)
    if summary is not None:
        fields.append("summary = ?")
        values.append(summary)
    if key_points is not None:
        fields.append("key_points = ?")
        values.append(json.dumps(key_points, ensure_ascii=False))
    if duration_seconds is not None:
        fields.append("duration_seconds = ?")
        values.append(duration_seconds)
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if error_message is not None:
        fields.append("error_message = ?")
        values.append(error_message)

    if not fields:
        return get_by_id(record_id)

    values.append(record_id)
    query = f"UPDATE transcriptions SET {', '.join(fields)} WHERE id = ?"

    with _get_connection() as conn:
        conn.execute(query, values)
        conn.commit()

    logger.info(f"Updated transcription record id={record_id}, status={status}")
    return get_by_id(record_id)


def get_all() -> list[dict]:
    """Return all transcription records ordered by created_at descending."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM transcriptions ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_by_id(record_id: int) -> Optional[dict]:
    """Return a single transcription record by ID."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM transcriptions WHERE id = ?", (record_id,)
        ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def delete_by_id(record_id: int) -> bool:
    """Delete a transcription record by ID. Returns True if deleted."""
    with _get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM transcriptions WHERE id = ?", (record_id,)
        )
        conn.commit()
        deleted = cursor.rowcount > 0

    if deleted:
        logger.info(f"Deleted transcription record id={record_id}")
    else:
        logger.warning(f"Attempted to delete non-existent record id={record_id}")
    return deleted
