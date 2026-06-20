"""Page 4 — Socioeconomic factors."""
import streamlit as st
import plotly.express as px

from app.analytics import income_summary, race_summary, gender_summary, percentile_distribution
from app.charts import scatter_income_score, radar_subjects, bar_race
from app.data_loader import load_data

st.set_page_config(
    page_title="Socioeconômico — ENEM Insights", page_icon="💰", layout="wide"
)

df_full = load_data()

with st.sidebar:
    st.header("🔧 Filtros")
    years = sorted(df_full["NU_ANO"].unique())
    sel_years = st.multiselect("Ano(s)", years, default=years)

df = df_full[df_full["NU_ANO"].isin(sel_years)]
if df.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()

st.title("💰 Fatores Socioeconômicos")

tab1, tab2, tab3, tab4 = st.tabs(["Renda Familiar", "Raça / Etnia", "Gênero", "Distribuição Percentil"])

with tab1:
    income_df = income_summary(df)
    st.plotly_chart(scatter_income_score(income_df), use_container_width=True)

    # Detailed bar chart
    fig_bar = px.bar(
        income_df, x="renda_label", y="media_geral",
        color="media_geral", color_continuous_scale="RdYlGn",
        labels={"renda_label": "Faixa de Renda", "media_geral": "Média Geral"},
        title="Nota Média por Faixa de Renda Familiar",
        text_auto=".1f",
    )
    fig_bar.update_layout(xaxis_tickangle=-45, template="plotly_white",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_bar, use_container_width=True)
    st.dataframe(income_df.rename(columns={"renda_label": "Renda", "media_geral": "Média",
                                            "participantes": "Candidatos"}),
                 use_container_width=True, hide_index=True)

with tab2:
    race_df = race_summary(df)
    st.plotly_chart(bar_race(race_df), use_container_width=True)

    radar_race = race_df.rename(columns={"raca_label": "raca_label"})
    st.plotly_chart(radar_subjects(race_df, "raca_label"), use_container_width=True)
    st.dataframe(race_df, use_container_width=True, hide_index=True)

with tab3:
    gender_df = gender_summary(df)
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(radar_subjects(gender_df, "genero_label"), use_container_width=True)
    with col2:
        fig_g = px.bar(
            gender_df.melt(id_vars="genero_label", var_name="Disciplina", value_name="Nota"),
            x="Disciplina", y="Nota", color="genero_label", barmode="group",
            template="plotly_white",
            title="Desempenho por Gênero e Disciplina",
        )
        fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_g, use_container_width=True)

with tab4:
    perc_df = percentile_distribution(df)
    fig_p = px.area(
        perc_df, x="nota", y="percentil",
        title="Distribuição de Percentis — Nota Média Geral",
        labels={"nota": "Nota Média", "percentil": "Percentil (%)"},
        color_discrete_sequence=["#3498db"],
        template="plotly_white",
    )
    fig_p.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_p, use_container_width=True)

    st.info(
        "**Como ler:** o percentil 50 corresponde à mediana — metade dos candidatos "
        f"ficou abaixo de **{perc_df[perc_df['percentil'] == 50]['nota'].values[0]:.0f} pontos**."
    )
