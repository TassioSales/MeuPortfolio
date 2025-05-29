import sqlite3
import os
from pathlib import Path

def verificar_tabelas():
    # Caminho para o banco de dados na pasta 'banco'
    db_path = os.path.join(os.path.dirname(__file__), 'banco', 'financas.db')
    
    print(f"Verificando banco de dados em: {db_path}")
    
    # Verifica se o arquivo do banco de dados existe
    if not os.path.exists(db_path):
        print("ERRO: O arquivo do banco de dados não foi encontrado!")
        return
    
    # Tamanho do arquivo em bytes
    tamanho = os.path.getsize(db_path)
    print(f"Tamanho do arquivo: {tamanho} bytes")
    
    try:
        # Conecta ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Consulta todas as tabelas no banco de dados
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        
        # Obtém os resultados
        tabelas = cursor.fetchall()
        
        if not tabelas:
            print("\nNenhuma tabela encontrada no banco de dados.")
        else:
            print(f"\nTabelas encontradas ({len(tabelas)}):")
            for i, tabela in enumerate(tabelas, 1):
                print(f"{i}. {tabela[0]}")
                
                # Para cada tabela, mostra as colunas
                cursor.execute(f"PRAGMA table_info({tabela[0]});")
                colunas = cursor.fetchall()
                print(f"   Colunas ({len(colunas)}):")
                for coluna in colunas:
                    print(f"   - {coluna[1]} ({coluna[2]})")
                print()  # Linha em branco entre tabelas
        
    except sqlite3.Error as e:
        print(f"\nERRO ao acessar o banco de dados: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=== Verificador de Banco de Dados ===\n")
    verificar_tabelas()
    print("\nVerificação concluída.")
