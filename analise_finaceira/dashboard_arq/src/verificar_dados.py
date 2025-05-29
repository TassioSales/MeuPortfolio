import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
    Verifica os dados de receitas e despesas no banco de dados, incluindo todas as colunas.
    """
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Verificar estrutura da tabela
        cursor.execute("PRAGMA table_info(transacoes)")
        columns = cursor.fetchall()
        logger.info("\n=== Estrutura da Tabela transacoes ===")
        for col in columns:
            logger.info(f"Coluna: {col[1]} - tipo: {col[2]} - Não Nulo: {col[3]} - PK: {col[5]}")
        
        # Verificar total de registros
        cursor.execute("SELECT COUNT(*) FROM transacoes")
        total_registros = cursor.fetchone()[0]
        logger.info(f"\nTotal de registros na tabela: {total_registros}")
        
        # Verificar distribuição por tipo
        cursor.execute("""
            SELECT tipo, COUNT(*) as qtd, SUM(valor) as total
            FROM transacoes
            GROUP BY tipo
            ORDER BY tipo
        """)
        tipos = cursor.fetchall()
        logger.info("\n=== Distribuição por tipo ===")
        for tipo, qtd, total in tipos:
            logger.info(f"tipo: {tipo} - Registros: {qtd} - Total: R$ {total:,.2f}")
        
        # Verificar distribuição por tipo_operacao
        cursor.execute("""
            SELECT tipo_operacao, COUNT(*) as qtd, SUM(valor) as total
            FROM transacoes
            WHERE tipo_operacao IS NOT NULL
            GROUP BY tipo_operacao
            ORDER BY tipo_operacao
        """)
        operacoes = cursor.fetchall()
        logger.info("\n=== Distribuição por tipo de Operação ===")
        for operacao, qtd, total in operacoes:
            logger.info(f"Operação: {operacao} - Registros: {qtd} - Total: R$ {total:,.2f}")
        
        # Verificar categorias
        cursor.execute("""
            SELECT categoria, COUNT(*) as qtd, SUM(valor) as total
            FROM transacoes
            WHERE categoria IS NOT NULL
            GROUP BY categoria
            ORDER BY total DESC
        """)
        categorias = cursor.fetchall()
        logger.info("\n=== categorias ===")
        for cat, qtd, total in categorias:
            logger.info(f"categoria: {cat} - Registros: {qtd} - Total: R$ {total:,.2f}")
        
        # Verificar valores extremos
        cursor.execute("""
            SELECT 
                MIN(valor) as menor_valor,
                MAX(valor) as maior_valor,
                AVG(valor) as media_valor,
                MIN(preco) as menor_preco,
                MAX(preco) as maior_preco,
                AVG(preco) as media_preco
            FROM transacoes
        """)
        extremos = cursor.fetchone()
        logger.info("\n=== Valores Extremos ===")
        logger.info(f"Menor valor: R$ {extremos[0]:,.2f}")
        logger.info(f"Maior valor: R$ {extremos[1]:,.2f}")
        logger.info(f"Média dos valores: R$ {extremos[2]:,.2f}")
        logger.info(f"Menor preço: R$ {extremos[3]:,.2f}")
        logger.info(f"Maior preço: R$ {extremos[4]:,.2f}")
        logger.info(f"Média dos preços: R$ {extremos[5]:,.2f}")
        
        # Verificar formas de pagamento
        cursor.execute("""
            SELECT forma_pagamento, COUNT(*) as qtd, SUM(valor) as total
            FROM transacoes
            WHERE forma_pagamento IS NOT NULL
            GROUP BY forma_pagamento
            ORDER BY total DESC
        """)
        formas_pag = cursor.fetchall()
        logger.info("\n=== Formas de Pagamento ===")
        for forma, qtd, total in formas_pag:
            logger.info(f"Forma: {forma} - Registros: {qtd} - Total: R$ {total:,.2f}")
        
        # Verificar ativos
        cursor.execute("""
            SELECT ativo, COUNT(*) as qtd, SUM(valor) as total
            FROM transacoes
            WHERE ativo IS NOT NULL
            GROUP BY ativo
            ORDER BY total DESC
        """)
        ativos = cursor.fetchall()
        logger.info("\n=== ativos ===")
        for ativo, qtd, total in ativos:
            logger.info(f"ativo: {ativo} - Registros: {qtd} - Total: R$ {total:,.2f}")
        
        # Verificar indicadores
        cursor.execute("""
            SELECT 
                AVG(indicador1) as media_ind1,
                AVG(indicador2) as media_ind2
            FROM transacoes
            WHERE indicador1 IS NOT NULL OR indicador2 IS NOT NULL
        """)
        indicadores = cursor.fetchone()
        logger.info("\n=== Indicadores ===")
        logger.info(f"Média Indicador 1: {indicadores[0]:,.2f}")
        logger.info(f"Média Indicador 2: {indicadores[1]:,.2f}")
        
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
