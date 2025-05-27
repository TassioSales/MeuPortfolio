import sqlite3
from datetime import datetime, timedelta
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import sys

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function

# Configura o logger
logger = get_logger("dashboard.utils")

def get_db_connection():
    """Estabelece conexão com o banco de dados."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, 'banco', 'financas.db')
    return sqlite3.connect(db_path)

def get_dashboard_highlights() -> Tuple[Dict[str, Any], int, Dict[str, Any]]:
    """
    Retorna os destaques do dashboard com métricas detalhadas.
    
    Returns:
        tuple: (
            dict: Dados de transações {total, variacao_mensal, variacao_percentual},
            int: Total de alertas ativos,
            dict: Dados de categorias {total, variacao_mensal}
        )
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obter data atual e do mês anterior
        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        primeiro_dia_mes_anterior = (primeiro_dia_mes - timedelta(days=1)).replace(day=1)
        
        # 1. Dados de transações
        # Total de transações
        cursor.execute("SELECT COUNT(*) FROM transacoes")
        total_transacoes = cursor.fetchone()[0] or 0
        
        # Transações deste mês
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM transacoes 
            WHERE date(data) >= date(?)
            """, 
            (primeiro_dia_mes.strftime('%Y-%m-%d'),)
        )
        transacoes_este_mes = cursor.fetchone()[0] or 0
        
        # Transações do mês anterior
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM transacoes 
            WHERE date(data) >= date(?) AND date(data) < date(?)
            """, 
            (
                primeiro_dia_mes_anterior.strftime('%Y-%m-%d'),
                primeiro_dia_mes.strftime('%Y-%m-%d')
            )
        )
        transacoes_mes_anterior = cursor.fetchone()[0] or 1  # Evita divisão por zero
        
        # Cálculo da variação
        variacao_transacoes = transacoes_este_mes - transacoes_mes_anterior
        variacao_percentual = (variacao_transacoes / transacoes_mes_anterior) * 100 if transacoes_mes_anterior > 0 else 100
        
        dados_transacoes = {
            'total': total_transacoes,
            'este_mes': transacoes_este_mes,
            'variacao': variacao_transacoes,
            'variacao_percentual': round(float(variacao_percentual), 1)  # Garante que é float
        }
        
        # 2. Dados de alertas ativos
        cursor.execute("""
            SELECT COUNT(*) 
            FROM alertas_financas 
            WHERE ativo = 1
        """)
        total_alertas_ativos = cursor.fetchone()[0] or 0
        
        # 3. Dados de categorias
        # Total de categorias únicas
        cursor.execute("""
            SELECT COUNT(DISTINCT categoria) 
            FROM transacoes 
            WHERE categoria IS NOT NULL AND categoria != ''
        """)
        total_categorias = cursor.fetchone()[0] or 0
        
        # Categorias adicionadas este mês
        cursor.execute("""
            SELECT COUNT(DISTINCT categoria) 
            FROM transacoes 
            WHERE date(data) >= date(?) 
            AND categoria IS NOT NULL 
            AND categoria != ''
        """, (primeiro_dia_mes.strftime('%Y-%m-%d'),))
        
        novas_categorias = cursor.fetchone()[0] or 0
        
        dados_categorias = {
            'total': total_categorias,
            'novas_este_mes': novas_categorias
        }
        
        return dados_transacoes, total_alertas_ativos, dados_categorias
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao obter destaques do dashboard: {str(e)}")
        return {'total': 0, 'este_mes': 0, 'variacao': 0, 'variacao_percentual': 0}, 0, {'total': 0, 'novas_este_mes': 0}
    finally:
        if conn:
            conn.close()

def calcular_saldo_atual() -> Dict[str, float]:
    """
    Calcula o saldo atual, total de receitas e total de despesas.
    
    Returns:
        Dict[str, float]: Dicionário contendo:
            - saldo_atual: Saldo atual (receitas - despesas)
            - total_receitas: Soma de todas as receitas
            - total_despesas: Soma de todas as despesas (valor absoluto)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.debug("Calculando saldo atual...")
        
        # Obter totais de receitas e despesas
        cursor.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END), 0) as total_receitas,
            COALESCE(SUM(CASE WHEN valor < 0 THEN ABS(valor) ELSE 0 END), 0) as total_despesas
        FROM transacoes
        """)
        
        resultado = cursor.fetchone()
        
        if not resultado:
            logger.warning("Nenhuma transação encontrada para cálculo do saldo")
            return {
                'saldo_atual': 0.0,
                'total_receitas': 0.0,
                'total_despesas': 0.0
            }
            
        total_receitas = float(resultado[0]) if resultado[0] is not None else 0.0
        total_despesas = float(resultado[1]) if resultado[1] is not None else 0.0
        saldo_atual = total_receitas - total_despesas
        
        logger.info(
            f"Saldo atual calculado: R$ {saldo_atual:.2f} "
            f"(Receitas: R$ {total_receitas:.2f} - Despesas: R$ {total_despesas:.2f})"
        )
        
        return {
            'saldo_atual': round(saldo_atual, 2),
            'total_receitas': round(total_receitas, 2),
            'total_despesas': round(total_despesas, 2)
        }
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao calcular saldo atual: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao calcular saldo: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()


def get_recent_activities(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retorna as atividades recentes do sistema, incluindo transações e alertas manuais.
    
    Args:
        limit (int): Número máximo de atividades a serem retornadas
        
    Returns:
        List[Dict]: Lista de dicionários contendo as atividades
    """
    activities = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Buscar transações recentes
        cursor.execute("""
            SELECT 
                'transacao' as tipo,
                data as data_ocorrencia,
                descricao,
                valor,
                categoria,
                tipo as tipo_transacao
            FROM transacoes
            ORDER BY date(data) DESC, id DESC
            LIMIT ?
        """, (limit,))
        
        for row in cursor.fetchall():
            try:
                valor = float(row[3]) if row[3] is not None else 0.0
                
                # Determinar o ícone e a cor com base no tipo de transação
                if row[5] == 'receita':
                    icone = 'arrow-up-circle'
                    cor = 'success'
                    prefixo = 'Receita: '
                else:
                    icone = 'arrow-down-circle'
                    cor = 'danger'
                    prefixo = 'Despesa: '
                
                activities.append({
                    'tipo': 'transacao',
                    'data_ocorrencia': row[1],
                    'titulo': f"{prefixo}{row[4] or 'Sem categoria'}",
                    'descricao': row[2] or 'Sem descrição',
                    'valor': valor,
                    'icone': icone,
                    'cor': cor
                })
            except Exception as e:
                logger.error(f"Erro ao processar transação: {str(e)}")
                continue
        
        # 2. Buscar alertas ativos recentes
        cursor.execute("""
            SELECT 
                'alerta' as tipo,
                criado_em as data_ocorrencia,
                descricao,
                tipo_alerta,
                prioridade,
                valor_referencia
            FROM alertas_financas
            WHERE ativo = 1
            ORDER BY criado_em DESC
            LIMIT ?
        """, (limit,))
        
        for row in cursor.fetchall():
            try:
                # Mapear prioridade para cores
                prioridade = row[4].lower() if row[4] else 'media'
                if prioridade == 'alta':
                    cor = 'danger'
                elif prioridade == 'media':
                    cor = 'warning'
                else:
                    cor = 'info'
                
                # Formatar valor de referência se existir
                valor = float(row[5]) if row[5] is not None else None
                descricao = row[2] or 'Sem descrição'
                
                # Determinar o título baseado no tipo de alerta
                tipo_alerta = row[3] or 'alerta'
                if tipo_alerta == 'manual':
                    titulo = 'Alerta Manual'
                elif tipo_alerta == 'acima_media':
                    titulo = 'Alerta: Valor Acima da Média'
                else:
                    titulo = f"Alerta: {tipo_alerta.replace('_', ' ').title()}"
                
                # Formatar data para exibição
                data_ocorrencia = row[1]
                if data_ocorrencia:
                    try:
                        if isinstance(data_ocorrencia, str):
                            # Tenta converter a string para datetime
                            data_dt = datetime.strptime(data_ocorrencia.split(' ')[0], '%Y-%m-%d')
                            data_ocorrencia = data_dt.strftime('%d/%m/%Y')
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Erro ao formatar data de alerta: {data_ocorrencia} - {str(e)}")
                
                activities.append({
                    'tipo': 'alerta',
                    'data_ocorrencia': data_ocorrencia or 'Data não informada',
                    'titulo': titulo,
                    'descricao': descricao,
                    'prioridade': prioridade.capitalize(),
                    'icone': 'exclamation-triangle',
                    'cor': cor,
                    'valor': valor
                })
            except Exception as e:
                logger.error(f"Erro ao processar alerta: {str(e)}")
                continue
        
        # Ordenar todas as atividades por data (mais recentes primeiro)
        def get_sort_key(activity):
            try:
                if isinstance(activity['data_ocorrencia'], str) and activity['data_ocorrencia'] != 'Data não informada':
                    try:
                        # Tenta primeiro o formato DD/MM/YYYY
                        return datetime.strptime(activity['data_ocorrencia'], '%d/%m/%Y')
                    except ValueError:
                        try:
                            # Tenta o formato SQLite
                            return datetime.strptime(activity['data_ocorrencia'], '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            return datetime.min
                return datetime.min
            except (ValueError, AttributeError, KeyError) as e:
                logger.error(f"Erro ao ordenar atividade: {str(e)}")
                return datetime.min
                
        activities.sort(key=get_sort_key, reverse=True)
        
        # Formatar as atividades para o template
        formatted_activities = []
        now = datetime.now()
        
        for activity in activities[:limit]:
            # Calcular tempo decorrido
            if activity['data_ocorrencia']:
                try:
                    if isinstance(activity['data_ocorrencia'], str):
                        try:
                            # Tenta primeiro o formato DD/MM/YYYY
                            dt = datetime.strptime(activity['data_ocorrencia'], '%d/%m/%Y')
                        except ValueError:
                            try:
                                # Tenta o formato ISO
                                if 'T' in activity['data_ocorrencia']:
                                    dt = datetime.fromisoformat(activity['data_ocrencia'].replace('Z', '+00:00'))
                                else:  # Formato SQLite
                                    dt = datetime.strptime(activity['data_ocorrencia'], '%Y-%m-%d %H:%M:%S')
                            except (ValueError, AttributeError):
                                dt = now
                    else:
                        dt = activity['data_ocorrencia']
                    
                    # Se dt for apenas uma data, adiciona meia-noite
                    if isinstance(dt, datetime):
                        diff = now - dt
                    else:
                        diff = now - datetime.combine(dt, datetime.min.time())
                    
                    if diff.days > 30:
                        tempo = f"Há {diff.days // 30} meses"
                    elif diff.days > 0:
                        tempo = f"Há {diff.days} dias"
                    elif diff.seconds // 3600 > 0:
                        horas = diff.seconds // 3600
                        tempo = f"Há {horas} hora{'s' if horas > 1 else ''}"
                    else:
                        minutos = max(1, diff.seconds // 60)
                        tempo = f"Há {minutos} minuto{'s' if minutos > 1 else ''}"
                except (ValueError, TypeError) as e:
                    logger.warning(f"Erro ao formatar data: {activity['data_ocorrencia']} - {str(e)}")
                    tempo = "Agora"
            else:
                tempo = "Agora"
            
            # Formatar descrição com valor se for transação
            descricao = activity['descricao']
            if activity['tipo'] == 'transacao':
                valor = f"R$ {activity['valor']:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")
                descricao = f"{descricao} - {valor}"
            
            formatted_activities.append({
                'titulo': activity['titulo'],
                'descricao': descricao,
                'tempo': tempo,
                'icone': activity['icone'],
                'cor': activity['cor']
            })
        
        return formatted_activities
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar atividades recentes: {str(e)}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()
