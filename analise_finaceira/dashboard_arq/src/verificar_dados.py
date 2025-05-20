import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path
from logger import get_logger
import os

# Configura o logger
logger = get_logger("dashboard.verificar_dados")

def conectar_banco():
    """Conecta ao banco de dados SQLite."""
    try:
        base_dir = str(Path(__file__).parent.parent.parent)
        db_path = os.path.join(base_dir, 'banco', 'financas.db')
        logger.debug(f"Conectando ao banco em: {db_path}")
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        logger.error(f"Erro ao conectar ao banco: {e}", exc_info=True)
        raise

def verificar_dados_receitas():
    """
    Verifica os dados de receitas no banco de dados e mostra estatísticas.
    """
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Verificar estrutura da tabela
        cursor.execute("PRAGMA table_info(transacoes)")
        columns = cursor.fetchall()
        logger.info("Colunas da tabela transacoes:")
        for col in columns:
            logger.info(f"{col[1]}: {col[2]}")
        
        # Verificar total de registros
        cursor.execute("SELECT COUNT(*) FROM transacoes")
        total_registros = cursor.fetchone()[0]
        logger.info(f"Total de registros na tabela: {total_registros}")
        
        # Verificar valores positivos e negativos
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END) as total_positivo,
                SUM(CASE WHEN valor < 0 THEN valor ELSE 0 END) as total_negativo,
                COUNT(CASE WHEN valor > 0 THEN 1 END) as qtd_positivo,
                COUNT(CASE WHEN valor < 0 THEN 1 END) as qtd_negativo
            FROM transacoes
        """)
        resultados = cursor.fetchone()
        logger.info(f"\nValores positivos: R$ {resultados[0]:,.2f} ({resultados[2]} registros)")
        logger.info(f"Valores negativos: R$ {resultados[1]:,.2f} ({resultados[3]} registros)")
        
        # Verificar categorias de receita
        cursor.execute("""
            SELECT categoria, COUNT(*) as qtd, SUM(valor) as total
            FROM transacoes
            WHERE valor > 0
            GROUP BY categoria
            ORDER BY total DESC
        """)
        categorias = cursor.fetchall()
        logger.info("\nCategorias de receita:")
        for cat, qtd, total in categorias:
            logger.info(f"{cat}: {qtd} registros, R$ {total:,.2f}")
        
        # Verificar valores extremos
        cursor.execute("""
            SELECT 
                MIN(valor) as menor_valor,
                MAX(valor) as maior_valor,
                AVG(valor) as media_valor
            FROM transacoes
            WHERE valor > 0
        """)
        extremos = cursor.fetchone()
        logger.info(f"\nValores extremos:")
        logger.info(f"Menor valor positivo: R$ {extremos[0]:,.2f}")
        logger.info(f"Maior valor positivo: R$ {extremos[1]:,.2f}")
        logger.info(f"Média dos valores positivos: R$ {extremos[2]:,.2f}")
        
        # Verificar valores duplicados
        cursor.execute("""
            SELECT categoria, valor, COUNT(*) as qtd
            FROM transacoes
            WHERE valor > 0
            GROUP BY categoria, valor
            HAVING COUNT(*) > 1
            ORDER BY qtd DESC
        """)
        duplicados = cursor.fetchall()
        if duplicados:
            logger.info("\nValores duplicados encontrados:")
            for cat, val, qtd in duplicados:
                logger.info(f"{cat}: R$ {val:.2f} aparece {qtd} vezes")
        else:
            logger.info("\nNenhum valor duplicado encontrado")
        
        # Verificar datas
        cursor.execute("""
            SELECT 
                MIN(data) as data_mais_antiga,
                MAX(data) as data_mais_recente,
                COUNT(DISTINCT data) as dias_unicos
            FROM transacoes
            WHERE valor > 0
        """)
        datas = cursor.fetchone()
        logger.info(f"\nDatas:")
        logger.info(f"Data mais antiga: {datas[0]}")
        logger.info(f"Data mais recente: {datas[1]}")
        logger.info(f"Dias únicos: {datas[2]}")
        
    except Exception as e:
        logger.error(f"Erro ao verificar dados: {e}", exc_info=True)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logger.info("Iniciando verificação de dados de receitas")
    verificar_dados_receitas()
