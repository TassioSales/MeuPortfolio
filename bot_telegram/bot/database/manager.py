import os
import sqlite3
from loguru import logger


class DatabaseManager:
    """Manages SQLite database for the Telegram bot."""

    def __init__(self, db_path: str = "data/bot.db") -> None:
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def setup(self) -> None:
        """Create tables and ensure the DB directory exists."""
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gastos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    descricao TEXT NOT NULL,
                    valor REAL NOT NULL,
                    categoria TEXT DEFAULT 'outros',
                    data TEXT DEFAULT (date('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    texto TEXT NOT NULL,
                    criado_em TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.commit()
        logger.info(f"Banco de dados configurado em: {self.db_path}")

    # ------------------------------------------------------------------
    # Gastos
    # ------------------------------------------------------------------

    def adicionar_gasto(
        self,
        user_id: int,
        descricao: str,
        valor: float,
        categoria: str = "outros",
    ) -> int:
        """Insert an expense and return its new id."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO gastos (user_id, descricao, valor, categoria) VALUES (?, ?, ?, ?)",
                (user_id, descricao, valor, categoria),
            )
            conn.commit()
            new_id: int = cursor.lastrowid  # type: ignore[assignment]
            logger.debug(f"Gasto adicionado: id={new_id}, user={user_id}, valor={valor}")
            return new_id

    def listar_gastos(self, user_id: int, mes: str | None = None) -> list[dict]:
        """Return expenses for a user, optionally filtered by month (YYYY-MM)."""
        with self._get_connection() as conn:
            if mes:
                rows = conn.execute(
                    "SELECT * FROM gastos WHERE user_id = ? AND strftime('%Y-%m', data) = ? ORDER BY data DESC",
                    (user_id, mes),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM gastos WHERE user_id = ? ORDER BY data DESC",
                    (user_id,),
                ).fetchall()
            return [dict(row) for row in rows]

    def total_gastos(self, user_id: int, mes: str | None = None) -> float:
        """Return the sum of expenses for a user, optionally filtered by month."""
        with self._get_connection() as conn:
            if mes:
                row = conn.execute(
                    "SELECT COALESCE(SUM(valor), 0) as total FROM gastos WHERE user_id = ? AND strftime('%Y-%m', data) = ?",
                    (user_id, mes),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COALESCE(SUM(valor), 0) as total FROM gastos WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
            return float(row["total"])

    # ------------------------------------------------------------------
    # Notas
    # ------------------------------------------------------------------

    def adicionar_nota(self, user_id: int, texto: str) -> int:
        """Insert a note and return its new id."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO notas (user_id, texto) VALUES (?, ?)",
                (user_id, texto),
            )
            conn.commit()
            new_id: int = cursor.lastrowid  # type: ignore[assignment]
            logger.debug(f"Nota adicionada: id={new_id}, user={user_id}")
            return new_id

    def listar_notas(self, user_id: int) -> list[dict]:
        """Return all notes for a user."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM notas WHERE user_id = ? ORDER BY criado_em DESC",
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def apagar_nota(self, user_id: int, nota_id: int) -> bool:
        """Delete a note by id (must belong to user). Returns True if deleted."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM notas WHERE id = ? AND user_id = ?",
                (nota_id, user_id),
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.debug(f"Nota {nota_id} apagada para user={user_id}")
            return deleted
