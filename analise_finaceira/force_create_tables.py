import os
import sys
import sqlite3
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = str(Path(__file__).parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Importa a função de criação de tabelas
from upload_arq.src.processamento import create_tables, DB_PATH

def main():
    print(f"Iniciando criação de tabelas no banco: {DB_PATH}")
    
    # Garante que o diretório do banco de dados existe
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        print(f"Criando diretório do banco de dados: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)
    
    try:
        # Tenta criar as tabelas
        print("Chamando a função create_tables()...")
        create_tables()
        print("Tabelas criadas com sucesso!")
        
        # Verifica se as tabelas foram criadas
        print("\nVerificando tabelas no banco de dados...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Lista todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("Nenhuma tabela encontrada no banco de dados.")
        else:
            print(f"Tabelas encontradas ({len(tables)}):")
            for table in tables:
                print(f"- {table[0]}")
                
                # Mostra a estrutura de cada tabela
                cursor.execute(f"PRAGMA table_info({table[0]});")
                columns = cursor.fetchall()
                print(f"  Colunas ({len(columns)}):")
                for column in columns:
                    print(f"  - {column[1]} ({column[2]})")
        
        conn.close()
        
    except Exception as e:
        print(f"Erro ao criar tabelas: {str(e)}")
        import traceback
        traceback.print_exc()
    
    input("Pressione Enter para sair...")

if __name__ == "__main__":
    main()
