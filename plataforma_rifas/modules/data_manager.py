from __future__ import annotations
import json
import random
import sqlite3
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timezone, timedelta
from logger import logger
from . import database as db  # Importação relativa correta

# --- Gerenciamento de Rifas ---

def listar_rifas() -> List[str]:
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT nome FROM rifas ORDER BY nome ASC")
        return [row['nome'] for row in cursor.fetchall()]
    finally:
        conn.close()

def get_config_rifa(nome_rifa: str) -> Optional[Dict[str, Any]]:
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rifas WHERE nome = ?", (nome_rifa,))
        row = cursor.fetchone()
        if not row:
            return None
        
        config = dict(row)
        extra_config = json.loads(config.pop('config_json', '{}'))
        config.update(extra_config)
        return config
    finally:
        conn.close()

def atualizar_config_rifa(nome_rifa: str, updates: Dict) -> Tuple[bool, str]:
    conn = db.get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT config_json FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cursor.fetchone()
            if not row:
                return False, "Rifa não encontrada."
            
            current_config = json.loads(row['config_json'])
            current_config.update(updates)
            
            cursor.execute("UPDATE rifas SET config_json = ? WHERE nome = ?", (json.dumps(current_config), nome_rifa))
        return True, "Configuração atualizada."
    except Exception as e:
        logger.exception(f"Erro ao atualizar config da rifa '{nome_rifa}': {e}")
        return False, f"Erro de banco de dados: {e}"

def salvar_nova_rifa(nome: str, valor_numero: float, total_numeros: int) -> Tuple[bool, str]:
    if not nome.strip() or total_numeros <= 0 or valor_numero < 0:
        return False, "Dados inválidos para criar a rifa."
    
    conn = db.get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO rifas (nome, valor_numero, total_numeros) VALUES (?, ?, ?)", 
                           (nome.strip(), float(valor_numero), int(total_numeros)))
        logger.info(f"Nova rifa criada no DB: '{nome}'")
        return True, "Rifa criada com sucesso."
    except sqlite3.IntegrityError:
        return False, "Já existe uma rifa com este nome."
    except Exception as e:
        logger.exception(f"Erro de DB ao criar rifa: {e}")
        return False, "Erro ao salvar no banco de dados."

def deletar_rifa(nome_rifa: str) -> Tuple[bool, str]:
    conn = db.get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rifas WHERE nome = ?", (nome_rifa,))
            if cursor.rowcount == 0:
                return False, "Rifa não encontrada."
        logger.warning(f"Rifa deletada do DB: '{nome_rifa}'")
        return True, "Rifa deletada com sucesso."
    except Exception as e:
        logger.exception(f"Erro de DB ao deletar rifa: {e}")
        return False, "Erro ao deletar no banco de dados."

# --- Operações de Venda, Reserva e Consulta ---

def carregar_dados_rifa(nome_rifa: str) -> Dict[str, str]:
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.numero, v.comprador FROM vendas v 
            JOIN rifas r ON v.rifa_id = r.id 
            WHERE r.nome = ?
        """, (nome_rifa,))
        return {str(row['numero']): row['comprador'] for row in cursor.fetchall()}
    finally:
        conn.close()

def registrar_venda(nome_rifa: str, nome_comprador: str, numeros: List[int]) -> Tuple[bool, List[int], str]:
    conn = db.get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, total_numeros FROM rifas WHERE nome = ?", (nome_rifa,))
            rifa = cursor.fetchone()
            if not rifa: return False, numeros, "Rifa não encontrada."

            rifa_id, total = rifa['id'], rifa['total_numeros']
            
            if any(n <= 0 or n > total for n in numeros):
                return False, numeros, "Há números fora do intervalo permitido."

            placeholders = ','.join('?' * len(numeros))
            cursor.execute(f"SELECT numero FROM vendas WHERE rifa_id = ? AND numero IN ({placeholders})", [rifa_id] + numeros)
            conflitos = [row['numero'] for row in cursor.fetchall()]
            if conflitos: return False, sorted(conflitos), "Alguns números já foram vendidos."

            ts = datetime.now(timezone.utc).isoformat()
            vendas = [(rifa_id, n, nome_comprador.strip(), ts) for n in numeros]
            cursor.executemany("INSERT INTO vendas (rifa_id, numero, comprador, timestamp) VALUES (?, ?, ?, ?)", vendas)
            
            cursor.execute(f"DELETE FROM reservas WHERE rifa_id = ? AND numero IN ({placeholders})", [rifa_id] + numeros)

        logger.info(f"Venda registrada no DB para '{nome_rifa}': {len(numeros)} números para '{nome_comprador}'")
        return True, sorted(numeros), "Venda registrada com sucesso."
    except Exception as e:
        logger.exception(f"Erro de DB ao registrar venda: {e}")
        return False, numeros, f"Erro no banco de dados: {e}"

def cancelar_venda(nome_rifa: str, numeros: List[int]) -> Tuple[bool, List[int], str]:
    conn = db.get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
            rifa = cursor.fetchone()
            if not rifa: return False, numeros, "Rifa não encontrada."
            rifa_id = rifa['id']

            placeholders = ','.join('?' * len(numeros))
            cursor.execute(f"DELETE FROM vendas WHERE rifa_id = ? AND numero IN ({placeholders})", [rifa_id] + numeros)
            
            if cursor.rowcount == 0:
                return False, [], "Nenhum dos números informados estava vendido."
            
            logger.warning(f"Vendas canceladas na rifa '{nome_rifa}': {numeros}")
            return True, numeros, f"Vendas canceladas ({cursor.rowcount} números)."
    except Exception as e:
        logger.exception(f"Erro ao cancelar venda: {e}")
        return False, [], f"Erro de banco de dados: {e}"

def transferir_venda(nome_rifa: str, numeros: List[int], novo_comprador: str) -> Tuple[bool, List[int], str]:
    if not novo_comprador.strip():
        return False, numeros, "O nome do novo comprador não pode ser vazio."
    
    conn = db.get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
            rifa = cursor.fetchone()
            if not rifa: return False, numeros, "Rifa não encontrada."
            rifa_id = rifa['id']
            
            placeholders = ','.join('?' * len(numeros))
            cursor.execute(f"UPDATE vendas SET comprador = ? WHERE rifa_id = ? AND numero IN ({placeholders})", 
                           [novo_comprador.strip(), rifa_id] + numeros)
            
            if cursor.rowcount == 0:
                return False, [], "Nenhum dos números informados foi encontrado para transferir."

            logger.info(f"Transferência de venda na rifa '{nome_rifa}': {numeros} para '{novo_comprador}'")
            return True, numeros, f"Transferência realizada ({cursor.rowcount} números)."
    except Exception as e:
        logger.exception(f"Erro ao transferir venda: {e}")
        return False, [], f"Erro de banco de dados: {e}"

def carregar_reservas_detalhe(nome_rifa: str) -> Dict[int, str]:
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT res.numero, res.timestamp FROM reservas res
            JOIN rifas r ON res.rifa_id = r.id
            WHERE r.nome = ?
        """, (nome_rifa,))
        return {row['numero']: row['timestamp'] for row in cursor.fetchall()}
    finally:
        conn.close()

def salvar_reservas_detalhe(nome_rifa: str, reservas: Dict[int, str]) -> None:
    conn = db.get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
            rifa = cursor.fetchone()
            if not rifa: return
            rifa_id = rifa['id']
            
            # Limpa reservas antigas e insere as novas
            cursor.execute("DELETE FROM reservas WHERE rifa_id = ?", (rifa_id,))
            
            reservas_para_inserir = [(rifa_id, num, ts) for num, ts in reservas.items()]
            if reservas_para_inserir:
                cursor.executemany("INSERT INTO reservas (rifa_id, numero, timestamp) VALUES (?, ?, ?)", reservas_para_inserir)
    except Exception as e:
        logger.exception(f"Erro ao salvar reservas: {e}")

def purge_expired_reservas(nome_rifa: str, ttl_minutes: int) -> Tuple[Dict[int, str], List[int]]:
    if ttl_minutes <= 0:
        return carregar_reservas_detalhe(nome_rifa), []

    conn = db.get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
            rifa = cursor.fetchone()
            if not rifa: return {}, []
            rifa_id = rifa['id']

            # Calcula o tempo limite em formato ISO
            limit_time = datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes)
            limit_ts_str = limit_time.isoformat()

            # Pega os números que serão removidos ANTES de deletar
            cursor.execute("SELECT numero FROM reservas WHERE rifa_id = ? AND timestamp < ?", (rifa_id, limit_ts_str))
            removidos = [row['numero'] for row in cursor.fetchall()]

            if removidos:
                cursor.execute("DELETE FROM reservas WHERE rifa_id = ? AND timestamp < ?", (rifa_id, limit_ts_str))
                logger.info(f"Reservas expiradas removidas para '{nome_rifa}': {sorted(removidos)}")
        
        # Recarrega as reservas ativas
        ativos = carregar_reservas_detalhe(nome_rifa)
        return ativos, removidos
    except Exception as e:
        logger.exception(f"Erro ao purgar reservas: {e}")
        return {}, []
        
# --- Funções para Sorteio e Relatórios ---

def escolher_vencedor(nome_rifa: str) -> Tuple[bool, Optional[int], Optional[str], str]:
    conn = db.get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, sorteio_realizado FROM rifas WHERE nome = ?", (nome_rifa,))
            rifa = cursor.fetchone()
            if not rifa: return False, None, None, "Rifa não encontrada."
            if rifa['sorteio_realizado']: return False, None, None, "Sorteio já foi realizado."
            
            rifa_id = rifa['id']
            
            cursor.execute("SELECT numero, comprador FROM vendas WHERE rifa_id = ?", (rifa_id,))
            vendidos = cursor.fetchall()
            if not vendidos:
                return False, None, None, "Nenhum número vendido para sortear."
            
            vencedor = random.choice(vendidos)
            numero_sorteado, comprador = vencedor['numero'], vencedor['comprador']
            
            cursor.execute("""
                UPDATE rifas SET sorteio_realizado = TRUE, sorteio_numero = ?, sorteio_comprador = ? 
                WHERE id = ?
            """, (numero_sorteado, comprador, rifa_id))
            
            logger.success(f"Sorteio realizado para '{nome_rifa}': Nº{numero_sorteado} - {comprador}")
            return True, numero_sorteado, comprador, "Sorteio realizado com sucesso."
    except Exception as e:
        logger.exception(f"Erro ao realizar sorteio: {e}")
        return False, None, None, f"Erro de banco de dados: {e}"

def listar_compradores(nome_rifa: str) -> List[str]:
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT comprador FROM vendas v
            JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ? ORDER BY comprador ASC
        """, (nome_rifa,))
        return [row['comprador'] for row in cursor.fetchall()]
    finally:
        conn.close()

def carregar_vendas_periodo(nome_rifa: str, periodo: str) -> List[Dict]:
    now = datetime.now(timezone.utc)
    if periodo == "dia": delta = timedelta(days=1)
    elif periodo == "semana": delta = timedelta(weeks=1)
    elif periodo == "mes": delta = timedelta(days=30)
    else: delta = timedelta(days=3650) # "tudo"
    
    start_time = (now - delta).isoformat()
    
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp as ts, comprador, numero
            FROM vendas v
            JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ? AND v.timestamp >= ?
            ORDER BY v.timestamp DESC
        """, (nome_rifa, start_time))
        # Agrupar por comprador e timestamp para recriar o formato de evento original
        eventos = {}
        for row in cursor.fetchall():
            key = (row['ts'], row['comprador'])
            if key not in eventos:
                eventos[key] = {'ts': row['ts'], 'comprador': row['comprador'], 'numeros': [], 'qtd': 0}
            eventos[key]['numeros'].append(row['numero'])
            eventos[key]['qtd'] += 1
        return list(eventos.values())
    finally:
        conn.close()

# --- Funções para Analytics ---

def get_sales_by_day(nome_rifa: str) -> List[Dict]:
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        # O SQLite pode extrair datas de strings ISO8601 diretamente
        cursor.execute("""
            SELECT DATE(timestamp) as dia, COUNT(id) as quantidade
            FROM vendas v JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ?
            GROUP BY dia ORDER BY dia ASC;
        """, (nome_rifa,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_top_buyers(nome_rifa: str, limit: int = 10) -> List[Dict]:
    """
    Retorna os principais compradores de uma rifa, ordenados pelo número de compras.
    
    Args:
        nome_rifa (str): Nome da rifa
        limit (int): Número máximo de compradores a retornar
        
    Returns:
        List[Dict]: Lista de dicionários com 'comprador' e 'quantidade'
    """
    logger.info(f"Buscando top {limit} compradores para a rifa: {nome_rifa}")
    
    # Primeiro, verifica se a rifa existe
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        
        # Obtém o ID da rifa
        cursor.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
        rifa = cursor.fetchone()
        
        if not rifa:
            logger.error(f"Rifa não encontrada: {nome_rifa}")
            return []
            
        rifa_id = rifa['id']
        
        # Consulta otimizada para obter os principais compradores
        cursor.execute("""
            SELECT 
                comprador,
                COUNT(*) as quantidade,
                SUM(CASE WHEN data_compra IS NOT NULL THEN 1 ELSE 0 END) as compras_pagas
            FROM vendas 
            WHERE rifa_id = ?
            GROUP BY comprador 
            ORDER BY quantidade DESC 
            LIMIT ?;
        """, (rifa_id, limit))
        
        # Processa os resultados
        result = []
        for row in cursor.fetchall():
            comprador = row['comprador']
            quantidade = row['quantidade']
            compras_pagas = row.get('compras_pagas', 0)
            
            # Formata o resultado
            result.append({
                'comprador': comprador,
                'quantidade': quantidade,
                'compras_pagas': compras_pagas
            })
            
            logger.debug(f"Comprador: {comprador}, Números: {quantidade}, Pagos: {compras_pagas}")
        
        logger.info(f"Encontrados {len(result)} compradores para a rifa {nome_rifa}")
        return result
        
    except Exception as e:
        logger.exception(f"Erro ao buscar top compradores para a rifa {nome_rifa}")
        # Em caso de erro, tenta um fallback mais simples
        try:
            cursor.execute("""
                SELECT comprador, COUNT(*) as quantidade
                FROM vendas 
                WHERE rifa_id = ?
                GROUP BY comprador 
                ORDER BY quantidade DESC 
                LIMIT ?;
            """, (rifa_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
        except:
            return []
    finally:
        conn.close()