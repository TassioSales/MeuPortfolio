import os
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function, LogLevel

# Configura o logger para este módulo
logger = get_logger("upload.processamento")

# Mapeamento de variações de nomes de colunas
COLUMN_MAPPING = {
    'data': ['data', 'date', 'data_transacao', 'data_transação', 'dt', 'datahora'],
    'descricao': ['descricao', 'descrição', 'desc', 'historico', 'histórico', 'detalhes', 'descricao_transacao'],
    'valor': ['valor', 'vlr', 'vl', 'value', 'amount', 'montante'],
    'tipo': ['tipo', 'tp', 'type', 'movimentacao', 'movimentação', 'movimento'],
    'categoria': ['categoria', 'categ', 'cat', 'category', 'grupo', 'classificacao']
}

# Caminho para o banco de dados
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'banco', 'financas.db')

def normalize_column_name(column_name):
    """Normaliza o nome da coluna para o padrão"""
    if not isinstance(column_name, str):
        return None
        
    column_name = column_name.lower().strip()
    
    for std_name, variations in COLUMN_MAPPING.items():
        if column_name in variations:
            return std_name
    return column_name

def check_column_exists(conn, table_name, column_name):
    """Verifica se uma coluna existe em uma tabela"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns

def create_tables():
    """Cria as tabelas no banco de dados se não existirem"""
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Tabela de histórico de uploads (deve ser criada primeiro por causa da chave estrangeira)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_arquivo TEXT NOT NULL,
            data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_registros INTEGER DEFAULT 0,
            registros_inseridos INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pendente',
            mensagem TEXT
        )
        ''')
        
        # Tabela de transações
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
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
        
        # Verifica se a coluna upload_id já existe na tabela transacoes
        if not check_column_exists(conn, 'transacoes', 'upload_id'):
            logger.info("Adicionando coluna upload_id à tabela transacoes")
            cursor.execute('''
            ALTER TABLE transacoes
            ADD COLUMN upload_id INTEGER
            ''')
            
            # Adiciona a chave estrangeira
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_transacoes_upload_id ON transacoes(upload_id)
            ''')
        
        conn.commit()
        logger.info("Tabelas criadas/atualizadas com sucesso")
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao criar/atualizar tabelas: {str(e)}")
        raise
        
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

@log_function(logger, LogLevel.INFO)
def process_csv(file_path):
    """Processa um arquivo CSV e salva no banco de dados"""
    try:
        logger.info(f"Iniciando processamento do arquivo: {file_path}")
        
        # Lê o arquivo CSV
        try:
            logger.debug("Lendo arquivo CSV...")
            df = pd.read_csv(file_path, encoding='utf-8', sep=';', decimal=',')
            logger.debug(f"Arquivo lido com sucesso. Colunas: {df.columns.tolist()}")
        except Exception as e:
            logger.error(f"Erro ao ler o arquivo CSV: {str(e)}", exc_info=True)
            return False, f'Erro ao ler o arquivo CSV: {str(e)}'
        
        # Registra o início do upload
        try:
            logger.debug("Registrando início do upload no banco de dados...")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO uploads_historico (nome_arquivo, data_upload, total_registros, status, mensagem)
                VALUES (?, datetime('now'), 0, 'processando', 'Iniciando processamento')
            ''', (os.path.basename(file_path),))
            upload_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Upload registrado com ID: {upload_id}")
            
        except Exception as e:
            error_msg = f"Erro ao registrar upload no banco de dados: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
        
        # Normaliza os nomes das colunas
        logger.debug("Normalizando nomes das colunas...")
        df.columns = [normalize_column_name(col) or col for col in df.columns]
        logger.debug(f"Colunas após normalização: {df.columns.tolist()}")
        
        # Verifica se as colunas necessárias estão presentes
        required_columns = ['data', 'descricao', 'valor']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            error_msg = f'Colunas obrigatórias não encontradas: {", ".join(missing_columns)}'
            logger.error(error_msg)
            try:
                cursor.execute('''
                    UPDATE uploads_historico 
                    SET status = 'erro', mensagem = ? 
                    WHERE id = ?
                ''', (error_msg, upload_id))
                conn.commit()
            except Exception as e:
                logger.error(f"Erro ao atualizar histórico de upload: {str(e)}", exc_info=True)
            return False, error_msg
        
        # Converte a data para o formato correto
        logger.debug("Convertendo coluna de data...")
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        
        # Remove linhas com dados inválidos
        initial_count = len(df)
        df = df.dropna(subset=['data', 'descricao', 'valor', 'tipo'])
        removed_missing = initial_count - len(df)
        if removed_missing > 0:
            logger.warning(f"Removidas {removed_missing} linhas com dados faltantes")
        
        # Converte valor para numérico, tratando possíveis problemas de formatação
        logger.debug("Convertendo valores para numérico...")
        initial_count = len(df)
        df['valor'] = pd.to_numeric(df['valor'].astype(str).str.replace(',', '.'), errors='coerce')
        df = df.dropna(subset=['valor'])
        removed_invalid = initial_count - len(df)
        if removed_invalid > 0:
            logger.warning(f"Removidas {removed_invalid} linhas com valores inválidos")
        
        # Converte valores para negativos se for despesa
        logger.debug("Ajustando valores negativos para despesas...")
        df['tipo'] = df['tipo'].str.lower().str.strip()
        df['valor'] = df.apply(
            lambda x: -abs(x['valor']) if x['tipo'] == 'despesa' else abs(x['valor']), 
            axis=1
        )
        
        # Converte para o formato do banco de dados
        logger.debug("Formatando dados para o banco de dados...")
        df['data'] = df['data'].dt.strftime('%Y-%m-%d')
        df['descricao'] = df['descricao'].astype(str).str.strip()
        df['tipo'] = df['tipo'].astype(str).str.strip()
        df['categoria'] = df.get('categoria', '').astype(str).str.strip()
        
        # Remove duplicatas baseado nas colunas principais
        logger.debug("Removendo duplicatas...")
        initial_count = len(df)
        df = df.drop_duplicates(subset=['data', 'descricao', 'valor', 'tipo'])
        removed_duplicates = initial_count - len(df)
        if removed_duplicates > 0:
            logger.warning(f"Removidas {removed_duplicates} linhas duplicadas")
            
        # Atualiza o total de registros no histórico
        logger.debug(f"Atualizando total de registros no histórico: {len(df)}")
        cursor.execute(
            "UPDATE uploads_historico SET total_registros = ? WHERE id = ?",
            (len(df), upload_id)
        )
        conn.commit()
        
        # Adiciona o upload_id ao DataFrame
        df['upload_id'] = upload_id
        
        # Insere os dados no banco, atualizando registros existentes
        for _, row in df.iterrows():
            try:
                # Tenta inserir o registro
                cursor.execute("""
                    INSERT INTO transacoes (data, descricao, valor, tipo, categoria, upload_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    row['data'],
                    row['descricao'],
                    row['valor'],
                    row['tipo'],
                    row.get('categoria', ''),
                    upload_id
                ))
            except sqlite3.IntegrityError as e:
                if 'UNIQUE constraint failed' in str(e):
                    # Se o registro já existe, atualiza o upload_id
                    cursor.execute("""
                        UPDATE transacoes 
                        SET upload_id = ?
                        WHERE data = ? 
                        AND descricao = ? 
                        AND valor = ? 
                        AND tipo = ?
                    """, (
                        upload_id,
                        row['data'],
                        row['descricao'],
                        row['valor'],
                        row['tipo']
                    ))
                    logger.info(f"Atualizado registro existente: {row['data']} - {row['descricao']}")
                else:
                    raise
        
        # Atualiza o histórico com o sucesso
        registros_inseridos = len(df)
        mensagem = f"Processados {registros_inseridos} de {total_registros} registros"
        cursor.execute(
            """
            UPDATE uploads_historico 
            SET status = 'concluido', 
                mensagem = ?,
                registros_inseridos = ?
            WHERE id = ?
            """,
            (mensagem, registros_inseridos, upload_id)
        )
        conn.commit()
        
        # Remove o arquivo após processamento bem-sucedido
        try:
            os.remove(file_path)
            logger.info(f"Arquivo {file_path} removido após processamento")
        except Exception as e:
            logger.warning(f"Não foi possível remover o arquivo {file_path}: {str(e)}")
        
        logger.info(f"Processados {registros_inseridos} registros do arquivo {nome_arquivo}")
        return True, mensagem
        
    except Exception as e:
        error_msg = f"Erro ao processar o arquivo {file_path}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    finally:
        if 'conn' in locals():
            conn.close()

def process_pdf(file_path):
    """Processa um arquivo PDF (implementação básica)"""
    try:
        # Lógica para processar PDF seria implementada aqui
        # Por enquanto, apenas retorna um erro informando que não está implementado
        error_msg = "Processamento de PDF ainda não implementado"
        logger.warning(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Erro ao processar o PDF {file_path}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def get_all_transactions(limit=1000):
    """Obtém todas as transações do banco de dados"""
    try:
        conn = sqlite3.connect(DB_PATH)
        query = f"SELECT * FROM transacoes ORDER BY data DESC LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        logger.error(f"Erro ao buscar transações: {str(e)}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals():
            conn.close()

def get_upload_history(limit=10):
    """Obtém o histórico de uploads recentes"""
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT 
                id,
                nome_arquivo,
                datetime(data_upload, 'localtime') as data_upload,
                total_registros,
                registros_inseridos,
                status,
                mensagem
            FROM uploads_historico
            ORDER BY data_upload DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(limit,))
        return df
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de uploads: {str(e)}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals():
            conn.close()

# Cria as tabelas ao importar o módulo
create_tables()
