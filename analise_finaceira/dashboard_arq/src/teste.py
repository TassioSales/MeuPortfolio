import sqlite3
import os
from pathlib import Path
from datetime import datetime
import pandas as pd

# Configuração do logger
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def conectar_banco():
    """Conecta ao banco de dados."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_path = os.path.join(base_dir, 'banco', 'financas.db')
        logger.info(f"Conectando ao banco em: {db_path}")
        return sqlite3.connect(db_path)
    except sqlite3.Error as e:
        logger.error(f"Erro ao conectar ao banco: {e}")
        raise

def calcular_total_receitas():
    """Calcula o total de receitas, despesas e saldo no banco de dados."""
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Consultas para calcular receitas, despesas e saldo
        query_receitas = """
        SELECT 
            COALESCE(SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END), 0) as total_receitas,
            COUNT(CASE WHEN valor > 0 THEN 1 END) as numero_receitas,
            MIN(CASE WHEN valor > 0 THEN data END) as data_primeira_receita,
            MAX(CASE WHEN valor > 0 THEN data END) as data_ultima_receita
        FROM transacoes
        """
        
        query_despesas = """
        SELECT 
            COALESCE(ABS(SUM(CASE WHEN valor < 0 THEN valor ELSE 0 END)), 0) as total_despesas,
            COUNT(CASE WHEN valor < 0 THEN 1 END) as numero_despesas,
            MIN(CASE WHEN valor < 0 THEN data END) as data_primeira_despesa,
            MAX(CASE WHEN valor < 0 THEN data END) as data_ultima_despesa
        FROM transacoes
        """
        
        cursor.execute(query_receitas)
        resultado_receitas = cursor.fetchone()
        
        cursor.execute(query_despesas)
        resultado_despesas = cursor.fetchone()
        
        if resultado_receitas and resultado_despesas:
            total_receitas, _, _, _ = resultado_receitas
            total_despesas, _, _, _ = resultado_despesas
            saldo = total_receitas - total_despesas
            
            # Formatação dos valores com separador de milhar e cores
            def formatar_valor(valor):
                return f"R$ {valor:,.2f}".replace(",", "").replace(",", ".")
            
            def cor_valor(valor):
                if valor > 0:
                    return "\033[32m" + formatar_valor(valor) + "\033[0m"  # Verde para positivo
                elif valor < 0:
                    return "\033[31m" + formatar_valor(valor) + "\033[0m"  # Vermelho para negativo
                else:
                    return "\033[33m" + formatar_valor(valor) + "\033[0m"  # Amarelo para zero
            
            logger.info("\n=== Resumo Financeiro ===")
            logger.info(f"Total de Receitas: {cor_valor(total_receitas)}")
            logger.info(f"Total de Despesas: {cor_valor(total_despesas)}")
            logger.info(f"Saldo Total: {cor_valor(saldo)}")
            
            # Detalhamento por mês
            logger.info("\n=== Detalhamento por Mês ===")
            query_mes = """
            SELECT 
                strftime('%Y-%m', data) as mes,
                SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END) as receitas_mes,
                SUM(CASE WHEN valor < 0 THEN valor ELSE 0 END) as despesas_mes,
                COUNT(*) as numero_transacoes
            FROM transacoes
            GROUP BY mes
            ORDER BY mes DESC
            LIMIT 12
            """
            
            df_mes = pd.read_sql_query(query_mes, conn)
            if not df_mes.empty:
                # Formatar os valores do DataFrame
                df_mes['receitas_mes'] = df_mes['receitas_mes'].apply(formatar_valor)
                df_mes['despesas_mes'] = df_mes['despesas_mes'].apply(formatar_valor)
                logger.info("\nMovimentações nos últimos 12 meses:")
                logger.info(df_mes.to_string(index=False))
            
        else:
            logger.info("Nenhuma transação encontrada no banco de dados")
        
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erro ao calcular receitas: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
    except sqlite3.Error as e:
        logger.error(f"Erro ao calcular receitas: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")

if __name__ == "__main__":
    logger.info("Iniciando cálculo de receitas")
    calcular_total_receitas()
