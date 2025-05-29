import sqlite3
import os

def verificar_tabela():
    try:
        # Caminho para o banco de dados
        db_path = os.path.join('banco', 'financas.db')
        
        # Verificar se o arquivo do banco de dados existe
        if not os.path.exists(db_path):
            print(f"Erro: O arquivo do banco de dados não foi encontrado em {db_path}")
            return
            
        # Conectar ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alertas_automaticos'")
        tabela = cursor.fetchone()
        
        if tabela:
            print(f"A tabela 'alertas_automaticos' existe no banco de dados.")
            
            # Contar o número de registros na tabela
            cursor.execute("SELECT COUNT(*) FROM alertas_automaticos")
            count = cursor.fetchone()[0]
            print(f"Número de registros na tabela: {count}")
            
            # Mostrar os primeiros 5 registros, se houver
            if count > 0:
                print("\nPrimeiros 5 registros:")
                cursor.execute("SELECT * FROM alertas_automaticos LIMIT 5")
                colunas = [desc[0] for desc in cursor.description]
                print(" | ".join(colunas))
                print("-" * 80)
                for linha in cursor.fetchall():
                    print(" | ".join(str(campo) for campo in linha))
        else:
            print("A tabela 'alertas_automaticos' NÃO foi encontrada no banco de dados.")
            
            # Mostrar todas as tabelas existentes
            print("\nTabelas existentes no banco de dados:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for tabela in cursor.fetchall():
                print(f"- {tabela[0]}")
        
        conn.close()
        
    except Exception as e:
        print(f"Erro ao verificar o banco de dados: {str(e)}")

if __name__ == "__main__":
    verificar_tabela()
