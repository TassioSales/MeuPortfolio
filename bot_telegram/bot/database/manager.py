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
                    data TEXT DEFAULT (date('now', 'localtime'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    texto TEXT NOT NULL,
                    criado_em TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metas (
                    user_id INTEGER PRIMARY KEY,
                    valor REAL NOT NULL,
                    atualizado_em TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)
            conn.commit()
        logger.info(f"Banco de dados configurado em: {self.db_path}")

    # ------------------------------------------------------------------
    # Gastos
    # ------------------------------------------------------------------

    def adicionar_gasto(self, user_id: int, descricao: str, valor: float, categoria: str = "outros") -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO gastos (user_id, descricao, valor, categoria) VALUES (?, ?, ?, ?)",
                (user_id, descricao, valor, categoria),
            )
            conn.commit()
            new_id: int = cursor.lastrowid  # type: ignore[assignment]
            logger.debug(f"Gasto adicionado: id={new_id}, user={user_id}, valor={valor}")
            return new_id

    def apagar_gasto(self, user_id: int, gasto_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM gastos WHERE id = ? AND user_id = ?",
                (gasto_id, user_id),
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.debug(f"Gasto {gasto_id} apagado para user={user_id}")
            return deleted

    def listar_gastos(self, user_id: int, mes: str | None = None) -> list[dict]:
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

    def gastos_por_categoria(self, user_id: int, mes: str | None = None) -> list[dict]:
        with self._get_connection() as conn:
            if mes:
                rows = conn.execute(
                    """SELECT categoria, COUNT(*) as qtd, SUM(valor) as total
                       FROM gastos WHERE user_id = ? AND strftime('%Y-%m', data) = ?
                       GROUP BY categoria ORDER BY total DESC""",
                    (user_id, mes),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT categoria, COUNT(*) as qtd, SUM(valor) as total
                       FROM gastos WHERE user_id = ?
                       GROUP BY categoria ORDER BY total DESC""",
                    (user_id,),
                ).fetchall()
            return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Notas
    # ------------------------------------------------------------------

    def adicionar_nota(self, user_id: int, texto: str) -> int:
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
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM notas WHERE user_id = ? ORDER BY criado_em DESC",
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def obter_nota(self, user_id: int, nota_id: int) -> dict | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM notas WHERE id = ? AND user_id = ?",
                (nota_id, user_id),
            ).fetchone()
            return dict(row) if row else None

    def apagar_nota(self, user_id: int, nota_id: int) -> bool:
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

    # ------------------------------------------------------------------
    # Metas
    # ------------------------------------------------------------------

    def definir_meta(self, user_id: int, valor: float) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO metas (user_id, valor) VALUES (?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET valor = excluded.valor,
                   atualizado_em = datetime('now', 'localtime')""",
                (user_id, valor),
            )
            conn.commit()
            logger.debug(f"Meta definida: user={user_id}, valor={valor}")

    def obter_meta(self, user_id: int) -> float | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT valor FROM metas WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return float(row["valor"]) if row else None
