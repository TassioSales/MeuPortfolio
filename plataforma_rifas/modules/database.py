from __future__ import annotations

import sqlite3
from pathlib import Path

# Diretórios
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "rifas.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    _create_tables(conn)
    return conn

def _create_tables(conn: sqlite3.Connection) -> None:
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
    # Garantir coluna opcional 'contato' em vendas
    try:
        cols = [r[1] for r in cur.execute("PRAGMA table_info(vendas)").fetchall()]
        if "contato" not in cols:
            cur.execute("ALTER TABLE vendas ADD COLUMN contato TEXT")
    except Exception:
        pass
    # Garantir coluna owner_id em rifas
    try:
        cols = [r[1] for r in cur.execute("PRAGMA table_info(rifas)").fetchall()]
        if "owner_id" not in cols:
            cur.execute("ALTER TABLE rifas ADD COLUMN owner_id INTEGER")
    except Exception:
        pass
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
    # Índices úteis
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vendas_rifa ON vendas(rifa_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reservas_rifa ON reservas(rifa_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rifas_owner ON rifas(owner_id)")
    conn.commit()