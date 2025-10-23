"""
Módulo de banco de dados para o sistema PDV.
Gerencia conexões e operações no banco de dados SQLite.
"""
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from contextlib import contextmanager
import logging

# Importa o logger
from .logger import logger

# Carrega variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

# Configurações do banco de dados
DB_PATH = os.getenv("DB_PATH", "data/database.db")
DB_SCHEMA = "data/initial_data.sql"

# Garante que o diretório do banco de dados existe
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

class DatabaseError(Exception):
    """Exceção para erros de banco de dados."""
    pass

@contextmanager
def get_connection():
    """
    Gerenciador de contexto para conexões com o banco de dados.
    
    Exemplo:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tabela")
            result = cursor.fetchall()
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Permite acesso a colunas por nome
        conn.execute("PRAGMA foreign_keys = ON")  # Ativa chaves estrangeiras
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Erro no banco de dados: {e}")
        raise DatabaseError(f"Erro no banco de dados: {e}")
    finally:
        if conn:
            conn.close()

def init_db():
    """
    Inicializa o banco de dados, criando as tabelas e dados iniciais se necessário.
    """
    # Verifica se o banco de dados já existe
    if not os.path.exists(DB_PATH):
        logger.info(f"Criando novo banco de dados em {DB_PATH}")
        
        try:
            with get_connection() as conn:
                # Lê o script SQL de inicialização
                with open(DB_SCHEMA, 'r', encoding='utf-8') as f:
                    sql_script = f.read()
                
                # Executa o script SQL
                conn.executescript(sql_script)
                conn.commit()
                
                logger.info("Banco de dados inicializado com sucesso")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao inicializar o banco de dados: {e}")
            raise DatabaseError(f"Falha ao inicializar o banco de dados: {e}")
    else:
        logger.info(f"Usando banco de dados existente em {DB_PATH}")
        return True

def execute_query(query: str, params: tuple = (), fetch: str = "all") -> Union[List[Dict], Dict, int, None]:
    """
    Executa uma consulta SQL e retorna os resultados.
    
    Args:
        query: Consulta SQL a ser executada
        params: Parâmetros para a consulta
        fetch: Tipo de retorno ('all', 'one', 'value', 'none')
    
    Returns:
        Dependendo do parâmetro 'fetch':
        - 'all': Lista de dicionários (padrão)
        - 'one': Um único dicionário
        - 'value': Um único valor
        - 'none': Nada (para INSERT/UPDATE/DELETE)
        - 'lastrowid': ID da última linha inserida
    """
    with get_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch.lower() == 'all':
                result = [dict(row) for row in cursor.fetchall()]
            elif fetch.lower() == 'one':
                row = cursor.fetchone()
                result = dict(row) if row else None
            elif fetch.lower() == 'value':
                row = cursor.fetchone()
                result = row[0] if row else None
            elif fetch.lower() == 'lastrowid':
                result = cursor.lastrowid
                conn.commit()
                return result
            else:  # 'none' ou operação sem retorno
                conn.commit()
                return None
                
            conn.commit()
            return result
            
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Erro na consulta: {query} - {params}. Erro: {e}")
            raise DatabaseError(f"Erro na consulta ao banco de dados: {e}")

def execute_many(query: str, params_list: list) -> int:
    """
    Executa uma consulta várias vezes com diferentes parâmetros.
    
    Args:
        query: Consulta SQL com placeholders
        params_list: Lista de tuplas de parâmetros
        
    Returns:
        Número de linhas afetadas
    """
    with get_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
            
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Erro na execução em lote: {query} - {params_list}. Erro: {e}")
            raise DatabaseError(f"Erro na execução em lote: {e}")

def backup_db(backup_path: str = None) -> str:
    """
    Cria um backup do banco de dados.
    
    Args:
        backup_path: Caminho para salvar o backup. Se None, usa 'data/backup_YYYYMMDD_HHMMSS.db'
        
    Returns:
        Caminho para o arquivo de backup criado
    """
    import shutil
    from datetime import datetime
    
    if backup_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join("backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")
    
    try:
        # Cria uma conexão para o banco de dados de origem
        with sqlite3.connect(DB_PATH) as src_conn:
            # Cria uma conexão para o banco de dados de destino
            with sqlite3.connect(backup_path) as dst_conn:
                # Faz o backup
                src_conn.backup(dst_conn)
        
        logger.info(f"Backup criado com sucesso em {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"Erro ao criar backup: {e}")
        raise DatabaseError(f"Falha ao criar backup: {e}")

# Testes unitários
if __name__ == "__main__":
    # Inicializa o banco de dados
    init_db()
    
    # Testa uma consulta simples
    result = execute_query("SELECT name FROM sqlite_master WHERE type='table'")
    print("Tabelas no banco de dados:", [row['name'] for row in result])
    
    # Testa uma inserção
    user_id = execute_query(
        "INSERT INTO usuarios (nome, email, senha_hash, role) VALUES (?, ?, ?, ?)",
        ("Teste", "teste@teste.com", "hash123", "vendedor"),
        fetch="lastrowid"
    )
    print(f"Usuário inserido com ID: {user_id}")
    
    # Testa uma consulta com parâmetros
    user = execute_query(
        "SELECT * FROM usuarios WHERE id = ?",
        (user_id,),
        fetch="one"
    )
    print(f"Usuário recuperado: {user}")
    
    # Testa backup
    backup_path = backup_db()
    print(f"Backup criado em: {backup_path}")
