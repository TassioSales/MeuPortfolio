import sqlite3
import os
from pathlib import Path

def verificar_colunas():
    db_path = os.path.join(Path(__file__).parent, 'banco', 'financas.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obter todas as colunas da tabela
        cursor.execute("SELECT * FROM alertas_financas LIMIT 0")
        colunas = [descricao[0] for descricao in cursor.description]
        
        print("Colunas na tabela alertas_financas:")
        for coluna in colunas:
            print(f"- {coluna}")
            
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")

if __name__ == "__main__":
    verificar_colunas()
