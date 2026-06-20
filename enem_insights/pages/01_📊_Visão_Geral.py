"""Page 1 — Overview."""
import streamlit as st

from app.analytics import regional_summary, score_distribution, top_states, yearly_trend
from app.charts import bar_regional, histogram_score, line_yearly_trend
from app.data_loader import SUBJECT_NAMES, load_data
from app.ai_insights import overview_insight
from app.analytics import school_type_summary

st.set_page_config(page_title="Visão Geral — ENEM Insights", page_icon="📊", layout="wide")

st.markdown("""
<style>
    .stMetric { background: #f0f4ff; border-radius: 10px; padding: .75rem 1rem; }
</style>
""", unsafe_allow_html=True)

df_full = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔧 Filtros")
    years = sorted(df_full["NU_ANO"].unique())
    sel_years = st.multiselect("Ano(s)", years, default=years)
    regions = sorted(df_full["regiao"].unique())
    sel_regions = st.multiselect("Região(ões)", regions, default=regions)
    sel_schools = st.multiselect("Tipo de Escola", ["Pública", "Privada"], default=["Pública", "Privada"])

df = df_full[
    df_full["NU_ANO"].isin(sel_years)
    & df_full["regiao"].isin(sel_regions)
    & df_full["escola_label"].isin(sel_schools)
]

if df.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 Visão Geral")

# AI insight banner
school_df = school_type_summary(df_full)
pub_mean = school_df.loc[school_df["escola_label"] == "Pública", "media_geral_mean"].values
prv_mean = school_df.loc[school_df["escola_label"] == "Privada", "media_geral_mean"].values
gap = float(prv_mean[0] - pub_mean[0]) if len(pub_mean) and len(prv_mean) else 0
reg_df = regional_summary(df_full)
top_region = reg_df.iloc[0]["regiao"] if not reg_df.empty else "Sul"

insight = overview_insight(df["media_geral"].mean(), top_region, gap)
st.info(f"💡 **Análise:** {insight}", icon=None)

st.markdown("---")

# ── KPI metrics ───────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Candidatos", f"{len(df):,}")
c2.metric("Média Geral", f"{df['media_geral'].mean():.1f}")
c3.metric("Média Redação", f"{df['NU_NOTA_REDACAO'].mean():.1f}")
c4.metric("Média Matemática", f"{df['NU_NOTA_MT'].mean():.1f}")
c5.metric("% Escola Privada", f"{(df['escola_label'] == 'Privada').mean() * 100:.1f}%")

st.markdown("---")

# ── Charts row 1 ─────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)
with col_a:
    st.plotly_chart(bar_regional(regional_summary(df)), use_container_width=True)

with col_b:
    subject_col = st.selectbox(
        "Disciplina para histograma:",
        list(SUBJECT_NAMES.keys()),
        format_func=lambda x: SUBJECT_NAMES[x],
    )
    centers, counts = score_distribution(df, subject_col)
    st.plotly_chart(histogram_score(centers, counts, SUBJECT_NAMES[subject_col]),
                    use_container_width=True)

# ── Trend ────────────────────────────────────────────────────────────────────
st.plotly_chart(line_yearly_trend(yearly_trend(df)), use_container_width=True)

# ── Top states ────────────────────────────────────────────────────────────────
st.subheader("Top 10 Estados por Média")
st.dataframe(top_states(df), use_container_width=True, hide_index=True)
