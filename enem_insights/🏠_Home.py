"""ENEM Insights — entry point."""
import streamlit as st

st.set_page_config(
    page_title="ENEM Insights",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ── global ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ── hero ── */
    .hero {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 20px;
        padding: 3rem 2.5rem;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .hero h1 { font-size: 3rem; font-weight: 700; margin: 0; letter-spacing: -1px; }
    .hero p  { font-size: 1.15rem; opacity: 0.85; margin-top: 0.75rem; }

    /* ── feature cards ── */
    .feat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
    .feat-card {
        background: white;
        border: 1px solid #e8ecf0;
        border-radius: 14px;
        padding: 1.5rem;
        transition: transform .2s, box-shadow .2s;
    }
    .feat-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,.08); }
    .feat-icon { font-size: 2rem; margin-bottom: .5rem; }
    .feat-title { font-weight: 600; font-size: 1rem; color: #1a1a2e; margin-bottom: .35rem; }
    .feat-desc  { font-size: .85rem; color: #666; line-height: 1.5; }

    /* ── sidebar ── */
    [data-testid="stSidebarNav"] { padding-top: .5rem; }
    .stMetric { background: #f8f9ff; border-radius: 10px; padding: .75rem 1rem; }
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div style="font-size:3.5rem">📚</div>
  <h1>ENEM Insights</h1>
  <p>Plataforma analítica completa do Exame Nacional do Ensino Médio<br>
     com IA generativa, mapas interativos e simulador SISU</p>
</div>
""", unsafe_allow_html=True)

# ── Feature cards ─────────────────────────────────────────────────────────────
st.markdown('<div class="feat-grid">', unsafe_allow_html=True)
features = [
    ("📊", "Visão Geral", "Métricas nacionais, tendências anuais e distribuição de notas por disciplina."),
    ("🗺️", "Mapa do Brasil", "Mapa coroplético interativo com desempenho por estado e região."),
    ("🏫", "Equidade Escolar", "Comparativo público × privado e análise de desigualdade educacional."),
    ("💰", "Fatores Socioeconômicos", "Impacto de renda, raça e gênero no desempenho do ENEM."),
    ("🤖", "Preditor com IA", "Modelo de ML prediz sua nota com intervalo de confiança e narrativa gerada por IA."),
    ("🎓", "Simulador SISU", "Descubra quais cursos e universidades sua nota pode alcançar."),
]
cols = st.columns(3)
for i, (icon, title, desc) in enumerate(features):
    with cols[i % 3]:
        st.markdown(
            f'<div class="feat-card">'
            f'<div class="feat-icon">{icon}</div>'
            f'<div class="feat-title">{title}</div>'
            f'<div class="feat-desc">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Quick stats ───────────────────────────────────────────────────────────────
from app.data_loader import load_data  # noqa: E402

df = load_data()

st.subheader("Dados em Tempo Real")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Participantes", f"{len(df):,}")
c2.metric("Média Geral", f"{df['media_geral'].mean():.1f}")
c3.metric("Média Matemática", f"{df['NU_NOTA_MT'].mean():.1f}")
c4.metric("Média Redação", f"{df['NU_NOTA_REDACAO'].mean():.1f}")
c5.metric("Anos Cobertos", f"{df['NU_ANO'].nunique()}")

st.markdown("""
---
<small style="color:#999">
Dados sintéticos gerados com as mesmas distribuições estatísticas dos microdados oficiais do INEP/MEC.
Para análise com microdados reais, defina a variável de ambiente <code>ENEM_DATA_PATH</code>.
</small>
""", unsafe_allow_html=True)
