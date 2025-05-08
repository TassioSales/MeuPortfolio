import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'banco', 'financas.db')

def limpar_alertas():
    if not os.path.exists(DB_PATH):
        print(f"Banco de dados não encontrado: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM alertas_financas;')
        conn.commit()
        print("Todos os registros da tabela alertas_financas foram apagados!")
    except Exception as e:
        print(f"Erro ao apagar registros: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    limpar_alertas()
