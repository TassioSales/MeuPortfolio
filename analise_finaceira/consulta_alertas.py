import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'banco', 'financas.db')

def consulta_alertas():
    if not os.path.exists(DB_PATH):
        print(f"Banco de dados não encontrado: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, descricao, ativo, data_inicio, data_fim FROM alertas_financas')
        rows = cursor.fetchall()
        if not rows:
            print("Nenhum alerta encontrado na tabela.")
        else:
            print(f"Total de registros encontrados: {len(rows)}\n")
            print(f"{'ID':<5} {'Ativo':<5} {'Descrição':<30} {'Início':<12} {'Fim':<12}")
            print('-'*70)
            for row in rows:
                print(f"{row[0]:<5} {row[2]:<5} {row[1]:<30} {row[3]:<12} {row[4]:<12}")
    except Exception as e:
        print(f"Erro ao consultar registros: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    consulta_alertas()
