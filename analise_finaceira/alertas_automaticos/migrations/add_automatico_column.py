import sqlite3
import os
from pathlib import Path

def run_migration():
    # Caminho para o banco de dados
    db_path = os.path.join(Path(__file__).parent.parent, '..', 'banco', 'financas.db')
    
    try:
        # Conecta ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica se a coluna já existe
        cursor.execute("PRAGMA table_info(alertas_automaticos)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'automatico' not in columns:
            # Adiciona a coluna automatico se não existir
            cursor.execute("""
                ALTER TABLE alertas_automaticos 
                ADD COLUMN automatico BOOLEAN NOT NULL DEFAULT 0
            """)
            conn.commit()
            print("Coluna 'automatico' adicionada com sucesso à tabela 'alertas_automaticos'.")
        else:
            print("A coluna 'automatico' já existe na tabela 'alertas_automaticos'.")
            
    except sqlite3.Error as e:
        print(f"Erro ao executar migração: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
