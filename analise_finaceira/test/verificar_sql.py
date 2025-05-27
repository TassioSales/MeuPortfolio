import sqlite3
import os
from pathlib import Path

def verificar_banco():
    db_path = os.path.join(Path(__file__).parent, 'banco', 'financas.db')
    
    if not os.path.exists(db_path):
        print(f"Erro: O arquivo do banco de dados não foi encontrado em {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obter informações da tabela
        cursor.execute("PRAGMA table_info(alertas_financas)")
        colunas = cursor.fetchall()
        
        print("\nEstrutura da tabela 'alertas_financas':")
        for col in colunas:
            print(f"- {col[1]} ({col[2]})")
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM alertas_financas")
        total = cursor.fetchone()[0]
        print(f"\nTotal de registros: {total}")
        
        # Mostrar alguns registros
        if total > 0:
            print("\nPrimeiros 3 registros:")
            cursor.execute("SELECT * FROM alertas_financas LIMIT 3")
            for linha in cursor.fetchall():
                print(linha)
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")

if __name__ == "__main__":
    verificar_banco()
