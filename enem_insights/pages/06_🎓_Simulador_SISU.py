"""Page 6 — SISU university course simulator."""
import streamlit as st
import plotly.express as px

from app.sisu_data import find_eligible, get_dataframe, unique_courses
from app.charts import sisu_waterfall

st.set_page_config(
    page_title="Simulador SISU — ENEM Insights", page_icon="🎓", layout="wide"
)

st.title("🎓 Simulador SISU")
st.markdown(
    "Informe sua nota média e descubra quais **cursos federais** você pode alcançar. "
    "Baseado nos cortes do SISU 2023 — modalidade ampla concorrência."
)

# ── Score input ───────────────────────────────────────────────────────────────
col_a, col_b = st.columns([1, 2])
with col_a:
    score = st.number_input(
        "Sua nota média ENEM",
        min_value=300.0, max_value=1000.0,
        value=650.0, step=5.0,
        format="%.1f",
    )
    margin = st.slider(
        "Margem de busca (pts acima do corte)",
        min_value=0, max_value=100, value=30, step=5,
        help="Inclui cursos com corte até X pontos acima da sua nota",
    )

    # Filters
    st.markdown("**Filtros opcionais**")
    all_courses = unique_courses()
    course_filter = st.multiselect("Curso(s)", all_courses, placeholder="Todos os cursos")
    all_ufs = sorted(get_dataframe()["uf"].unique())
    uf_filter = st.multiselect("Estado (UF)", all_ufs, placeholder="Todos os estados")

    run = st.button("🔍 Buscar cursos", use_container_width=True, type="primary")

with col_b:
    st.markdown("### Como funciona?")
    st.markdown("""
    1. Informe sua **nota média** (calculada como a média das 5 provas do ENEM)
    2. Ajuste a **margem** para incluir cursos um pouco acima do seu alcance atual
    3. Use os filtros para refinar por curso ou estado
    4. Veja quais cursos em universidades federais você pode pleitear via SISU

    > Os dados são aproximações baseadas nos cortes **SISU 2023 — ampla concorrência**.
    > Cortes variam a cada edição. Consulte sempre o site oficial do MEC.
    """)

    # Quick stats
    eligible_all = find_eligible(score, margin)
    approved = (eligible_all["situacao"] == "✅ Aprovado").sum()
    marginal = (eligible_all["situacao"] == "⚠️ Margem").sum()
    c1, c2 = st.columns(2)
    c1.metric("✅ Dentro da nota", approved)
    c2.metric("⚠️ Na margem", marginal)

st.markdown("---")

if run or True:  # auto-run on page load
    eligible = find_eligible(score, margin)

    if course_filter:
        eligible = eligible[eligible["curso"].isin(course_filter)]
    if uf_filter:
        eligible = eligible[eligible["uf"].isin(uf_filter)]

    if eligible.empty:
        st.warning(
            f"Nenhum curso encontrado para nota {score:.0f} com margem {margin} pts. "
            "Tente aumentar a margem ou selecionar mais estados."
        )
    else:
        # ── Waterfall chart ───────────────────────────────────────────────────
        st.plotly_chart(sisu_waterfall(eligible, score), use_container_width=True)

        # ── Table ─────────────────────────────────────────────────────────────
        st.subheader(f"Resultados — {len(eligible)} cursos encontrados")

        display = eligible[["situacao", "curso", "universidade", "uf", "nota_corte", "diferenca"]].rename(
            columns={
                "situacao": "Status",
                "curso": "Curso",
                "universidade": "Universidade",
                "uf": "UF",
                "nota_corte": "Corte 2023",
                "diferenca": "Diferença (sua - corte)",
            }
        )

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Corte 2023": st.column_config.NumberColumn(format="%.2f"),
                "Diferença (sua - corte)": st.column_config.NumberColumn(
                    format="%.2f",
                    help="Positivo = aprovado; negativo = abaixo do corte (dentro da margem)"
                ),
            },
        )

        # ── Course distribution ────────────────────────────────────────────────
        st.subheader("Cursos Disponíveis por Área")
        counts = eligible[eligible["situacao"] == "✅ Aprovado"]["curso"].value_counts().reset_index()
        counts.columns = ["Curso", "Opções"]
        if not counts.empty:
            fig = px.bar(
                counts.head(15), x="Opções", y="Curso",
                orientation="h", color="Opções",
                color_continuous_scale="Blues",
                title="Número de Opções por Curso (aprovado)",
                template="plotly_white",
            )
            fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption(
    "Fonte: MEC / INEP — SISU 2023, modalidade ampla concorrência. "
    "Os cortes são aproximações baseadas em dados públicos e podem variar. "
    "Consulte sempre o [portal oficial do SISU](https://sisu.mec.gov.br)."
)
