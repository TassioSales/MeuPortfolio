from __future__ import annotations

from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timezone, timedelta
import json
import random
from pathlib import Path
import bcrypt
import os
import io
import zipfile

from . import database as db
from logger import logger

# ----------------- Util -----------------

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ----------------- JSON fallback/mirror -----------------

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
INDEX_FILE = DATA_DIR / "index.json"

# Ligamos o espelhamento para JSON (quando possível) para manter compatibilidade
# Pode ser controlado por variável de ambiente JSON_MIRROR=true/false
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
            return json.loads(INDEX_FILE.read_text(encoding='utf-8') or '{}')
    except Exception:
        pass
    return {}

def _json_index_save(index: Dict[str, Dict]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as e:
        logger.warning(f"Mirror JSON: falha ao salvar index.json: {e}")

def _json_dados_load(nome_rifa: str) -> Dict[str, str]:
    p = _json_rifa_path(nome_rifa)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8') or '{}')
    except Exception:
        return {}

def _json_dados_save(nome_rifa: str, dados: Dict[str, str]) -> None:
    try:
        p = _json_rifa_path(nome_rifa)
        p.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as e:
        logger.warning(f"Mirror JSON: falha ao salvar {p.name}: {e}")

def migrate_from_json() -> None:
    """Importa dados de JSON para SQLite se o DB estiver vazio para aquela rifa."""
    index = _json_index_load()
    if not index:
        return
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            for nome, cfg in index.items():
                # Se rifa já existe no DB, pule
                cur.execute("SELECT id FROM rifas WHERE nome = ?", (nome,))
                row = cur.fetchone()
                if not row:
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
                # Vendas
                dados = _json_dados_load(nome)
                if dados:
                    ts = _utcnow_iso()
                    vendas = [(rifa_id, int(n), c, ts) for n, c in dados.items()]
                    try:
                        cur.executemany(
                            "INSERT OR IGNORE INTO vendas (rifa_id, numero, comprador, timestamp) VALUES (?, ?, ?, ?)",
                            vendas,
                        )
                    except Exception:
                        pass
        logger.info("Migração JSON→SQLite concluída.")
    except Exception as e:
        logger.exception(f"Falha na migração JSON→SQLite: {e}")

def export_backup_json_zip() -> bytes:
    """Gera um ZIP com index.json e arquivos de rifas JSON."""
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        if INDEX_FILE.exists():
            zf.writestr('index.json', INDEX_FILE.read_text(encoding='utf-8'))
        for jf in DATA_DIR.glob('*.json'):
            if jf.name == 'index.json':
                continue
            zf.writestr(jf.name, jf.read_text(encoding='utf-8'))
    mem.seek(0)
    return mem.getvalue()

# ----------------- Users (Multiusuário) -----------------

def _hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def _check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def create_user(name: str, email: str, password: str) -> Tuple[bool, str, Optional[int]]:
    name = (name or '').strip()
    email = (email or '').strip().lower()
    if not name or not email or not password:
        return False, 'Dados inválidos.', None
    # senha forte mínima: 8+, 1 maiúscula, 1 minúscula, 1 dígito
    if len(password) < 8 or not any(c.isupper() for c in password) or not any(c.islower() for c in password) or not any(c.isdigit() for c in password):
        return False, 'Senha fraca. Use ao menos 8 caracteres, incluindo maiúscula, minúscula e número.', None
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cur.fetchone():
                return False, 'E-mail já cadastrado.', None
            cur.execute(
                "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (name, email, _hash_password(password), _utcnow_iso()),
            )
            cur.execute("SELECT id FROM users WHERE email = ?", (email,))
            row = cur.fetchone()
            return True, 'Usuário criado com sucesso.', int(row['id']) if row else None
    except Exception as e:
        logger.exception(f"DB: create_user erro: {e}")
        return False, f"Erro: {e}", None
    finally:
        conn.close()

def set_json_mirror(enabled: bool) -> None:
    """Ativa/desativa espelhamento JSON em tempo de execução."""
    global JSON_MIRROR
    JSON_MIRROR = bool(enabled)

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
        return [dict(dow=d, quantidade=res.get(d, 0)) for d in range(7)]
    finally:
        conn.close()

def get_revenue_by_day(nome_rifa: str, start_iso: Optional[str], end_iso: Optional[str]) -> List[Dict]:
    """Retorna receita por dia no período utilizando valor_numero atual da rifa (aproximação)."""
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT valor_numero FROM rifas WHERE nome = ?", (nome_rifa,))
        r = cur.fetchone()
        valor_unit = float(r['valor_numero']) if r else 0.0

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
        return [dict(dia=row['dia'], receita=float(row['qtd']) * valor_unit, qtd=int(row['qtd'])) for row in cur.fetchall()]
    finally:
        conn.close()

def get_cumulative_revenue(nome_rifa: str, start_iso: Optional[str], end_iso: Optional[str]) -> List[Dict]:
    """Retorna receita acumulada por dia no período (aproximação pelo valor_unit atual)."""
    series = get_revenue_by_day(nome_rifa, start_iso, end_iso)
    total = 0.0
    out: List[Dict] = []
    for item in series:
        total += float(item['receita'])
        out.append(dict(dia=item['dia'], acumulado=total))
    return out

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
        return data
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
        return [dict(hora=h, quantidade=res.get(h, 0)) for h in range(24)]
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
        return [dict(numero=int(r['numero']), comprador=r['comprador'], contato=r['contato'], timestamp=r['timestamp']) for r in cur.fetchall()]
    finally:
        conn.close()

# ----------------- Minha Conta -----------------

def update_user_name(user_id: int, new_name: str) -> Tuple[bool, str]:
    new_name = (new_name or '').strip()
    if not new_name:
        return False, 'Nome inválido.'
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, int(user_id)))
        return True, 'Nome atualizado.'
    except Exception as e:
        logger.exception(f"DB: update_user_name erro: {e}")
        return False, f"Erro: {e}"
    finally:
        conn.close()

def update_user_password(user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
    if not new_password:
        return False, 'Nova senha inválida.'
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE id = ?", (int(user_id),))
        row = cur.fetchone()
        if not row:
            return False, 'Usuário não encontrado.'
        if not _check_password(old_password or '', row['password_hash']):
            return False, 'Senha atual incorreta.'
        new_hash = _hash_password(new_password)
        with conn:
            cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, int(user_id)))
        return True, 'Senha atualizada.'
    except Exception as e:
        logger.exception(f"DB: update_user_password erro: {e}")
        return False, f"Erro: {e}"
    finally:
        conn.close()

def listar_rifas_sem_dono() -> List[str]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT nome FROM rifas WHERE owner_id IS NULL ORDER BY nome ASC")
        return [row['nome'] for row in cur.fetchall()]
    finally:
        conn.close()

def authenticate(email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    email = (email or '').strip().lower()
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        # Rate limit: verificar bloqueio
        cur.execute("SELECT fail_count, locked_until FROM login_attempts WHERE email = ?", (email,))
        la = cur.fetchone()
        now_iso = _utcnow_iso()
        if la and la["locked_until"] and la["locked_until"] > now_iso:
            return False, 'Muitas tentativas. Tente novamente mais tarde.', None

        cur.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        if not row:
            # registrar falha
            with conn:
                if la:
                    fc = int(la["fail_count"]) + 1
                    locked = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat() if fc >= 5 else None
                    cur.execute("UPDATE login_attempts SET fail_count = ?, locked_until = ? WHERE email = ?", (fc, locked, email))
                else:
                    cur.execute("INSERT INTO login_attempts (email, fail_count, locked_until) VALUES (?, ?, ?)", (email, 1, None))
            return False, 'Usuário não encontrado.', None
        if not _check_password(password, row['password_hash']):
            with conn:
                if la:
                    fc = int(la["fail_count"]) + 1
                    locked = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat() if fc >= 5 else None
                    cur.execute("UPDATE login_attempts SET fail_count = ?, locked_until = ? WHERE email = ?", (fc, locked, email))
                else:
                    cur.execute("INSERT INTO login_attempts (email, fail_count, locked_until) VALUES (?, ?, ?)", (email, 1, None))
            return False, 'Senha inválida.', None
        # sucesso: reset contador
        with conn:
            cur.execute("DELETE FROM login_attempts WHERE email = ?", (email,))
        return True, 'Autenticado.', {'id': row['id'], 'name': row['name'], 'email': row['email']}
    except Exception as e:
        logger.exception(f"DB: authenticate erro: {e}")
        return False, f"Erro: {e}", None
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, email FROM users WHERE id = ?", (int(user_id),))
        r = cur.fetchone()
        return dict(r) if r else None
    finally:
        conn.close()

# ----------------- Rifas -----------------

def listar_rifas() -> List[str]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT nome FROM rifas ORDER BY nome ASC")
        return [row["nome"] for row in cur.fetchall()]
    finally:
        conn.close()

def listar_rifas_do_usuario(user_id: int) -> List[str]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT nome FROM rifas WHERE owner_id = ? ORDER BY nome ASC", (int(user_id),))
        return [row['nome'] for row in cur.fetchall()]
    finally:
        conn.close()

# ----------------- Analytics helpers -----------------

def get_sales_by_day(nome_rifa: str) -> List[Dict]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DATE(v.timestamp) as dia, COUNT(v.id) as quantidade
            FROM vendas v JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ?
            GROUP BY DATE(v.timestamp)
            ORDER BY DATE(v.timestamp) ASC
            """,
            (nome_rifa,),
        )
        return [dict(dia=row["dia"], quantidade=row["quantidade"]) for row in cur.fetchall()]
    finally:
        conn.close()

def get_top_buyers(nome_rifa: str, limit: int = 10) -> List[Dict]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT v.comprador as comprador, COUNT(v.id) as quantidade
            FROM vendas v JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ?
            GROUP BY v.comprador
            ORDER BY quantidade DESC
            LIMIT ?
            """,
            (nome_rifa, int(limit)),
        )
        return [dict(comprador=row["comprador"], quantidade=row["quantidade"]) for row in cur.fetchall()]
    finally:
        conn.close()

def get_recent_sales(nome_rifa: str, limit: int = 10) -> List[Dict]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT v.timestamp as ts, v.comprador, v.numero, IFNULL(v.contato, '') AS contato
            FROM vendas v JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ?
            ORDER BY v.timestamp DESC, v.id DESC
            LIMIT ?
            """,
            (nome_rifa, int(limit)),
        )
        return [dict(ts=row['ts'], comprador=row['comprador'], numero=int(row['numero']), contato=row['contato']) for row in cur.fetchall()]
    finally:
        conn.close()

def get_all_sales(nome_rifa: str) -> List[Dict]:
    """Retorna todas as vendas da rifa com contato e timestamp."""
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT v.numero, v.comprador, IFNULL(v.contato, '') AS contato, v.timestamp
            FROM vendas v JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ?
            ORDER BY v.numero ASC
            """,
            (nome_rifa,),
        )
        return [dict(numero=int(r['numero']), comprador=r['comprador'], contato=r['contato'], timestamp=r['timestamp']) for r in cur.fetchall()]
    finally:
        conn.close()


def get_config_rifa(nome_rifa: str) -> Optional[Dict[str, Any]]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM rifas WHERE nome = ?", (nome_rifa,))
        row = cur.fetchone()
        if not row:
            return None
        cfg = dict(row)
        extra = json.loads(cfg.get("config_json", "{}") or "{}")
        cfg.update(extra)
        return cfg
    finally:
        conn.close()


def atualizar_config_rifa(nome_rifa: str, updates: Dict) -> Tuple[bool, str]:
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT config_json FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
                return False, "Rifa não encontrada."
            current = json.loads(row["config_json"] or "{}")
            current.update(updates or {})
            cur.execute("UPDATE rifas SET config_json = ? WHERE nome = ?", (json.dumps(current, ensure_ascii=False), nome_rifa))
        return True, "Configuração atualizada."
    except Exception as e:
        logger.exception(f"DB: atualizar_config_rifa falhou: {e}")
        return False, f"Erro de banco de dados: {e}"


def salvar_nova_rifa(nome: str, valor_numero: float, total_numeros: int) -> Tuple[bool, str]:
    nome = (nome or "").strip()
    if not nome or total_numeros <= 0 or valor_numero < 0:
        return False, "Dados inválidos para criar a rifa."
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO rifas (nome, valor_numero, total_numeros) VALUES (?, ?, ?)",
                (nome, float(valor_numero), int(total_numeros)),
            )
        logger.info(f"DB: Rifa criada '{nome}'")
        # mirror JSON index
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
            return False, "Já existe uma rifa com este nome."
        logger.exception(f"DB: salvar_nova_rifa erro: {e}")
        return False, "Erro ao salvar no banco de dados."

def salvar_nova_rifa_com_owner(nome: str, valor_numero: float, total_numeros: int, owner_id: int) -> Tuple[bool, str]:
    ok, msg = salvar_nova_rifa(nome, valor_numero, total_numeros)
    if not ok:
        return ok, msg
    # atribuir owner
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("UPDATE rifas SET owner_id = ? WHERE nome = ?", (int(owner_id), nome))
        return True, "Rifa criada e atribuída ao usuário."
    except Exception as e:
        logger.exception(f"DB: salvar_nova_rifa_com_owner erro: {e}")
        return True, "Rifa criada, mas não foi possível atribuir o dono (owner)."
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
                return False, 'Rifa não encontrada.'
            if row['owner_id'] is not None:
                return False, 'Rifa já possui dono.'
            cur.execute("UPDATE rifas SET owner_id = ? WHERE nome = ?", (int(user_id), nome_rifa))
        return True, 'Rifa atribuída ao seu usuário.'
    except Exception as e:
        logger.exception(f"DB: claim_rifa erro: {e}")
        return False, f"Erro: {e}"
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
        return {str(row["numero"]): row["comprador"] for row in cur.fetchall()}
    finally:
        conn.close()


def registrar_venda(nome_rifa: str, nome_comprador: str, numeros: List[int], contato: Optional[str] = None) -> Tuple[bool, List[int], str]:
    if not isinstance(numeros, list):
        numeros = [int(numeros)]
    nome_comprador = (nome_comprador or "").strip()
    if not nome_comprador:
        return False, numeros, "Comprador inválido."

    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, total_numeros FROM rifas WHERE nome = ?", (nome_rifa,))
            rifa = cur.fetchone()
            if not rifa:
                return False, numeros, "Rifa não encontrada."
            rifa_id = rifa["id"]
            total = int(rifa["total_numeros"])
            nums = [int(n) for n in numeros if 1 <= int(n) <= total]
            if not nums:
                return False, numeros, "Números inválidos."
            placeholders = ",".join(["?"] * len(nums))
            cur.execute(
                f"SELECT numero FROM vendas WHERE rifa_id = ? AND numero IN ({placeholders})",
                [rifa_id] + nums,
            )
            conflitos = [row["numero"] for row in cur.fetchall()]
            if conflitos:
                return False, sorted(conflitos), "Alguns números já foram vendidos."
            ts = _utcnow_iso()
            vendas = [(rifa_id, n, nome_comprador, ts, (contato or "")) for n in nums]
            cur.executemany(
                "INSERT INTO vendas (rifa_id, numero, comprador, timestamp, contato) VALUES (?, ?, ?, ?, ?)",
                vendas,
            )
            # Remove reservas desses números
            cur.execute(
                f"DELETE FROM reservas WHERE rifa_id = ? AND numero IN ({placeholders})",
                [rifa_id] + nums,
            )
        logger.info(f"DB: venda registrada rifa='{nome_rifa}' comprador='{nome_comprador}' nums={sorted(nums)}")
        # mirror JSON vendas
        if JSON_MIRROR:
            dados = _json_dados_load(nome_rifa)
            for n in nums:
                dados[str(int(n))] = nome_comprador
            _json_dados_save(nome_rifa, dados)
        return True, sorted(nums), "Venda registrada com sucesso."
    except Exception as e:
        logger.exception(f"DB: registrar_venda erro: {e}")
        return False, numeros, f"Erro de banco de dados: {e}"


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
                return False, [], "Nenhum dos números informados estava vendido."
        logger.warning(f"DB: vendas canceladas rifa='{nome_rifa}' nums={sorted(nums)}")
        # mirror JSON remover
        if JSON_MIRROR:
            dados = _json_dados_load(nome_rifa)
            for n in nums:
                dados.pop(str(int(n)), None)
            _json_dados_save(nome_rifa, dados)
        return True, nums, f"Vendas canceladas ({affected} números)."
    except Exception as e:
        logger.exception(f"DB: cancelar_venda erro: {e}")
        return False, [], f"Erro de banco de dados: {e}"


def transferir_venda(nome_rifa: str, numeros: List[int], novo_comprador: str) -> Tuple[bool, List[int], str]:
    if not isinstance(numeros, list):
        numeros = [int(numeros)]
    novo_comprador = (novo_comprador or "").strip()
    if not novo_comprador:
        return False, numeros, "Nome do novo comprador inválido."
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
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
                return False, [], "Nenhum dos números informados foi encontrado para transferir."
        logger.info(f"DB: venda transferida rifa='{nome_rifa}' nums={sorted(nums)} novo='{novo_comprador}'")
        # mirror JSON atualizar
        if JSON_MIRROR:
            dados = _json_dados_load(nome_rifa)
            for n in nums:
                if str(int(n)) in dados:
                    dados[str(int(n))] = novo_comprador
            _json_dados_save(nome_rifa, dados)
        return True, nums, f"Transferência realizada ({affected} números)."
    except Exception as e:
        logger.exception(f"DB: transferir_venda erro: {e}")
        return False, [], f"Erro de banco de dados: {e}"

def deletar_rifa(nome_rifa: str) -> Tuple[bool, str]:
    """Deleta a rifa e seus dados relacionados. Operação irreversível."""
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
                return False, "Rifa não encontrada."
            rifa_id = row["id"]
            # Deleta a rifa (vendas e reservas serão removidas via ON DELETE CASCADE)
            cur.execute("DELETE FROM rifas WHERE id = ?", (rifa_id,))
        # Mirror JSON: remover index e arquivo da rifa
        if JSON_MIRROR:
            idx = _json_index_load()
            if nome_rifa in idx:
                idx.pop(nome_rifa, None)
                _json_index_save(idx)
            try:
                p = _json_rifa_path(nome_rifa)
                if p.exists():
                    p.unlink()
            except Exception:
                pass
        logger.warning(f"DB: Rifa deletada '{nome_rifa}' (id={rifa_id})")
        return True, "Rifa deletada com sucesso."
    except Exception as e:
        logger.exception(f"DB: deletar_rifa erro: {e}")
        return False, f"Erro ao deletar rifa: {e}"

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
        return {int(row["numero"]): row["timestamp"] for row in cur.fetchall()}
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
                return
            rifa_id = row["id"]
            # clear and insert
            cur.execute("DELETE FROM reservas WHERE rifa_id = ?", (rifa_id,))
            batch = [(rifa_id, int(num), str(ts)) for num, ts in (reservas or {}).items()]
            if batch:
                cur.executemany(
                    "INSERT INTO reservas (rifa_id, numero, timestamp) VALUES (?, ?, ?)",
                    batch,
                )
    except Exception as e:
        logger.exception(f"DB: salvar_reservas_detalhe erro: {e}")


def purge_expired_reservas(nome_rifa: str, ttl_minutes: int) -> Tuple[Dict[int, str], List[int]]:
    if ttl_minutes <= 0:
        return carregar_reservas_detalhe(nome_rifa), []
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
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
        ativos = carregar_reservas_detalhe(nome_rifa)
        if removidos:
            logger.info(f"Reservas expiradas removidas '{nome_rifa}': {sorted(removidos)}")
        return ativos, removidos
    except Exception as e:
        logger.exception(f"DB: purge_expired_reservas erro: {e}")
        return {}, []

# ----------------- Sorteio e Relatórios -----------------

def escolher_vencedor(nome_rifa: str) -> Tuple[bool, Optional[int], Optional[str], str]:
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, sorteio_realizado FROM rifas WHERE nome = ?", (nome_rifa,))
            row = cur.fetchone()
            if not row:
                return False, None, None, "Rifa não encontrada."
            if int(row["sorteio_realizado"]) == 1:
                return False, None, None, "Sorteio já foi realizado."
            rifa_id = row["id"]
            cur.execute("SELECT numero, comprador FROM vendas WHERE rifa_id = ?", (rifa_id,))
            vendidos = cur.fetchall()
            if not vendidos:
                return False, None, None, "Nenhum número vendido para sortear."
            vencedor = random.choice(vendidos)
            numero_sorteado = int(vencedor["numero"])
            comprador = vencedor["comprador"]
            cur.execute(
                "UPDATE rifas SET sorteio_realizado = 1, sorteio_numero = ?, sorteio_comprador = ? WHERE id = ?",
                (numero_sorteado, comprador, rifa_id),
            )
        logger.success(f"Sorteio realizado: rifa='{nome_rifa}' nº {numero_sorteado} comprador='{comprador}'")
        return True, numero_sorteado, comprador, "Sorteio realizado com sucesso."
    except Exception as e:
        logger.exception(f"DB: escolher_vencedor erro: {e}")
        return False, None, None, f"Erro de banco de dados: {e}"


def listar_compradores(nome_rifa: str) -> List[str]:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT comprador FROM vendas v
            JOIN rifas r ON v.rifa_id = r.id
            WHERE r.nome = ? ORDER BY comprador ASC
            """,
            (nome_rifa,),
        )
        return [row["comprador"] for row in cur.fetchall()]
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
        return list(eventos.values())
    finally:
        conn.close()
