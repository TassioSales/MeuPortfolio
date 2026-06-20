"""Page 2 — Brazil state choropleth map."""
import streamlit as st

from app.analytics import state_summary, yearly_trend, regional_summary
from app.charts import choropleth_brazil, bar_regional, line_yearly_trend
from app.data_loader import SUBJECT_NAMES, load_data

st.set_page_config(page_title="Mapa — ENEM Insights", page_icon="🗺️", layout="wide")

df_full = load_data()

with st.sidebar:
    st.header("🔧 Filtros")
    years = sorted(df_full["NU_ANO"].unique())
    sel_years = st.multiselect("Ano(s)", years, default=years)
    metric = st.selectbox(
        "Métrica do Mapa",
        list(SUBJECT_NAMES.keys()) + ["media_geral"],
        format_func=lambda x: SUBJECT_NAMES.get(x, "Média Geral"),
    )

df = df_full[df_full["NU_ANO"].isin(sel_years)]

st.title("🗺️ Mapa Interativo do Brasil")
st.caption("Desempenho médio por estado. Passe o mouse para ver detalhes.")

# ── Compute state summary ─────────────────────────────────────────────────────
state_df = state_summary(df)
metric_label = SUBJECT_NAMES.get(metric, "Média Geral")

st.plotly_chart(
    choropleth_brazil(state_df, value_col=metric, title=f"{metric_label} por Estado"),
    use_container_width=True,
)

st.markdown("---")

# ── Region bar + detail table ─────────────────────────────────────────────────
col1, col2 = st.columns([1, 1])
with col1:
    reg_df = regional_summary(df)
    st.plotly_chart(bar_regional(reg_df), use_container_width=True)

with col2:
    st.subheader("Ranking por Estado")
    display = state_df[["SG_UF_RESIDENCIA", "regiao", metric, "participantes"]].rename(columns={
        "SG_UF_RESIDENCIA": "Estado",
        "regiao": "Região",
        metric: metric_label,
        "participantes": "Candidatos",
    })
    st.dataframe(display, use_container_width=True, hide_index=True, height=420)

# ── Trend by region ───────────────────────────────────────────────────────────
st.subheader("Evolução Temporal das Médias")
st.plotly_chart(line_yearly_trend(yearly_trend(df)), use_container_width=True)
