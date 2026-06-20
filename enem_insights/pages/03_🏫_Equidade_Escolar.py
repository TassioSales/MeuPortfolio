"""Page 3 — School equity analysis."""
import streamlit as st
import plotly.graph_objects as go

from app.analytics import (
    school_type_summary,
    gender_summary,
    race_summary,
    inequality_index,
    regional_summary,
)
from app.charts import bar_school_gap, radar_subjects, bar_race, heatmap_correlation
from app.analytics import subject_correlations
from app.data_loader import SUBJECT_NAMES, load_data

st.set_page_config(page_title="Equidade — ENEM Insights", page_icon="🏫", layout="wide")

df_full = load_data()

with st.sidebar:
    st.header("🔧 Filtros")
    years = sorted(df_full["NU_ANO"].unique())
    sel_years = st.multiselect("Ano(s)", years, default=years)
    regions = sorted(df_full["regiao"].unique())
    sel_regions = st.multiselect("Região(ões)", regions, default=regions)

df = df_full[df_full["NU_ANO"].isin(sel_years) & df_full["regiao"].isin(sel_regions)]
if df.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()

st.title("🏫 Equidade Escolar & Desigualdade")

# ── Inequality index banner ───────────────────────────────────────────────────
ineq = inequality_index(df)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Índice de Desigualdade", f"{ineq['index']:.1f} / 100",
          help="Composto por gap escola, renda e raça")
c2.metric("Gap Pública vs Privada", f"+{ineq['school_gap']:.1f} pts")
c3.metric("Gap Renda (menor→maior)", f"+{ineq['income_gap']:.1f} pts")
c4.metric("Gap Racial (maior−menor)", f"{ineq['race_gap']:.1f} pts")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🏫 Escola Pública vs Privada", "⚧ Gênero", "🎨 Raça / Etnia"])

with tab1:
    school_df = school_type_summary(df)
    st.plotly_chart(bar_school_gap(school_df), use_container_width=True)

    pub = df[df["escola_label"] == "Pública"]["media_geral"].mean()
    pri = df[df["escola_label"] == "Privada"]["media_geral"].mean()
    st.info(
        f"Escola privada supera a pública em **{pri - pub:.1f} pontos** em média geral. "
        "Essa diferença é mais pronunciada em Matemática e Redação."
    )

    # radar by school type
    radar_df = (
        df[df["escola_label"].isin(["Pública", "Privada"])]
        .groupby("escola_label")[list(SUBJECT_NAMES.keys())]
        .mean()
        .round(1)
        .reset_index()
    )
    st.plotly_chart(radar_subjects(radar_df, "escola_label"), use_container_width=True)

with tab2:
    gender_df = gender_summary(df)
    st.plotly_chart(radar_subjects(gender_df, "genero_label"), use_container_width=True)
    st.dataframe(gender_df.rename(columns={"genero_label": "Gênero"}),
                 use_container_width=True, hide_index=True)
    m = gender_df.set_index("genero_label")
    if "Masculino" in m.index and "Feminino" in m.index:
        mt_gap = m.loc["Masculino", "NU_NOTA_MT"] - m.loc["Feminino", "NU_NOTA_MT"]
        red_gap = m.loc["Feminino", "NU_NOTA_REDACAO"] - m.loc["Masculino", "NU_NOTA_REDACAO"]
        st.info(
            f"Homens superam mulheres em Matemática por **{mt_gap:.1f} pts**. "
            f"Mulheres lideram em Redação por **{red_gap:.1f} pts**."
        )

with tab3:
    race_df = race_summary(df)
    st.plotly_chart(bar_race(race_df), use_container_width=True)
    st.dataframe(race_df.rename(columns={"raca_label": "Raça / Etnia", "media_geral": "Média Geral"}),
                 use_container_width=True, hide_index=True)

st.markdown("---")
st.subheader("Correlação entre Disciplinas")
st.plotly_chart(heatmap_correlation(subject_correlations(df)), use_container_width=True)
