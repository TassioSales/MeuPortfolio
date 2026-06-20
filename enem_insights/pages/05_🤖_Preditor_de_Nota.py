"""Page 5 — ML score predictor with AI narrative."""
import streamlit as st

from app.ai_insights import profile_insight
from app.data_loader import INCOME_MAP, REGIONS, calc_percentile, load_data
from app.charts import gauge_predicted_score, percentile_band_chart, feature_importance_chart
from app.ml_model import predict_score, train_model

st.set_page_config(
    page_title="Preditor — ENEM Insights", page_icon="🤖", layout="wide"
)

df_full = load_data()

st.title("🤖 Preditor de Nota com IA")
st.markdown(
    "Preencha seu perfil e o modelo de **Gradient Boosting** estima sua nota média "
    "com **intervalo de confiança de 95%**. A IA gera um insight personalizado sobre seu perfil."
)

# ── Train model ───────────────────────────────────────────────────────────────
model, metrics, feat_importance = train_model(df_full)

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("MAE (erro médio)", f"± {metrics['mae']:.1f} pts")
col_m2.metric("R² do modelo", f"{metrics['r2']:.3f}")
col_m3.metric("RMSE", f"{metrics['rmse']:.1f} pts")

st.markdown("---")

# ── Input form ────────────────────────────────────────────────────────────────
st.subheader("📋 Seu Perfil")

with st.form("predictor"):
    c1, c2, c3 = st.columns(3)
    with c1:
        school = st.radio("Tipo de escola", ["Pública", "Privada"])
        gender = st.radio("Gênero", ["Feminino", "Masculino"])
    with c2:
        regions_list = sorted(set(REGIONS.values()))
        region = st.selectbox("Região de residência", regions_list)
        income_options = list(INCOME_MAP.values())
        income = st.selectbox("Renda familiar mensal", income_options, index=3)
    with c3:
        race_options = ["Branco", "Pardo", "Preto", "Amarelo", "Indígena", "Não declarado"]
        race = st.selectbox("Raça / Etnia", race_options)
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🔮 Prever minha nota", use_container_width=True)

if submitted:
    score, lo, hi = predict_score(
        model,
        std_residual=metrics["std_residual"],
        school_private=(school == "Privada"),
        income_label=income,
        region=region,
        gender_male=(gender == "Masculino"),
        race_label=race,
    )
    percentile = calc_percentile(df_full, score)

    # ── Results ───────────────────────────────────────────────────────────────
    st.markdown("---")
    col_g, col_info = st.columns([1.2, 1])

    with col_g:
        st.plotly_chart(gauge_predicted_score(score), use_container_width=True)
        st.plotly_chart(percentile_band_chart(score, percentile), use_container_width=True)

    with col_info:
        st.markdown("### Resultado")
        st.markdown(
            f"**Nota prevista:** {score:.0f} pontos  \n"
            f"**Intervalo 95%:** {lo:.0f} – {hi:.0f} pts  \n"
            f"**Percentil nacional:** {percentile:.0f}%"
        )
        st.markdown("---")

        with st.spinner("Gerando análise com IA..."):
            narrative = profile_insight(
                predicted_score=score,
                school=school,
                income=income,
                region=region,
                race=race,
                percentile=percentile,
            )
        st.info(f"💡 **Análise IA:** {narrative}")

        # SISU quick hint
        if score >= 600:
            st.success(
                f"Com {score:.0f} pontos você pode ser elegível para cursos "
                "como Administração, Direito e Engenharia em universidades federais. "
                "Confira o **Simulador SISU** na barra lateral!"
            )
        elif score >= 500:
            st.warning(
                "Sua nota já abre portas para cursos como Pedagogia e Serviço Social em "
                "universidades federais do Nordeste e Norte. Veja o **Simulador SISU**!"
            )

    st.markdown("---")
    st.plotly_chart(feature_importance_chart(feat_importance), use_container_width=True)
