import os
import io
import json
import tempfile
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from mistralai import Mistral
from fpdf import FPDF

st.set_page_config(
    page_title="DataNarrator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")

PALETTE = ["#00d4aa", "#ff7000", "#2496ed", "#ff4b4b", "#a855f7", "#facc15"]

# ── helpers ──────────────────────────────────────────────────────────────────

def load_data(file) -> pd.DataFrame:
    name = file.name.lower()
    if name.endswith(".csv"):
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                return pd.read_csv(file, encoding=enc)
            except UnicodeDecodeError:
                file.seek(0)
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    raise ValueError("Formato não suportado. Use CSV ou Excel.")


def basic_profile(df: pd.DataFrame) -> dict:
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    date_cols = df.select_dtypes(include=["datetime"]).columns.tolist()

    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)

    desc = df[num_cols].describe().round(4).to_dict() if num_cols else {}

    return {
        "rows": len(df),
        "cols": len(df.columns),
        "num_cols": num_cols,
        "cat_cols": cat_cols,
        "date_cols": date_cols,
        "missing": {col: int(v) for col, v in missing[missing > 0].items()},
        "missing_pct": {col: float(v) for col, v in missing_pct[missing_pct > 0].items()},
        "duplicates": int(df.duplicated().sum()),
        "describe": desc,
        "dtypes": {col: str(dt) for col, dt in df.dtypes.items()},
        "sample": df.head(5).to_dict(orient="records"),
    }


def ask_mistral(prompt: str, api_key: str) -> str:
    client = Mistral(api_key=api_key)
    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um analista de dados sênior especialista em BI e storytelling com dados. "
                    "Responda sempre em português brasileiro. "
                    "Seja direto, técnico e específico. "
                    "Formate a resposta em Markdown com seções claras."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


def build_prompt(profile: dict, col_names: list) -> str:
    return f"""
Analise este dataset e gere um relatório narrativo completo.

**Metadados:**
- Linhas: {profile['rows']} | Colunas: {profile['cols']}
- Colunas numéricas: {profile['num_cols']}
- Colunas categóricas: {profile['cat_cols']}
- Colunas de data: {profile['date_cols']}
- Valores ausentes: {json.dumps(profile['missing_pct'], ensure_ascii=False)}
- Duplicatas: {profile['duplicates']}
- Estatísticas descritivas: {json.dumps(profile['describe'], ensure_ascii=False)}
- Amostra (5 linhas): {json.dumps(profile['sample'], ensure_ascii=False, default=str)}

**Instruções:**
1. **Resumo Executivo** — o que este dataset parece representar? Qual o domínio provável?
2. **Qualidade dos Dados** — avalie ausentes, duplicatas e tipos. O que precisa de atenção?
3. **Principais Padrões e Insights** — o que se destaca nas distribuições e estatísticas? Identifique anomalias ou outliers prováveis.
4. **Correlações Esperadas** — quais colunas provavelmente se relacionam? Por quê?
5. **Recomendações de Análise** — que perguntas de negócio este dataset pode responder? Sugira 3 análises concretas.
6. **Próximos Passos** — limpeza, feature engineering, modelagem se aplicável.

Seja específico, use os nomes reais das colunas e valores do dataset.
""".strip()


def generate_pdf(narrative: str, profile: dict, filename: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(0, 212, 170)
    pdf.cell(0, 12, "DataNarrator — Relatório de Análise", ln=True, align="C")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, f"Arquivo: {filename}  |  Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(4)

    pdf.set_draw_color(0, 212, 170)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Sumário do Dataset", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Linhas: {profile['rows']}   Colunas: {profile['cols']}   Duplicatas: {profile['duplicates']}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Narrativa Gerada por IA", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)

    clean = narrative.replace("**", "").replace("##", "").replace("###", "").replace("#", "")
    for line in clean.split("\n"):
        line = line.strip()
        if not line:
            pdf.ln(3)
            continue
        pdf.multi_cell(0, 6, line)

    return bytes(pdf.output())


# ── UI ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .metric-card {
        background: #1a1a2e;
        border: 1px solid #00d4aa33;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #00d4aa; }
    .metric-label { font-size: 0.85rem; color: #888; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚙️ Configuração")
    api_key = st.text_input(
        "Mistral API Key",
        value=MISTRAL_API_KEY,
        type="password",
        placeholder="sk-...",
        help="Obtenha em console.mistral.ai",
    )
    st.divider()
    st.markdown("### 📂 Upload")
    uploaded = st.file_uploader(
        "CSV ou Excel",
        type=["csv", "xlsx", "xls"],
        help="Até 200 MB",
    )
    st.divider()
    st.markdown("### 🎛️ Opções")
    max_cat_unique = st.slider("Máx. categorias em gráficos", 5, 30, 15)
    generate_ai = st.checkbox("Gerar narrativa com IA", value=True)

st.title("📊 DataNarrator")
st.caption("Transforme qualquer CSV em uma análise completa com insights de IA.")

if not uploaded:
    st.info("⬅️ Faça o upload de um arquivo CSV ou Excel na barra lateral para começar.")
    st.stop()

with st.spinner("Carregando dados..."):
    try:
        df = load_data(uploaded)
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        st.stop()

profile = basic_profile(df)
num_cols = profile["num_cols"]
cat_cols = profile["cat_cols"]

# ── métricas topo ─────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-value">{profile["rows"]:,}</div><div class="metric-label">Linhas</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-value">{profile["cols"]}</div><div class="metric-label">Colunas</div></div>', unsafe_allow_html=True)
with c3:
    missing_count = sum(profile["missing"].values())
    st.markdown(f'<div class="metric-card"><div class="metric-value">{missing_count:,}</div><div class="metric-label">Valores Ausentes</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-value">{profile["duplicates"]:,}</div><div class="metric-label">Duplicatas</div></div>', unsafe_allow_html=True)

st.divider()

# ── tabs ──────────────────────────────────────────────────────────────────
tab_data, tab_eda, tab_ai, tab_export = st.tabs(["📋 Dados", "📈 EDA", "🧠 Narrativa IA", "📄 Exportar"])

# ── TAB: Dados ─────────────────────────────────────────────────────────────
with tab_data:
    st.subheader("Prévia dos dados")
    st.dataframe(df.head(100), use_container_width=True, height=400)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Tipos de dados")
        dtype_df = pd.DataFrame({"Coluna": df.columns, "Tipo": [str(dt) for dt in df.dtypes]})
        st.dataframe(dtype_df, use_container_width=True)
    with col_b:
        if profile["missing"]:
            st.subheader("Valores ausentes")
            miss_df = pd.DataFrame({
                "Coluna": list(profile["missing"].keys()),
                "Ausentes": list(profile["missing"].values()),
                "% do Total": [profile["missing_pct"][c] for c in profile["missing"]],
            })
            st.dataframe(miss_df, use_container_width=True)
        else:
            st.success("Nenhum valor ausente encontrado.")

    if num_cols:
        st.subheader("Estatísticas descritivas")
        st.dataframe(df[num_cols].describe().round(4), use_container_width=True)

# ── TAB: EDA ──────────────────────────────────────────────────────────────
with tab_eda:
    if num_cols:
        st.subheader("Distribuições — Numéricas")
        cols_per_row = 2
        for i in range(0, len(num_cols), cols_per_row):
            row_cols = st.columns(cols_per_row)
            for j, col in enumerate(num_cols[i : i + cols_per_row]):
                with row_cols[j]:
                    fig = px.histogram(
                        df, x=col, nbins=40,
                        title=col,
                        color_discrete_sequence=[PALETTE[j % len(PALETTE)]],
                        template="plotly_dark",
                    )
                    fig.update_layout(showlegend=False, margin=dict(t=36, b=0, l=0, r=0), height=280)
                    st.plotly_chart(fig, use_container_width=True)

    if cat_cols:
        st.subheader("Distribuições — Categóricas")
        for i in range(0, len(cat_cols), 2):
            row_cols = st.columns(2)
            for j, col in enumerate(cat_cols[i : i + 2]):
                with row_cols[j]:
                    vc = df[col].value_counts().head(max_cat_unique)
                    fig = px.bar(
                        x=vc.values, y=vc.index, orientation="h",
                        title=col,
                        labels={"x": "Contagem", "y": col},
                        color_discrete_sequence=[PALETTE[(i + j) % len(PALETTE)]],
                        template="plotly_dark",
                    )
                    fig.update_layout(showlegend=False, margin=dict(t=36, b=0, l=0, r=0), height=max(280, len(vc) * 22))
                    st.plotly_chart(fig, use_container_width=True)

    if len(num_cols) >= 2:
        st.subheader("Matriz de Correlação")
        corr = df[num_cols].corr()
        fig = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            zmin=-1, zmax=1,
            template="plotly_dark",
            aspect="auto",
        )
        fig.update_layout(margin=dict(t=20, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    if len(num_cols) >= 2:
        st.subheader("Scatter Explorer")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            x_col = st.selectbox("Eixo X", num_cols, key="sx")
        with sc2:
            y_col = st.selectbox("Eixo Y", num_cols, index=min(1, len(num_cols) - 1), key="sy")
        with sc3:
            color_col = st.selectbox("Cor (opcional)", ["Nenhuma"] + cat_cols + num_cols, key="sc")
        color_arg = None if color_col == "Nenhuma" else color_col
        fig = px.scatter(
            df, x=x_col, y=y_col, color=color_arg,
            template="plotly_dark",
            color_discrete_sequence=PALETTE,
            opacity=0.7,
        )
        fig.update_layout(margin=dict(t=20, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    if not num_cols and not cat_cols:
        st.warning("Nenhuma coluna numérica ou categórica detectada.")

# ── TAB: Narrativa IA ─────────────────────────────────────────────────────
with tab_ai:
    if not generate_ai:
        st.info("Ative 'Gerar narrativa com IA' na barra lateral.")
    elif not api_key:
        st.warning("Informe sua Mistral API Key na barra lateral.")
    else:
        if "narrative" not in st.session_state or st.button("🔄 Regenerar análise"):
            with st.spinner("Consultando IA... isso pode levar alguns segundos."):
                try:
                    prompt = build_prompt(profile, df.columns.tolist())
                    st.session_state["narrative"] = ask_mistral(prompt, api_key)
                except Exception as e:
                    st.error(f"Erro na API Mistral: {e}")
                    st.stop()

        st.markdown(st.session_state["narrative"])

# ── TAB: Exportar ─────────────────────────────────────────────────────────
with tab_export:
    st.subheader("Exportar Resultados")

    col_e1, col_e2 = st.columns(2)

    with col_e1:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Baixar CSV limpo",
            data=csv_bytes,
            file_name=f"datnarrator_{uploaded.name}",
            mime="text/csv",
            use_container_width=True,
        )

        stats_df = df[num_cols].describe().round(4) if num_cols else pd.DataFrame()
        if not stats_df.empty:
            stats_bytes = stats_df.to_csv().encode("utf-8")
            st.download_button(
                "⬇️ Baixar estatísticas (CSV)",
                data=stats_bytes,
                file_name="estatisticas_descritivas.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with col_e2:
        narrative_text = st.session_state.get("narrative", "")
        if narrative_text:
            pdf_bytes = generate_pdf(narrative_text, profile, uploaded.name)
            st.download_button(
                "⬇️ Baixar Relatório PDF",
                data=pdf_bytes,
                file_name=f"relatorio_{uploaded.name.split('.')[0]}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.info("Gere a narrativa IA primeiro para exportar o PDF.")

        profile_json = json.dumps(profile, ensure_ascii=False, indent=2, default=str)
        st.download_button(
            "⬇️ Baixar perfil JSON",
            data=profile_json.encode("utf-8"),
            file_name="perfil_dataset.json",
            mime="application/json",
            use_container_width=True,
        )
