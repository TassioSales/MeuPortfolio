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
def obter_despesas_12_meses() -> float:
    """
    Retorna o total de despesas dos últimos 12 meses.
    
    Returns:
        float: Total de despesas dos últimos 12 meses
    """
    conn = None
    try:
        conn = conectar_banco()
        hoje = datetime.now()
        data_inicio = hoje - timedelta(days=30*12)
        
        logger.debug(f"Obtendo despesas dos últimos 12 meses")
        
        query = """
        SELECT COALESCE(SUM(ABS(valor)), 0) as total_despesas
        FROM transacoes
        WHERE date(data) >= date(?)
        AND valor < 0
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (data_inicio.strftime('%Y-%m-%d'),))
        resultado = cursor.fetchone()
        total_despesas = float(resultado[0]) if resultado and resultado[0] is not None else 0.0
        
        logger.info(f"Total de despesas dos últimos 12 meses: R$ {total_despesas:.2f}")
        
        return round(total_despesas, 2)
    except sqlite3.Error as e:
        logger.error(f"Erro ao obter total de despesas: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()



@log_function()
def obter_despesas_por_categoria() -> Dict[str, float]:
    """
    Retorna um dicionário com o total de despesas por categoria dos últimos 12 meses.
    
    Returns:
        Dict[str, float]: Dicionário com despesas por categoria
    """
    conn = None
    try:
        conn = conectar_banco()
        
        # Obter data de 12 meses atrás
        hoje = datetime.now()
        data_inicio = hoje - timedelta(days=365)
        
        logger.debug(f"Obtendo despesas por categoria dos últimos 12 meses")
        
        query = """
        SELECT 
            COALESCE(categoria, 'Sem categoria') as categoria,
            ROUND(SUM(ABS(valor)), 2) as total
        FROM transacoes
        WHERE date(data) >= date(?)
        AND valor < 0
        GROUP BY categoria
        HAVING total > 0
        ORDER BY total DESC
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (data_inicio.strftime('%Y-%m-%d'),))
        resultados = cursor.fetchall()
        
        # Criar dicionário com os resultados
        despesas_por_categoria = {}
        total_geral = 0.0
        
        for categoria, total in resultados:
            if total and total > 0:
                try:
                    total_float = float(total)
                    despesas_por_categoria[categoria] = total_float
                    total_geral += total_float
                except (ValueError, TypeError):
                    logger.warning(f"Valor inválido para a categoria {categoria}: {total}")
        
        logger.debug(f"Total de categorias de despesa encontradas: {len(despesas_por_categoria)}")
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
            except (TypeError, AttributeError):
                # Se não for possível obter o nível de log, apenas continue sem o log detalhado
                pass
        
        return despesas_por_categoria
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao obter despesas por categoria: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()