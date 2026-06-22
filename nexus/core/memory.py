"""SQLite-backed conversation memory for Nexus."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger


class Memory:
    """Persistent conversation memory backed by SQLite.

    Database lives at ``~/.nexus/memory.db``. The directory is created
    automatically on first use.
    """

    _DB_PATH = Path.home() / ".nexus" / "memory.db"

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or self._DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._setup_schema()
        logger.info("Memory inicializada em {}", self._db_path)

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _setup_schema(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    title      TEXT    NOT NULL DEFAULT 'Nova sessão',
                    created_at TEXT    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id   INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    role         TEXT    NOT NULL,
                    content      TEXT,
                    tool_calls   TEXT,
                    tool_call_id TEXT,
                    name         TEXT,
                    created_at   TEXT    NOT NULL
                );
                """
            )

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(self, title: str = "Nova sessão") -> int:
        """Insert a new session and return its id."""
        now = _utcnow()
        cursor = self._conn.execute(
            "INSERT INTO sessions (title, created_at) VALUES (?, ?)",
            (title, now),
        )
        self._conn.commit()
        session_id = cursor.lastrowid
        logger.debug("Sessão criada | id={} title={}", session_id, title)
        return session_id  # type: ignore[return-value]

    def update_session_title(self, session_id: int, title: str) -> None:
        """Update the title of an existing session."""
        self._conn.execute(
            "UPDATE sessions SET title = ? WHERE id = ?",
            (title, session_id),
        )
        self._conn.commit()
        logger.debug("Título da sessão {} atualizado para '{}'", session_id, title)

    def get_sessions(self) -> list[dict]:
        """Return the 20 most recent sessions, newest first."""
        rows = self._conn.execute(
            "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Message helpers
    # ------------------------------------------------------------------

    def add_user_message(self, session_id: int, content: str) -> None:
        """Persist a user message."""
        self._insert_message(session_id=session_id, role="user", content=content)

    def add_assistant_message(
        self,
        session_id: int,
        content: str,
        tool_calls: list | None = None,
    ) -> None:
        """Persist an assistant message, optionally with tool call data."""
        tool_calls_json: str | None = None
        if tool_calls:
            tool_calls_json = json.dumps(tool_calls, ensure_ascii=False)
        self._insert_message(
            session_id=session_id,
            role="assistant",
            content=content,
            tool_calls=tool_calls_json,
        )

    def add_tool_result(
        self,
        session_id: int,
        tool_call_id: str,
        tool_name: str,
        content: str,
    ) -> None:
        """Persist a tool result message."""
        self._insert_message(
            session_id=session_id,
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name,
        )

    def get_messages(self, session_id: int) -> list[dict]:
        """Return all messages for a session in Mistral API format."""
        rows = self._conn.execute(
            """
            SELECT role, content, tool_calls, tool_call_id, name
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()

        result: list[dict] = []
        for row in rows:
            msg: dict = {"role": row["role"]}

            # Content may be None for pure tool-call assistant messages.
            if row["content"] is not None:
                msg["content"] = row["content"]

            if row["tool_calls"]:
                msg["tool_calls"] = json.loads(row["tool_calls"])

            if row["tool_call_id"]:
                msg["tool_call_id"] = row["tool_call_id"]

            if row["name"]:
                msg["name"] = row["name"]

            result.append(msg)

        return result

    def clear_session(self, session_id: int) -> None:
        """Delete all messages belonging to a session."""
        self._conn.execute(
            "DELETE FROM messages WHERE session_id = ?", (session_id,)
        )
        self._conn.commit()
        logger.debug("Mensagens da sessão {} removidas", session_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _insert_message(
        self,
        *,
        session_id: int,
        role: str,
        content: str | None = None,
        tool_calls: str | None = None,
        tool_call_id: str | None = None,
        name: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO messages
                (session_id, role, content, tool_calls, tool_call_id, name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, role, content, tool_calls, tool_call_id, name, _utcnow()),
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()
