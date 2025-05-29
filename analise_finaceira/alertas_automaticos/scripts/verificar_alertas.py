"""
Script para verificar os alertas na tabela alertas_automaticos.
"""
import sqlite3
import os
import sys
from datetime import datetime

# Adiciona o diretório raiz ao path para importar o logger
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, LogLevel
# Adiciona o diretório src ao path para importar o config
src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)

from config import CONFIG

def listar_alertas():
    """Lista todos os alertas da tabela alertas_automaticos."""
    # Configura o logger
    logger = get_logger('verificar_alertas')
    logger.level(LogLevel.INFO)
    
    db_path = CONFIG['db_path']
    
    try:
        # Conecta ao banco de dados
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
        cursor = conn.cursor()
        
        # Conta o total de alertas
        cursor.execute("SELECT COUNT(*) as total FROM alertas_automaticos")
        total_alertas = cursor.fetchone()['total']
        
        print(f"\n{'='*80}")
        print(f"TOTAL DE ALERTAS ENCONTRADOS: {total_alertas}")
        print(f"{'='*80}")
        
        if total_alertas == 0:
            print("Nenhum alerta encontrado na tabela.")
            return
        
        # Lista os alertas mais recentes (últimos 20)
        cursor.execute("""
            SELECT 
                id, 
                titulo, 
                strftime('%d/%m/%Y %H:%M', data_ocorrencia) as data_ocorrencia,
                valor,
                prioridade,
                status
            FROM alertas_automaticos 
            ORDER BY data_ocorrencia DESC 
            LIMIT 20
        """)
        
        alertas = cursor.fetchall()
        
        print("\nÚLTIMOS ALERTAS REGISTRADOS:")
        print("-" * 100)
        print(f"{'ID':<5} | {'DATA':<16} | {'PRIORIDADE':<10} | {'STATUS':<10} | {'VALOR':>15} | {'TÍTULO'}")
        print("-" * 100)
        
        for alerta in alertas:
            print(f"{alerta['id']:<5} | {alerta['data_ocorrencia']:<16} | {alerta['prioridade']:<10} | "
                  f"{alerta['status']:<10} | R$ {float(alerta['valor'] or 0):>10.2f} | {alerta['titulo']}")
        
        # Mostra contagem por status
        cursor.execute("""
            SELECT 
                status,
                COUNT(*) as total
            FROM alertas_automaticos
            GROUP BY status
            ORDER BY total DESC
        """)
        
        print("\nTOTAL DE ALERTAS POR STATUS:")
        print("-" * 30)
        for row in cursor.fetchall():
            print(f"{row['status']:<15}: {row['total']:>3}")
        
        # Mostra contagem por prioridade
        cursor.execute("""
            SELECT 
                prioridade,
                COUNT(*) as total
            FROM alertas_automaticos
            GROUP BY prioridade
            ORDER BY total DESC
        """)
        
        print("\nTOTAL DE ALERTAS POR PRIORIDADE:")
        print("-" * 30)
        for row in cursor.fetchall():
            print(f"{row['prioridade']:<15}: {row['total']:>3}")
        
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=== VERIFICADOR DE ALERTAS ===")
    print(f"Banco de dados: {CONFIG['db_path']}")
    listar_alertas()
    print("\nFim da verificação.")
