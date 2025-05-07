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
    """
    Normaliza o nome da coluna para o padrão.
    
    Args:
        column_name: Nome da coluna a ser normalizado
        
    Returns:
        str: Nome normalizado da coluna ou None se não for possível normalizar
    """
    if not isinstance(column_name, str):
        return None
        
    # Limpa o nome da coluna
    column_name = column_name.lower().strip()
    
    # Remove caracteres especiais e acentos
    char_map = {
        'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c',
        ' ': '_', '-': '_', '.': '_'
    }
    
    # Aplica o mapeamento de caracteres
    clean_name = ''.join(char_map.get(c, c) for c in column_name)
    
    # Remove múltiplos underscores consecutivos
    import re
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    
    # Verifica se o nome limpo corresponde a alguma variação conhecida
    for std_name, variations in COLUMN_MAPPING.items():
        if clean_name in variations or any(v in clean_name for v in variations):
            return std_name
    
    # Se não encontrou correspondência, retorna o nome limpo
    return clean_name if clean_name else None

def check_column_exists(conn, table_name, column_name):
    """Verifica se uma coluna existe em uma tabela"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns

def create_tables():
    """Cria as tabelas no banco de dados se não existirem"""
    try:
        # Cria o diretório do banco de dados se não existir
        db_dir = os.path.dirname(DB_PATH)
        if not os.path.exists(db_dir):
            logger.info(f"Criando diretório do banco de dados: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
        
        logger.info(f"Conectando ao banco de dados: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Tabela para histórico de uploads
        logger.info("Criando/verificando tabela 'uploads_historico'")
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
        logger.info("Tabela 'uploads_historico' criada/verificada com sucesso")
        
        # Verifica e adiciona colunas ausentes
        columns_to_add = [
            ('data_conclusao', 'TEXT'),
            ('registros_atualizados', 'INTEGER DEFAULT 0'),
            ('registros_com_erro', 'INTEGER DEFAULT 0')
        ]
        
        for column_name, column_type in columns_to_add:
            if not check_column_exists(conn, 'uploads_historico', column_name):
                logger.info(f"Adicionando coluna {column_name} à tabela uploads_historico")
                cursor.execute(f'ALTER TABLE uploads_historico ADD COLUMN {column_name} {column_type}')
        
        conn.commit()
        
        # Tabela de transações
        logger.info("Criando/verificando tabela 'transacoes'")
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
        logger.info("Tabela 'transacoes' criada/verificada com sucesso")
        
        # Cria índices para melhorar o desempenho
        logger.info("Criando/verificando índices")
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_transacoes_data ON transacoes(data)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_transacoes_tipo ON transacoes(tipo)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_transacoes_categoria ON transacoes(categoria)
        ''')
        
        conn.commit()
        logger.info("Todas as tabelas e índices foram criados/verificados com sucesso")
        
    except sqlite3.Error as e:
        error_msg = f"Erro SQLite ao criar tabelas: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Erro inesperado ao criar tabelas: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg)
    finally:
        if 'conn' in locals():
            try:
                conn.close()
                logger.info("Conexão com o banco de dados fechada")
            except Exception as e:
                logger.error(f"Erro ao fechar conexão com o banco de dados: {str(e)}", exc_info=True)

@log_function(logger, LogLevel.INFO)
def process_csv(file_path):
    """Processa um arquivo CSV e salva no banco de dados"""
    try:
        logger.info(f"Iniciando processamento do arquivo: {file_path}")
        
        # Lê o arquivo CSV
        try:
            logger.debug("Lendo arquivo CSV...")
            
            # Primeiro, lê o arquivo como texto para verificar o formato
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                first_line = f.readline().strip()
                
            # Verifica se o arquivo usa vírgula ou ponto e vírgula como separador
            if ',' in first_line and ';' not in first_line:
                # Usa vírgula como separador e ponto como decimal
                df = pd.read_csv(file_path, sep=',', decimal='.')
            else:
                # Tenta com ponto e vírgula como separador e vírgula como decimal
                df = pd.read_csv(file_path, sep=';', decimal=',')
                
            # Se ainda tiver apenas uma coluna, tenta com o outro separador
            if len(df.columns) == 1:
                if ',' in first_line:
                    df = pd.read_csv(file_path, sep=',', decimal='.')
                else:
                    df = pd.read_csv(file_path, sep=';', decimal=',')
            
            # Log detalhado das colunas e primeiras linhas
            logger.debug(f"Colunas encontradas: {df.columns.tolist()}")
            logger.debug(f"Primeiras linhas do arquivo:\n{df.head().to_string()}")
            logger.debug(f"Tipos de dados das colunas:\n{df.dtypes}")
            
            # Verifica se o DataFrame está vazio
            if df.empty:
                logger.error("O arquivo CSV está vazio")
                return False, "O arquivo CSV está vazio"
                
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
        original_columns = df.columns.tolist()
        
        # Primeiro, remove espaços extras e converte para minúsculas
        df.columns = [str(col).strip().lower() for col in df.columns]
        logger.debug(f"Colunas após limpeza: {df.columns.tolist()}")
        
        # Mapeia colunas para nomes padrão
        column_mapping = {}
        for col in df.columns:
            # Remove acentos e caracteres especiais
            col_clean = normalize_column_name(col)
            if col_clean:
                column_mapping[col] = col_clean
                logger.debug(f"Mapeando coluna '{col}' para '{col_clean}'")
        
        # Aplica o mapeamento
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # Converte os nomes das colunas para o padrão
        df.columns = [normalize_column_name(col) or col for col in df.columns]
        
        # Renomeia as colunas
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        logger.debug(f"Colunas após normalização: {df.columns.tolist()}")
        
        # Verifica se as colunas necessárias estão presentes
        required_columns = ['data', 'descricao', 'valor']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            error_msg = f'Colunas obrigatórias não encontradas: {", ".join(missing_columns)}. Colunas disponíveis: {", ".join(df.columns)}'
            logger.error(error_msg)
            logger.error(f"Colunas originais: {original_columns}")
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
        
        # Insere os dados no banco de dados
        registros_inseridos = 0
        registros_atualizados = 0
        total_registros = len(df)
        logger.info(f"Iniciando inserção/atualização de {total_registros} registros...")
        
        for i, (_, row) in enumerate(df.iterrows(), 1):
            try:
                cursor.execute(
                    """
                    INSERT INTO transacoes (data, descricao, valor, tipo, categoria, upload_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(data, descricao, valor, tipo) 
                    DO UPDATE SET 
                        categoria = COALESCE(excluded.categoria, categoria),
                        upload_id = excluded.upload_id
                    """,
                    (
                        row['data'],
                        row['descricao'],
                        row['valor'],
                        row['tipo'],
                        row['categoria'],
                        row['upload_id']
                    )
                )
                
                if cursor.rowcount == 1:
                    registros_inseridos += 1
                    if registros_inseridos % 100 == 0:  # Log a cada 100 inserções
                        logger.debug(f"Inseridos {registros_inseridos} registros...")
                else:
                    registros_atualizados += 1
                    if registros_atualizados % 100 == 0:  # Log a cada 100 atualizações
                        logger.debug(f"Atualizados {registros_atualizados} registros...")
                
                # Log de progresso a cada 10%
                if i % max(1, total_registros // 10) == 0 or i == total_registros:
                    logger.info(f"Progresso: {i}/{total_registros} ({i/total_registros:.0%}) - Inseridos: {registros_inseridos}, Atualizados: {registros_atualizados}")
                    
            except Exception as e:
                error_msg = f"Erro ao processar registro {i}/{total_registros}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                continue
        
        # Atualiza o histórico com o sucesso
        mensagem = f"Processamento concluído: {registros_inseridos} registros inseridos, {registros_atualizados} atualizados"
        try:
            cursor.execute(
                """
                UPDATE uploads_historico 
                SET status = 'concluido', 
                    mensagem = ?,
                    registros_inseridos = ?,
                    registros_atualizados = ?,
                    data_conclusao = datetime('now')
                WHERE id = ?
                """,
                (mensagem, registros_inseridos, registros_atualizados, upload_id)
            )
            conn.commit()
            logger.info("Histórico de upload atualizado com sucesso")
            
            # Remove o arquivo após processamento bem-sucedido
            try:
                os.remove(file_path)
                logger.info(f"Arquivo {file_path} removido após processamento")
            except Exception as e:
                logger.warning(f"Não foi possível remover o arquivo {file_path}: {str(e)}")
            
            logger.info(f"Processamento concluído: {registros_inseridos} registros inseridos, {registros_atualizados} atualizados")
            return True, mensagem
            
        except Exception as e:
            error_msg = f"Erro ao atualizar histórico de upload: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
        
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
