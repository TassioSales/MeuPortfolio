import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function

# Configura o logger para este módulo
logger = get_logger("dashboard.despesas")

@log_function()
def conectar_banco() -> sqlite3.Connection:
    """Conecta ao banco de dados SQLite.
    
    Returns:
        sqlite3.Connection: Conexão com o banco de dados
    """
    try:
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'banco', 
            'financas.db'
        )
        logger.debug(f"Conectando ao banco de dados em: {db_path}")
        return sqlite3.connect(db_path)
    except sqlite3.Error as e:
        logger.error(f"Erro ao conectar ao banco de dados: {str(e)}")
        raise

@log_function()
def obter_despesas_totais() -> float:
    """
    Retorna o total de despesas do mês atual.
    
    Returns:
        float: Total de despesas do mês atual
    """
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Obter o primeiro dia do mês atual
        hoje = datetime.now()
        primeiro_dia = hoje.replace(day=1).strftime('%Y-%m-%d')
        
        logger.debug(f"Obtendo despesas a partir de {primeiro_dia}")
        
        # Consulta para obter o total de despesas do mês atual
        query = """
        SELECT COALESCE(SUM(ABS(valor)), 0) as total_despesas
        FROM transacoes
        WHERE data >= ? 
        AND valor < 0
        """
        
        cursor.execute(query, (primeiro_dia,))
        resultado = cursor.fetchone()
        total_despesas = resultado[0] if resultado and resultado[0] is not None else 0.0
        
        logger.debug(f"Total de despesas do mês: R$ {total_despesas:.2f}")
        
        return round(total_despesas, 2)
    except sqlite3.Error as e:
        logger.error(f"Erro ao obter total de despesas: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

@log_function()
def obter_variacao_mensal() -> float:
    """
    Retorna a variação percentual das despesas em relação ao mês anterior.
    
    Returns:
        float: Variação percentual (pode ser positiva ou negativa)
    """
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Obter o primeiro dia do mês atual e do mês anterior
        hoje = datetime.now()
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
        
        # Consulta para obter o total de despesas do mês atual
        query_atual = """
        SELECT COALESCE(SUM(ABS(valor)), 0) as total_despesas
        FROM transacoes
        WHERE data >= ? 
        AND valor < 0
        """
        
        # Consulta para obter o total de despesas do mês anterior
        query_anterior = """
        SELECT COALESCE(SUM(ABS(valor)), 0) as total_despesas
        FROM transacoes
        WHERE data BETWEEN ? AND ?
        AND valor < 0
        """
        
        # Executar consultas
        cursor.execute(query_atual, (str_primeiro_dia_atual,))
        total_atual = cursor.fetchone()[0] or 0.0
        
        cursor.execute(query_anterior, (str_primeiro_dia_anterior, str_ultimo_dia_anterior))
        total_anterior = cursor.fetchone()[0] or 0.0
        
        logger.debug(f"Total despesas mês atual: R$ {total_atual:.2f}")
        logger.debug(f"Total despesas mês anterior: R$ {total_anterior:.2f}")
        
        # Calcular a variação percentual
        if total_anterior == 0:
            logger.info("Sem dados do mês anterior para comparação")
            return 0.0  # Evitar divisão por zero
            
        variacao = ((total_atual - total_anterior) / total_anterior) * 100
        
        logger.info(f"Variação mensal: {variacao:.2f}%")
        return round(variacao, 2)
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao calcular variação mensal: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

@log_function()
def obter_despesas_por_categoria() -> Dict[str, float]:
    """
    Retorna um dicionário com o total de despesas por categoria.
    
    Returns:
        Dict[str, float]: Dicionário com categorias e valores totais
    """
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Obter o primeiro dia do mês atual
        hoje = datetime.now()
        primeiro_dia = hoje.replace(day=1).strftime('%Y-%m-%d')
        
        logger.debug(f"Obtendo despesas por categoria a partir de {primeiro_dia}")
        
        # Consulta para obter o total de despesas por categoria
        query = """
        SELECT 
            COALESCE(categoria, 'Sem Categoria') as categoria, 
            ROUND(SUM(ABS(valor)), 2) as total
        FROM transacoes
        WHERE data >= ?
        AND valor < 0
        GROUP BY categoria
        ORDER BY total DESC
        """
        
        cursor.execute(query, (primeiro_dia,))
        resultados = cursor.fetchall()
        
        # Criar dicionário com os resultados
        despesas_por_categoria = {}
        total_geral = 0.0
        
        for categoria, total in resultados:
            if total > 0:  # Apenas incluir categorias com valor positivo
                despesas_por_categoria[categoria] = total
                total_geral += total
        
        logger.debug(f"Total de categorias encontradas: {len(despesas_por_categoria)}")
        logger.debug(f"Total geral de despesas: R$ {total_geral:.2f}")
        
        # Log detalhado das categorias (apenas em nível de debug)
        if logger and hasattr(logger, 'isEnabledFor'):
            try:
                # Verifica se o nível de debug está habilitado
                if logger.isEnabledFor(10):  # 10 é o nível numérico para DEBUG
                    for i, (categoria, total) in enumerate(despesas_por_categoria.items(), 1):
                        percentual = (total / total_geral * 100) if total_geral > 0 else 0
                        total_formatado = f"{total:.2f}" if isinstance(total, (int, float)) else str(total)
                        logger.debug(f"{i}. {categoria}: R$ {total_formatado} ({percentual:.1f}%)")
            except Exception as e:
                # Se ocorrer algum erro, apenas continue sem o log detalhado
                logger.warning(f"Erro ao registrar log detalhado: {str(e)}")
        
        return despesas_por_categoria
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao obter despesas por categoria: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()
