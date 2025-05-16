import sqlite3
import os

def check_database(db_path):
    print(f"\nVerificando banco de dados: {os.path.abspath(db_path)}")
    print("=" * 80)
    
    if not os.path.exists(db_path):
        print("Arquivo não encontrado.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Lista todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("Nenhuma tabela encontrada no banco de dados.")
        else:
            print(f"\nTabelas encontradas ({len(tables)}):")
            for table in tables:
                table_name = table[0]
                print(f"\n=== {table_name} ===")
                
                # Mostra a estrutura da tabela
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                print("Colunas:")
                for col in columns:
                    print(f"  - {col[1]} ({col[2]})")
                
                # Conta registros
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                print(f"  Total de registros: {count}")
                
                # Verifica índices
                cursor.execute(f"PRAGMA index_list({table_name});")
                indexes = cursor.fetchall()
                if indexes:
                    print("  Índices:")
                    for idx in indexes:
                        print(f"    - {idx[1]}")
                
                # Verifica chaves estrangeiras
                cursor.execute(f"PRAGMA foreign_key_list({table_name});")
                fks = cursor.fetchall()
                if fks:
                    print("  Chaves estrangeiras:")
                    for fk in fks:
                        print(f"    - {fk[3]} -> {fk[2]}.{fk[4]}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Erro ao verificar o banco de dados: {str(e)}")
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")

if __name__ == "__main__":
    db_path = "banco/financas.db"
    if len(os.sys.argv) > 1:
        db_path = os.sys.argv[1]
    check_database(db_path)
