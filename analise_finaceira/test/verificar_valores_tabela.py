import sqlite3
import os
from pathlib import Path

def verificar_valores_tabela():
    # Caminho para o banco de dados
    db_path = os.path.join(Path(__file__).parent, 'banco', 'financas.db')
    
    if not os.path.exists(db_path):
        print(f"Erro: O arquivo do banco de dados não foi encontrado em {db_path}")
        return
    
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
        cursor = conn.cursor()
        
        # Verificar se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alertas_financas'")
        if not cursor.fetchone():
            print("A tabela 'alertas_financas' não existe no banco de dados.")
            return
        
        # Obter informações sobre as colunas da tabela
        cursor.execute("PRAGMA table_info(alertas_financas)")
        colunas = [col[1] for col in cursor.fetchall()]
        
        print(f"\nColunas encontradas na tabela 'alertas_financas': {', '.join(colunas)}\n")
        
        # Contar o número de registros
        cursor.execute("SELECT COUNT(*) as total FROM alertas_financas")
        total_registros = cursor.fetchone()[0]
        print(f"Total de registros na tabela: {total_registros}\n")
        
        if total_registros > 0:
            # Obter os primeiros 5 registros para visualização
            cursor.execute("SELECT * FROM alertas_financas LIMIT 5")
            registros = cursor.fetchall()
            
            print("Amostra dos registros (primeiros 5):")
            print("-" * 80)
            
            # Imprimir cabeçalhos
            print(" | ".join(f"{col:<15}" for col in colunas))
            print("-" * 80)
            
            # Imprimir registros
            for registro in registros:
                valores = []
                for col in colunas:
                    valor = registro[col] if col in registro.keys() else "NULL"
                    if isinstance(valor, str) and len(str(valor)) > 15:
                        valor = str(valor)[:12] + "..."
                    valores.append(f"{str(valor):<15}")
                print(" | ".join(valores))
            
            if total_registros > 5:
                print(f"\n... e mais {total_registros - 5} registros")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")

if __name__ == "__main__":
    verificar_valores_tabela()
