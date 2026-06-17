"""ENEM Insights — Streamlit dashboard."""
import streamlit as st

from .analytics import (
    gender_summary,
    income_summary,
    race_summary,
    regional_summary,
    school_type_summary,
    score_distribution,
    subject_correlations,
    yearly_trend,
    top_states,
)
from .charts import (
    bar_regional,
    bar_school_gap,
    gauge_predicted_score,
    heatmap_correlation,
    histogram_score,
    line_yearly_trend,
    radar_subjects,
    scatter_income_score,
)
from .data_loader import INCOME_MAP, REGIONS, SUBJECT_NAMES, load_data
from .ml_model import predict_score, train_model

SUBJECT_NAMES = {
    "NU_NOTA_CN": "Ciências da Natureza",
    "NU_NOTA_CH": "Ciências Humanas",
    "NU_NOTA_LC": "Linguagens e Códigos",
    "NU_NOTA_MT": "Matemática",
    "NU_NOTA_REDACAO": "Redação",
}

st.set_page_config(
    page_title="ENEM Insights",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        color: white;
    }
    .stMetric label { font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


def sidebar_filters(df):
    st.sidebar.header("🔧 Filtros")

    years = sorted(df["NU_ANO"].unique())
    selected_years = st.sidebar.multiselect(
        "Ano(s) do ENEM", years, default=years
    )

    regions = sorted(df["regiao"].unique())
    selected_regions = st.sidebar.multiselect(
        "Região(ões)", regions, default=regions
    )

    school_types = ["Pública", "Privada"]
    selected_schools = st.sidebar.multiselect(
        "Tipo de Escola", school_types, default=school_types
    )

    mask = (
        df["NU_ANO"].isin(selected_years)
        & df["regiao"].isin(selected_regions)
        & df["escola_label"].isin(selected_schools)
    )
    return df[mask]


def page_overview(df):
    st.title("📚 ENEM Insights — Visão Geral")
    st.caption(
        "Análise do Exame Nacional do Ensino Médio. "
        "Dados sintéticos gerados com as mesmas distribuições estatísticas dos microdados oficiais do INEP."
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Participantes", f"{len(df):,}")
    col2.metric("Média Geral", f"{df['media_geral'].mean():.1f}")
    col3.metric("Média Matemática", f"{df['NU_NOTA_MT'].mean():.1f}")
    col4.metric("Média Redação", f"{df['NU_NOTA_REDACAO'].mean():.1f}")
    col5.metric("% Escola Privada", f"{(df['escola_label'] == 'Privada').mean() * 100:.1f}%")

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        reg_df = regional_summary(df)
        st.plotly_chart(bar_regional(reg_df), use_container_width=True)

    with col_b:
        subject_col = st.selectbox("Disciplina para distribuição:", list(SUBJECT_NAMES.keys()),
                                   format_func=lambda x: SUBJECT_NAMES[x])
        centers, counts = score_distribution(df, subject_col)
        st.plotly_chart(
            histogram_score(centers, counts, SUBJECT_NAMES[subject_col]),
            use_container_width=True,
        )

    st.plotly_chart(line_yearly_trend(yearly_trend(df)), use_container_width=True)


def page_regional(df):
    st.title("🗺️ Análise Regional")

    reg_df = regional_summary(df)
    st.dataframe(reg_df.rename(columns={"regiao": "Região", "media_geral": "Média Geral",
                                         "participantes": "Participantes"}),
                 use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(bar_regional(reg_df), use_container_width=True)
    with col2:
        st.subheader("Top 10 Estados")
        top = top_states(df)
        st.dataframe(top, use_container_width=True, hide_index=True)

    st.subheader("Radar de Desempenho por Região")
    reg_df["regiao"] = reg_df["regiao"]
    st.plotly_chart(radar_subjects(reg_df, "regiao"), use_container_width=True)


def page_school(df):
    st.title("🏫 Pública vs Privada")

    school_df = school_type_summary(df)
    st.plotly_chart(bar_school_gap(school_df), use_container_width=True)

    pub = df[df["escola_label"] == "Pública"]["media_geral"].mean()
    pri = df[df["escola_label"] == "Privada"]["media_geral"].mean()
    gap = pri - pub
    col1, col2, col3 = st.columns(3)
    col1.metric("Média — Escola Pública", f"{pub:.1f}")
    col2.metric("Média — Escola Privada", f"{pri:.1f}")
    col3.metric("Diferença", f"+{gap:.1f}", delta=f"{gap:.1f} pts", delta_color="normal")

    st.subheader("Radar: Perfil por Tipo de Escola")
    radar_df = df[df["escola_label"].isin(["Pública", "Privada"])].groupby("escola_label")[
        list(SUBJECT_NAMES.keys())
    ].mean().round(1).reset_index()
    st.plotly_chart(radar_subjects(radar_df, "escola_label"), use_container_width=True)


def page_socioeconomic(df):
    st.title("💰 Fatores Socioeconômicos")

    tab1, tab2, tab3 = st.tabs(["Renda Familiar", "Raça / Etnia", "Gênero"])

    with tab1:
        income_df = income_summary(df)
        st.plotly_chart(scatter_income_score(income_df), use_container_width=True)
        st.dataframe(income_df, use_container_width=True, hide_index=True)

    with tab2:
        race_df = race_summary(df)
        st.plotly_chart(
            bar_regional(race_df.rename(columns={"raca_label": "regiao"})),
            use_container_width=True,
        )
        st.dataframe(race_df, use_container_width=True, hide_index=True)

    with tab3:
        gender_df = gender_summary(df)
        st.dataframe(gender_df, use_container_width=True, hide_index=True)
        st.plotly_chart(radar_subjects(gender_df, "genero_label"), use_container_width=True)

    st.subheader("Correlação entre Disciplinas")
    corr = subject_correlations(df)
    st.plotly_chart(heatmap_correlation(corr), use_container_width=True)


def page_predictor(df):
    st.title("🤖 Preditor de Nota")
    st.write(
        "Preencha o perfil abaixo para que o modelo de Gradient Boosting estime "
        "a nota média esperada no ENEM."
    )

    model, metrics, feat_importance = train_model(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("MAE (erro médio)", f"{metrics['mae']:.1f} pts")
    col2.metric("R² do modelo", f"{metrics['r2']:.3f}")
    col3.metric("RMSE", f"{metrics['rmse']:.1f} pts")

    st.markdown("---")
    st.subheader("Simule seu perfil")

    regions = sorted(set(REGIONS.values()))
    income_options = list(INCOME_MAP.values())
    race_options = ["Branco", "Pardo", "Preto", "Amarelo", "Indígena", "Não declarado"]

    c1, c2 = st.columns(2)
    with c1:
        school = st.radio("Tipo de escola", ["Pública", "Privada"])
        gender = st.radio("Gênero", ["Masculino", "Feminino"])
        region = st.selectbox("Região de residência", regions)
    with c2:
        income = st.selectbox("Renda familiar mensal", income_options, index=3)
        race = st.selectbox("Raça / Etnia", race_options)

    score = predict_score(
        model,
        school_private=(school == "Privada"),
        income_label=income,
        region=region,
        gender_male=(gender == "Masculino"),
        race_label=race,
    )

    st.plotly_chart(gauge_predicted_score(score), use_container_width=True)

    st.subheader("Importância das Variáveis")
    fi_df = feat_importance.reset_index()
    fi_df.columns = ["Variável", "Importância"]
    labels_map = {
        "school_private": "Escola Privada",
        "income_rank": "Renda Familiar",
        "regiao_encoded": "Região",
        "gender_male": "Gênero",
        "race_encoded": "Raça/Etnia",
    }
    fi_df["Variável"] = fi_df["Variável"].map(labels_map)
    st.bar_chart(fi_df.set_index("Variável"))


PAGES = {
    "🏠 Visão Geral": page_overview,
    "🗺️ Análise Regional": page_regional,
    "🏫 Escola Pública vs Privada": page_school,
    "💰 Fatores Socioeconômicos": page_socioeconomic,
    "🤖 Preditor de Nota": page_predictor,
}


def main():
    df_full = load_data()
    df = sidebar_filters(df_full)

    if df.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
        return

    page = st.sidebar.radio("Navegação", list(PAGES.keys()))
    PAGES[page](df)

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Dados: microdados ENEM — INEP/MEC.\n\n"
        "Em modo demo, dados sintéticos são usados para preservar a privacidade."
    )


if __name__ == "__main__":
    main()
