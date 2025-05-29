import os
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys
import re
import logging

root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function, LogLevel

logger = get_logger("upload.processamento")


COLUMN_MAPPING = {
    'data': ['data', 'date', 'data_transacao', 'data_transação', 'dt', 'datahora'],
    'descricao': ['descricao', 'descrição', 'desc', 'historico', 'histórico', 'detalhes', 'descricao_transacao'],
    'valor': ['valor', 'vlr', 'vl', 'value', 'amount', 'montante'],
    'tipo': ['tipo', 'tp', 'type', 'movimentacao', 'movimentação', 'movimento'],
    'categoria': ['categoria', 'categ', 'cat', 'category', 'grupo', 'classificacao'],
    'preco': ['preco', 'price', 'preço', 'valor_unitario'],
    'quantidade': ['quantidade', 'qtd', 'qtde', 'amount', 'quant'],
    'tipo_operacao': ['tipo_operacao', 'tipo_oper', 'operacao', 'operation'],
    'taxa': ['taxa', 'tax', 'fee', 'tarifa'],
    'ativo': ['ativo', 'asset', 'ativo_id', 'ativo_codigo'],
    'forma_pagamento': ['forma_pagamento', 'forma_pag', 'pagamento', 'payment_method'],
    'indicador1': ['indicador1', 'ind1', 'indicador_1', 'indicator1'],
    'indicador2': ['indicador2', 'ind2', 'indicador_2', 'indicator2']
}

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'banco', 'financas.db')

def normalize_column_name(column_name):
    if not isinstance(column_name, str):
        return None
    column_name = column_name.lower().strip()
    char_map = {
        'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c',
        ' ': '_', '-': '_', '.': '_'
    }
    clean_name = ''.join(char_map.get(c, c) for c in column_name)
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    for std_name, variations in COLUMN_MAPPING.items():
        if clean_name in variations or any(v in clean_name for v in variations):
            return std_name
    return clean_name if clean_name else None

def check_column_exists(conn, table_name, column_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns

def create_tables():
    try:
        db_dir = os.path.dirname(DB_PATH)
        if not os.path.exists(db_dir):
            logger.info(f"Criando diretório do banco de dados: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
        
        logger.info(f"Conectando ao banco de dados: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
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
        
        columns_to_add = [
            ('data_conclusao', 'TEXT'),
            ('registros_atualizados', 'INTEGER DEFAULT 0'),
            ('registros_com_erro', 'INTEGER DEFAULT 0')
        ]
        
        for column_name, column_type in columns_to_add:
            if not check_column_exists(conn, 'uploads_historico', column_name):
                logger.info(f"Adicionando coluna {column_name} à tabela uploads_historico")
                cursor.execute(f'ALTER TABLE uploads_historico ADD COLUMN {column_name} {column_type}')
        
        logger.info("Criando/verificando tabela 'transacoes'")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT,
            preco REAL,
            quantidade REAL,
            tipo_operacao TEXT,
            taxa REAL,
            ativo TEXT,
            forma_pagamento TEXT,
            indicador1 REAL,
            indicador2 REAL,
            data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            upload_id INTEGER,
            FOREIGN KEY (upload_id) REFERENCES uploads_historico(id),
            CONSTRAINT unique_transacao UNIQUE (data, descricao, valor, tipo)
        )
        ''')
        logger.info("Tabela 'transacoes' criada/verificada com sucesso")
        
        # Verificar e corrigir a constraint UNIQUE na tabela transacoes
        cursor.execute("PRAGMA table_info(transacoes)")
        columns = [col[1] for col in cursor.fetchall()]
        cursor.execute("PRAGMA index_list(transacoes)")
        indexes = [idx[1] for idx in cursor.fetchall()]
        if 'unique_transacao' not in indexes:
            logger.warning("Constraint 'unique_transacao' não encontrada. Corrigindo esquema da tabela transacoes...")
            cursor.execute("ALTER TABLE transacoes RENAME TO transacoes_old")
            cursor.execute('''
                CREATE TABLE transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    valor REAL NOT NULL,
                    tipo TEXT NOT NULL,
                    categoria TEXT,
                    preco REAL,
                    quantidade REAL,
                    tipo_operacao TEXT,
                    taxa REAL,
                    ativo TEXT,
                    forma_pagamento TEXT,
                    indicador1 REAL,
                    indicador2 REAL,
                    data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    upload_id INTEGER,
                    FOREIGN KEY (upload_id) REFERENCES uploads_historico(id),
                    CONSTRAINT unique_transacao UNIQUE (data, descricao, valor, tipo)
                )
            ''')
            cursor.execute('''
                INSERT INTO transacoes (
                    id, data, descricao, valor, tipo, categoria, preco, quantidade,
                    tipo_operacao, taxa, ativo, forma_pagamento, indicador1, indicador2,
                    data_importacao, upload_id
                )
                SELECT
                    id, data, descricao, valor, tipo, categoria, preco, quantidade,
                    tipo_operacao, taxa, ativo, forma_pagamento, indicador1, indicador2,
                    data_importacao, upload_id
                FROM transacoes_old
            ''')
            cursor.execute("DROP TABLE transacoes_old")
            logger.info("Esquema da tabela transacoes corrigido com sucesso")
        
        columns_to_add = [
            ('preco', 'REAL'),
            ('quantidade', 'REAL'),
            ('tipo_operacao', 'TEXT'),
            ('taxa', 'REAL'),
            ('ativo', 'TEXT'),
            ('forma_pagamento', 'TEXT'),
            ('indicador1', 'REAL'),
            ('indicador2', 'REAL')
        ]
        
        for column_name, column_type in columns_to_add:
            if not check_column_exists(conn, 'transacoes', column_name):
                logger.info(f"Adicionando coluna {column_name} à tabela transacoes")
                cursor.execute(f'ALTER TABLE transacoes ADD COLUMN {column_name} {column_type}')
        
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
    try:
        logger.info(f"Iniciando processamento do arquivo: {file_path}")
        
        try:
            logger.debug("Lendo arquivo CSV...")
            
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                first_line = f.readline().strip()
                
            dtype = {
                'data': str,
                'descricao': str,
                'valor': str,
                'tipo': str,
                'categoria': str,
                'preco': str,
                'quantidade': str,
                'taxa': str,
                'ativo': str,
                'forma_pagamento': str,
                'indicador1': str,
                'indicador2': str,
                'tipo_operacao': str
            }
            
            if ';' in first_line:
                sep = ';'
            else:
                sep = ','
            logger.debug(f"Separador detectado: '{sep}'")
            
            df = pd.read_csv(file_path, sep=sep, dtype=dtype, encoding='utf-8-sig')
                
            if len(df.columns) != len(set(df.columns)):
                duplicate_cols = [col for col in df.columns if list(df.columns).count(col) > 1]
                logger.error(f"Colunas duplicadas encontradas no CSV: {duplicate_cols}")
                new_columns = []
                col_count = {}
                for col in df.columns:
                    if col in col_count:
                        col_count[col] += 1
                        new_columns.append(f"{col}_{col_count[col]}")
                    else:
                        col_count[col] = 0
                        new_columns.append(col)
                df.columns = new_columns
                logger.debug(f"Colunas após correção de duplicatas: {df.columns.tolist()}")
                
            if len(df.columns) == 1:
                logger.warning(f"Leitura inicial resultou em uma única coluna. Tentando separador alternativo...")
                alt_sep = ',' if sep == ';' else ';'
                try:
                    df = pd.read_csv(file_path, sep=alt_sep, dtype=dtype, encoding='utf-8-sig')
                    logger.debug(f"Separador alternativo '{alt_sep}' funcionou")
                    if len(df.columns) != len(set(df.columns)):
                        duplicate_cols = [col for col in df.columns if list(df.columns).count(col) > 1]
                        logger.error(f"Colunas duplicadas encontradas com separador alternativo: {duplicate_cols}")
                        new_columns = []
                        col_count = {}
                        for col in df.columns:
                            if col in col_count:
                                col_count[col] += 1
                                new_columns.append(f"{col}_{col_count[col]}")
                            else:
                                col_count[col] = 0
                                new_columns.append(col)
                        df.columns = new_columns
                        logger.debug(f"Colunas após correção de duplicatas com separador alternativo: {df.columns.tolist()}")
                except Exception as e:
                    logger.error(f"Erro ao tentar separador alternativo: {str(e)}")
                    return False, f"Erro ao ler o arquivo CSV com separadores ';' ou ',': {str(e)}"
                    
            df.columns = [str(col).strip().lower() for col in df.columns]
            
            numeric_cols = ['valor', 'preco', 'taxa', 'quantidade', 'indicador1', 'indicador2']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(' ', '', regex=False).str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.debug("Valores numéricos após conversão:")
            for col in numeric_cols:
                if col in df.columns:
                    logger.debug(f"{col}: {df[col].head().tolist()}")
            
            logger.debug(f"Colunas encontradas após leitura: {df.columns.tolist()}")
            logger.debug(f"tipos de dados iniciais:\n{df.dtypes}")
            logger.debug(f"Primeiras linhas do arquivo:\n{df.head().to_string()}")
            
        except Exception as e:
            logger.error(f"Erro ao ler o arquivo CSV: {str(e)}", exc_info=True)
            return False, f'Erro ao ler o arquivo CSV: {str(e)}'
        
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
        
        logger.debug("Normalizando nomes das colunas...")
        original_columns = df.columns.tolist()
        column_mapping = {}
        used_names = set()
        for col in df.columns:
            col_clean = normalize_column_name(col)
            if col_clean:
                if col_clean in used_names:
                    suffix = 1
                    while f"{col_clean}_{suffix}" in used_names:
                        suffix += 1
                    col_clean = f"{col_clean}_{suffix}"
                column_mapping[col] = col_clean
                used_names.add(col_clean)
                logger.debug(f"Mapeando coluna '{col}' para '{col_clean}'")
        
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        df.columns = [normalize_column_name(col) or col for col in df.columns]
        logger.debug(f"Colunas após normalização: {df.columns.tolist()}")
        
        if len(df.columns) != len(set(df.columns)):
            duplicate_cols = [col for col in df.columns if list(df.columns).count(col) > 1]
            logger.warning(f"Colunas duplicadas após normalização: {duplicate_cols}")
            new_columns = []
            col_count = {}
            for col in df.columns:
                if col in col_count:
                    col_count[col] += 1
                    new_columns.append(f"{col}_{col_count[col]}")
                else:
                    col_count[col] = 0
                    new_columns.append(col)
            df.columns = new_columns
            logger.debug(f"Colunas após segunda correção de duplicatas: {df.columns.tolist()}")
        
        required_columns = ['data', 'descricao', 'valor', 'tipo']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            error_msg = f'Colunas obrigatórias não encontradas: {", ".join(missing_columns)}. Colunas disponíveis: {", ".join(df.columns)}'
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
        
        all_columns = ['data', 'descricao', 'valor', 'tipo', 'categoria', 'preco', 'quantidade', 'taxa', 'ativo', 'forma_pagamento', 'indicador1', 'indicador2', 'tipo_operacao']
        
        for col in df.columns:
            if col not in all_columns:
                logger.warning(f"Coluna extra encontrada: {col}")
        
        for col in all_columns:
            if col not in df.columns:
                if col == 'categoria':
                    df[col] = ''
                elif col == 'tipo_operacao':
                    df[col] = 'Lançamento'
                elif col == 'quantidade':
                    df[col] = 1.0
                elif col == 'taxa':
                    df[col] = 0.0
                elif col == 'indicador1':
                    df[col] = 0.0
                elif col == 'indicador2':
                    df[col] = 0.0
                elif col == 'ativo':
                    df[col] = ''
                elif col == 'forma_pagamento':
                    df[col] = ''
                logger.debug(f"Adicionada coluna {col} com valor padrão")
        
        df = df[all_columns]
        
        if df.empty:
            logger.error("O arquivo CSV está vazio após leitura inicial")
            try:
                cursor.execute('''
                    UPDATE uploads_historico 
                    SET status = 'erro', mensagem = ? 
                    WHERE id = ?
                ''', ("O arquivo CSV está vazio após leitura inicial", upload_id))
                conn.commit()
            except Exception as e:
                logger.error(f"Erro ao atualizar histórico de upload: {str(e)}", exc_info=True)
            return False, "O arquivo CSV está vazio após leitura inicial"
        
        logger.debug("Convertendo coluna de data...")
        unique_dates = df['data'].dropna().unique()
        logger.debug(f"Valores únicos na coluna 'data' antes da conversão: {unique_dates[:10].tolist()}")
        
        try:
            df['data'] = pd.to_datetime(df['data'], errors='coerce', dayfirst=True)
        except Exception as e:
            logger.warning(f"Conversão inicial de datas falhou: {str(e)}. Tentando formatos específicos...")
            date_formats = [
                '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%Y/%m/%d',
                '%d %b %Y', '%d %B %Y', '%Y.%m.%d', '%b %d %Y', '%B %d %Y',
                '%Y%m%d', '%d.%m.%Y', '%m-%d-%Y'
            ]
            for fmt in date_formats:
                try:
                    df['data'] = pd.to_datetime(df['data'], format=fmt, errors='coerce')
                    if not df['data'].isna().all():
                        logger.debug(f"Formato de data '{fmt}' funcionou parcialmente")
                        break
                except Exception:
                    continue
        
        invalid_dates = df['data'].isna().sum()
        if invalid_dates > 0:
            invalid_date_examples = df[df['data'].isna()]['data'].head(5).tolist()
            logger.warning(f"Removidas {invalid_dates} linhas com datas inválidas. Exemplos: {invalid_date_examples}")
            df = df.dropna(subset=['data'])
        
        if df.empty:
            error_msg = f"Nenhuma data válida encontrada após conversão. Exemplos de datas no arquivo: {unique_dates[:5].tolist()}. Formatos suportados: {', '.join(date_formats)}"
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
        
        logger.debug("Convertendo colunas textuais para string...")
        text_columns = ['descricao', 'tipo', 'categoria', 'tipo_operacao', 'ativo', 'forma_pagamento']
        for col in text_columns:
            if col in df.columns:
                try:
                    if not isinstance(df[col], pd.Series):
                        logger.error(f"Coluna '{col}' não é uma Series, é um {type(df[col])}. Colunas disponíveis: {df.columns.tolist()}")
                        error_msg = f"Erro ao processar coluna {col}: Não é uma coluna única. Verifique colunas duplicadas no CSV."
                        try:
                            cursor.execute('''
                                UPDATE uploads_historico 
                                SET status = 'erro', mensagem = ? 
                                WHERE id = ?
                            ''', (error_msg, upload_id))
                            conn.commit()
                        except Exception as ex:
                            logger.error(f"Erro ao atualizar histórico de upload: {str(ex)}", exc_info=True)
                        return False, error_msg
                    df[col] = df[col].astype(str).str.strip().replace({'nan': '', 'NaN': '', '': 'Lançamento' if col == 'tipo_operacao' else ''})
                    logger.debug(f"Coluna {col} convertida para string e limpa")
                    unique_values = df[col].dropna().unique()[:5].tolist()
                    logger.debug(f"Amostra de valores na coluna '{col}': {unique_values}")
                except Exception as e:
                    logger.error(f"Erro ao processar coluna {col}: {str(e)}", exc_info=True)
                    try:
                        cursor.execute('''
                            UPDATE uploads_historico 
                            SET status = 'erro', mensagem = ? 
                            WHERE id = ?
                        ''', (f"Erro ao processar coluna {col}: {str(e)}", upload_id))
                        conn.commit()
                    except Exception as ex:
                        logger.error(f"Erro ao atualizar histórico de upload: {str(ex)}", exc_info=True)
                    return False, f"Erro ao processar coluna {col}: {str(e)}"
        
        logger.debug("Convertendo valores para float...")
        if 'valor' in df.columns:
            try:
                if not isinstance(df['valor'], pd.Series):
                    logger.error(f"Coluna 'valor' não é uma Series, é um {type(df['valor'])}. Colunas disponíveis: {df.columns.tolist()}")
                    error_msg = f"Erro ao processar coluna valor: Não é uma coluna única. Verifique colunas duplicadas no CSV."
                    try:
                        cursor.execute('''
                            UPDATE uploads_historico 
                            SET status = 'erro', mensagem = ? 
                            WHERE id = ?
                        ''', (error_msg, upload_id))
                        conn.commit()
                    except Exception as ex:
                        logger.error(f"Erro ao atualizar histórico de upload: {str(ex)}", exc_info=True)
                    return False, error_msg
                df['valor'] = df['valor'].astype(str).str.strip().replace('nan', '')
                df['valor'] = df['valor'].str.replace(',', '.', regex=False)
                df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
                invalid_values = df['valor'].isna().sum()
                if invalid_values > 0:
                    logger.warning(f"Removidas {invalid_values} linhas com valores inválidos na coluna 'valor'")
                    df = df.dropna(subset=['valor'])
                if df.empty:
                    logger.error("Nenhum valor válido encontrado após conversão")
                    try:
                        cursor.execute('''
                            UPDATE uploads_historico 
                            SET status = 'erro', mensagem = ? 
                            WHERE id = ?
                        ''', ("Nenhum valor válido encontrado após conversão", upload_id))
                        conn.commit()
                    except Exception as e:
                        logger.error(f"Erro ao atualizar histórico de upload: {str(e)}", exc_info=True)
                    return False, "Nenhum valor válido encontrado após conversão"
                unique_values = df['valor'].dropna().unique()[:5].tolist()
                logger.debug(f"Amostra de valores na coluna 'valor': {unique_values}")
            except Exception as e:
                logger.error(f"Erro ao processar coluna 'valor': {str(e)}", exc_info=True)
                try:
                    cursor.execute('''
                        UPDATE uploads_historico 
                        SET status = 'erro', mensagem = ? 
                        WHERE id = ?
                    ''', (f"Erro ao processar coluna 'valor': {str(e)}", upload_id))
                    conn.commit()
                except Exception as ex:
                    logger.error(f"Erro ao atualizar histórico de upload: {str(ex)}", exc_info=True)
                return False, f"Erro ao processar coluna 'valor': {str(e)}"
        
        logger.debug("Convertendo colunas numéricas...")
        numeric_columns = ['preco', 'quantidade', 'taxa', 'indicador1', 'indicador2']
        for col in numeric_columns:
            if col in df.columns:
                try:
                    if not isinstance(df[col], pd.Series):
                        logger.error(f"Coluna '{col}' não é uma Series, é um {type(df[col])}. Colunas disponíveis: {df.columns.tolist()}")
                        error_msg = f"Erro ao processar coluna {col}: Não é uma coluna única. Verifique colunas duplicadas no CSV."
                        try:
                            cursor.execute('''
                                UPDATE uploads_historico 
                                SET status = 'erro', mensagem = ? 
                                WHERE id = ?
                            ''', (error_msg, upload_id))
                            conn.commit()
                        except Exception as ex:
                            logger.error(f"Erro ao atualizar histórico de upload: {str(ex)}", exc_info=True)
                        return False, error_msg
                    df[col] = df[col].astype(str).str.strip().replace('nan', '')
                    df[col] = df[col].str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    invalid_values = df[col].isna().sum()
                    if invalid_values > 0:
                        logger.warning(f"Removidas {invalid_values} linhas com valores inválidos na coluna {col}")
                        df[col] = df[col].fillna(0.0)
                    unique_values = df[col].dropna().unique()[:5].tolist()
                    logger.debug(f"Amostra de valores na coluna '{col}': {unique_values}")
                except Exception as e:
                    logger.error(f"Erro ao processar coluna {col}: {str(e)}", exc_info=True)
                    try:
                        cursor.execute('''
                            UPDATE uploads_historico 
                            SET status = 'erro', mensagem = ? 
                            WHERE id = ?
                        ''', (f"Erro ao processar coluna {col}: {str(e)}", upload_id))
                        conn.commit()
                    except Exception as ex:
                        logger.error(f"Erro ao atualizar histórico de upload: {str(ex)}", exc_info=True)
                    return False, f"Erro ao processar coluna {col}: {str(e)}"
        
        logger.debug("Ajustando valores negativos para despesas...")
        if 'tipo' in df.columns:
            try:
                if not isinstance(df['tipo'], pd.Series):
                    logger.error(f"Coluna 'tipo' não é uma Series, é um {type(df['tipo'])}. Colunas disponíveis: {df.columns.tolist()}")
                    error_msg = f"Erro ao processar coluna tipo: Não é uma coluna única. Verifique colunas duplicadas no CSV."
                    try:
                        cursor.execute('''
                            UPDATE uploads_historico 
                            SET status = 'erro', mensagem = ? 
                            WHERE id = ?
                        ''', (error_msg, upload_id))
                        conn.commit()
                    except Exception as ex:
                        logger.error(f"Erro ao atualizar histórico de upload: {str(ex)}", exc_info=True)
                    return False, error_msg
                
                logger.debug(f"Valores de 'tipo' antes do ajuste: {df['tipo'].unique().tolist()}")
                
                # Mover valores de 'tipo' para 'tipo_operacao'
                df['tipo_operacao'] = df['tipo'].str.lower().str.strip()
                
                # Classificar como 'receita' ou 'despesa' com base em categoria e tipo_operacao
                def classify_transaction(row):
                    categoria = row['categoria'].lower().strip() if pd.notna(row['categoria']) else ''
                    tipo_operacao = row['tipo_operacao'].lower().strip() if pd.notna(row['tipo_operacao']) else ''
                    
                    # Receita: Trabalho ou Investimentos com resgate/dividendo
                    if categoria == 'trabalho' or (categoria == 'investimentos' and tipo_operacao in ['resgate', 'dividendo']):
                        return 'receita'
                    # Despesa: Moradia, Saúde, Educação, Alimentação, ou Investimentos com compra
                    elif categoria in ['moradia', 'saúde', 'educação', 'alimentação'] or (categoria == 'investimentos' and tipo_operacao == 'compra'):
                        return 'despesa'
                    # Default: Despesa para outras categorias ou tipos desconhecidos
                    else:
                        return 'despesa'
                
                df['tipo'] = df.apply(classify_transaction, axis=1)
                
                # Ajustar o sinal do valor: negativo para despesas, positivo para receitas
                df['valor'] = df.apply(
                    lambda x: -abs(x['valor']) if x['tipo'] == 'despesa' else abs(x['valor']), 
                    axis=1
                )
                
                unique_values = df['tipo'].dropna().unique()[:5].tolist()
                logger.debug(f"Amostra de valores na coluna 'tipo' após ajuste: {unique_values}")
                unique_operacao = df['tipo_operacao'].dropna().unique()[:5].tolist()
                logger.debug(f"Amostra de valores na coluna 'tipo_operacao' após ajuste: {unique_operacao}")
                
            except Exception as e:
                logger.error(f"Erro ao ajustar valores para despesas: {str(e)}", exc_info=True)
                try:
                    cursor.execute('''
                        UPDATE uploads_historico 
                        SET status = 'erro', mensagem = ? 
                        WHERE id = ?
                    ''', (f"Erro ao ajustar valores para despesas: {str(e)}", upload_id))
                    conn.commit()
                except Exception as ex:
                    logger.error(f"Erro ao atualizar histórico de upload: {str(ex)}", exc_info=True)
                return False, f"Erro ao ajustar valores para despesas: {str(e)}"
        
        logger.debug("Formatando dados para o banco de dados...")
        try:
            df['data'] = df['data'].dt.strftime('%Y-%m-%d')
            df['descricao'] = df['descricao'].astype(str).str.strip()
            df['tipo'] = df['tipo'].astype(str).str.strip()
            df['categoria'] = df.get('categoria', '').astype(str).str.strip()
            df['tipo_operacao'] = df['tipo_operacao'].astype(str).str.strip().replace({'': 'Lançamento', 'nan': 'Lançamento'})
        except Exception as e:
            logger.error(f"Erro ao formatar dados para o banco: {str(e)}", exc_info=True)
            try:
                cursor.execute('''
                    UPDATE uploads_historico 
                    SET status = 'erro', mensagem = ? 
                    WHERE id = ?
                ''', (f"Erro ao formatar dados para o banco: {str(e)}", upload_id))
                conn.commit()
            except Exception as ex:
                logger.error(f"Erro ao atualizar histórico de upload: {str(ex)}", exc_info=True)
            return False, f"Erro ao formatar dados para o banco: {str(e)}"
        
        logger.debug("Removendo duplicatas...")
        initial_count = len(df)
        df = df.drop_duplicates(subset=['data', 'descricao', 'valor', 'tipo'])
        removed_duplicates = initial_count - len(df)
        if removed_duplicates > 0:
            logger.warning(f"Removidas {removed_duplicates} linhas duplicadas")
            
        logger.debug(f"Atualizando total de registros no histórico: {len(df)}")
        try:
            cursor.execute(
                "UPDATE uploads_historico SET total_registros = ? WHERE id = ?",
                (len(df), upload_id)
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Erro ao atualizar total de registros: {str(e)}", exc_info=True)
            return False, f"Erro ao atualizar total de registros: {str(e)}"
        
        df['upload_id'] = upload_id
        
        registros_inseridos = 0
        registros_atualizados = 0
        registros_com_erro = 0
        total_registros = len(df)
        logger.info(f"Iniciando inserção/atualização de {total_registros} registros...")
        
        for i, (_, row) in enumerate(df.iterrows(), 1):
            try:
                logger.debug(f"Processando registro {i}/{total_registros}: tipo_operacao={row['tipo_operacao']}, tipo={row['tipo']}, valor={row['valor']}")
                
                cursor.execute(
                    """
                    INSERT INTO transacoes (
                        data, descricao, valor, tipo, categoria, preco, quantidade, taxa,
                        ativo, tipo_operacao, forma_pagamento, indicador1, indicador2, upload_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(data, descricao, valor, tipo) 
                    DO UPDATE SET 
                        categoria = COALESCE(excluded.categoria, categoria),
                        preco = COALESCE(excluded.preco, preco),
                        quantidade = COALESCE(excluded.quantidade, quantidade),
                        taxa = COALESCE(excluded.taxa, taxa),
                        ativo = COALESCE(excluded.ativo, ativo),
                        tipo_operacao = COALESCE(excluded.tipo_operacao, tipo_operacao),
                        forma_pagamento = COALESCE(excluded.forma_pagamento, forma_pagamento),
                        indicador1 = COALESCE(excluded.indicador1, indicador1),
                        indicador2 = COALESCE(excluded.indicador2, indicador2),
                        upload_id = excluded.upload_id
                    """,
                    (
                        row['data'],
                        row['descricao'],
                        row['valor'],
                        row['tipo'],
                        row['categoria'],
                        row['preco'],
                        row['quantidade'],
                        row['taxa'],
                        row['ativo'],
                        row['tipo_operacao'],
                        row['forma_pagamento'],
                        row['indicador1'],
                        row['indicador2'],
                        row['upload_id']
                    )
                )
                
                if cursor.rowcount == 1:
                    registros_inseridos += 1
                    if registros_inseridos % 100 == 0:
                        logger.debug(f"Inseridos {registros_inseridos} registros...")
                else:
                    registros_atualizados += 1
                    if registros_atualizados % 100 == 0:
                        logger.debug(f"Atualizados {registros_atualizados} registros...")
                
                if i % max(1, total_registros // 10) == 0 or i == total_registros:
                    logger.info(f"Progresso: {i}/{total_registros} ({i/total_registros:.0%}) - Inseridos: {registros_inseridos}, Atualizados: {registros_atualizados}, Erros: {registros_com_erro}")
                    
            except Exception as e:
                registros_com_erro += 1
                error_msg = f"Erro ao processar registro {i}/{total_registros}: coluna 'tipo_operacao'={row.get('tipo_operacao', 'N/A')}, erro: {str(e)}"
                logger.error(error_msg, exc_info=True)
                continue
        
        mensagem = f"Processamento concluído: {registros_inseridos} registros inseridos, {registros_atualizados} atualizados, {registros_com_erro} com erro"
        try:
            cursor.execute(
                """
                UPDATE uploads_historico 
                SET status = 'concluido', 
                    mensagem = ?,
                    registros_inseridos = ?,
                    registros_atualizados = ?,
                    registros_com_erro = ?,
                    data_conclusao = datetime('now')
                WHERE id = ?
                """,
                (mensagem, registros_inseridos, registros_atualizados, registros_com_erro, upload_id)
            )
            conn.commit()
            logger.info("Histórico de upload atualizado com sucesso")
            
            try:
                os.remove(file_path)
                logger.info(f"Arquivo {file_path} removido após processamento")
            except Exception as e:
                logger.warning(f"Não foi possível remover o arquivo {file_path}: {str(e)}")
            
            logger.info(f"Processamento concluído: {registros_inseridos} registros inseridos, {registros_atualizados} atualizados, {registros_com_erro} com erro")
            return True, mensagem
            
        except Exception as e:
            error_msg = f"Erro ao atualizar histórico de upload: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
        
    except Exception as e:
        error_msg = f"Erro ao processar o arquivo {file_path}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg
    finally:
        if 'conn' in locals():
            try:
                conn.close()
                logger.info("Conexão com o banco de dados fechada")
            except Exception as e:
                logger.error(f"Erro ao fechar conexão com o banco de dados: {str(e)}", exc_info=True)

def process_pdf(file_path):
    try:
        error_msg = "Processamento de PDF ainda não implementado"
        logger.warning(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Erro ao processar o PDF {file_path}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg

def get_all_transactions():
    limit = None  # Remove o limite de transações
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(transacoes)")
        columns_info = cursor.fetchall()
        
        required_columns = ['data', 'descricao', 'valor', 'tipo']
        
        all_columns = ['data', 'descricao', 'valor', 'tipo', 'categoria', 'preco', 'quantidade', 'taxa', 'ativo', 'forma_pagamento', 'indicador1', 'indicador2', 'tipo_operacao']
        
        missing_columns = []
        for col in all_columns:
            if not any(info[1].lower() == col for info in columns_info):
                missing_columns.append(col)
        
        if missing_columns:
            logger.warning(f"Colunas obrigatórias faltando na tabela: {', '.join(missing_columns)}")
        
        query = "SELECT * FROM transacoes ORDER BY data DESC"
        df = pd.read_sql_query(query, conn)
        
        numeric_columns = ['valor', 'preco', 'quantidade', 'taxa', 'indicador1', 'indicador2']
        
        for col in all_columns:
            if col not in df.columns:
                if col in numeric_columns:
                    df[col] = 0.0
                else:
                    df[col] = None
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        df = df[all_columns + ['data_importacao', 'upload_id']]
        
        df['missing_columns'] = str(missing_columns) if missing_columns else None
        
        return df
    except Exception as e:
        logger.error(f"Erro ao buscar transações: {str(e)}", exc_info=True)
        return pd.DataFrame()
    finally:
        if 'conn' in locals():
            try:
                conn.close()
                logger.info("Conexão com o banco de dados fechada")
            except Exception as e:
                logger.error(f"Erro ao fechar conexão com o banco de dados: {str(e)}", exc_info=True)

def get_upload_history(limit=10):
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
        logger.error(f"Erro ao buscar histórico de uploads: {str(e)}", exc_info=True)
        return pd.DataFrame()
    finally:
        if 'conn' in locals():
            try:
                conn.close()
                logger.info("Conexão com o banco de dados fechada")
            except Exception as e:
                logger.error(f"Erro ao buscar histórico de uploads: {str(e)}", exc_info=True)

def get_categorias_por_tipo(tipo=None):
    """
    Obtém as categorias filtradas por tipo (Receita/Despesa)
    
    Args:
        tipo (str, optional): 'Receita' ou 'Despesa'. Se None, retorna todas as categorias.
        
    Returns:
        list: Lista de categorias únicas
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        query = """
            SELECT DISTINCT categoria 
            FROM transacoes 
            WHERE categoria IS NOT NULL AND categoria != ''
        """
        
        params = ()
        
        if tipo:
            query += " AND LOWER(tipo) = LOWER(?)"
            params = (tipo.lower(),)
            
        query += " ORDER BY categoria"
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        # Retorna uma lista simples de categorias
        return [row[0] for row in cursor.fetchall() if row[0]]
        
    except Exception as e:
        logger.error(f"Erro ao obter categorias por tipo: {str(e)}")
        return []
    finally:
        conn.close()

create_tables()