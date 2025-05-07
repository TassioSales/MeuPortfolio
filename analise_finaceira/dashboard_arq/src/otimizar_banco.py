import sqlite3
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger

# Configura o logger para este módulo
otimizacao_logger = get_logger("dashboard.otimizar_banco")

def criar_indices():
    """Cria índices para melhorar o desempenho das consultas"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'banco', 'financas.db')
    
    try:
        otimizacao_logger.info(f"Conectando ao banco de dados: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se a tabela transacoes existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transacoes'")
        if not cursor.fetchone():
            otimizacao_logger.warning("Tabela 'transacoes' não encontrada no banco de dados")
            return False
        
        otimizacao_logger.info("Criando índices para otimização...")
        
        # Índice para consultas por tipo de transação
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transacoes_tipo 
        ON transacoes(tipo);
        """)
        otimizacao_logger.debug("Índice para tipo de transação criado/verificado")
        
        # Índice para consultas por data
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transacoes_data 
        ON transacoes(data);
        """)
        otimizacao_logger.debug("Índice para data de transação criado/verificado")
        
        # Índice para consultas por categoria
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transacoes_categoria 
        ON transacoes(categoria);
        """)
        otimizacao_logger.debug("Índice para categoria de transação criado/verificado")
        
        # Índice composto para consultas frequentes
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transacoes_tipo_data 
        ON transacoes(tipo, data);
        """)
        otimizacao_logger.debug("Índice composto para tipo e data criado/verificado")
        
        conn.commit()
        conn.close()
        otimizacao_logger.info("Índices criados/verificados com sucesso")
        return True
        
    except sqlite3.Error as e:
        otimizacao_logger.error(f"Erro ao criar índices: {e}", exc_info=True)
        return False
    except Exception as e:
        otimizacao_logger.error(f"Erro inesperado ao otimizar banco: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    otimizacao_logger.info("Iniciando otimização do banco de dados")
    if criar_indices():
        otimizacao_logger.info("Otimização concluída com sucesso")
    else:
        otimizacao_logger.error("Falha na otimização do banco de dados")
