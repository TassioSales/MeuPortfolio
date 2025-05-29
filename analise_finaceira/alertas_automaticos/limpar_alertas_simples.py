"""
Script simples para limpar a tabela de alertas_automaticos.
Caminho do banco de dados: D:/Github/MeuPortfolio/analise_finaceira/banco/financas.db
"""
import sqlite3
import os
import shutil
from datetime import datetime

def fazer_backup_banco(db_path):
    """Cria um backup do banco de dados."""
    try:
        backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'financas_backup_{timestamp}.db')
        
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup criado com sucesso em: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        return False

def limpar_tabela_alertas():
    """Limpa a tabela de alertas_automaticos."""
    db_path = r"D:/Github/MeuPortfolio/analise_finaceira/banco/financas.db"
    
    print("\n=== LIMPEZA DA TABELA DE ALERTAS AUTOMÁTICOS ===")
    print(f"Banco de dados: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Erro: O arquivo do banco de dados não foi encontrado em {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Conta o total de alertas
        cursor.execute("SELECT COUNT(*) FROM alertas_automaticos")
        total_alertas = cursor.fetchone()[0]
        
        if total_alertas == 0:
            print("\nℹ️  A tabela de alertas_automaticos já está vazia.")
            return
            
        print(f"\nℹ️  Total de alertas encontrados: {total_alertas}")
        
        # Mostra exemplos
        cursor.execute("""
            SELECT id, titulo, data_ocorrencia, valor 
            FROM alertas_automaticos 
            ORDER BY data_ocorrencia DESC 
            LIMIT 3
        """)
        
        print("\n📋 Exemplos de alertas que serão removidos:")
        print("-" * 80)
        for alerta in cursor.fetchall():
            print(f"ID: {alerta[0]}, Data: {alerta[2]}, Valor: R$ {alerta[3]:.2f}, Título: {alerta[1]}")
        print("-" * 80)
        
        # Pede confirmação
        confirmacao = input(f"\n⚠️  ATENÇÃO: Você tem certeza que deseja remover TODOS os {total_alertas} alertas? (s/n): ")
        
        if confirmacao.lower() != 's':
            print("\nOperação cancelada pelo usuário.")
            return
            
        # Cria backup
        print("\nCriando backup do banco de dados...")
        if not fazer_backup_banco(db_path):
            confirmacao = input("\n⚠️  Não foi possível criar o backup. Deseja continuar mesmo assim? (s/n): ")
            if confirmacao.lower() != 's':
                print("\nOperação cancelada pelo usuário.")
                return
        
        # Limpa a tabela
        cursor.execute("DELETE FROM alertas_automaticos")
        conn.commit()
        
        # Verifica se foi limpo
        cursor.execute("SELECT COUNT(*) FROM alertas_automaticos")
        total_apos = cursor.fetchone()[0]
        
        if total_apos == 0:
            print(f"\n✅ Sucesso! Todos os {total_alertas} alertas foram removidos.")
        else:
            print(f"\n⚠️  Aviso: Aparentemente não foi possível remover todos os alertas. Restaram {total_apos} registros.")
            
    except sqlite3.Error as e:
        print(f"\n❌ Erro ao acessar o banco de dados: {e}")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    limpar_tabela_alertas()
    input("\nPressione Enter para sair...")
