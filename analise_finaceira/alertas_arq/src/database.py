import os
import sys
import sqlite3
from pathlib import Path

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function, RequestContext

# Configura o logger para este módulo
logger = get_logger("alertas.database")

# Caminho para o banco de dados
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'banco')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'alertas.db')

@log_function(logger_instance=logger, level="DEBUG")
def get_connection():
    """Retorna uma conexão com o banco de dados"""
    return sqlite3.connect(DB_PATH)

@log_function(logger_instance=logger, level="INFO")
def create_tables():
    """Cria as tabelas necessárias no banco de dados"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Tabela de alertas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            valor_referencia REAL,
            categoria TEXT,
            data_inicio TEXT NOT NULL,
            data_fim TEXT,
            frequencia TEXT NOT NULL,
            notificacao_sistema INTEGER NOT NULL DEFAULT 1,
            notificacao_email INTEGER NOT NULL DEFAULT 1,
            prioridade TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            data_criacao TEXT NOT NULL,
            data_atualizacao TEXT,
            usuario_id INTEGER
        )
        ''')
        
        # Tabela de histórico de disparos de alertas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alertas_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alerta_id INTEGER NOT NULL,
            data_disparo TEXT NOT NULL,
            mensagem TEXT,
            status TEXT NOT NULL,
            FOREIGN KEY (alerta_id) REFERENCES alertas (id)
        )
        ''')
        
        # Índices para melhorar desempenho
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alertas_ativo ON alertas(ativo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alertas_data_inicio ON alertas(data_inicio)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alertas_historico_alerta_id ON alertas_historico(alerta_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alertas_historico_data_disparo ON alertas_historico(data_disparo)')
        
        conn.commit()
        logger.info("Tabelas criadas com sucesso no banco de dados.")
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao criar tabelas: {e}")
        raise
    finally:
        conn.close()

@log_function(logger_instance=logger, level="INFO")
def check_tables():
    """Verifica se as tabelas existem e estão com a estrutura correta"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        if 'alertas' not in table_names or 'alertas_historico' not in table_names:
            logger.warning("Algumas tabelas não foram encontradas. Criando tabelas...")
            create_tables()
            return
            
        # Verifica a estrutura da tabela alertas
        cursor.execute("PRAGMA table_info(alertas)")
        columns = [column[1] for column in cursor.fetchall()]
        required_columns = [
            'id', 'tipo', 'descricao', 'valor_referencia', 'categoria',
            'data_inicio', 'data_fim', 'frequencia', 'notificacao_sistema',
            'notificacao_email', 'prioridade', 'ativo', 'data_criacao',
            'data_atualizacao', 'usuario_id'
        ]
        
        for column in required_columns:
            if column not in columns:
                logger.warning(f"Coluna {column} não encontrada na tabela alertas. Recriando tabelas...")
                create_tables()
                break
                
        logger.info("Todas as tabelas estão com a estrutura correta.")
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao verificar tabelas: {e}")
        raise
    finally:
        conn.close()

# Cria as tabelas quando o módulo é importado
if __name__ != '__main__':
    check_tables()
