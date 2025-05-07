import os
import sqlite3
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Caminho para o banco de dados
DB_PATH = os.path.join(os.path.dirname(__file__), 'banco', 'financas.db')

def check_column_exists(conn, table_name, column_name):
    """Verifica se uma coluna existe em uma tabela"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns

def update_database_schema():
    """Atualiza o esquema do banco de dados"""
    try:
        # Garante que o diretório do banco de dados existe
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Conecta ao banco de dados
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        logger.info(f"Conectado ao banco de dados em {DB_PATH}")
        
        # Verifica se a tabela de histórico de uploads existe
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_arquivo TEXT NOT NULL,
            data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_registros INTEGER DEFAULT 0,
            registros_inseridos INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pendente',
            mensagem TEXT
        )
        """)
        logger.info("Tabela uploads_historico verificada/criada")
        
        # Verifica se a tabela de transações existe
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT,
            data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            upload_id INTEGER
        )
        """)
        logger.info("Tabela transacoes verificada/criada")
        
        # Verifica se a coluna upload_id existe na tabela transacoes
        if not check_column_exists(conn, 'transacoes', 'upload_id'):
            logger.info("Adicionando coluna upload_id à tabela transacoes")
            cursor.execute('''
            ALTER TABLE transacoes
            ADD COLUMN upload_id INTEGER
            ''')
            logger.info("Coluna upload_id adicionada com sucesso")
        
        # Tenta adicionar a chave estrangeira (pode falhar se já existir)
        try:
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_transacoes_upload_id ON transacoes(upload_id)
            ''')
            logger.info("Índice para upload_id verificado/criado")
            
            # Tenta adicionar a chave estrangeira
            cursor.execute('''
            PRAGMA foreign_keys = OFF;
            ''')
            cursor.execute('''
            PRAGMA foreign_key_check;
            ''')
            cursor.execute(f'''
            PRAGMA foreign_key_list(transacoes);
            ''')
            
            # Verifica se a chave estrangeira já existe
            cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type = 'table' AND 
                  sql LIKE '%FOREIGN KEY%(upload_id)%REFERENCES%uploads_historico%';
            ''')
            
            if not cursor.fetchone():
                # Cria uma tabela temporária sem a restrição
                cursor.execute('''
                CREATE TABLE transacoes_temp AS SELECT * FROM transacoes;
                ''')
                
                # Remove a tabela original
                cursor.execute('''
                DROP TABLE transacoes;
                ''')
                
                # Recria a tabela com a restrição de chave estrangeira
                cursor.execute('''
                CREATE TABLE transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data DATE NOT NULL,
                    descricao TEXT NOT NULL,
                    valor REAL NOT NULL,
                    tipo TEXT NOT NULL,
                    categoria TEXT,
                    data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    upload_id INTEGER,
                    FOREIGN KEY (upload_id) REFERENCES uploads_historico(id),
                    UNIQUE(data, descricao, valor, tipo)
                )
                ''')
                
                # Copia os dados de volta
                cursor.execute('''
                INSERT INTO transacoes 
                SELECT * FROM transacoes_temp;
                ''')
                
                # Remove a tabela temporária
                cursor.execute('''
                DROP TABLE transacoes_temp;
                ''')
                
                logger.info("Chave estrangeira adicionada com sucesso")
            
            cursor.execute('''
            PRAGMA foreign_keys = ON;
            ''')
            
        except sqlite3.Error as e:
            logger.warning(f"Não foi possível adicionar a chave estrangeira: {e}")
            logger.warning("A aplicação continuará sem a restrição de chave estrangeira")
        
        conn.commit()
        logger.info("Esquema do banco de dados atualizado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao atualizar o esquema do banco de dados: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("Atualizando esquema do banco de dados...")
    update_database_schema()
    print("Concluído!")
