from __future__ import annotations

import sqlite3
from pathlib import Path

from logger import get_logger

logger = get_logger(__name__)

# Diretórios
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.success(f"Diretório de dados criado ou verificado com sucesso: {DATA_DIR}")
except Exception as e:
    logger.critical(f"Falha ao criar/verificar diretório de dados: {DATA_DIR}", exception=e)
    raise RuntimeError(f"Erro ao criar diretório de dados: {e}") from e

DB_PATH = DATA_DIR / "rifas.db"

def get_connection() -> sqlite3.Connection:
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        _create_tables(conn)
        logger.success("Conexão com banco de dados estabelecida com sucesso")
        return conn
    except sqlite3.Error as e:
        logger.critical("Erro ao conectar ao banco de dados", exception=e)
        raise RuntimeError(f"Erro de conexão com DB: {e}") from e

def _create_tables(conn: sqlite3.Connection) -> None:
    try:
        cur = conn.cursor()
        # Users
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        logger.debug("Tabela 'users' criada ou verificada")
        # Login attempts for rate limiting
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS login_attempts (
                email TEXT PRIMARY KEY,
                fail_count INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT
            );
            """
        )
        logger.debug("Tabela 'login_attempts' criada ou verificada")
        # Rifas
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS rifas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                valor_numero REAL NOT NULL,
                total_numeros INTEGER NOT NULL,
                sorteio_realizado INTEGER DEFAULT 0,
                sorteio_numero INTEGER,
                sorteio_comprador TEXT,
                config_json TEXT DEFAULT '{}',
                owner_id INTEGER,
                FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE SET NULL
            );
            """
        )
        logger.debug("Tabela 'rifas' criada ou verificada")
        # Vendas
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rifa_id INTEGER NOT NULL,
                numero INTEGER NOT NULL,
                comprador TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(rifa_id) REFERENCES rifas(id) ON DELETE CASCADE,
                UNIQUE(rifa_id, numero)
            );
            """
        )
        logger.debug("Tabela 'vendas' criada ou verificada")
        # Garantir coluna opcional 'contato' em vendas
        try:
            cols = [r[1] for r in cur.execute("PRAGMA table_info(vendas)").fetchall()]
            if "contato" not in cols:
                cur.execute("ALTER TABLE vendas ADD COLUMN contato TEXT")
                logger.success("Coluna 'contato' adicionada à tabela vendas")
        except sqlite3.Error as e:
            logger.warning("Falha ao adicionar coluna 'contato' à tabela vendas (pode já existir)", exception=e)
        # Garantir coluna owner_id em rifas
        try:
            cols = [r[1] for r in cur.execute("PRAGMA table_info(rifas)").fetchall()]
            if "owner_id" not in cols:
                cur.execute("ALTER TABLE rifas ADD COLUMN owner_id INTEGER")
                logger.success("Coluna 'owner_id' adicionada à tabela rifas")
        except sqlite3.Error as e:
            logger.warning("Falha ao adicionar coluna 'owner_id' à tabela rifas (pode já existir)", exception=e)
        # Reservas
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reservas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rifa_id INTEGER NOT NULL,
                numero INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(rifa_id) REFERENCES rifas(id) ON DELETE CASCADE,
                UNIQUE(rifa_id, numero)
            );
            """
        )
        logger.debug("Tabela 'reservas' criada ou verificada")
        # Índices úteis
        cur.execute("CREATE INDEX IF NOT EXISTS idx_vendas_rifa ON vendas(rifa_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reservas_rifa ON reservas(rifa_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rifas_owner ON rifas(owner_id)")
        logger.debug("Índices criados ou verificados")
        conn.commit()
        logger.success("Tabelas e índices do banco de dados criados/verificados com sucesso")
    except sqlite3.Error as e:
        logger.critical("Erro ao criar/verificar tabelas no banco de dados", exception=e)
        raise RuntimeError(f"Erro na criação de tabelas: {e}") from e
    except Exception as e:
        logger.critical("Erro inesperado ao criar/verificar tabelas", exception=e)
        raise