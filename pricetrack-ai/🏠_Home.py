import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, Any, List
from core.models import create_tables, SessionLocal
from core.database import DatabaseManager, DatabaseTransaction
from core.utils import format_currency
from core.ai_services import gemini_service, AIServiceError
from core.logger import get_logger, setup_logging

# Esconder menu padrão (reforçado para 100% invisível)
st.markdown("""
<style>
    #MainMenu, header[data-testid="stHeader"], footer[data-testid="stFooter"], .stDeployButton, #stDecoration, [data-testid="collapsedControl"], .st-emotion-cache-1uqpsho p, [data-testid="stStatusWidget"] { 
        visibility: hidden !important; display: none !important; opacity: 0 !important; height: 0 !important; 
    }
    .stApp { padding-top: 0 !important; padding-bottom: 0 !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    section[data-testid="stSidebar"] { overflow-y: auto; }
</style>
""", unsafe_allow_html=True)

# Configuração da página
st.set_page_config(
    page_title="PriceTrack AI - Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar logging
logger = get_logger(__name__)
setup_logging()

class UIManager:
    """UI Manager: Animações e Estilos Dinâmicos."""
    @staticmethod
    def inject_custom_css():
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        :root {
            --primary: #8b5cf6;
            --primary-dark: #7c3aed;
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --radius-lg: 1rem;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
            --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
            --glass-bg: rgba(255, 255, 255, 0.03);
            --glass-border: rgba(255, 255, 255, 0.1);
        }
        
        /* Base Styles */
        .main { 
            background: var(--bg-primary); 
            color: var(--text-primary); 
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
        }
        
        /* Cards */
        .stats-card { 
            background: var(--bg-secondary); 
            border-radius: var(--radius-lg); 
            padding: 1.5rem; 
            box-shadow: var(--shadow);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid var(--glass-border);
            height: 100%;
            position: relative;
            overflow: hidden;
        }
        
        .stats-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--primary-dark));
        }
        
        .stats-card:hover { 
            transform: translateY(-5px); 
            box-shadow: var(--shadow-xl);
            border-color: rgba(139, 92, 246, 0.3);
        }
        
        /* Welcome Header */
        .welcome-header { 
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white; 
            padding: 3rem 2.5rem; 
            border-radius: var(--radius-lg); 
            margin-bottom: 2.5rem; 
            box-shadow: var(--shadow-xl); 
            position: relative; 
            overflow: hidden;
        }
        
        .welcome-header::after {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 100%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%);
            transform: rotate(30deg);
            pointer-events: none;
        }
        
        /* Buttons */
        .stButton > button {
            border-radius: 0.5rem;
            padding: 0.5rem 1.25rem;
            font-weight: 500;
            transition: all 0.2s;
            border: none;
            background: var(--primary);
            color: white;
        }
        
        .stButton > button:hover {
            background: var(--primary-dark);
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        
        /* Quick Actions */
        .quick-action { 
            background: var(--bg-secondary); 
            border: 1px solid var(--glass-border); 
            padding: 1.5rem; 
            border-radius: var(--radius-lg); 
            transition: all 0.3s; 
            cursor: pointer;
            text-align: center;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        .quick-action:hover { 
            transform: translateY(-5px); 
            box-shadow: var(--shadow-lg); 
            background: rgba(139, 92, 246, 0.1); 
            border-color: var(--primary);
        }
        
        /* Alerts */
        .alert-item { 
            background: var(--bg-secondary); 
            border-left: 4px solid var(--warning); 
            padding: 1.25rem; 
            border-radius: var(--radius-lg); 
            margin-bottom: 1rem; 
            animation: fadeIn 0.3s ease-out;
            box-shadow: var(--shadow);
        }
        
        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-secondary);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--primary);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--primary-dark);
        }
        @keyframes bounceIn {{ 0% {{ transform: scale(0.95); opacity: 0; }} 50% {{ transform: scale(1.02); }} 100% {{ transform: scale(1); opacity: 1; }} }}
        .tour-step {{ background: rgba(139,92,246,0.1); border-left: 4px solid var(--primary); padding: 1.5rem; border-radius: var(--radius-lg); margin: 1rem 0; transition: all 0.3s; }}
        .tour-step:hover {{ transform: scale(1.01); box-shadow: var(--shadow-lg); }}
        .stButton > button {{ background: linear-gradient(135deg, var(--primary), #7c3aed); border-radius: var(--radius-lg); color: white; box-shadow: 0 4px 12px rgba(139,92,246,0.3); transition: all 0.3s; }}
        .stButton > button:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(139,92,246,0.4); }}
        </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def render_card(title: str, content: str, icon: str, color: str = "#8b5cf6") -> None:
        """Card animado com ícone e glass effect."""
        st.markdown(f"""
        <div class="stats-card" style="border-left: 4px solid {color};">
            <h3>{icon} {title}</h3>
            <p>{content}</p>
        </div>
        """, unsafe_allow_html=True)

class DataManager:
    """Data Manager: Caches e Queries Robustas."""
    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        @st.cache_data(ttl=300)
        def _cached() -> Dict[str, Any]:
            try:
                with SessionLocal() as db, DatabaseTransaction(db) as db_manager:
                    stats = db_manager.get_stats()
                    return {**stats, 'total_savings': stats.get('total_savings', 0), 'coverage_percentage': stats.get('coverage_percentage', 0)}
            except Exception as e:
                logger.error(f"Stats: {e}")
                return {'total_products': 0, 'active_alerts': 0, 'products_with_history': 0, 'products_with_tags': 0, 'total_savings': 0, 'coverage_percentage': 0}
        return _cached()

    @staticmethod
    def get_ai_insight() -> str:
        @st.cache_data(ttl=600)
        def _cached() -> str:
            try:
                return gemini_service._make_api_call("Artemis: Insight breve sobre preços. Dicas para economizar. 2 parágrafos.").text.strip()
            except Exception as e:
                logger.error(f"Insight: {e}")
                return "💡 Monitore sazonalmente para deals. Artemis prevê quedas!"
        return _cached()

def initialize_session_state() -> None:
    if 'initialized' not in st.session_state:
        st.session_state.update({'initialized': True, 'tour_step': 0, 'tour_completed': False})
        logger.info("Estado inicializado")

def configure_ai_sidebar() -> None:
    with st.sidebar.expander("⚙️ IA Config"):
        st.markdown("Chave Gemini: [Obter](https://aistudio.google.com/) | [Guia](https://ai.google.dev/gemini-api/docs/quickstart?hl=pt-br)")
        api_key = st.text_input("API Key", type="password")
        if api_key and not (len(api_key) > 20 and api_key.startswith('AIza')):
            st.error("Chave inválida.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Aplicar"):
                try:
                    gemini_service.configure_api_key(api_key)
                    st.session_state["GEMINI_API_KEY"] = api_key
                    with SessionLocal() as db, DatabaseTransaction(db) as db_manager:
                        db_manager.set_setting("GEMINI_API_KEY", api_key)
                    st.success("Aplicada!")
                except Exception as e:
                    st.error(f"Erro: {e}")
        with col2:
            if st.button("Limpar"):
                st.session_state.pop("GEMINI_API_KEY", None)
                with SessionLocal() as db, DatabaseTransaction(db) as db_manager:
                    db_manager.delete_setting("GEMINI_API_KEY")
                st.info("Limpa!")

def display_welcome_section() -> None:
    st.markdown("""
    <div class="welcome-header">
        <h1>🏠 Bem-vindo ao PriceTrack AI</h1>
        <p>Sua consultora inteligente para e-commerce. Monitore, compare e economize com Artemis.</p>
    </div>
    """, unsafe_allow_html=True)

def display_stats_cards(stats: Dict[str, Any]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        UIManager.render_card("Produtos", f"{stats['total_products']}", "📦")
    with col2:
        UIManager.render_card("Alertas", f"{stats['active_alerts']}", "🔔")
    with col3:
        UIManager.render_card("Histórico", f"{stats['products_with_history']}", "📊")
    with col4:
        UIManager.render_card("Cobertura", f"{stats['coverage_percentage']:.1f}%", "📈")

def display_coverage_chart(stats: Dict[str, Any]) -> None:
    data = {'Categoria': ['Histórico', 'Sem'], 'Quantidade': [stats['products_with_history'], stats['total_products'] - stats['products_with_history']]}
    fig = px.pie(data, values='Quantidade', names='Categoria', color_discrete_map={'Histórico': '#10b981', 'Sem': '#ef4444'})
    st.plotly_chart(fig, use_container_width=True)

def display_quick_actions() -> None:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🔍 Pesquisar"):
            st.switch_page("pages/1_🔎_Pesquisar_e_Adicionar_Produto.py")
    with col2:
        if st.button("📊 Dashboard"):
            st.switch_page("pages/2_📊_Dashboard_de_Análise.py")
    with col3:
        if st.button("⚔️ Comparar"):
            st.switch_page("pages/3_⚔️_Comparador_Inteligente.py")
    with col4:
        if st.button("🔔 Alertas"):
            st.switch_page("pages/4_🔔_Alertas_e_Notificações.py")

def display_recent_alerts() -> None:
    st.info("Nenhum alerta recente. Configure na página de Alertas!")

def display_ai_insights() -> None:
    insight = DataManager.get_ai_insight()
    UIManager.render_card("Insight Artemis", insight, "🤖", "#8b5cf6")

def display_tour_section() -> None:
    if not st.session_state.tour_completed:
        current = st.session_state.tour_step
        steps = ["Pesquisar", "Dashboard", "Comparador", "Alertas"]
        st.progress(current / len(steps))
        st.markdown(f"**Passo {current + 1}/{len(steps)}: {steps[current]}**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➡️ Próximo"):
                st.session_state.tour_step += 1
                if st.session_state.tour_step >= len(steps):
                    st.session_state.tour_completed = True
                st.rerun()
        with col2:
            if st.button("✅ Concluir"):
                st.session_state.tour_completed = True
                st.balloons()
                st.rerun()
    else:
        st.success("Tour concluído! 🎉")

def display_sidebar_content() -> None:
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; margin-bottom: 2rem;'>
            <svg width="80" height="80" viewBox="0 0 80 80"><circle cx="40" cy="40" r="35" fill="#8b5cf6" opacity="0.2"/><text x="40" y="48" text-anchor="middle" fill="#8b5cf6" font-size="24" font-weight="bold">PT</text><text x="40" y="58" text-anchor="middle" fill="#a78bfa" font-size="10">AI</text></svg>
            <h2 style='color: #8b5cf6; font-size: 1.2rem;'>PriceTrack AI</h2>
            <p style='color: #94a3b8; font-size: 0.8rem;'>Monitoramento Inteligente</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<h3 style="color: #a78bfa; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.1em;">Navegação</h3>', unsafe_allow_html=True)
        
        nav = [
            ("🏠 Página Inicial", "#", True),
            ("🔍 Pesquisar", "pages/1_🔎_Pesquisar_e_Adicionar_Produto.py", False),
            ("📊 Dashboard", "pages/2_📊_Dashboard_de_Análise.py", False),
            ("⚔️ Comparador", "pages/3_⚔️_Comparador_Inteligente.py", False),
            ("🔔 Alertas", "pages/4_🔔_Alertas_e_Notificações.py", False)
        ]
        
        for icon, page, active in nav:
            cls = "nav-item active" if active else "nav-item"
            st.markdown(f'<a href="{page}" class="{cls}" onclick="if(this.href==\'#\'){{return false;}}else{{window.location.href=this.href;}}"><span style="margin-right: 0.75rem;">{icon}</span>{page.split("/")[-1].replace("_", " ").title()}</a>', unsafe_allow_html=True)
            if not active:
                st.markdown('<hr style="border: none; border-top: 1px solid #334155; margin: 0.5rem 0;">', unsafe_allow_html=True)
        
        st.markdown('<hr style="border: none; border-top: 1px solid #334155; margin: 1.5rem 0;">', unsafe_allow_html=True)
        configure_ai_sidebar()

def main() -> None:
    try:
        initialize_session_state()
        create_tables()
        UIManager.inject_custom_css()
        display_sidebar_content()
        
        with st.spinner("Carregando dashboard..."):
            display_welcome_section()
            stats = DataManager.get_dashboard_stats()
            st.markdown("### 📊 Visão Geral")
            display_stats_cards(stats)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                display_coverage_chart(stats)
            with col2:
                display_quick_actions()
            
            display_recent_alerts()
            display_ai_insights()
            display_tour_section()
        
        st.markdown("""
        <div style='text-align: center; padding: 2rem; color: #64748b; border-top: 1px solid #334155;'>
            <p>🚀 PriceTrack AI - Dados em decisões | ❤️ Streamlit + Gemini | v1.0 © 2025</p>
        </div>
        """, unsafe_allow_html=True)
        logger.info("Home carregado")
    except Exception as e:
        logger.error(f"Home: {e}")
        st.error("Erro. Recarregue ou ver logs.")

if __name__ == "__main__":
    main()