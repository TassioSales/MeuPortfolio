import sqlite3
import os

def verificar_tabela_alertas():
    """Conecta ao banco de dados e exibe todas as linhas da tabela alertas_financas."""
    try:
        # Constrói o caminho para o banco de dados
        # Assumindo que este script está na raiz do projeto e o banco está em 'banco/financas.db'
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'banco', 'financas.db')

        print(f"Tentando conectar ao banco de dados em: {db_path}")

        if not os.path.exists(db_path):
            print(f"Erro: Arquivo do banco de dados não encontrado em {db_path}")
            return

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Acessar colunas pelo nome
        cursor = conn.cursor()

        print("Conexão com o banco de dados estabelecida.")

        # Imprime o esquema da tabela
        print("\n--- Esquema da Tabela 'alertas_financas' ---")
        cursor.execute('PRAGMA table_info(alertas_financas)')
        schema_rows = cursor.fetchall()
        if not schema_rows:
            print("Não foi possível obter o esquema da tabela 'alertas_financas'.")
        else:
            print(f"{'Coluna':<20} | {'Tipo':<15} | {'Not Null':<8} | {'Default':<10} | {'PK':<3}")
            print("-" * 70)
            for row in schema_rows:
                print(f"{row['name']:<20} | {row['type']:<15} | {str(bool(row['notnull'])):<8} | {str(row['dflt_value']):<10} | {str(bool(row['pk'])):<3}")

        # Executa a consulta para buscar os dados (COMENTADO PARA ESTE TESTE)
        # cursor.execute('SELECT * FROM alertas_financas')
        # rows = cursor.fetchall()

        # if not rows:
        #     print("\nA tabela 'alertas_financas' está vazia ou não existe.")
        # else:
        #     # Imprime os nomes das colunas
        #     column_names = [description[0] for description in cursor.description]
        #     print("\n--- Conteúdo da Tabela 'alertas_financas' ---")
        #     print(" | ".join(column_names))
        #     print("-" * (sum(len(name) for name in column_names) + (len(column_names) -1) * 3))

        #     # Imprime as linhas
        #     for row in rows:
        #         print(" | ".join(str(row[col]) for col in column_names))
        #     print("\n--- Fim do Conteúdo ---")
        #     print(f"Total de {len(rows)} linhas encontradas.")

    except sqlite3.Error as e:
        print(f"Erro ao interagir com o banco de dados: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("Conexão com o banco de dados fechada.")

if __name__ == '__main__':
    verificar_tabela_alertas()
