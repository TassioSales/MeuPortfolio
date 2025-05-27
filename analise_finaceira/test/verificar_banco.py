import os
import sqlite3
from pathlib import Path
import sys

# Adicionar o diretório raiz ao path para importar os módulos
root_dir = str(Path(__file__).parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Importar a configuração do banco de dados do módulo de alertas manuais
from alertas_manuais.config import Config

def verificar_estrutura_banco():
    """Verifica a estrutura do banco de dados e da tabela de alertas."""
    db_path = Config.DATABASE_PATH
    print(f"\n=== Verificando banco de dados em: {db_path} ===")
    
    # Verificar se o arquivo do banco de dados existe
    if not os.path.exists(db_path):
        print("❌ O arquivo do banco de dados não existe.")
        print(f"Caminho verificado: {db_path}")
        return
    
    print("✅ Arquivo do banco de dados encontrado.")
    
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar tabelas existentes
        print("\n📋 Tabelas no banco de dados:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = cursor.fetchall()
        
        if not tabelas:
            print("❌ Nenhuma tabela encontrada no banco de dados.")
            return
            
        for tabela in tabelas:
            print(f"- {tabela[0]}")
        
        # Verificar se a tabela de alertas existe
        tabela_alertas = 'alertas'  # ou 'alertas_financas' se for o caso
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabela_alertas}'")
        tabela_existe = cursor.fetchone() is not None
        
        if not tabela_existe:
            print(f"\n❌ A tabela '{tabela_alertas}' não foi encontrada no banco de dados.")
            return
        
        print(f"\n✅ Tabela '{tabela_alertas}' encontrada.")
        
        # Obter informações sobre as colunas
        print(f"\n📋 Estrutura da tabela '{tabela_alertas}':")
        cursor.execute(f"PRAGMA table_info({tabela_alertas})")
        colunas = cursor.fetchall()
        
        if not colunas:
            print("❌ Não foi possível obter informações sobre as colunas da tabela.")
            return
        
        # Exibir informações sobre as colunas
        print("\n🔍 Colunas:")
        print(f"{'Nome':<20} {'Tipo':<15} {'Pode ser NULL':<15} {'Valor Padrão':<15} {'Chave Primária'}")
        print("-" * 80)
        
        for coluna in colunas:
            cid, name, type_, notnull, dflt_value, pk = coluna
            print(f"{name:<20} {type_:<15} {'NÃO' if notnull else 'SIM':<15} {str(dflt_value)[:15]:<15} {'PK' if pk else ''}")
        
        # Verificar índices
        print("\n🔍 Índices:")
        cursor.execute(f"PRAGMA index_list({tabela_alertas})")
        indices = cursor.fetchall()
        
        if not indices:
            print("Nenhum índice encontrado.")
        else:
            for idx in indices:
                idx_name = idx[1]
                print(f"\nÍndice: {idx_name}")
                cursor.execute(f"PRAGMA index_info({idx_name})")
                colunas_idx = cursor.fetchall()
                print("  Colunas:", ", ".join([col[2] for col in colunas_idx]))
        
        # Verificar alguns registros de exemplo
        try:
            cursor.execute(f"SELECT * FROM {tabela_alertas} LIMIT 3")
            registros = cursor.fetchall()
            
            if registros:
                print(f"\n📝 Primeiros {len(registros)} registros:")
                colunas = [desc[0] for desc in cursor.description]
                print(", ".join(colunas))
                
                for registro in registros:
                    print(registro)
            else:
                print("\nℹ️ A tabela está vazia.")
                
        except sqlite3.Error as e:
            print(f"\n⚠️ Não foi possível ler registros da tabela: {e}")
    
    except sqlite3.Error as e:
        print(f"\n❌ Erro ao acessar o banco de dados: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    verificar_estrutura_banco()
    print("\n✅ Verificação concluída.")
