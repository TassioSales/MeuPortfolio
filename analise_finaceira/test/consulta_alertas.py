import sqlite3
import os
from logger import get_logger

logger = get_logger("consulta_alertas")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'banco', 'financas.db')

def consulta_alertas():
    if not os.path.exists(DB_PATH):
        logger.error(f"Banco de dados não encontrado: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, descricao, ativo, data_inicio, data_fim FROM alertas_financas')
        rows = cursor.fetchall()
        if not rows:
            logger.info("Nenhum alerta encontrado na tabela.")
        else:
            logger.info(f"Total de registros encontrados: {len(rows)}")
            logger.info(f"{'ID':<5} {'ativo':<5} {'Descrição':<30} {'Início':<12} {'Fim':<12}")
            logger.info('-'*70)
            for row in rows:
                logger.info(f"{row[0]:<5} {row[2]:<5} {row[1]:<30} {row[3]:<12} {row[4]:<12}")
    except Exception as e:
        logger.error(f"Erro ao consultar registros: {e}", exc_info=True)
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Iniciando consulta de alertas...")
    consulta_alertas()
