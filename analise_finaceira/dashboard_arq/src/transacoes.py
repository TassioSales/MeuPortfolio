import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function

# Configura o logger para este módulo
logger = get_logger("dashboard.transacoes")

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
def obter_transacoes_recentes(limite: int = 10) -> List[Dict[str, Any]]:
    """
    Retorna as transações mais recentes do banco de dados.
    
    Args:
        limite (int): Número máximo de transações a serem retornadas
        
    Returns:
        List[Dict[str, Any]]: Lista de dicionários contendo as transações
    """
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        logger.debug(f"Obtendo as últimas {limite} transações")
        
        query = """
        SELECT 
            data,
            descricao,
            valor,
            COALESCE(categoria, 'Sem Categoria') as categoria,
            tipo
        FROM transacoes
        ORDER BY data DESC, id DESC
        LIMIT ?
        """
        
        cursor.execute(query, (limite,))
        colunas = [desc[0] for desc in cursor.description]
        resultados = cursor.fetchall()
        
        # Converter para lista de dicionários
        transacoes = [dict(zip(colunas, linha)) for linha in resultados]
        
        logger.debug(f"Encontradas {len(transacoes)} transações")
        
        # Log detalhado apenas se estiver em modo debug
        if logger and hasattr(logger, 'isEnabledFor'):
            try:
                # Verifica se o nível de debug está habilitado
                if logger.isEnabledFor(10):  # 10 é o nível numérico para DEBUG
                    for i, transacao in enumerate(transacoes, 1):
                        valor_formatado = f"{transacao['valor']:.2f}" if isinstance(transacao['valor'], (int, float)) else str(transacao['valor'])
                        logger.debug(f"Transação {i}: {transacao['data']} - {transacao['descricao']} - R$ {valor_formatado}")
            except Exception as e:
                # Se ocorrer algum erro, apenas continue sem o log detalhado
                logger.warning(f"Erro ao registrar log detalhado: {str(e)}")
        
        return transacoes
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao obter transações recentes: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao processar transações: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

@log_function()
def obter_saldo_atual() -> float:
    """
    Retorna o saldo atual (total de receitas - total de despesas)
    
    Returns:
        float: Saldo atual
    """
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        logger.debug("Calculando saldo atual...")
        
        query = """
        SELECT 
            COALESCE(SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END), 0) as total_receitas,
            COALESCE(SUM(CASE WHEN valor < 0 THEN ABS(valor) ELSE 0 END), 0) as total_despesas
        FROM transacoes
        """
        
        cursor.execute(query)
        resultado = cursor.fetchone()
        
        if not resultado:
            logger.warning("Nenhum resultado retornado ao calcular saldo")
            return 0.0
            
        total_receitas = float(resultado[0]) if resultado[0] is not None else 0.0
        total_despesas = float(resultado[1]) if resultado[1] is not None else 0.0
        saldo = total_receitas - total_despesas
        
        logger.info(f"Saldo atual: R$ {saldo:.2f} (Receitas: R$ {total_receitas:.2f} - Despesas: R$ {total_despesas:.2f})")
        
        return round(saldo, 2)
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao calcular saldo atual: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao calcular saldo: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Teste das funções
    logger.info("Testando funções do módulo de transações")
    try:
        transacoes = obter_transacoes_recentes(5)
        logger.info(f"Transações recentes: {len(transacoes)} encontradas")
        
        saldo = obter_saldo_atual()
        logger.info(f"Saldo atual: R$ {saldo:.2f}")
    except Exception as e:
        logger.error(f"Erro durante os testes: {str(e)}", exc_info=True)
