from __future__ import annotations
import json
import random
import sqlite3
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timezone, timedelta
from pathlib import Path  # Adicionando importação do Path
from logger import logger
from .database import get_connection  # Importando a função get_connection diretamente

# Manter a importação do módulo database para outras funções que podem precisar
from . import database as db
import bcrypt
import os
import io
import zipfile
from logger import get_logger

logger = get_logger(__name__)

# ----------------- Util -----------------

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ----------------- JSON fallback/mirror -----------------

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
INDEX_FILE = DATA_DIR / "index.json"

JSON_MIRROR = os.getenv("JSON_MIRROR", "true").lower() == "true"

def _json_safe_filename(name: str) -> str:
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(ch, '-')
    return name

def _json_rifa_path(nome_rifa: str) -> Path:
    return DATA_DIR / f"{_json_safe_filename(nome_rifa)}.json"

def _json_index_load() -> Dict[str, Dict]:
    try:
        if INDEX_FILE.exists():
            data = json.loads(INDEX_FILE.read_text(encoding='utf-8') or '{}')
            logger.debug(f"index.json carregado com {len(data)} rifas")
            return data
        logger.debug("index.json não encontrado")
        return {}
    except Exception as e:
        logger.error("Falha ao carregar index.json", exception=e)
        return {}

def _json_index_save(index: Dict[str, Dict]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
        logger.debug("index.json salvo com sucesso")
    except Exception as e:
        logger.warning("Falha ao salvar index.json", exception=e)

def _json_dados_load(nome_rifa: str) -> Dict[str, str]:
    p = _json_rifa_path(nome_rifa)
    if not p.exists():
        logger.debug(f"Arquivo JSON não encontrado para rifa {nome_rifa}")
        return {}
    try:
        data = json.loads(p.read_text(encoding='utf-8') or '{}')
        logger.debug(f"Dados JSON carregados para rifa {nome_rifa}")
        return data
    except Exception as e:
        logger.error(f"Falha ao carregar dados JSON para rifa {nome_rifa}", exception=e)
        return {}

def _json_dados_save(nome_rifa: str, dados: Dict[str, str]) -> None:
    try:
        p = _json_rifa_path(nome_rifa)
        p.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding='utf-8')
        logger.debug(f"Dados JSON salvos para rifa {nome_rifa}")
    except Exception as e:
        logger.warning(f"Falha ao salvar dados JSON para rifa {nome_rifa}", exception=e)

def migrate_from_json() -> None:
    """Importa dados de JSON para SQLite se o DB estiver vazio para aquela rifa."""
    index = _json_index_load()
    if not index:
        logger.info("Nenhum dado JSON para migrar")
        return
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            for nome, cfg in index.items():
                cur.execute("SELECT id FROM rifas WHERE nome = ?", (nome,))
                row = cur.fetchone()
                if row:
                    logger.debug(f"Rifa {nome} já existe no DB, pulando migração")
                    continue
                try:
                    cur.execute(
                        "INSERT INTO rifas (nome, valor_numero, total_numeros, config_json) VALUES (?, ?, ?, ?)",
                        (
                            nome,
                            float(cfg.get('valor_numero', 0.0)),
                            int(cfg.get('total_numeros', 0)),
                            json.dumps(cfg.get('sorteio', {}), ensure_ascii=False),
                        ),
                    )
                    cur.execute("SELECT id FROM rifas WHERE nome = ?", (nome,))
                    row = cur.fetchone()
                    rifa_id = row["id"]
                    dados = _json_dados_load(nome)
                    if dados:
                        ts = _utcnow_iso()
                        vendas = [(rifa_id, int(n), c, ts) for n, c in dados.items()]
                        try:
                            cur.executemany(
                                "INSERT OR IGNORE INTO vendas (rifa_id, numero, comprador, timestamp) VALUES (?, ?, ?, ?)",
                                vendas,
                            )
                            logger.success(f"Migração de {len(vendas)} vendas concluída para rifa {nome}")
                        except Exception as e:
                            logger.error(f"Falha ao migrar vendas para rifa {nome}", exception=e)
                    logger.success(f"Rifa {nome} migrada com sucesso")
                except Exception as e:
                    logger.error(f"Falha ao migrar rifa {nome}", exception=e)
                    continue
        logger.success("Migração JSON→SQLite concluída")
    except Exception as e:
        logger.error("Falha geral na migração JSON→SQLite", exception=e)
    finally:
        conn.close()

def export_backup_json_zip() -> bytes:
    """Gera um ZIP com index.json e arquivos de rifas JSON."""
    mem = io.BytesIO()
    try:
        with zipfile.ZipFile(mem, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            if INDEX_FILE.exists():
                zf.writestr('index.json', INDEX_FILE.read_text(encoding='utf-8'))
                logger.debug("index.json adicionado ao backup ZIP")
            for jf in DATA_DIR.glob('*.json'):
                if jf.name == 'index.json':
                    continue
                zf.writestr(jf.name, jf.read_text(encoding='utf-8'))
                logger.debug(f"{jf.name} adicionado ao backup ZIP")
        mem.seek(0)
        logger.success("Backup JSON ZIP gerado com sucesso")
        return mem.getvalue()
    except Exception as e:
        logger.error("Falha ao gerar backup JSON ZIP", exception=e)
        raise RuntimeError("Erro ao criar backup JSON ZIP") from e

# ----------------- Users (Multiusuário) -----------------

def _hash_password(password: str) -> str:
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        logger.debug("Senha hasheada com sucesso")
        return hashed
    except Exception as e:
        logger.error("Falha ao hashear senha", exception=e)
        raise ValueError("Erro ao processar a senha") from e

def _check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        logger.error("Falha ao verificar senha", exception=e)
        return False

def create_user(name: str, email: str, password: str) -> Tuple[bool, str, Optional[int]]:
    name = (name or '').strip()
    email = (email or '').strip().lower()
    if not name or not email or not password:
        logger.warning("Tentativa de criar usuário com dados inválidos", name=name, email=email)
        return False, 'Dados inválidos.', None
    if len(password) < 8 or not any(c.isupper() for c in password) or not any(c.islower() for c in password) or not any(c.isdigit() for c in password):
        logger.warning("Tentativa de criar usuário com senha fraca", email=email)
        return False, 'Senha fraca. Use ao menos 8 caracteres, incluindo maiúscula, minúscula e número.', None
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cur.fetchone():
                logger.warning(f"Email {email} já cadastrado")
                return False, 'E-mail já cadastrado.', None
            hashed_password = _hash_password(password)
            cur.execute(
                "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (name, email, hashed_password, _utcnow_iso()),
            )
            cur.execute("SELECT id FROM users WHERE email = ?", (email,))
            row = cur.fetchone()
            user_id = int(row['id']) if row else None
            logger.success(f"Usuário criado com sucesso", user_id=user_id, email=email)
            return True, 'Usuário criado com sucesso.', user_id
    except Exception as e:
        logger.error(f"Falha ao criar usuário {email}", exception=e)
        return False, f"Erro ao criar usuário: {str(e)}", None
    finally:
        conn.close()

def set_json_mirror(enabled: bool) -> None:
    """Ativa/desativa espelhamento JSON em tempo de execução."""
    global JSON_MIRROR
    try:
        JSON_MIRROR = bool(enabled)
        logger.success(f"Espelhamento JSON {'ativado' if enabled else 'desativado'}")
    except Exception as e:
        logger.error("Falha ao configurar espelhamento JSON", exception=e)
        raise ValueError("Erro ao configurar espelhamento JSON") from e

def get_sales_by_weekday(nome_rifa: str, days: int = 30) -> List[Dict]:
    """Retorna quantidade de vendas por dia da semana (0=Domingo..6=Sábado) nos últimos N dias."""
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT CAST(STRFTIME('%w', v.timestamp) AS INTEGER) as dow, COUNT(v.id) as quantidade
            FROM vendas v JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ? AND v.timestamp >= DATETIME('now', ?)
            GROUP BY dow
            ORDER BY dow ASC
            """,
            (nome_rifa, f'-{int(days)} days'),
        )
        res = {int(row['dow']): int(row['quantidade']) for row in cur.fetchall()}
        data = [dict(dow=d, quantidade=res.get(d, 0)) for d in range(7)]
        logger.debug(f"Vendas por dia da semana carregadas para rifa {nome_rifa}", days=days)
        return data
    except Exception as e:
        logger.error(f"Falha ao obter vendas por dia da semana para rifa {nome_rifa}", exception=e)
        return []
    finally:
        conn.close()

def get_revenue_by_day(nome_rifa: str, start_iso: Optional[str], end_iso: Optional[str]) -> List[Dict]:
    """Retorna receita por dia no período utilizando valor_numero atual da rifa (aproximação)."""
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT valor_numero FROM rifas WHERE nome = ?", (nome_rifa,))
        r = cur.fetchone()
        if not r:
            logger.warning(f"Rifa {nome_rifa} não encontrada para cálculo de receita")
            return []
        valor_unit = float(r['valor_numero'])
        base_sql = (
            "SELECT DATE(v.timestamp) as dia, COUNT(v.id) as qtd FROM vendas v "
            "JOIN rifas r ON v.rifa_id = r.id WHERE r.nome = ?"
        )
        params: List[Any] = [nome_rifa]
        if start_iso:
            base_sql += " AND v.timestamp >= ?"
            params.append(start_iso)
        if end_iso:
            base_sql += " AND v.timestamp <= ?"
            params.append(end_iso)
        base_sql += " GROUP BY DATE(v.timestamp) ORDER BY DATE(v.timestamp) ASC"
        cur.execute(base_sql, params)
        data = [dict(dia=row['dia'], receita=float(row['qtd']) * valor_unit, qtd=int(row['qtd'])) for row in cur.fetchall()]
        logger.debug(f"Receita por dia carregada para rifa {nome_rifa}", period=f"{start_iso} to {end_iso}")
        return data
    except Exception as e:
        logger.error(f"Falha ao obter receita por dia para rifa {nome_rifa}", exception=e)
        return []
    finally:
        conn.close()

def get_cumulative_revenue(nome_rifa: str, start_iso: Optional[str], end_iso: Optional[str]) -> List[Dict]:
    """Retorna receita acumulada por dia no período (aproximação pelo valor_unit atual)."""
    try:
        series = get_revenue_by_day(nome_rifa, start_iso, end_iso)
        total = 0.0
        out: List[Dict] = []
        for item in series:
            total += float(item['receita'])
            out.append(dict(dia=item['dia'], acumulado=total))
        logger.debug(f"Receita acumulada calculada para rifa {nome_rifa}")
        return out
    except Exception as e:
        logger.error(f"Falha ao calcular receita acumulada para rifa {nome_rifa}", exception=e)
        return []

def get_sales_heatmap(nome_rifa: str, days: int = 30) -> List[Dict]:
    """Retorna contagem de vendas por dia da semana (0-6) e hora (0-23) nos últimos N dias."""
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT CAST(STRFTIME('%w', v.timestamp) AS INTEGER) AS dow,
                   CAST(STRFTIME('%H', v.timestamp) AS INTEGER) AS hour,
                   COUNT(v.id) AS quantidade
            FROM vendas v JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ? AND v.timestamp >= DATETIME('now', ?)
            GROUP BY dow, hour
            """,
            (nome_rifa, f'-{int(days)} days'),
        )
        rows = cur.fetchall()
        data = [dict(dow=int(r['dow']), hour=int(r['hour']), quantidade=int(r['quantidade'])) for r in rows]
        logger.debug(f"Heatmap de vendas carregado para rifa {nome_rifa}", days=days)
        return data
    except Exception as e:
        logger.error(f"Falha ao obter heatmap de vendas para rifa {nome_rifa}", exception=e)
        return []
    finally:
        conn.close()

def get_sales_by_hour(nome_rifa: str, days: int = 7) -> List[Dict]:
    """Retorna quantidade de vendas por hora (0-23) nos últimos N dias."""
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT CAST(STRFTIME('%H', v.timestamp) AS INTEGER) as hora, COUNT(v.id) as quantidade
            FROM vendas v JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ? AND v.timestamp >= DATETIME('now', ?)
            GROUP BY hora
            ORDER BY hora ASC
            """,
            (nome_rifa, f'-{int(days)} days'),
        )
        res = {int(row['hora']): int(row['quantidade']) for row in cur.fetchall()}
        data = [dict(hora=h, quantidade=res.get(h, 0)) for h in range(24)]
        logger.debug(f"Vendas por hora carregadas para rifa {nome_rifa}", days=days)
        return data
    except Exception as e:
        logger.error(f"Falha ao obter vendas por hora para rifa {nome_rifa}", exception=e)
        return []
    finally:
        conn.close()

def get_sales_in_period(nome_rifa: str, start_iso: Optional[str], end_iso: Optional[str]) -> List[Dict]:
    """Retorna vendas no período [start_iso, end_iso]. Se algum limite for None, não aplica esse lado."""
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        base_sql = (
            "SELECT v.numero, v.comprador, IFNULL(v.contato, '') AS contato, v.timestamp "
            "FROM vendas v JOIN rifas r ON v.rifa_id = r.id WHERE r.nome = ?"
        )
        params: List[Any] = [nome_rifa]
        if start_iso:
            base_sql += " AND v.timestamp >= ?"
            params.append(start_iso)
        if end_iso:
            base_sql += " AND v.timestamp <= ?"
            params.append(end_iso)
        base_sql += " ORDER BY v.timestamp DESC, v.id DESC"
        cur.execute(base_sql, params)
        data = [dict(numero=int(r['numero']), comprador=r['comprador'], contato=r['contato'], timestamp=r['timestamp']) for r in cur.fetchall()]
        logger.debug(f"Vendas no período carregadas para rifa {nome_rifa}", period=f"{start_iso} to {end_iso}")
        return data
    except Exception as e:
        logger.error(f"Falha ao obter vendas no período para rifa {nome_rifa}", exception=e)
        return []
    finally:
        conn.close()

# ----------------- Minha Conta -----------------

def update_user_name(user_id: int, new_name: str) -> Tuple[bool, str]:
    new_name = (new_name or '').strip()
    if not new_name:
        logger.warning("Tentativa de atualizar nome com valor inválido", user_id=user_id)
        return False, 'Nome inválido.'
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, int(user_id)))
            logger.success(f"Nome do usuário {user_id} atualizado para {new_name}")
            return True, 'Nome atualizado.'
    except Exception as e:
        logger.error(f"Falha ao atualizar nome do usuário {user_id}", exception=e)
        return False, f"Erro ao atualizar nome: {str(e)}"
    finally:
        conn.close()

def update_user_password(user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
    if not new_password:
        logger.warning("Tentativa de atualizar senha com valor inválido", user_id=user_id)
        return False, 'Nova senha inválida.'
    if len(new_password) < 8 or not any(c.isupper() for c in new_password) or not any(c.islower() for c in new_password) or not any(c.isdigit() for c in new_password):
        logger.warning("Tentativa de atualizar com senha fraca", user_id=user_id)
        return False, 'Nova senha fraca. Use ao menos 8 caracteres, incluindo maiúscula, minúscula e número.'
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE id = ?", (int(user_id),))
        row = cur.fetchone()
        if not row:
            logger.warning(f"Usuário {user_id} não encontrado para atualização de senha")
            return False, 'Usuário não encontrado.'
        if not _check_password(old_password or '', row['password_hash']):
            logger.warning(f"Senha atual incorreta para usuário {user_id}")
            return False, 'Senha atual incorreta.'
        new_hash = _hash_password(new_password)
        with conn:
            cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, int(user_id)))
        logger.success(f"Senha do usuário {user_id} atualizada com sucesso")
        return True, 'Senha atualizada.'
    except Exception as e:
        logger.error(f"Falha ao atualizar senha do usuário {user_id}", exception=e)
        return False, f"Erro ao atualizar senha: {str(e)}"
    finally:
        conn.close()

def listar_rifas_sem_dono() -> List[str]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT nome FROM rifas WHERE owner_id IS NULL ORDER BY nome ASC")
        data = [row['nome'] for row in cur.fetchall()]
        logger.debug("Rifas sem dono listadas", count=len(data))
        return data
    except Exception as e:
        logger.error("Falha ao listar rifas sem dono", exception=e)
        return []
    finally:
        conn.close()

def authenticate(email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    email = (email or '').strip().lower()
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT fail_count, locked_until FROM login_attempts WHERE email = ?", (email,))
        la = cur.fetchone()
        now_iso = _utcnow_iso()
        if la and la["locked_until"] and la["locked_until"] > now_iso:
            logger.warning(f"Conta {email} bloqueada por excesso de tentativas")
            return False, 'Muitas tentativas. Tente novamente mais tarde.', None
        cur.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        if not row:
            with conn:
                if la:
                    fc = int(la["fail_count"]) + 1
                    locked = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat() if fc >= 5 else None
                    cur.execute("UPDATE login_attempts SET fail_count = ?, locked_until = ? WHERE email = ?", (fc, locked, email))
                else:
                    cur.execute("INSERT INTO login_attempts (email, fail_count, locked_until) VALUES (?, ?, ?)", (email, 1, None))
            logger.warning(f"Usuário {email} não encontrado")
            return False, 'Usuário não encontrado.', None
        if not _check_password(password, row['password_hash']):
            with conn:
                if la:
                    fc = int(la["fail_count"]) + 1
                    locked = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat() if fc >= 5 else None
                    cur.execute("UPDATE login_attempts SET fail_count = ?, locked_until = ? WHERE email = ?", (fc, locked, email))
                else:
                    cur.execute("INSERT INTO login_attempts (email, fail_count, locked_until) VALUES (?, ?, ?)", (email, 1, None))
            logger.warning(f"Senha inválida para usuário {email}")
            return False, 'Senha inválida.', None
        with conn:
            cur.execute("DELETE FROM login_attempts WHERE email = ?", (email,))
        logger.success(f"Usuário {email} autenticado com sucesso", user_id=row['id'])
        return True, 'Autenticado.', {'id': row['id'], 'name': row['name'], 'email': row['email']}
    except Exception as e:
        logger.error(f"Falha ao autenticar usuário {email}", exception=e)
        return False, f"Erro ao autenticar: {str(e)}", None
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, email FROM users WHERE id = ?", (int(user_id),))
        r = cur.fetchone()
        if r:
            logger.debug(f"Usuário {user_id} carregado com sucesso")
            return dict(r)
        logger.warning(f"Usuário {user_id} não encontrado")
        return None
    except Exception as e:
        logger.error(f"Falha ao carregar usuário {user_id}", exception=e)
        return None
    finally:
        conn.close()

# ----------------- Rifas -----------------

def listar_rifas() -> List[str]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT nome FROM rifas ORDER BY nome ASC")
        data = [row["nome"] for row in cur.fetchall()]
        logger.debug("Rifas listadas", count=len(data))
        return data
    except Exception as e:
        logger.error("Falha ao listar rifas", exception=e)
        return []
    finally:
        conn.close()

def listar_rifas_do_usuario(user_id: int) -> List[str]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT nome FROM rifas WHERE owner_id = ? ORDER BY nome ASC", (int(user_id),))
        data = [row['nome'] for row in cur.fetchall()]
        logger.debug(f"Rifas do usuário {user_id} listadas", count=len(data))
        return data
    except Exception as e:
        logger.error(f"Falha ao listar rifas do usuário {user_id}", exception=e)
        return []
    finally:
        conn.close()

def get_config_rifa(nome_rifa: str) -> Optional[Dict[str, Any]]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT nome, valor_numero, total_numeros, config_json, sorteio_realizado, sorteio_numero, sorteio_comprador, owner_id
            FROM rifas WHERE nome = ?
            """,
            (nome_rifa,),
        )
        row = cur.fetchone()
        if not row:
            logger.warning(f"Rifa {nome_rifa} não encontrada")
            return None
        cfg = dict(row)
        extra = json.loads(cfg.get("config_json", "{}") or "{}")
        cfg.update(extra)
        logger.debug(f"Configuração da rifa {nome_rifa} carregada")
        return cfg
    except Exception as e:
        logger.error(f"Falha ao carregar configuração da rifa {nome_rifa}", exception=e)
        return None
    finally:
        conn.close()

def atualizar_config_rifa(nome_rifa: str, updates: Dict) -> Tuple[bool, str]:
    try:
        conn = db.get_connection()
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT config_json FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"Rifa {nome_rifa} não encontrada para atualização de configuração")
                return False, "Rifa não encontrada."
            current = json.loads(row["config_json"] or "{}")
            current.update(updates or {})
            cur.execute("UPDATE rifas SET config_json = ? WHERE nome = ?", (json.dumps(current, ensure_ascii=False), nome_rifa))
            logger.success(f"Configuração da rifa {nome_rifa} atualizada")
            return True, "Configuração atualizada."
    except Exception as e:
        logger.error(f"Falha ao atualizar configuração da rifa {nome_rifa}", exception=e)
        return False, f"Erro ao atualizar configuração: {str(e)}"
    finally:
        conn.close()

def salvar_nova_rifa(nome: str, valor_numero: float, total_numeros: int) -> Tuple[bool, str]:
    nome = (nome or "").strip()
    if not nome or total_numeros <= 0 or valor_numero < 0:
        logger.warning("Tentativa de criar rifa com dados inválidos", nome=nome, valor_numero=valor_numero, total_numeros=total_numeros)
        return False, "Dados inválidos para criar a rifa."
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO rifas (nome, valor_numero, total_numeros) VALUES (?, ?, ?)",
                (nome, float(valor_numero), int(total_numeros)),
            )
            logger.success(f"Rifa {nome} criada com sucesso")
            if JSON_MIRROR:
                idx = _json_index_load()
                idx[nome] = {
                    "valor_numero": float(valor_numero),
                    "total_numeros": int(total_numeros),
                    "sorteio": {"realizado": False, "numero": None, "comprador": None},
                }
                _json_index_save(idx)
            return True, "Rifa criada com sucesso."
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            logger.warning(f"Tentativa de criar rifa com nome duplicado: {nome}")
            return False, "Já existe uma rifa com este nome."
        logger.error(f"Falha ao criar rifa {nome}", exception=e)
        return False, f"Erro ao criar rifa: {str(e)}"
    finally:
        conn.close()

def salvar_nova_rifa_com_owner(nome: str, valor_numero: float, total_numeros: int, owner_id: int) -> Tuple[bool, str]:
    ok, msg = salvar_nova_rifa(nome, valor_numero, total_numeros)
    if not ok:
        return ok, msg
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("UPDATE rifas SET owner_id = ? WHERE nome = ?", (int(owner_id), nome))
            logger.success(f"Rifa {nome} atribuída ao usuário {owner_id}")
            return True, "Rifa criada e atribuída ao usuário."
    except Exception as e:
        logger.error(f"Falha ao atribuir dono à rifa {nome}", exception=e)
        return True, "Rifa criada, mas não foi possível atribuir o dono."
    finally:
        conn.close()

def claim_rifa(nome_rifa: str, user_id: int) -> Tuple[bool, str]:
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT owner_id FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"Rifa {nome_rifa} não encontrada para reivindicação")
                return False, 'Rifa não encontrada.'
            if row['owner_id'] is not None:
                logger.warning(f"Rifa {nome_rifa} já possui dono")
                return False, 'Rifa já possui dono.'
            cur.execute("UPDATE rifas SET owner_id = ? WHERE nome = ?", (int(user_id), nome_rifa))
            logger.success(f"Rifa {nome_rifa} reivindicada pelo usuário {user_id}")
            return True, 'Rifa atribuída ao seu usuário.'
    except Exception as e:
        logger.error(f"Falha ao reivindicar rifa {nome_rifa} para usuário {user_id}", exception=e)
        return False, f"Erro ao reivindicar rifa: {str(e)}"
    finally:
        conn.close()

# ----------------- Vendas -----------------

def carregar_dados_rifa(nome_rifa: str) -> Dict[str, str]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT v.numero, v.comprador
            FROM vendas v JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ?
            """,
            (nome_rifa,),
        )
        data = {str(row["numero"]): row["comprador"] for row in cur.fetchall()}
        logger.debug(f"Dados da rifa {nome_rifa} carregados", count=len(data))
        return data
    except Exception as e:
        logger.error(f"Falha ao carregar dados da rifa {nome_rifa}", exception=e)
        return {}
    finally:
        conn.close()

def registrar_venda(nome_rifa: str, nome_comprador: str, numeros: List[int], contato: Optional[str] = None, data_compra: Optional[str] = None) -> Tuple[bool, List[int], str]:
    if not isinstance(numeros, list):
        numeros = [int(numeros)]
    nome_comprador = (nome_comprador or "").strip()
    if not nome_comprador:
        logger.warning("Tentativa de registrar venda com comprador inválido", rifa=nome_rifa)
        return False, numeros, "Comprador inválido."
    
    # Validar e formatar a data de compra, se fornecida
    if data_compra:
        try:
            # Tenta converter para datetime para validar o formato
            from datetime import datetime
            data_obj = datetime.fromisoformat(data_compra.replace('Z', '+00:00'))
            # Garante que está no formato ISO 8601 com timezone
            data_compra = data_obj.isoformat()
        except (ValueError, AttributeError) as e:
            logger.warning(f"Formato de data inválido: {data_compra}", exception=e)
            return False, numeros, "Formato de data inválido. Use o formato AAAA-MM-DD ou AAAA-MM-DDTHH:MM:SS±HH:MM"
    
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, total_numeros FROM rifas WHERE nome = ?", (nome_rifa,))
            rifa = cur.fetchone()
            if not rifa:
                logger.warning(f"Rifa {nome_rifa} não encontrada para venda")
                return False, numeros, "Rifa não encontrada."
            rifa_id = rifa["id"]
            total = int(rifa["total_numeros"])
            nums = [int(n) for n in numeros if 1 <= int(n) <= total]
            if not nums:
                logger.warning("Tentativa de registrar venda com números inválidos", rifa=nome_rifa, numeros=numeros)
                return False, numeros, "Números inválidos."
            placeholders = ",".join(["?"] * len(nums))
            cur.execute(
                f"SELECT numero FROM vendas WHERE rifa_id = ? AND numero IN ({placeholders})",
                [rifa_id] + nums,
            )
            conflitos = [row["numero"] for row in cur.fetchall()]
            if conflitos:
                logger.warning(f"Números já vendidos para rifa {nome_rifa}", conflitos=conflitos)
                return False, sorted(conflitos), "Alguns números já foram vendidos."
            
            # Usa a data fornecida ou a data/hora atual
            ts = data_compra if data_compra else _utcnow_iso()
            
            # Inserir vendas com data de compra
            vendas = [(rifa_id, n, nome_comprador, ts, (contato or ""), ts) for n in nums]
            cur.executemany(
                "INSERT INTO vendas (rifa_id, numero, comprador, timestamp, contato, data_compra) VALUES (?, ?, ?, ?, ?, ?)",
                vendas,
            )
            cur.execute(
                f"DELETE FROM reservas WHERE rifa_id = ? AND numero IN ({placeholders})",
                [rifa_id] + nums,
            )
            logger.success(f"Venda registrada para rifa {nome_rifa}", comprador=nome_comprador, numeros=sorted(nums))
            if JSON_MIRROR:
                dados = _json_dados_load(nome_rifa)
                for n in nums:
                    dados[str(int(n))] = nome_comprador
                _json_dados_save(nome_rifa, dados)
            return True, sorted(nums), "Venda registrada com sucesso."
    except Exception as e:
        logger.error(f"Falha ao registrar venda para rifa {nome_rifa}", exception=e)
        return False, numeros, f"Erro ao registrar venda: {str(e)}"
    finally:
        conn.close()

def cancelar_venda(nome_rifa: str, numeros: List[int]) -> Tuple[bool, List[int], str]:
    if not isinstance(numeros, list):
        numeros = [int(numeros)]
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"Rifa {nome_rifa} não encontrada para cancelamento de venda")
                return False, numeros, "Rifa não encontrada."
            rifa_id = row["id"]
            nums = [int(n) for n in numeros]
            placeholders = ",".join(["?"] * len(nums))
            cur.execute(
                f"DELETE FROM vendas WHERE rifa_id = ? AND numero IN ({placeholders})",
                [rifa_id] + nums,
            )
            affected = cur.rowcount
            if affected <= 0:
                logger.warning(f"Nenhum número vendido encontrado para cancelamento na rifa {nome_rifa}", numeros=nums)
                return False, [], "Nenhum dos números informados estava vendido."
            logger.success(f"Vendas canceladas para rifa {nome_rifa}", numeros=sorted(nums), affected=affected)
            if JSON_MIRROR:
                dados = _json_dados_load(nome_rifa)
                for n in nums:
                    dados.pop(str(int(n)), None)
                _json_dados_save(nome_rifa, dados)
            return True, nums, f"Vendas canceladas ({affected} números)."
    except Exception as e:
        logger.error(f"Falha ao cancelar vendas para rifa {nome_rifa}", exception=e)
        return False, [], f"Erro ao cancelar vendas: {str(e)}"
    finally:
        conn.close()

def transferir_venda(nome_rifa: str, numeros: List[int], novo_comprador: str) -> Tuple[bool, List[int], str]:
    if not isinstance(numeros, list):
        numeros = [int(numeros)]
    novo_comprador = (novo_comprador or "").strip()
    if not novo_comprador:
        logger.warning("Tentativa de transferir venda com comprador inválido", rifa=nome_rifa)
        return False, numeros, "Nome do novo comprador inválido."
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"Rifa {nome_rifa} não encontrada para transferência de venda")
                return False, numeros, "Rifa não encontrada."
            rifa_id = row["id"]
            nums = [int(n) for n in numeros]
            placeholders = ",".join(["?"] * len(nums))
            cur.execute(
                f"UPDATE vendas SET comprador = ? WHERE rifa_id = ? AND numero IN ({placeholders})",
                [novo_comprador, rifa_id] + nums,
            )
            affected = cur.rowcount
            if affected <= 0:
                logger.warning(f"Nenhum número encontrado para transferência na rifa {nome_rifa}", numeros=nums)
                return False, [], "Nenhum dos números informados foi encontrado para transferir."
            logger.success(f"Venda transferida para rifa {nome_rifa}", novo_comprador=novo_comprador, numeros=sorted(nums), affected=affected)
            if JSON_MIRROR:
                dados = _json_dados_load(nome_rifa)
                for n in nums:
                    if str(int(n)) in dados:
                        dados[str(int(n))] = novo_comprador
                _json_dados_save(nome_rifa, dados)
            return True, nums, f"Transferência realizada ({affected} números)."
    except Exception as e:
        logger.error(f"Falha ao transferir vendas para rifa {nome_rifa}", exception=e)
        return False, [], f"Erro ao transferir vendas: {str(e)}"
    finally:
        conn.close()

def deletar_rifa(nome_rifa: str) -> Tuple[bool, str]:
    """Deleta a rifa e seus dados relacionados. Operação irreversível."""
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"Rifa {nome_rifa} não encontrada para deleção")
                return False, "Rifa não encontrada."
            rifa_id = row["id"]
            cur.execute("DELETE FROM rifas WHERE id = ?", (rifa_id,))
            logger.success(f"Rifa {nome_rifa} deletada com sucesso", rifa_id=rifa_id)
            if JSON_MIRROR:
                idx = _json_index_load()
                if nome_rifa in idx:
                    idx.pop(nome_rifa, None)
                    _json_index_save(idx)
                try:
                    p = _json_rifa_path(nome_rifa)
                    if p.exists():
                        p.unlink()
                        logger.debug(f"Arquivo JSON da rifa {nome_rifa} removido")
                except Exception as e:
                    logger.warning(f"Falha ao remover arquivo JSON da rifa {nome_rifa}", exception=e)
            return True, "Rifa deletada com sucesso."
    except Exception as e:
        logger.error(f"Falha ao deletar rifa {nome_rifa}", exception=e)
        return False, f"Erro ao deletar rifa: {str(e)}"
    finally:
        conn.close()

# ----------------- Reservas -----------------

def carregar_reservas_detalhe(nome_rifa: str) -> Dict[int, str]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT res.numero, res.timestamp
            FROM reservas res JOIN rifas r ON res.rifa_id = r.id
            WHERE r.nome = ?
            """,
            (nome_rifa,),
        )
        data = {int(row["numero"]): row["timestamp"] for row in cur.fetchall()}
        logger.debug(f"Reservas detalhadas carregadas para rifa {nome_rifa}", count=len(data))
        return data
    except Exception as e:
        logger.error(f"Falha ao carregar reservas detalhadas para rifa {nome_rifa}", exception=e)
        return {}
    finally:
        conn.close()

def salvar_reservas_detalhe(nome_rifa: str, reservas: Dict[int, str]) -> None:
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"Rifa {nome_rifa} não encontrada para salvar reservas")
                return
            rifa_id = row["id"]
            cur.execute("DELETE FROM reservas WHERE rifa_id = ?", (rifa_id,))
            batch = [(rifa_id, int(num), str(ts)) for num, ts in (reservas or {}).items()]
            if batch:
                cur.executemany(
                    "INSERT INTO reservas (rifa_id, numero, timestamp) VALUES (?, ?, ?)",
                    batch,
                )
                logger.success(f"Reservas salvas para rifa {nome_rifa}", count=len(batch))
    except Exception as e:
        logger.error(f"Falha ao salvar reservas detalhadas para rifa {nome_rifa}", exception=e)
    finally:
        conn.close()

def purge_expired_reservas(nome_rifa: str, ttl_minutes: int) -> Tuple[Dict[int, str], List[int]]:
    if ttl_minutes <= 0:
        data = carregar_reservas_detalhe(nome_rifa)
        logger.debug(f"TTL de reservas desativado para rifa {nome_rifa}, retornando reservas atuais")
        return data, []
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"Rifa {nome_rifa} não encontrada para purga de reservas")
                return {}, []
            rifa_id = row["id"]
            limit_ts = (datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes)).isoformat()
            cur.execute(
                "SELECT numero FROM reservas WHERE rifa_id = ? AND timestamp < ?",
                (rifa_id, limit_ts),
            )
            removidos = [int(r["numero"]) for r in cur.fetchall()]
            if removidos:
                cur.execute(
                    "DELETE FROM reservas WHERE rifa_id = ? AND timestamp < ?",
                    (rifa_id, limit_ts),
                )
                logger.success(f"Reservas expiradas removidas para rifa {nome_rifa}", removidos=sorted(removidos))
            ativos = carregar_reservas_detalhe(nome_rifa)
            return ativos, removidos
    except Exception as e:
        logger.error(f"Falha ao purgar reservas expiradas para rifa {nome_rifa}", exception=e)
        return {}, []
    finally:
        conn.close()

# ----------------- Sorteio e Relatórios -----------------

def escolher_vencedor(nome_rifa: str) -> Tuple[bool, Optional[int], Optional[str], str]:
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, sorteio_realizado FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"Rifa {nome_rifa} não encontrada para sorteio")
                return False, None, None, "Rifa não encontrada."
            if int(row["sorteio_realizado"]) == 1:
                logger.warning(f"Sorteio já realizado para rifa {nome_rifa}")
                return False, None, None, "Sorteio já foi realizado."
            rifa_id = row["id"]
            cur.execute("SELECT numero, comprador FROM vendas WHERE rifa_id = ?", (rifa_id,))
            vendidos = cur.fetchall()
            if not vendidos:
                logger.warning(f"Nenhum número vendido para sorteio na rifa {nome_rifa}")
                return False, None, None, "Nenhum número vendido para sortear."
            vencedor = random.choice(vendidos)
            numero_sorteado = int(vencedor["numero"])
            comprador = vencedor["comprador"]
            cur.execute(
                "UPDATE rifas SET sorteio_realizado = 1, sorteio_numero = ?, sorteio_comprador = ? WHERE id = ?",
                (numero_sorteado, comprador, rifa_id),
            )
            logger.success(f"Sorteio realizado para rifa {nome_rifa}", numero=numero_sorteado, comprador=comprador)
            return True, numero_sorteado, comprador, "Sorteio realizado com sucesso."
    except Exception as e:
        logger.exception(f"Erro ao realizar sorteio para rifa {nome_rifa}")
        return False, None, None, f"Erro ao realizar sorteio: {str(e)}"

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
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Obtém o ID da rifa e o valor unitário
        cursor.execute("SELECT id, valor_numero FROM rifas WHERE nome = ?", (nome_rifa,))
        rifa = cursor.fetchone()
        
        if not rifa:
            logger.error(f"Rifa não encontrada: {nome_rifa}")
            return []
            
        rifa_id = rifa['id']
        valor_unit = float(rifa['valor_numero'])
        
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
                'compras_pagas': compras_pagas,
                'valor_total': quantidade * valor_unit
            })
            
            logger.debug(f"Comprador: {comprador}, Números: {quantidade}, Pagos: {compras_pagas}")
        
        logger.info(f"Encontrados {len(result)} compradores para a rifa {nome_rifa}")
        return result
        
    except Exception as e:
        logger.error(f"Erro ao buscar top compradores para a rifa {nome_rifa}", exception=e)
        # Em caso de erro, tenta um fallback mais simples
        try:
            # Obtém o valor unitário para o cálculo do valor_total
            cursor.execute("SELECT valor_numero FROM rifas WHERE id = ?", (rifa_id,))
            rifa = cursor.fetchone()
            valor_unit = float(rifa['valor_numero']) if rifa else 0
            
            cursor.execute("""
                SELECT comprador, COUNT(*) as quantidade
                FROM vendas 
                WHERE rifa_id = ?
                GROUP BY comprador 
                ORDER BY quantidade DESC 
                LIMIT ?;
            """, (rifa_id, limit))
            
            # Garante que todos os campos necessários estejam presentes
            result = []
            for row in cursor.fetchall():
                comprador = row['comprador']
                quantidade = row['quantidade']
                result.append({
                    'comprador': comprador,
                    'quantidade': quantidade,
                    'compras_pagas': 0,  # Valor padrão para o fallback
                    'valor_total': quantidade * valor_unit
                })
            
            return result
        except Exception as e2:
            logger.error("Erro no fallback de busca de compradores", exception=e2)
            return []
    finally:
        conn.close()

def carregar_vendas_periodo(nome_rifa: str, periodo: str) -> List[Dict]:
    now = datetime.now(timezone.utc)
    if periodo == "dia":
        delta = timedelta(days=1)
    elif periodo == "semana":
        delta = timedelta(weeks=1)
    elif periodo == "mes":
        delta = timedelta(days=30)
    else:
        delta = timedelta(days=3650)
    start = (now - delta).isoformat()
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT v.timestamp as ts, v.comprador, v.numero
            FROM vendas v JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ? AND v.timestamp >= ?
            ORDER BY v.timestamp DESC
            """,
            (nome_rifa, start),
        )
        eventos: Dict[Tuple[str, str], Dict] = {}
        for row in cur.fetchall():
            key = (row["ts"], row["comprador"])
            if key not in eventos:
                eventos[key] = {"ts": row["ts"], "comprador": row["comprador"], "numeros": [], "qtd": 0}
            eventos[key]["numeros"].append(int(row["numero"]))
            eventos[key]["qtd"] += 1
        data = list(eventos.values())
        logger.debug(f"Vendas do período {periodo} carregadas para rifa {nome_rifa}", count=len(data))
        return data
    except Exception as e:
        logger.error(f"Falha ao carregar vendas do período {periodo} para rifa {nome_rifa}", exception=e)
        return []
    finally:
        conn.close()