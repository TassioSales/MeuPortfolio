import streamlit as st
from loguru import logger
import json
from typing import Dict, Any, List

st.set_page_config(page_title="Roteiro Gerado", page_icon="🧾", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for results page with dark-mode support
st.markdown("""
<style>
    :root {
        --bg: #f6f7f9;
        --text: #1f2937;
        --muted: #6b7280;
        --card-bg: #ffffff;
        --section-bg: #f3f4f6;
        --border: #e5e7eb;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --bg: #0b0f14;
            --text: #e5e7eb;
            --muted: #9ca3af;
            --card-bg: #111827;
            --section-bg: rgba(255,255,255,0.04);
            --border: #1f2937;
        }
        body { color: var(--text); }
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    div[data-testid="stDecoration"] {display:none;}
    div[data-testid="stToolbar"] {display:none;}
    
    /* Custom navigation */
    .nav-container {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 0.75rem 1.25rem;
        margin-bottom: 1.25rem;
        border-radius: 10px;
        box-shadow: 0 3px 5px rgba(0, 0, 0, 0.08);
    }
    
    .nav-title {
        color: white;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        text-align: center;
    }
    
    .nav-subtitle {
        color: rgba(255, 255, 255, 0.85);
        font-size: 0.95rem;
        text-align: center;
        margin-top: 0.35rem;
    }
    
    /* Main container */
    .main-container {
        max-width: 1100px;
        margin: 0 auto;
        padding: 0 1rem;
    }
    
    /* Cards */
    .card {
        background: var(--card-bg);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 3px 6px rgba(0, 0, 0, 0.08);
        border: 1px solid var(--border);
    }
    
    .card-header {
        border-bottom: 1px solid var(--border);
        padding-bottom: 0.75rem;
        margin-bottom: 1rem;
    }
    
    .card-title {
        color: var(--text);
        font-size: 1.25rem;
        font-weight: 600;
        margin: 0;
    }
    
    .card-subtitle {
        color: var(--muted);
        font-size: 0.95rem;
        margin-top: 0.35rem;
    }
    
    /* Itinerary sections */
    .itinerary-section {
        background: var(--section-bg);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
        border: 1px solid var(--border);
    }
    
    .section-title {
        color: var(--text);
        font-size: 1.15rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
    }
    
    .section-icon {
        margin-right: 0.5rem;
        font-size: 1.25rem;
    }
    
    .day-card {
        background: var(--card-bg);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
        border: 1px solid var(--border);
    }
    
    .day-title {
        color: #8b9bff;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border);
    }
    
    .time-slot {
        margin-bottom: 0.6rem;
        padding: 0.6rem;
        background: var(--section-bg);
        border-radius: 6px;
        border-left: 3px solid #28a745;
        border: 1px solid var(--border);
    }
    
    .time-label {
        font-weight: 600;
        color: var(--text);
        margin-bottom: 0.15rem;
    }
    
    .activity {
        color: var(--muted);
        line-height: 1.55;
    }
    
    /* Navigation buttons */
    .nav-button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 18px;
        padding: 0.6rem 1.5rem;
        font-size: 0.95rem;
        font-weight: 500;
        text-decoration: none;
        display: inline-block;
        transition: all 0.25s ease;
        margin: 0.35rem;
        cursor: pointer;
    }
    
    .nav-button:hover {
        transform: translateY(-1px);
        box-shadow: 0 3px 6px rgba(0, 0, 0, 0.1);
        text-decoration: none;
        color: white;
    }
    
    /* Provider badge */
    .provider-badge {
        display: inline-block;
        background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
        color: white;
        padding: 0.4rem 0.9rem;
        border-radius: 18px;
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 0.85rem;
    }
    
    /* Tips box */
    .tips-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.85rem 0;
    }
    
    .tips-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
    }
    
    .tips-icon {
        margin-right: 0.5rem;
        font-size: 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

# Custom navigation header
st.markdown("""
<div class="nav-container">
	<h1 class="nav-title">🧾 Roteiro Gerado</h1>
	<p class="nav-subtitle">Seu plano de viagem personalizado está pronto!</p>
</div>
""", unsafe_allow_html=True)

# Main container
st.markdown('<div class="main-container">', unsafe_allow_html=True)

json_data = st.session_state.get("roteiro_json")
provider_used = st.session_state.get("provider_used")

if not json_data:
	st.markdown("""
	<div class="card">
		<div class="card-header">
			<h2 class="card-title">⚠️ Nenhum roteiro encontrado</h2>
			<p class="card-subtitle">Volte à página inicial para gerar um roteiro personalizado</p>
		</div>
		<div style="text-align: center; margin-top: 1rem;">
			<a href="app.py" class="nav-button">🏠 Voltar para gerar</a>
		</div>
	</div>
	""", unsafe_allow_html=True)
	logger.warning("Tentativa de abrir página de roteiro sem conteúdo")
	st.stop()

# Provider badge
st.markdown(f"""
<div class="provider-badge">
	🤖 Gerado com {provider_used}
</div>
""", unsafe_allow_html=True)

# Main title and subtitle
st.markdown(f"""
<div class="card">
	<div class="card-header">
		<h1 class="card-title">{json_data.get('titulo', 'Roteiro de Viagem')}</h1>
		<p class="card-subtitle">{json_data.get('subtitulo', 'Seu plano de viagem personalizado')}</p>
	</div>
</div>
""", unsafe_allow_html=True)

# Create tabs for organized content
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Visão Geral", "🗓️ Cronograma", "🍽️ Gastronomia", "🌃 Vida Noturna", "💡 Dicas"])

with tab1:
	visao_geral = json_data.get('visao_geral', {})
	st.markdown("""
	<div class="card">
		<div class="card-header">
			<h2 class="card-title">📋 Informações da Viagem</h2>
		</div>
		<div class="itinerary-section">
	""", unsafe_allow_html=True)
	
	col1, col2 = st.columns(2)
	with col1:
		st.markdown(f"**🏙️ Destino:** {visao_geral.get('destino', 'N/A')}")
		st.markdown(f"**📅 Duração:** {visao_geral.get('duracao', 'N/A')} dias")
		st.markdown(f"**💰 Estilo:** {visao_geral.get('estilo', 'N/A')}")
	
	with col2:
		st.markdown(f"**🌤️ Clima Esperado:** {visao_geral.get('clima_esperado', 'N/A')}")
		st.markdown(f"**🏨 Hospedagem Sugerida:** {visao_geral.get('hospedagem_sugerida', 'N/A')}")
	
	# Período escolhido
	periodo_escolhido = visao_geral.get('periodo_escolhido', '')
	if periodo_escolhido and periodo_escolhido != "Descreva o período escolhido e por que é ideal para este destino":
		st.markdown("**📆 Período Escolhido:**")
		st.markdown(f"*{periodo_escolhido}*")
	
	st.markdown("</div></div>", unsafe_allow_html=True)

with tab2:
	cronograma = json_data.get('cronograma', [])
	st.markdown("""
	<div class="card">
		<div class="card-header">
			<h2 class="card-title">🗓️ Cronograma Detalhado</h2>
			<p class="card-subtitle">Sua jornada dia a dia</p>
		</div>
	""", unsafe_allow_html=True)
	
	for dia in cronograma:
		st.markdown(f"""
		<div class="day-card">
			<div class="day-title">Dia {dia.get('dia', 'N/A')}: {dia.get('titulo', 'Atividades')}</div>
		""", unsafe_allow_html=True)
		
		atividades = dia.get('atividades', [])
		for atividade in atividades:
			dica = atividade.get('dica', '')
			dica_html = f'<br><small style="color: #28a745; font-style: italic;">💡 {dica}</small>' if dica else ''
			
			st.markdown(f"""
			<div class="time-slot">
				<div class="time-label">{atividade.get('horario', 'N/A')}</div>
				<div class="activity">{atividade.get('atividade', 'N/A')}{dica_html}</div>
			</div>
			""", unsafe_allow_html=True)
		
		st.markdown("</div>", unsafe_allow_html=True)
	
	st.markdown("</div>", unsafe_allow_html=True)

with tab3:
	gastronomia = json_data.get('gastronomia', {})
	st.markdown("""
	<div class="card">
		<div class="card-header">
			<h2 class="card-title">🍽️ Arsenal Gastronômico</h2>
		</div>
		<div class="itinerary-section">
	""", unsafe_allow_html=True)
	
	st.markdown("**🍴 Pratos Indispensáveis:**")
	pratos = gastronomia.get('pratos_indispensaveis', [])
	if pratos:
		for i, prato in enumerate(pratos, 1):
			st.markdown(f"{i}. {prato}")
	else:
		st.markdown("Experimente a culinária local")
	
	st.markdown("**🏆 Restaurante Tesouro Escondido:**")
	st.markdown(f"*{gastronomia.get('restaurante_tesouro', 'Consulte recomendações locais')}*")
	
	st.markdown("**🎯 Experiência Culinária:**")
	st.markdown(f"*{gastronomia.get('experiencia_culinaria', 'Explore mercados e restaurantes locais')}*")
	
	st.markdown("</div></div>", unsafe_allow_html=True)

with tab4:
	vida_noturna = json_data.get('vida_noturna', {})
	st.markdown("""
	<div class="card">
		<div class="card-header">
			<h2 class="card-title">🌃 Vida Noturna</h2>
			<p class="card-subtitle">Bares, festas, shows e experiências noturnas</p>
		</div>
		<div class="itinerary-section">
	""", unsafe_allow_html=True)
	
	# Bares recomendados
	st.markdown("**🍻 Bares e Pubs Recomendados:**")
	bares = vida_noturna.get('bares_recomendados', [])
	if bares and bares[0] != "Liste 3-5 bares, pubs ou lounges imperdíveis":
		for i, bar in enumerate(bares, 1):
			st.markdown(f"{i}. {bar}")
	else:
		st.markdown("Explore bares locais e pubs tradicionais")
	
	# Clubes e festas
	st.markdown("**🎉 Clubes e Festas:**")
	clubes = vida_noturna.get('clubes_festas', [])
	if clubes and clubes[0] != "Sugira clubes, discotecas ou locais de festa":
		for i, clube in enumerate(clubes, 1):
			st.markdown(f"{i}. {clube}")
	else:
		st.markdown("Consulte eventos locais e festas da região")
	
	# Shows e eventos
	st.markdown("**🎵 Shows e Eventos:**")
	shows = vida_noturna.get('shows_eventos', [])
	if shows and shows[0] != "Mencione shows, concertos ou eventos noturnos especiais":
		for i, show in enumerate(shows, 1):
			st.markdown(f"{i}. {show}")
	else:
		st.markdown("Verifique agenda de shows e eventos noturnos")
	
	# Roteiro bar hopping
	roteiro = vida_noturna.get('roteiro_bar_hopping', '')
	if roteiro and roteiro != "Sugira um roteiro de bar hopping ou experiência noturna única":
		st.markdown("**🍺 Roteiro Bar Hopping:**")
		st.markdown(f"*{roteiro}*")
	
	# Dicas noturnas
	dicas_noturnas = vida_noturna.get('dicas_noturnas', '')
	if dicas_noturnas and dicas_noturnas != "Dicas específicas para a vida noturna (horários, dress code, segurança)":
		st.markdown("**💡 Dicas Noturnas:**")
		st.markdown(f"*{dicas_noturnas}*")
	
	st.markdown("</div></div>", unsafe_allow_html=True)

with tab5:
	dicas = json_data.get('dicas_viagem', {})
	st.markdown("""
	<div class="tips-box">
		<div class="tips-title">
			<span class="tips-icon">💡</span>
			Inteligência de Viagem
		</div>
	""", unsafe_allow_html=True)
	
	st.markdown("**🚗 Mobilidade:**")
	st.markdown(f"*{dicas.get('mobilidade', 'Use transporte público ou aplicativos de carona')}*")
	
	st.markdown("**💬 Comunicação:**")
	st.markdown(f"*{dicas.get('comunicacao', 'Aprenda frases básicas do idioma local')}*")
	
	st.markdown("**⚠️ Alerta de Especialista:**")
	st.markdown(f"*{dicas.get('alerta_especialista', 'Mantenha-se seguro e hidratado')}*")
	
	st.markdown("</div>", unsafe_allow_html=True)

# Navigation buttons container
st.markdown("""
<div style="margin-top: 2rem; padding: 1.25rem; background: var(--section-bg); 
            border-radius: 10px; border: 1px solid var(--border);">
    <h3 style="color: var(--text); text-align: center; margin-bottom: 1rem;">
        O que você gostaria de fazer agora?
    </h3>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    if st.button("✨ Gerar novo roteiro", 
                use_container_width=True,
                type="primary"):
        # Limpa a sessão e volta para a página principal
        st.session_state.clear()
        st.switch_page("app.py")
        
with col2:
    if st.button("🏠 Voltar ao início", 
                use_container_width=True,
                type="primary"):
        # Limpa a sessão e volta para a página principal
        st.session_state.clear()
        st.switch_page("app.py")

# Close main container
st.markdown("</div>", unsafe_allow_html=True)
