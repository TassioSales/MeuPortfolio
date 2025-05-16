import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta

def print_header(title, width=80):
    """Imprime um cabeçalho formatado"""
    print("\n" + "="*width)
    print(f"{title.upper():^{width}}")
    print("="*width)

def get_db_connection():
    """Estabelece conexão com o banco de dados"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'banco', 'financas.db')
    
    print(f"\nConectando ao banco de dados: {db_path}")
    print(f"Arquivo existe: {os.path.exists(db_path)}")
    
    if not os.path.exists(db_path):
        print("ERRO: Arquivo do banco de dados não encontrado!")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        print("Conexão com o banco de dados estabelecida com sucesso!")
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

def check_tables(conn):
    """Verifica as tabelas existentes no banco de dados"""
    print_header("verificando tabelas")
    
    cursor = conn.cursor()
    
    # Listar todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    if not tables:
        print("Nenhuma tabela encontrada no banco de dados!")
        return []
    
    table_names = [table[0] for table in tables]
    print(f"Tabelas encontradas: {', '.join(table_names)}")
    
    return table_names

def check_table_structure(conn, table_name):
    """Verifica a estrutura de uma tabela específica"""
    print_header(f"estrutura da tabela: {table_name}")
    
    cursor = conn.cursor()
    
    try:
        # Obter informações das colunas
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        if not columns:
            print(f"Nenhuma coluna encontrada na tabela {table_name}")
            return
            
        print(f"\nColunas da tabela {table_name}:")
        print("-" * 60)
        print(f"{'Nome':<20} {'Tipo':<15} {'Não Nulo':<10} {'Valor Padrão'}")
        print("-" * 60)
        
        for col in columns:
            print(f"{col['name']:<20} {col['type']:<15} {'SIM' if col['notnull'] else 'NÃO':<10} {col['dflt_value']}")
        
        # Verificar índices
        cursor.execute(f"PRAGMA index_list({table_name});")
        indexes = cursor.fetchall()
        
        if indexes:
            print("\nÍndices:")
            for idx in indexes:
                print(f"- Nome: {idx['name']}, Único: {bool(idx['unique'])}")
                
    except sqlite3.Error as e:
        print(f"Erro ao verificar a estrutura da tabela {table_name}: {e}")

def check_data_quality(conn, table_name):
    """Verifica a qualidade dos dados na tabela"""
    print_header(f"verificando qualidade dos dados: {table_name}")
    
    try:
        # Contar registros
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) as total FROM {table_name};")
        total = cursor.fetchone()['total']
        print(f"Total de registros: {total:,}")
        
        if total == 0:
            print("AVISO: A tabela está vazia!")
            return
        
        # Verificar valores nulos em colunas importantes
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [col['name'] for col in cursor.fetchall()]
        
        print("\nVerificando valores nulos:")
        for col in columns:
            cursor.execute(f"SELECT COUNT(*) as total FROM {table_name} WHERE {col} IS NULL;")
            null_count = cursor.fetchone()['total']
            if null_count > 0:
                print(f"- {col}: {null_count:,} valores nulos encontrados")
        
        # Verificar duplicatas
        if 'id' in columns:
            cursor.execute(f"""
                SELECT COUNT(*) as total_duplicatas
                FROM (
                    SELECT id, COUNT(*) as cnt 
                    FROM {table_name}
                    GROUP BY id
                    HAVING COUNT(*) > 1
                ) t;
            """)
            dup_count = cursor.fetchone()['total_duplicatas']
            if dup_count > 0:
                print(f"\nAVISO: {dup_count} IDs duplicados encontrados!")
        
        # Verificar dados recentes
        if 'data' in columns:
            cursor.execute(f"""
                SELECT MIN(data) as mais_antiga, 
                       MAX(data) as mais_recente,
                       COUNT(*) as total_registros
                FROM {table_name};
            """)
            data_info = cursor.fetchone()
            print(f"\nPeríodo dos dados:")
            print(f"- Data mais antiga: {data_info['mais_antiga']}")
            print(f"- Data mais recente: {data_info['mais_recente']}")
            print(f"- Total de registros: {data_info['total_registros']:,}")
            
    except sqlite3.Error as e:
        print(f"Erro ao verificar qualidade dos dados: {e}")

def check_transactions_data(conn):
    """Verifica os dados da tabela de transações"""
    print_header("verificando dados de transações")
    
    try:
        cursor = conn.cursor()
        
        # Verificar totais por tipo
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN valor > 0 THEN 'Receita'
                    WHEN valor < 0 THEN 'Despesa'
                    ELSE 'Zero'
                END as tipo,
                COUNT(*) as total,
                SUM(ABS(valor)) as valor_total
            FROM transacoes
            GROUP BY tipo;
        """)
        
        print("\nResumo de Transações:")
        print("-" * 60)
        print(f"{'Tipo':<15} {'Quantidade':>15} {'Valor Total':>20}")
        print("-" * 60)
        
        for row in cursor.fetchall():
            print(f"{row['tipo']:<15} {row['total']:>15,} {row['valor_total']:>20,.2f}")
        
        # Verificar categorias mais comuns
        cursor.execute("""
            SELECT categoria, COUNT(*) as total, SUM(ABS(valor)) as valor_total
            FROM transacoes
            GROUP BY categoria
            ORDER BY valor_total DESC
            LIMIT 10;
        """)
        
        print("\nTop 10 Categorias:")
        print("-" * 60)
        print(f"{'Categoria':<30} {'Qtd':>10} {'Valor Total':>20}")
        print("-" * 60)
        
        for row in cursor.fetchall():
            print(f"{row['categoria']:<30} {row['total']:>10,} {row['valor_total']:>20,.2f}")
        
    except sqlite3.Error as e:
        print(f"Erro ao verificar dados de transações: {e}")

def check_data_consistency(conn):
    """Verifica a consistência dos dados entre tabelas"""
    print_header("verificando consistência dos dados")
    
    try:
        cursor = conn.cursor()
        
        # Verificar se há categorias sem transações
        cursor.execute("""
            SELECT c.nome as categoria, 
                   COUNT(t.id) as total_transacoes,
                   COUNT(DISTINCT strftime('%Y-%m', t.data)) as meses_com_transacoes
            FROM categorias c
            LEFT JOIN transacoes t ON c.nome = t.categoria
            GROUP BY c.nome
            ORDER BY total_transacoes DESC;
        """)
        
        print("\nUso de Categorias:")
        print("-" * 80)
        print(f"{'Categoria':<30} {'Transações':>15} {'Meses com Transações':>25}")
        print("-" * 80)
        
        for row in cursor.fetchall():
            print(f"{row['categoria']:<30} {row['total_transacoes']:>15,} {row['meses_com_transacoes']:>25,}")
        
    except sqlite3.Error as e:
        print(f"Erro ao verificar consistência dos dados: {e}")

def main():
    print_header("verificação do banco de dados")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^80}")
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        # Verificar tabelas existentes
        tables = check_tables(conn)
        
        # Verificar estrutura e dados de cada tabela
        for table in tables:
            check_table_structure(conn, table)
            check_data_quality(conn, table)
        
        # Verificações específicas para a tabela de transações
        if 'transacoes' in tables:
            check_transactions_data(conn)
        
        # Verificar consistência entre tabelas
        if 'categorias' in tables and 'transacoes' in tables:
            check_data_consistency(conn)
        
    finally:
        conn.close()
        print("\nConexão com o banco de dados fechada.")

if __name__ == "__main__":
    main()