import sqlite3
import os

def verificar_banco():
    db_path = r"D:\Github\MeuPortfolio\analise_finaceira\banco\financas.db"
    
    if not os.path.exists(db_path):
        print(f"Erro: O arquivo do banco de dados não foi encontrado em: {db_path}")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar tabelas existentes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = cursor.fetchall()
        
        print("Tabelas encontradas no banco de dados:")
        for tabela in tabelas:
            print(f"- {tabela[0]}")
            
            # Verificar colunas de cada tabela
            cursor.execute(f"PRAGMA table_info({tabela[0]})")
            colunas = cursor.fetchall()
            print(f"  Colunas: {[col[1] for col in colunas]}")
            
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    verificar_banco()
