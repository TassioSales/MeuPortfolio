from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent.parent / "data" / "panorama.db")))

_DDL = """
CREATE TABLE IF NOT EXISTS macro_indicators (
  indicator TEXT PRIMARY KEY,
  value REAL NOT NULL,
  unit TEXT DEFAULT '',
  ref_date TEXT DEFAULT '',
  updated_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS indicator_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  indicator TEXT NOT NULL,
  value REAL NOT NULL,
  date TEXT NOT NULL,
  UNIQUE(indicator, date)
);

CREATE TABLE IF NOT EXISTS market_snapshot (
  symbol TEXT PRIMARY KEY,
  name TEXT DEFAULT '',
  price REAL DEFAULT 0,
  change_pct REAL DEFAULT 0,
  volume REAL DEFAULT 0,
  market_cap REAL DEFAULT 0,
  updated_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS regional_indicators (
  uf TEXT NOT NULL,
  year INTEGER NOT NULL,
  state_name TEXT DEFAULT '',
  region TEXT DEFAULT '',
  pib REAL DEFAULT 0,
  pib_per_capita REAL DEFAULT 0,
  population INTEGER DEFAULT 0,
  desemprego REAL DEFAULT 0,
  PRIMARY KEY (uf, year)
);

CREATE TABLE IF NOT EXISTS pipeline_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_at TEXT NOT NULL,
  status TEXT NOT NULL,
  message TEXT DEFAULT '',
  duration_s REAL DEFAULT 0
);
"""


def get_conn() -> sqlite3.Connection:
    """Abre conexão com o banco SQLite em modo WAL e cria as tabelas se necessário."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_DDL)
    conn.commit()
    return conn


def upsert_macro(
    conn: sqlite3.Connection,
    indicator: str,
    value: float,
    unit: str,
    ref_date: str,
) -> None:
    updated_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT OR REPLACE INTO macro_indicators (indicator, value, unit, ref_date, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (indicator, value, unit, ref_date, updated_at),
    )
    conn.commit()


def insert_history(
    conn: sqlite3.Connection,
    indicator: str,
    value: float,
    date: str,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO indicator_history (indicator, value, date)
        VALUES (?, ?, ?)
        """,
        (indicator, value, date),
    )
    conn.commit()


def upsert_market(
    conn: sqlite3.Connection,
    symbol: str,
    name: str,
    price: float,
    change_pct: float,
    volume: float,
    market_cap: float,
) -> None:
    updated_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT OR REPLACE INTO market_snapshot
          (symbol, name, price, change_pct, volume, market_cap, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (symbol, name, price, change_pct, volume, market_cap, updated_at),
    )
    conn.commit()


def upsert_regional(
    conn: sqlite3.Connection,
    uf: str,
    year: int,
    state_name: str,
    region: str,
    pib: float,
    pib_per_capita: float,
    population: int,
    desemprego: float,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO regional_indicators
          (uf, year, state_name, region, pib, pib_per_capita, population, desemprego)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (uf, year, state_name, region, pib, pib_per_capita, population, desemprego),
    )
    conn.commit()


def log_run(
    conn: sqlite3.Connection,
    status: str,
    message: str,
    duration_s: float,
) -> None:
    run_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO pipeline_log (run_at, status, message, duration_s)
        VALUES (?, ?, ?, ?)
        """,
        (run_at, status, message, duration_s),
    )
    conn.commit()
