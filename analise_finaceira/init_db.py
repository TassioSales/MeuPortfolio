import os
import sqlite3
from pathlib import Path
from logger import get_logger

logger = get_logger("init_db")

def init_db():
    """Inicializa o banco de dados criando a tabela de histórico de uploads se ela não existir."""
    # Caminho para o banco de dados
    db_path = os.path.join(os.path.dirname(__file__), 'financas.db')
    
    logger.info(f"Inicializando banco de dados em: {db_path}")
    
    try:
        # Conecta ao banco de dados (ou cria se não existir)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Cria a tabela de histórico de uploads se não existir
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_arquivo TEXT NOT NULL,
            data_upload TEXT NOT NULL,
            data_conclusao TEXT,
            total_registros INTEGER DEFAULT 0,
            registros_inseridos INTEGER DEFAULT 0,
            registros_atualizados INTEGER DEFAULT 0,
            registros_com_erro INTEGER DEFAULT 0,
            status TEXT NOT NULL,
            mensagem TEXT
        )
        ''')
        
        # Salva as alterações
        conn.commit()
        logger.info("Tabela 'uploads_historico' criada com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro ao inicializar o banco de dados: {e}", exc_info=True)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    logger.info("Iniciando script init_db...")
    init_db()
