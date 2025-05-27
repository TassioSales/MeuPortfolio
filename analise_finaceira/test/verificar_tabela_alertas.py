import sqlite3
import os
from pathlib import Path

def verificar_estrutura_tabela():
    # Caminho para o banco de dados
    db_path = os.path.join(Path(__file__).parent, 'banco', 'financas.db')
    
    if not os.path.exists(db_path):
        print(f"Erro: O arquivo do banco de dados não foi encontrado em {db_path}")
        return
    
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alertas_financas'")
        if not cursor.fetchone():
            print("A tabela 'alertas_financas' não existe no banco de dados.")
            return
        
        # Obter informações sobre as colunas da tabela
        cursor.execute("PRAGMA table_info(alertas_financas)")
        colunas = cursor.fetchall()
        
        if not colunas:
            print("A tabela 'alertas_financas' não possui colunas.")
            return
        
        print("\nEstrutura da tabela 'alertas_financas':")
        print("-" * 80)
        print(f"{'Nome':<20} | {'Tipo':<15} | Pode ser NULL | Valor Padrão")
        print("-" * 80)
        
        for coluna in colunas:
            cid, name, type_, notnull, dflt_value, pk = coluna
            print(f"{name:<20} | {type_:<15} | {'Não' if notnull else 'Sim':<13} | {dflt_value if dflt_value is not None else 'NULL'}")
        
        # Verificar índices
        cursor.execute("PRAGMA index_list('alertas_financas')")
        indices = cursor.fetchall()
        
        if indices:
            print("\nÍndices na tabela 'alertas_financas':")
            print("-" * 80)
            for idx in indices:
                idx_name = idx[1]
                cursor.execute(f"PRAGMA index_info('{idx_name}')")
                idx_info = cursor.fetchall()
                colunas_idx = [info[2] for info in idx_info]
                print(f"Índice: {idx_name}")
                print(f"Colunas: {', '.join(colunas_idx)}")
                print("-" * 40)
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")

if __name__ == "__main__":
    verificar_estrutura_tabela()
