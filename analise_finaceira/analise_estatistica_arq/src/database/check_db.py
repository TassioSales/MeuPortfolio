import sqlite3
from prettytable import PrettyTable

def check_database():
    # Conectar ao banco de dados
    conn = sqlite3.connect('transacoes.db')
    cursor = conn.cursor()
    
    # Verificar se a tabela existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transacoes'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        print("Tabela 'transacoes' não existe no banco de dados.")
        return
    
    # Obter informações das colunas
    cursor.execute("PRAGMA table_info(transacoes)")
    columns = cursor.fetchall()
    
    # Criar tabela formatada para mostrar as colunas
    table = PrettyTable()
    table.field_names = ["ID", "Nome", "Tipo", "Não Nulo", "Padrão", "PK"]
    
    for col in columns:
        table.add_row(col)
    
    print("\nEstrutura da tabela transacoes:")
    print(table)
    
    # Verificar quantas linhas existem
    cursor.execute("SELECT COUNT(*) FROM transacoes")
    row_count = cursor.fetchone()[0]
    print(f"\nNúmero de registros na tabela: {row_count}")
    
    # Verificar se existem dados em algumas colunas importantes
    important_columns = ['data', 'valor', 'ativo', 'tipo', 'quantidade', 'tipo_operacao']
    print("\nVerificando dados em colunas importantes:")
    for col in important_columns:
        cursor.execute(f"SELECT COUNT(*) FROM transacoes WHERE {col} IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"- {col}: {count} registros com dados")
    
    conn.close()

if __name__ == '__main__':
    check_database()
