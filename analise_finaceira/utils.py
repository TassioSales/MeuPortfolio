import sqlite3
import os
from flask import current_app
from logger import get_logger

logger = get_logger("utils")

def get_db_connection():
    db_path = current_app.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_dashboard_highlights():
    conn = get_db_connection()
    try:
        total_transacoes = conn.execute('SELECT COUNT(*) FROM transacoes').fetchone()[0]
        total_alertas_ativos = conn.execute('SELECT COUNT(*) FROM alertas_financas WHERE ativo = 1').fetchone()[0]
        total_categorias = conn.execute('SELECT COUNT(DISTINCT categoria) FROM transacoes').fetchone()[0]
    except Exception as e:
        logger.error(f"Erro ao buscar destaques do dashboard: {e}", exc_info=True)
        total_transacoes = total_alertas_ativos = total_categorias = 0
    finally:
        conn.close()
    return total_transacoes, total_alertas_ativos, total_categorias
