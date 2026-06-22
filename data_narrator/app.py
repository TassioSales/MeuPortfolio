import os
import io
import csv as _csv_mod
import json
import unicodedata
import hashlib
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from loguru import logger
from mistralai import Mistral
from fpdf import FPDF

# ── logging ──────────────────────────────────────────────────────────────────

os.makedirs("logs", exist_ok=True)
logger.add(
    "logs/datnarrator.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)

# ── page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="DataNarrator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── constants ─────────────────────────────────────────────────────────────────

MISTRAL_MODELS = ["mistral-small-latest", "mistral-large-latest"]
MISTRAL_DEFAULT = "mistral-small-latest"

PALETTE = ["#00d4aa", "#ff7000", "#2496ed", "#ff4b4b", "#a855f7", "#facc15"]
MAX_EDA_COLS = 20
MAX_SCATTER_ROWS = 10_000
MAX_ROWS_WARN = 500_000
TIMEOUT_MS = 180_000
MAX_DESCRIBE_COLS = 12
MAX_SAMPLE_CHARS = 2_000

_SYSTEM_PROMPT = (
    "Você é um analista de dados sênior especialista em BI e storytelling com dados. "
    "Responda sempre em português brasileiro. "
    "Seja direto, técnico e específico. "
    "Formate a resposta em Markdown com seções claras."
)

_CHAT_SYSTEM_PROMPT = (
    "Você é um analista de dados sênior respondendo perguntas de follow-up sobre um dataset "
    "já analisado. Responda em português brasileiro de forma direta e técnica. "
    "Use os dados do contexto fornecido para fundamentar suas respostas."
)

# ── misc helpers ─────────────────────────────────────────────────────────────

def _get_secret(key: str, env_var: str = "") -> str:
    """Lê de .streamlit/secrets.toml primeiro, cai em variável de ambiente."""
    try:
        val = st.secrets.get(key)
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(env_var or key, "")


def _sniff_sep(file_bytes: bytes) -> str:
    """Detecta separador de CSV via Sniffer (vírgula como fallback)."""
    try:
        sample = file_bytes[:8192].decode("utf-8", errors="replace")
        dialect = _csv_mod.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except Exception:
        return ","


def _file_hash(file_bytes: bytes) -> str:
    return hashlib.md5(file_bytes).hexdigest()[:12]

# ── data helpers ─────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_data(file_bytes: bytes, filename: str) -> pd.DataFrame:
    logger.info(f"Carregando: {filename} ({len(file_bytes):,} bytes)")
    name = filename.lower()
    if name.endswith(".csv"):
        sep = _sniff_sep(file_bytes)
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc, sep=sep)
                # se sniffer errou e gerou só 1 coluna, tenta vírgula
                if len(df.columns) == 1 and sep != ",":
                    df2 = pd.read_csv(io.BytesIO(file_bytes), encoding=enc, sep=",")
                    if len(df2.columns) > 1:
                        df = df2
                        sep = ","
                logger.info(f"CSV ok encoding={enc} sep={sep!r} shape={df.shape}")
                return df
            except UnicodeDecodeError:
                continue
        raise ValueError("Não foi possível decodificar o CSV. Salve como UTF-8.")
    elif name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_bytes))
        logger.info(f"Excel ok shape={df.shape}")
        return df
    raise ValueError(f"Formato não suportado: '{filename}'. Use CSV ou Excel.")


def _detect_string_dates(df: pd.DataFrame, cat_cols: list[str]) -> list[str]:
    """Detecta colunas objeto que provavelmente contêm datas por heurística."""
    date_like = []
    sample_size = min(50, len(df))
    for col in cat_cols:
        sample = df[col].dropna().head(sample_size).astype(str)
        try:
            parsed = pd.to_datetime(sample, errors="coerce")
            if parsed.notna().mean() > 0.7:
                date_like.append(col)
        except Exception:
            pass
    return date_like


@st.cache_data(show_spinner=False)
def basic_profile(df: pd.DataFrame) -> dict:
    logger.info(f"Gerando perfil shape={df.shape}")
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    date_cols = df.select_dtypes(include=["datetime"]).columns.tolist()
    string_dates = _detect_string_dates(df, cat_cols)

    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    duplicates = int(df.duplicated().sum())

    desc = df[num_cols].describe().round(4).to_dict() if num_cols else {}
    skewness = {}
    if num_cols:
        skew = df[num_cols].skew().round(3)
        skewness = {col: float(v) for col, v in skew.items() if pd.notna(v)}

    outlier_counts: dict[str, int] = {}
    for col in num_cols:
        s = df[col].dropna()
        if len(s) < 4:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        n = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
        if n:
            outlier_counts[col] = n

    total_cells = len(df) * len(df.columns) or 1
    missing_rate = missing.sum() / total_cells * 100
    dup_rate = duplicates / len(df) * 100
    outlier_rate = sum(outlier_counts.values()) / max(len(df) * len(num_cols), 1) * 100
    quality_score = round(max(0, 100 - missing_rate * 0.6 - dup_rate * 0.3 - outlier_rate * 0.1), 1)
    memory_mb = round(df.memory_usage(deep=True).sum() / 1_048_576, 2)

    logger.info(f"Perfil: {len(num_cols)} num | {len(cat_cols)} cat | {duplicates} dup | Q={quality_score}")
    return {
        "rows": len(df),
        "cols": len(df.columns),
        "num_cols": num_cols,
        "cat_cols": cat_cols,
        "date_cols": date_cols,
        "string_dates": string_dates,
        "missing": {col: int(v) for col, v in missing[missing > 0].items()},
        "missing_pct": {col: float(v) for col, v in missing_pct[missing_pct > 0].items()},
        "duplicates": duplicates,
        "outlier_counts": outlier_counts,
        "skewness": skewness,
        "describe": desc,
        "dtypes": {col: str(dt) for col, dt in df.dtypes.items()},
        "sample": df.head(5).to_dict(orient="records"),
        "quality_score": quality_score,
        "memory_mb": memory_mb,
    }


def _filter_profile_for_cols(profile: dict, cols: list[str]) -> dict:
    """Filtra o perfil para incluir apenas as colunas selecionadas pelo usuário."""
    col_set = set(cols)
    p = dict(profile)
    p["num_cols"] = [c for c in profile["num_cols"] if c in col_set]
    p["cat_cols"] = [c for c in profile["cat_cols"] if c in col_set]
    p["date_cols"] = [c for c in profile["date_cols"] if c in col_set]
    p["string_dates"] = [c for c in profile.get("string_dates", []) if c in col_set]
    p["missing"] = {c: v for c, v in profile["missing"].items() if c in col_set}
    p["missing_pct"] = {c: v for c, v in profile["missing_pct"].items() if c in col_set}
    p["outlier_counts"] = {c: v for c, v in profile["outlier_counts"].items() if c in col_set}
    p["skewness"] = {c: v for c, v in profile.get("skewness", {}).items() if c in col_set}
    p["describe"] = {c: v for c, v in profile.get("describe", {}).items() if c in col_set}
    p["cols"] = len(cols)
    p["sample"] = [{k: row.get(k) for k in cols if k in row} for row in profile["sample"]]
    return p


@st.cache_data(show_spinner=False)
def build_prompt(profile_json: str) -> str:
    profile = json.loads(profile_json)
    describe = profile["describe"]
    if len(describe) > MAX_DESCRIBE_COLS:
        keys = list(describe.keys())[:MAX_DESCRIBE_COLS]
        describe = {k: describe[k] for k in keys}
        describe["_truncated"] = f"(+{profile['cols'] - MAX_DESCRIBE_COLS} colunas omitidas)"

    sample_str = json.dumps(profile["sample"], ensure_ascii=False, default=str)
    if len(sample_str) > MAX_SAMPLE_CHARS:
        sample_str = sample_str[:MAX_SAMPLE_CHARS] + "... [truncado]"

    skew_info = {k: v for k, v in profile.get("skewness", {}).items() if abs(v) > 1}

    prompt = f"""Analise este dataset e gere um relatório narrativo completo.

**Metadados:**
- Linhas: {profile['rows']:,} | Colunas: {profile['cols']} | Memória: {profile['memory_mb']} MB
- Score de qualidade: {profile['quality_score']}/100
- Colunas numéricas: {profile['num_cols']}
- Colunas categóricas: {profile['cat_cols']}
- Colunas de data: {profile['date_cols']}
- Colunas com padrão de data (string): {profile.get('string_dates', [])}
- Valores ausentes (%): {json.dumps(profile['missing_pct'], ensure_ascii=False)}
- Duplicatas: {profile['duplicates']}
- Outliers (IQR): {json.dumps(profile['outlier_counts'], ensure_ascii=False)}
- Assimetria elevada (|skew|>1): {json.dumps(skew_info, ensure_ascii=False)}
- Estatísticas descritivas: {json.dumps(describe, ensure_ascii=False)}
- Amostra (5 linhas): {sample_str}

**Instruções:**
1. **Resumo Executivo** — o que este dataset representa? Qual o domínio provável?
2. **Qualidade dos Dados** — avalie ausentes, duplicatas, outliers e assimetria.
3. **Principais Padrões e Insights** — o que se destaca nas distribuições e estatísticas?
4. **Correlações Esperadas** — quais colunas provavelmente se relacionam e por quê?
5. **Recomendações de Análise** — 3 perguntas de negócio concretas que este dataset pode responder.
6. **Próximos Passos** — limpeza, feature engineering, modelagem se aplicável.

Use os nomes reais das colunas e valores do dataset.""".strip()

    logger.info(f"Prompt: {len(prompt)} chars")
    return prompt


@st.cache_data(show_spinner=False)
def build_excel(df: pd.DataFrame, profile: dict) -> bytes:
    buf = io.BytesIO()
    num_cols = profile["num_cols"]
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Dados", index=False)
        if num_cols:
            df[num_cols].describe().round(4).to_excel(writer, sheet_name="Estatisticas")
        if profile["missing"]:
            pd.DataFrame({
                "Coluna": list(profile["missing"].keys()),
                "Ausentes": list(profile["missing"].values()),
                "Pct": [profile["missing_pct"][c] for c in profile["missing"]],
            }).to_excel(writer, sheet_name="Ausentes", index=False)
        if profile["outlier_counts"]:
            pd.DataFrame({
                "Coluna": list(profile["outlier_counts"].keys()),
                "Outliers": list(profile["outlier_counts"].values()),
            }).to_excel(writer, sheet_name="Outliers", index=False)
        if profile.get("skewness"):
            pd.DataFrame({
                "Coluna": list(profile["skewness"].keys()),
                "Assimetria": list(profile["skewness"].values()),
            }).to_excel(writer, sheet_name="Assimetria", index=False)
    return buf.getvalue()


@st.cache_data(show_spinner=False)
def top_correlations(df: pd.DataFrame, threshold: float = 0.7) -> list[tuple]:
    """Retorna pares de colunas com |r| >= threshold, ordenados por |r| desc."""
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if len(num_cols) < 2:
        return []
    corr = df[num_cols].corr()
    pairs = []
    for i, c1 in enumerate(num_cols):
        for c2 in num_cols[i + 1:]:
            r = corr.loc[c1, c2]
            if pd.notna(r) and abs(r) >= threshold:
                pairs.append((c1, c2, round(float(r), 3)))
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    return pairs[:20]

# ── AI streaming ─────────────────────────────────────────────────────────────

def _messages(prompt: str) -> list[dict]:
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


def _chat_messages(profile: dict, narrative: str, history: list[dict], question: str) -> list[dict]:
    ctx = json.dumps(
        {k: profile[k] for k in ("rows", "cols", "num_cols", "cat_cols", "quality_score",
                                  "missing_pct", "outlier_counts", "skewness")},
        ensure_ascii=False, default=str
    )
    system = (
        f"{_CHAT_SYSTEM_PROMPT}\n\n"
        f"Contexto do dataset: {ctx}\n\n"
        f"Narrativa gerada:\n{narrative[:1500]}"
    )
    msgs = [{"role": "system", "content": system}]
    for m in history[-8:]:
        msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": question})
    return msgs


def stream_mistral(messages: list[dict], api_key: str, model: str):
    t0 = datetime.now()
    logger.info(f"Mistral stream model={model}")
    client = Mistral(api_key=api_key, timeout_ms=TIMEOUT_MS)
    for event in client.chat.stream(model=model, messages=messages):
        content = event.data.choices[0].delta.content
        if content:
            yield content
    logger.info(f"Mistral ok em {(datetime.now()-t0).total_seconds():.1f}s")


def classify_error(e: Exception) -> tuple[str, str, str]:
    msg = str(e)
    ml = msg.lower()
    if "401" in msg or "unauthorized" in ml or "authentication failed" in ml:
        return "auth", "Chave de API inválida", (
            "A chave foi recusada pelo Mistral. "
            "Verifique em [console.mistral.ai](https://console.mistral.ai)."
        )
    if "429" in msg or "rate limit" in ml or "too many" in ml:
        return "ratelimit", "Limite de requisições atingido", (
            "Aguarde alguns segundos e tente novamente, ou troque de modelo/provedor."
        )
    if "timeout" in ml or "readtimeout" in ml or "timed out" in ml:
        return "timeout", "Tempo limite excedido", (
            f"O modelo não respondeu em {TIMEOUT_MS//1000}s. "
            "Tente `mistral-nemo-12b-instruct` ou `nemotron-mini-4b-instruct` (mais rápidos)."
        )
    if "connection" in ml or "network" in ml:
        return "network", "Erro de conexão", "Verifique sua internet e tente novamente."
    return "unknown", "Erro inesperado", msg


def validate_key(provider: str, key: str) -> tuple[bool, str]:
    if not key or not key.strip():
        return False, "Chave não informada"
    return True, "ok"

# ── PDF ───────────────────────────────────────────────────────────────────────

def _pdf_safe(text: str) -> str:
    replacements = {
        "—": "-", "–": "-", "'": "'", "'": "'",
        "“": '"', "”": '"', "…": "...",
        "•": "*", "·": "*", "​": "", "‌": "",
        "‍": "", "﻿": "",
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    return "".join(c if c.isprintable() or c in ("\n", "\t") else " " for c in text)


def generate_pdf(narrative: str, profile: dict, filename: str) -> bytes:
    logger.info(f"Gerando PDF: {filename}")
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pw = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(0, 212, 170)
    pdf.cell(pw, 12, "DataNarrator - Relatorio de Analise", ln=True, align="C")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(pw, 6, _pdf_safe(
        f"Arquivo: {filename}  |  Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ), ln=True, align="C")
    pdf.ln(4)
    pdf.set_draw_color(0, 212, 170)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(pw, 8, "Sumario do Dataset", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(pw, 6, _pdf_safe(
        f"Linhas: {profile['rows']:,}  Colunas: {profile['cols']}  "
        f"Duplicatas: {profile['duplicates']}  Qualidade: {profile['quality_score']}/100"
    ), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(pw, 8, "Narrativa Gerada por IA", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)

    clean = narrative.replace("**", "").replace("###", "").replace("##", "").replace("#", "")
    for line in clean.split("\n"):
        line = _pdf_safe(line.strip())
        if not line:
            pdf.ln(3)
            continue
        try:
            pdf.multi_cell(pw, 6, line)
        except Exception as exc:
            logger.warning(f"Linha PDF ignorada ({exc}): {line[:60]!r}")

    result = bytes(pdf.output())
    logger.info(f"PDF ok: {len(result):,} bytes")
    return result

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.metric-card{background:#1a1a2e;border:1px solid #00d4aa33;border-radius:10px;
  padding:16px;text-align:center}
.metric-value{font-size:2rem;font-weight:700;color:#00d4aa}
.metric-label{font-size:.85rem;color:#888;margin-top:4px}
.quality-good{color:#00d4aa}.quality-mid{color:#facc15}.quality-bad{color:#ff4b4b}
.provider-badge{background:#1e3a5f;border:1px solid #2496ed55;border-radius:6px;
  padding:4px 10px;font-size:.8rem;color:#2496ed;display:inline-block;margin-bottom:8px}
.file-info{background:#111;border:1px solid #333;border-radius:6px;padding:8px 12px;
  font-size:.8rem;color:#aaa;margin-top:6px}
.corr-high{color:#ff4b4b;font-weight:700}
.corr-mod{color:#facc15}
.corr-pos{color:#00d4aa}
</style>
""", unsafe_allow_html=True)

# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Configuração")

    mistral_key = st.text_input(
        "Mistral API Key",
        value=_get_secret("MISTRAL_API_KEY"),
        type="password",
        placeholder="sk-...",
        help="console.mistral.ai  |  Também lido de .streamlit/secrets.toml",
    )
    _ms_ok, _ms_msg = validate_key("mistral", mistral_key)
    if mistral_key:
        st.caption("✅ Chave informada" if _ms_ok else f"⚠️ {_ms_msg}")
    mistral_model = st.selectbox("Modelo", MISTRAL_MODELS, index=0)

    st.divider()
    st.markdown("### 📂 Upload")
    uploaded = st.file_uploader("CSV ou Excel", type=["csv", "xlsx", "xls"], help="Até 200 MB")
    st.divider()
    st.markdown("### 🎛️ Opções")
    max_cat_unique = st.slider("Máx. categorias em gráficos", 5, 30, 15)
    generate_ai = st.checkbox("Gerar narrativa com IA", value=True)

# ── welcome ───────────────────────────────────────────────────────────────────

st.title("📊 DataNarrator")
st.caption("Transforme qualquer CSV em uma análise completa com insights de IA.")

if not uploaded:
    col1, col2 = st.columns(2)
    with col1:
        st.info("⬅️ Faça o upload de um arquivo CSV ou Excel na barra lateral.")
        st.markdown("**O que o DataNarrator faz:**")
        st.markdown("- Perfil automático: tipos, ausentes, outliers, correlações")
        st.markdown("- EDA interativo com histogramas, barras, scatter, séries temporais")
        st.markdown("- Narrativa em linguagem natural gerada por IA (Mistral)")
        st.markdown("- Exporta PDF, Markdown, Excel e JSON")
        st.markdown("- Modo chat para perguntas de follow-up sobre o dataset")
    with col2:
        st.markdown("**Configuração rápida:**")
        st.markdown("1. Obtenha sua chave em [console.mistral.ai](https://console.mistral.ai)")
        st.markdown("2. Cole na sidebar → campo **Mistral API Key**")
        st.markdown("3. Faça upload do seu CSV ou Excel")
        st.markdown("")
        st.markdown("**Dica:** salve a chave em `.streamlit/secrets.toml` para não redigitar.")
        st.code('MISTRAL_API_KEY = "sk-..."', language="toml")
    st.stop()

# ── load ─────────────────────────────────────────────────────────────────────

with st.spinner("Carregando dados..."):
    try:
        file_bytes = uploaded.read()
        df = load_data(file_bytes, uploaded.name)
    except ValueError as e:
        logger.warning(f"Arquivo rejeitado: {e}")
        st.error(f"Arquivo inválido: {e}")
        st.stop()
    except Exception as e:
        logger.error(f"Erro ao carregar: {e}")
        st.error(f"Erro ao carregar arquivo: {e}")
        st.stop()

with st.spinner("Analisando estrutura..."):
    try:
        profile = basic_profile(df)
    except Exception as e:
        logger.error(f"Erro no perfil: {e}")
        st.error(f"Erro ao analisar o dataset: {e}")
        st.stop()

# ── hash check: limpa estado ao trocar de arquivo ────────────────────────────

current_hash = _file_hash(file_bytes)
if st.session_state.get("_file_hash") != current_hash:
    for key in ("narrative", "pdf_bytes", "used_provider", "used_model", "chat_history"):
        st.session_state.pop(key, None)
    st.session_state["_file_hash"] = current_hash
    logger.info(f"Novo arquivo detectado (hash={current_hash}), estado limpo.")

if profile["rows"] > MAX_ROWS_WARN:
    st.warning(
        f"Dataset grande: {profile['rows']:,} linhas. "
        "EDA e perfil podem ser lentos. Considere filtrar antes do upload."
    )

with st.sidebar:
    st.markdown(
        f'<div class="file-info">📄 <b>{uploaded.name}</b><br>'
        f'{profile["rows"]:,} linhas · {profile["cols"]} colunas · {profile["memory_mb"]} MB</div>',
        unsafe_allow_html=True,
    )

num_cols = profile["num_cols"]
cat_cols = profile["cat_cols"]

# ── metrics ───────────────────────────────────────────────────────────────────

qs = profile["quality_score"]
q_class = "quality-good" if qs >= 80 else ("quality-mid" if qs >= 50 else "quality-bad")
missing_count = sum(profile["missing"].values())
outlier_count = sum(profile["outlier_counts"].values())

cols_m = st.columns(5)
labels_vals = [
    (f"{profile['rows']:,}", "Linhas"),
    (str(profile["cols"]), "Colunas"),
    (f"{missing_count:,}", "Ausentes"),
    (f"{outlier_count:,}", "Outliers"),
    (str(qs), "Score Qualidade"),
]
for col_obj, (value, label) in zip(cols_m, labels_vals):
    val_cls = f"metric-value {q_class}" if label == "Score Qualidade" else "metric-value"
    with col_obj:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="{val_cls}">{value}</div>'
            f'<div class="metric-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

st.divider()

# ── tabs ──────────────────────────────────────────────────────────────────────

tab_data, tab_eda, tab_ai, tab_export = st.tabs(["📋 Dados", "📈 EDA", "🧠 Narrativa IA", "📄 Exportar"])

# ── TAB: Dados ────────────────────────────────────────────────────────────────

with tab_data:
    st.subheader("Prévia dos dados")
    st.dataframe(df.head(100), use_container_width=True, height=400)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Tipos de dados")
        dtype_rows = []
        for col in df.columns:
            sd = "📅 data detectada" if col in profile.get("string_dates", []) else ""
            dtype_rows.append({"Coluna": col, "Tipo": str(df[col].dtype), "Obs": sd})
        st.dataframe(pd.DataFrame(dtype_rows), use_container_width=True)

    with col_b:
        if profile["missing"]:
            st.subheader("Valores ausentes")
            st.dataframe(pd.DataFrame({
                "Coluna": list(profile["missing"].keys()),
                "Ausentes": list(profile["missing"].values()),
                "% do Total": [profile["missing_pct"][c] for c in profile["missing"]],
            }), use_container_width=True)
        else:
            st.success("Nenhum valor ausente encontrado.")

    # Heatmap de missingness
    if profile["missing"]:
        miss_cols = list(profile["missing"].keys())
        sample_n = min(300, len(df))
        miss_mask = df[miss_cols].head(sample_n).isnull().astype(int)
        try:
            fig_miss = px.imshow(
                miss_mask.T,
                color_continuous_scale=["#1e3a5f", "#ff4b4b"],
                labels={"x": "Linha", "y": "Coluna", "color": "Ausente"},
                title=f"Padrão de missingness (amostra {sample_n} linhas)",
                template="plotly_dark",
                aspect="auto",
            )
            fig_miss.update_layout(
                margin=dict(t=40, b=0, l=0, r=0),
                height=max(120, len(miss_cols) * 28),
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_miss, use_container_width=True)
        except Exception as e:
            logger.warning(f"Heatmap missing: {e}")

    if profile["outlier_counts"]:
        st.subheader("Outliers detectados (IQR)")
        st.dataframe(pd.DataFrame({
            "Coluna": list(profile["outlier_counts"].keys()),
            "Outliers": list(profile["outlier_counts"].values()),
        }), use_container_width=True)

    if num_cols:
        st.subheader("Estatísticas descritivas")
        desc_df = df[num_cols].describe().round(4)
        if profile.get("skewness"):
            skew_series = pd.Series(profile["skewness"], name="skewness").round(3)
            desc_df = pd.concat([desc_df, skew_series.to_frame().T])
        st.dataframe(desc_df, use_container_width=True)

# ── TAB: EDA ─────────────────────────────────────────────────────────────────

with tab_eda:
    # Série temporal
    all_date_cols = profile["date_cols"] + profile.get("string_dates", [])
    if all_date_cols:
        st.subheader("Série Temporal")
        ts1, ts2, ts3 = st.columns(3)
        ts_col = ts1.selectbox("Coluna de data", all_date_cols, key="ts_col")
        ts_val = ts2.selectbox("Métrica", ["Contagem"] + num_cols, key="ts_val")
        ts_freq = ts3.selectbox("Granularidade", ["Dia", "Mês", "Ano"], key="ts_freq", index=1)
        freq_map = {"Dia": "D", "Mês": "ME", "Ano": "YE"}
        try:
            ts_df = df.copy()
            ts_df["_dt"] = pd.to_datetime(ts_df[ts_col], errors="coerce")
            ts_df = ts_df.dropna(subset=["_dt"]).set_index("_dt").sort_index()
            if ts_val == "Contagem":
                agg = ts_df.resample(freq_map[ts_freq]).size().reset_index(name="Contagem")
                y_col = "Contagem"
            else:
                agg = ts_df[[ts_val]].resample(freq_map[ts_freq]).mean().reset_index()
                y_col = ts_val
            agg.columns = [ts_col, y_col]
            fig_ts = px.line(
                agg, x=ts_col, y=y_col,
                template="plotly_dark",
                color_discrete_sequence=[PALETTE[0]],
                title=f"{y_col} por {ts_freq.lower()}",
            )
            fig_ts.update_layout(margin=dict(t=36, b=0, l=0, r=0))
            st.plotly_chart(fig_ts, use_container_width=True)
        except Exception as e:
            logger.warning(f"Série temporal: {e}")
            st.warning("Não foi possível gerar a série temporal.")

    if num_cols:
        st.subheader("Distribuições — Numéricas")
        display_num = num_cols[:MAX_EDA_COLS]
        if len(num_cols) > MAX_EDA_COLS:
            st.caption(f"⚠️ Mostrando {MAX_EDA_COLS}/{len(num_cols)} colunas numéricas.")
        for i in range(0, len(display_num), 2):
            row_cols = st.columns(2)
            for j, col in enumerate(display_num[i : i + 2]):
                with row_cols[j]:
                    try:
                        fig = px.histogram(
                            df, x=col, nbins=40, title=col,
                            color_discrete_sequence=[PALETTE[j % len(PALETTE)]],
                            template="plotly_dark",
                        )
                        fig.update_layout(showlegend=False, margin=dict(t=36, b=0, l=0, r=0), height=280)
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        logger.warning(f"Histograma '{col}': {e}")
                        st.warning(f"Gráfico indisponível para '{col}'.")

    if cat_cols:
        st.subheader("Distribuições — Categóricas")
        display_cat = cat_cols[:MAX_EDA_COLS]
        if len(cat_cols) > MAX_EDA_COLS:
            st.caption(f"⚠️ Mostrando {MAX_EDA_COLS}/{len(cat_cols)} colunas categóricas.")
        for i in range(0, len(display_cat), 2):
            row_cols = st.columns(2)
            for j, col in enumerate(display_cat[i : i + 2]):
                with row_cols[j]:
                    try:
                        vc = df[col].value_counts().head(max_cat_unique)
                        fig = px.bar(
                            x=vc.values, y=vc.index, orientation="h", title=col,
                            labels={"x": "Contagem", "y": col},
                            color_discrete_sequence=[PALETTE[(i + j) % len(PALETTE)]],
                            template="plotly_dark",
                        )
                        fig.update_layout(
                            showlegend=False,
                            margin=dict(t=36, b=0, l=0, r=0),
                            height=max(280, len(vc) * 22),
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        logger.warning(f"Barras '{col}': {e}")
                        st.warning(f"Gráfico indisponível para '{col}'.")

    if len(num_cols) >= 2:
        # Top correlações em tabela
        corr_pairs = top_correlations(df)
        if corr_pairs:
            st.subheader("Correlações Fortes (|r| ≥ 0.7)")
            corr_df = pd.DataFrame(corr_pairs, columns=["Coluna A", "Coluna B", "r"])
            corr_df["Força"] = corr_df["r"].abs().apply(
                lambda v: "Alta (≥0.9)" if v >= 0.9 else ("Média (0.7–0.9)" if v >= 0.7 else "Baixa")
            )
            st.dataframe(corr_df, use_container_width=True, hide_index=True)

        st.subheader("Matriz de Correlação")
        try:
            corr_cols = num_cols[:MAX_EDA_COLS]
            fig = px.imshow(
                df[corr_cols].corr(), text_auto=".2f",
                color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                template="plotly_dark", aspect="auto",
            )
            fig.update_layout(margin=dict(t=20, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            logger.warning(f"Correlação: {e}")
            st.warning("Não foi possível calcular a matriz de correlação.")

        st.subheader("Scatter Explorer")
        sc1, sc2, sc3 = st.columns(3)
        x_col = sc1.selectbox("Eixo X", num_cols, key="sx")
        y_col = sc2.selectbox("Eixo Y", num_cols, index=min(1, len(num_cols) - 1), key="sy")
        color_col = sc3.selectbox("Cor", ["Nenhuma"] + cat_cols + num_cols, key="sc")
        try:
            scatter_df = df
            note = ""
            if len(df) > MAX_SCATTER_ROWS:
                scatter_df = df.sample(MAX_SCATTER_ROWS, random_state=42)
                note = f" (amostra {MAX_SCATTER_ROWS:,}/{len(df):,} linhas)"
            fig = px.scatter(
                scatter_df, x=x_col, y=y_col,
                color=None if color_col == "Nenhuma" else color_col,
                template="plotly_dark",
                color_discrete_sequence=PALETTE,
                opacity=0.6,
                title=f"{x_col} × {y_col}{note}",
            )
            fig.update_layout(margin=dict(t=36, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            logger.warning(f"Scatter: {e}")
            st.warning("Não foi possível gerar o scatter plot.")

    if not num_cols and not cat_cols:
        st.warning("Nenhuma coluna numérica ou categórica detectada.")

# ── TAB: Narrativa IA ────────────────────────────────────────────────────────

with tab_ai:
    if not generate_ai:
        st.info("Ative 'Gerar narrativa com IA' na barra lateral.")
    else:
        _ms_valid = validate_key("mistral", mistral_key)[0]

        if not _ms_valid:
            st.warning("Informe sua Mistral API Key na barra lateral.")
            st.markdown("Obtenha em [console.mistral.ai](https://console.mistral.ai).")
        else:
            # Seletor de colunas para o prompt
            with st.expander("🔧 Colunas para análise IA", expanded=False):
                all_cols = list(df.columns)
                selected_cols = st.multiselect(
                    "Selecione as colunas a incluir no prompt",
                    all_cols,
                    default=all_cols,
                    help="Útil para datasets com muitas colunas — inclua apenas as relevantes.",
                )

            if not selected_cols:
                st.warning("Selecione pelo menos uma coluna para análise.")
                st.stop()

            if "narrative" not in st.session_state or st.button("🔄 Regenerar análise"):
                st.session_state.pop("pdf_bytes", None)
                st.session_state.pop("narrative", None)
                st.session_state.pop("chat_history", None)

                filtered_profile = _filter_profile_for_cols(profile, selected_cols)
                profile_json = json.dumps(filtered_profile, ensure_ascii=False, default=str)
                prompt = build_prompt(profile_json)

                def _run_stream():
                    try:
                        logger.info(f"Mistral stream model={mistral_model}")
                        yield from stream_mistral(_messages(prompt), mistral_key, mistral_model)
                        st.session_state["used_model"] = mistral_model
                    except Exception as e:
                        _, title, guidance = classify_error(e)
                        logger.error(f"Mistral falhou: {title} — {e}")
                        raise RuntimeError(f"__err__{title}|||{guidance}")

                try:
                    full_text = st.write_stream(_run_stream())
                    st.session_state["narrative"] = full_text
                    mdl = st.session_state.get("used_model", mistral_model)
                    st.markdown(f'<span class="provider-badge">💳 Mistral AI · {mdl}</span>',
                                unsafe_allow_html=True)
                    words = len(full_text.split())
                    st.caption(f"Narrativa: {words:,} palavras · {len(full_text):,} caracteres")
                except Exception as e:
                    msg = str(e)
                    if msg.startswith("__err__"):
                        parts = msg[7:].split("|||", 1)
                        title, guidance = parts[0], parts[1] if len(parts) > 1 else msg
                        logger.error(f"Narrativa falhou: {title}")
                        st.error(f"**{title}**\n\n{guidance}")
                    else:
                        logger.error(f"Narrativa falhou: {e}")
                        st.error(f"Erro ao gerar narrativa: {e}")
            else:
                mdl = st.session_state.get("used_model", mistral_model)
                st.markdown(f'<span class="provider-badge">💳 Mistral AI · {mdl}</span>',
                            unsafe_allow_html=True)
                narrative = st.session_state["narrative"]
                st.markdown(narrative)
                words = len(narrative.split())
                st.caption(f"Narrativa: {words:,} palavras · {len(narrative):,} caracteres")

            # ── modo chat ────────────────────────────────────────────────────
            if "narrative" in st.session_state:
                st.divider()
                st.markdown("#### 💬 Perguntas sobre o dataset")

                if "chat_history" not in st.session_state:
                    st.session_state["chat_history"] = []

                for msg in st.session_state["chat_history"]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

                user_q = st.chat_input(
                    "Faça uma pergunta sobre o dataset...",
                    key="chat_input",
                )
                if user_q:
                    st.session_state["chat_history"].append({"role": "user", "content": user_q})
                    with st.chat_message("user"):
                        st.markdown(user_q)

                    chat_msgs = _chat_messages(
                        profile,
                        st.session_state["narrative"],
                        st.session_state["chat_history"][:-1],
                        user_q,
                    )

                    used_mdl = st.session_state.get("used_model", mistral_model)

                    def _chat_stream():
                        if _ms_valid:
                            yield from stream_mistral(chat_msgs, mistral_key, used_mdl)
                        else:
                            yield "Informe a Mistral API Key na sidebar para usar o chat."

                    with st.chat_message("assistant"):
                        try:
                            response = st.write_stream(_chat_stream())
                            st.session_state["chat_history"].append(
                                {"role": "assistant", "content": response}
                            )
                        except Exception as e:
                            err_type, title, guidance = classify_error(e)
                            st.error(f"**{title}:** {guidance}")
                            logger.error(f"Chat falhou [{err_type}]: {e}")

# ── TAB: Exportar ─────────────────────────────────────────────────────────────

with tab_export:
    st.subheader("Exportar Resultados")
    col_e1, col_e2 = st.columns(2)

    with col_e1:
        st.markdown("**Dados**")
        st.download_button(
            "⬇️ CSV limpo",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"datnarrator_{uploaded.name}",
            mime="text/csv",
            use_container_width=True,
        )
        if num_cols:
            st.download_button(
                "⬇️ Estatísticas (CSV)",
                data=df[num_cols].describe().round(4).to_csv().encode("utf-8"),
                file_name="estatisticas_descritivas.csv",
                mime="text/csv",
                use_container_width=True,
            )
        st.download_button(
            "⬇️ Excel completo",
            data=build_excel(df, profile),
            file_name=f"datnarrator_{uploaded.name.split('.')[0]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.download_button(
            "⬇️ Perfil JSON",
            data=json.dumps(profile, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
            file_name="perfil_dataset.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_e2:
        narrative_text = st.session_state.get("narrative", "")
        st.markdown("**Narrativa IA**")
        if narrative_text:
            # Markdown
            md_header = (
                f"# Relatório DataNarrator\n\n"
                f"**Arquivo:** {uploaded.name}  \n"
                f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}  \n"
                f"**Linhas:** {profile['rows']:,} · **Colunas:** {profile['cols']} · "
                f"**Score de qualidade:** {profile['quality_score']}/100\n\n---\n\n"
            )
            st.download_button(
                "⬇️ Narrativa (.md)",
                data=(md_header + narrative_text).encode("utf-8"),
                file_name=f"narrativa_{uploaded.name.split('.')[0]}.md",
                mime="text/markdown",
                use_container_width=True,
            )

            # PDF
            if "pdf_bytes" not in st.session_state:
                if st.button("📄 Gerar PDF", use_container_width=True):
                    with st.spinner("Gerando PDF..."):
                        try:
                            st.session_state["pdf_bytes"] = generate_pdf(
                                narrative_text, profile, uploaded.name
                            )
                        except Exception as e:
                            logger.error(f"PDF falhou: {e}")
                            st.error(f"Erro ao gerar PDF: {e}")
            if "pdf_bytes" in st.session_state:
                st.download_button(
                    "⬇️ Relatório PDF",
                    data=st.session_state["pdf_bytes"],
                    file_name=f"relatorio_{uploaded.name.split('.')[0]}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            # Histórico de chat
            chat_hist = st.session_state.get("chat_history", [])
            if chat_hist:
                chat_md = "# Histórico de Perguntas\n\n"
                for m in chat_hist:
                    prefix = "**Pergunta:**" if m["role"] == "user" else "**Resposta:**"
                    chat_md += f"{prefix}\n\n{m['content']}\n\n---\n\n"
                st.download_button(
                    "⬇️ Histórico chat (.md)",
                    data=chat_md.encode("utf-8"),
                    file_name="chat_historico.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
        else:
            st.info("Gere a narrativa IA primeiro para exportar o PDF e o Markdown.")
