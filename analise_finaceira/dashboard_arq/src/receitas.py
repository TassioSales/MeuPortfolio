import sqlite3
import pandas as pd
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function

# Configura o logger para este módulo
logger = get_logger("dashboard.receitas")

@log_function()
def conectar_banco() -> sqlite3.Connection:
    """Estabelece conexão com o banco de dados.
    
    Returns:
        sqlite3.Connection: Conexão com o banco de dados
    """
    try:
        # Obtém o diretório do projeto
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Define o caminho para o banco de dados
        db_path = os.path.join(base_dir, 'banco', 'financas.db')
        logger.debug(f"Conectando ao banco de dados em: {db_path}")
        return sqlite3.connect(db_path)
    except sqlite3.Error as e:
        logger.error(f"Erro ao conectar ao banco de dados: {str(e)}")
        raise

@log_function()
def obter_receitas_mes_atual() -> float:
    """
    Retorna o total de receitas do mês atual.
    
    Returns:
        float: Total de receitas do mês atual
    """
    conn = None
    try:
        conn = conectar_banco()
        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1).strftime('%Y-%m-%d')
        
        logger.debug(f"Obtendo receitas a partir de {primeiro_dia_mes}")
        
        query = """
        SELECT COALESCE(SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END), 0) as total_receitas
        FROM transacoes
        WHERE data >= ?
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (primeiro_dia_mes,))
        resultado = cursor.fetchone()
        total_receitas = float(resultado[0]) if (resultado and resultado[0] is not None) else 0.0
        
        logger.info(f"Total de receitas do mês: R$ {total_receitas:.2f}")
        return total_receitas
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao obter receitas do mês atual: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao obter receitas: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

@log_function()
def obter_variacao_receitas() -> float:
    """
    Calcula a variação percentual das receitas em relação ao mês anterior.
    
    Returns:
        float: Variação percentual (pode ser positiva ou negativa)
    """
    conn = None
    try:
        conn = conectar_banco()
        hoje = datetime.now()
        
        # Primeiro dia do mês atual
        primeiro_dia_mes_atual = hoje.replace(day=1)
        
        # Calcular o último dia do mês anterior
        ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
        primeiro_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
        
        # Converter para string no formato YYYY-MM-DD
        str_primeiro_dia_atual = primeiro_dia_mes_atual.strftime('%Y-%m-%d')
        str_primeiro_dia_anterior = primeiro_dia_mes_anterior.strftime('%Y-%m-%d')
        str_ultimo_dia_anterior = ultimo_dia_mes_anterior.strftime('%Y-%m-%d')
        
        logger.debug(f"Período atual: {str_primeiro_dia_atual} até hoje")
        logger.debug(f"Período anterior: {str_primeiro_dia_anterior} até {str_ultimo_dia_anterior}")
        
        query = """
        SELECT 
            COALESCE(SUM(CASE WHEN data >= ? AND valor > 0 THEN valor ELSE 0 END), 0) as receitas_mes_atual,
            COALESCE(SUM(CASE WHEN data BETWEEN ? AND ? AND valor > 0 THEN valor ELSE 0 END), 0) as receitas_mes_anterior
        FROM transacoes
        """
        
        cursor = conn.cursor()
        cursor.execute(
            query, 
            (str_primeiro_dia_atual, str_primeiro_dia_anterior, str_ultimo_dia_anterior)
        )
        
        resultado = cursor.fetchone()
        if not resultado:
            logger.warning("Nenhum resultado retornado ao calcular variação de receitas")
            return 0.0
            
        receitas_mes_atual = float(resultado[0]) if resultado[0] is not None else 0.0
        receitas_mes_anterior = float(resultado[1]) if resultado[1] is not None else 0.0
        
        logger.debug(f"Receitas mês atual: R$ {receitas_mes_atual:.2f}")
        logger.debug(f"Receitas mês anterior: R$ {receitas_mes_anterior:.2f}")
        
        if receitas_mes_anterior == 0:
            logger.info("Sem dados do mês anterior para comparação")
            return 0.0  # Evita divisão por zero
            
        variacao = ((receitas_mes_atual - receitas_mes_anterior) / receitas_mes_anterior) * 100
        
        logger.info(f"Variação mensal das receitas: {variacao:.2f}%")
        return round(variacao, 2)
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao calcular variação das receitas: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao calcular variação: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

@log_function()
def obter_receitas_por_categoria() -> Dict[str, float]:
    """
    Retorna um dicionário com as receitas agrupadas por categoria.
    
    Returns:
        Dict[str, float]: Dicionário com categorias como chaves e valores totais
    """
    conn = None
    try:
        conn = conectar_banco()
        
        # Obter o primeiro dia do mês atual
        primeiro_dia_mes = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        
        logger.debug(f"Obtendo receitas por categoria a partir de {primeiro_dia_mes}")
        
        query = """
        SELECT 
            COALESCE(categoria, 'Outras') as categoria,
            ROUND(SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END), 2) as total
        FROM transacoes
        WHERE data >= ?
        AND valor > 0
        GROUP BY categoria
        HAVING total > 0
        ORDER BY total DESC
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (primeiro_dia_mes,))
        resultados = cursor.fetchall()
        
        # Criar dicionário com os resultados
        receitas_por_categoria = {}
        total_geral = 0.0
        
        for categoria, total in resultados:
            if total > 0:  # Apenas incluir categorias com valor positivo
                receitas_por_categoria[categoria] = total
                total_geral += total
        
        logger.debug(f"Total de categorias de receita encontradas: {len(receitas_por_categoria)}")
        logger.debug(f"Total geral de receitas: R$ {total_geral:.2f}")
        
        # Log detalhado das categorias (apenas em nível de debug)
        if logger and hasattr(logger, 'isEnabledFor'):
            try:
                # Verifica se o nível de debug está habilitado
                if logger.isEnabledFor(10):  # 10 é o nível numérico para DEBUG
                    for i, (categoria, total) in enumerate(receitas_por_categoria.items(), 1):
                        percentual = (total / total_geral * 100) if total_geral > 0 else 0
                        total_formatado = f"{total:.2f}" if isinstance(total, (int, float)) else str(total)
                        logger.debug(f"{i}. {categoria}: R$ {total_formatado} ({percentual:.1f}%)")
            except (TypeError, AttributeError):
                # Se não for possível obter o nível de log, apenas continue sem o log detalhado
                pass
        
        return receitas_por_categoria
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao obter receitas por categoria: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao processar receitas por categoria: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Testes
    logger.info(f"Total de receitas do mês: R$ {obter_receitas_mes_atual():.2f}")
    logger.info(f"Variação das receitas: {obter_variacao_receitas():.2f}%")
    logger.info(f"Receitas por categoria: {obter_receitas_por_categoria()}")
