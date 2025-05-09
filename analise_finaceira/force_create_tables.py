import os
import sys
import sqlite3
from pathlib import Path
from logger import get_logger

logger = get_logger("force_create_tables")

# Adiciona o diretório raiz ao path
root_dir = str(Path(__file__).parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Importa a função de criação de tabelas
from upload_arq.src.processamento import create_tables, DB_PATH

def main():
    logger.info(f"Iniciando criação de tabelas no banco: {DB_PATH}")
    
    # Garante que o diretório do banco de dados existe
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        logger.info(f"Criando diretório do banco de dados: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)
    
    try:
        # Tenta criar as tabelas
        logger.info("Chamando a função create_tables()...")
        create_tables()
        logger.info("Tabelas criadas com sucesso!")
        
        # Verifica se as tabelas foram criadas
        logger.info("Verificando tabelas no banco de dados...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Lista todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            logger.warning("Nenhuma tabela encontrada no banco de dados.")
        else:
            logger.info(f"Tabelas encontradas ({len(tables)}):")
            for table in tables:
                logger.info(f"- {table[0]}")
                # Mostra a estrutura de cada tabela
                cursor.execute(f"PRAGMA table_info({table[0]});")
                columns = cursor.fetchall()
                logger.info(f"  Colunas ({len(columns)}):")
                for column in columns:
                    logger.info(f"  - {column[1]} ({column[2]})")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {str(e)}", exc_info=True)
    
    # input("Pressione Enter para sair...")

if __name__ == "__main__":
    logger.info("Iniciando script force_create_tables...")
    main()
