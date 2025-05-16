import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime

def get_db_info(conn):
    """Obtém informações gerais sobre o banco de dados"""
    cursor = conn.cursor()
    info = {}
    
    # Versão do SQLite
    cursor.execute("SELECT sqlite_version()")
    info['version'] = cursor.fetchone()[0]
    
    # Configurações do banco de dados
    cursor.execute("PRAGMA foreign_keys")
    info['foreign_keys'] = cursor.fetchone()[0] == 1
    
    cursor.execute("PRAGMA journal_mode")
    info['journal_mode'] = cursor.fetchone()[0]
    
    cursor.execute("PRAGMA synchronous")
    info['synchronous'] = cursor.fetchone()[0]
    
    return info

def get_table_info(conn, table_name):
    """Obtém informações detalhadas sobre uma tabela"""
    cursor = conn.cursor()
    info = {}
    
    # Estrutura da tabela
    cursor.execute(f"PRAGMA table_info({table_name})")
    info['columns'] = cursor.fetchall()
    
    # Chaves estrangeiras
    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    info['foreign_keys'] = cursor.fetchall()
    
    # Índices
    cursor.execute(f"PRAGMA index_list({table_name})")
    indexes = cursor.fetchall()
    info['indexes'] = {}
    
    for idx in indexes:
        idx_name = idx[1]
        cursor.execute(f"PRAGMA index_info({idx_name})")
        info['indexes'][idx_name] = cursor.fetchall()
    
    # Contagem de registros
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        info['row_count'] = cursor.fetchone()[0]
    except sqlite3.Error:
        info['row_count'] = 'Erro ao contar registros'
    
    return info

def check_database(db_path):
    """
    Verifica as tabelas em um banco de dados SQLite.
    
    Args:
        db_path: Caminho para o arquivo do banco de dados
    """
    print(f"\n{'='*80}")
    print(f"Analisando banco de dados: {os.path.abspath(db_path)}")
    print(f"{'='*80}")
    
    if not os.path.exists(db_path):
        print("Arquivo não encontrado.")
        return
    
    try:
        # Conecta ao banco de dados
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
        cursor = conn.cursor()
        
        # Informações do arquivo
        file_stats = os.stat(db_path)
        print(f"Tamanho do arquivo: {file_stats.st_size / (1024 * 1024):.2f} MB")
        print(f"Última modificação: {datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Informações do banco de dados
        db_info = get_db_info(conn)
        print(f"\nInformações do SQLite:")
        print(f"- Versão: {db_info['version']}")
        print(f"- Foreign Keys: {'Habilitado' if db_info['foreign_keys'] else 'Desabilitado'}")
        print(f"- Modo Journal: {db_info['journal_mode']}")
        print(f"- Sincronização: {db_info['synchronous']}")
        
        # Lista todas as tabelas no banco de dados
        cursor.execute("""
        SELECT name 
        FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("\nNenhuma tabela encontrada no banco de dados.")
        else:
            print(f"\nTabelas encontradas ({len(tables)}):")
            for table_name in tables:
                print(f"\n{'='*60}")
                print(f"Tabela: {table_name}")
                print(f"{'='*60}")
                
                # Obtém informações detalhadas da tabela
                table_info = get_table_info(conn, table_name)
                
                # Mostra colunas
                print(f"\nColunas ({len(table_info['columns'])}):")
                for col in table_info['columns']:
                    col_def = [
                        col['name'],
                        col['type'],
                        'NOT NULL' if col['notnull'] else '',
                        f"DEFAULT {col['dflt_value']}" if col['dflt_value'] is not None else '',
                        'PRIMARY KEY' if col['pk'] > 0 else ''
                    ]
                    print(f"  - {' '.join(filter(None, col_def))}")
                
                # Mostra contagem de registros
                print(f"\nRegistros: {table_info['row_count']:,}")
                
                # Mostra chaves estrangeiras
                if table_info['foreign_keys']:
                    print("\nChaves estrangeiras:")
                    for fk in table_info['foreign_keys']:
                        print(f"  - {fk['from']} -> {fk['table']}.{fk['to']}")
                
                # Mostra índices
                if table_info['indexes']:
                    print("\nÍndices:")
                    for idx_name, idx_columns in table_info['indexes'].items():
                        cols = ', '.join([col['name'] for col in idx_columns])
                        print(f"  - {idx_name}: ({cols})")
        
        # Verifica tabelas do sistema (opcional)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sqlite_%'")
        system_tables = cursor.fetchall()
        if system_tables:
            print(f"\nTabelas do sistema SQLite ({len(system_tables)}):")
            for table in system_tables:
                print(f"  - {table[0]}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"\nErro ao verificar o banco de dados: {str(e)}")
    except Exception as e:
        print(f"\nErro inesperado: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    # Lista de bancos de dados para verificar
    db_files = [
        'banco/financas.db',  # Banco de dados principal
        'financas.db',        # Possível duplicata
        'upload_arq/financas.db',  # Possível cópia
        'dashboard_arq/analise_financeira.db',  # Banco de dados do dashboard
        'analise_financeira.db'  # Possível cópia antiga
    ]
    
    # Verifica se foi passado algum arquivo como argumento
    if len(sys.argv) > 1:
        db_files = sys.argv[1:]
    
    # Verifica cada banco de dados
    for db_file in db_files:
        # Se for um diretório, verifica se contém arquivos .db
        if os.path.isdir(db_file):
            for root, _, files in os.walk(db_file):
                for file in files:
                    if file.endswith(('.db', '.sqlite', '.sqlite3')):
                        full_path = os.path.join(root, file)
                        check_database(full_path)
        # Se for um arquivo, verifica diretamente
        elif os.path.exists(db_file) or any(x in db_file for x in ['financas.db', '.db', '.sqlite', '.sqlite3']):
            check_database(db_file)
    
    print("\nAnálise concluída!")

if __name__ == "__main__":
    main()
