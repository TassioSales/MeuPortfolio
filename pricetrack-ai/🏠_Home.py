# Sidebar: configuração de IA (chave manual)
def configure_ai_sidebar():
    with st.sidebar.expander("⚙️ Configuração de IA", expanded=False):
        st.markdown(
            """
            - Informe sua chave da API Gemini obtida no **Google AI Studio**.
            - Guia: **Gemini API – Início Rápido**.
            """
        )
        st.markdown(
            """
            • Obter chave: https://aistudio.google.com/

            • Quickstart: https://ai.google.dev/gemini-api/docs/quickstart?hl=pt-br
            """
        )

        api_key_input = st.text_input(
            "GEMINI_API_KEY",
            type="password",
            placeholder="Cole sua chave aqui",
            help="A chave não será salva em disco; fica apenas nesta sessão."
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Aplicar chave", use_container_width=True):
                try:
                    gemini_service.configure_api_key(api_key_input)
                    st.session_state["GEMINI_API_KEY"] = api_key_input
                    st.success("Chave aplicada com sucesso.")
                except AIServiceError as e:
                    st.error(f"Erro ao configurar chave: {e}")

        with col_b:
            if st.button("Limpar chave", use_container_width=True):
                st.session_state.pop("GEMINI_API_KEY", None)
                # Não reinicializamos automaticamente para evitar estado inconsistente
                st.info("Chave removida desta sessão. Informe novamente para usar a IA.")

    # Auto-aplicar chave da sessão ao carregar, se ainda não configurado
    try:
        if st.session_state.get("GEMINI_API_KEY") and getattr(gemini_service, "client", None) is None:
            gemini_service.configure_api_key(st.session_state["GEMINI_API_KEY"])
    except Exception:
        pass

"""
🏠 Página Inicial - PriceTrack AI
Dashboard principal com overview e tour guiado
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from core.logger import setup_logging, get_logger, log_user_action
from core.models import create_tables, SessionLocal
from core.database import DatabaseManager, DatabaseTransaction
from core.utils import format_currency, format_percentage, get_product_status, format_completeness_score
from core.ai_services import gemini_service, AIServiceError

# Configurar página
st.set_page_config(
    page_title="PriceTrack AI - Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar logging
logger = get_logger(__name__)
setup_logging()

# CSS customizado
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .feature-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e9ecef;
        margin: 0.5rem 0;
    }
    .alert-banner {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Inicializa variáveis do session state"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.user_name = "Usuário"
        st.session_state.chat_history = {}
        st.session_state.comparison_history = []
        logger.info("Session state inicializado")


def get_dashboard_stats():
    """Obtém estatísticas do dashboard"""
    try:
        db = SessionLocal()
        with DatabaseTransaction(db) as db_manager:
            stats = db_manager.get_stats()
            return stats
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        return {
            "total_products": 0,
            "active_alerts": 0,
            "products_with_history": 0,
            "products_with_tags": 0,
            "coverage_percentage": 0
        }


def display_welcome_section():
    """Exibe seção de boas-vindas"""
    st.markdown("""
    <div class="main-header">
        <h1>🏠 Bem-vindo ao PriceTrack AI</h1>
        <h3>Sua consultora pessoal de e-commerce inteligente</h3>
        <p>Transforme dados de preços em decisões acionáveis com a Artemis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Efeito de balões
    if st.button("🎉 Celebrar!", key="celebrate"):
        st.balloons()
        log_user_action(logger, "Celebração ativada")


def display_stats_cards(stats):
    """Exibe cards de estatísticas"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <h3>📦</h3>
            <h2>{stats['total_products']}</h2>
            <p>Produtos Monitorados</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <h3>🔔</h3>
            <h2>{stats['active_alerts']}</h2>
            <p>Alertas Ativos</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <h3>📊</h3>
            <h2>{stats['products_with_history']}</h2>
            <p>Com Histórico</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <h3>🏷️</h3>
            <h2>{stats['products_with_tags']}</h2>
            <p>Com Tags</p>
        </div>
        """, unsafe_allow_html=True)


def display_coverage_chart(stats):
    """Exibe gráfico de cobertura de dados"""
    if stats['total_products'] > 0:
        coverage_data = {
            'Categoria': ['Com Histórico', 'Sem Histórico'],
            'Quantidade': [
                stats['products_with_history'],
                stats['total_products'] - stats['products_with_history']
            ]
        }
        
        fig = px.pie(
            coverage_data,
            values='Quantidade',
            names='Categoria',
            title='📈 Cobertura de Dados de Preços',
            color_discrete_map={
                'Com Histórico': '#28a745',
                'Sem Histórico': '#dc3545'
            }
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)


def display_quick_actions():
    """Exibe ações rápidas"""
    st.subheader("🚀 Ações Rápidas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Pesquisar Produto", key="quick_search", use_container_width=True):
            st.switch_page("pages/1_🔎_Pesquisar_e_Adicionar_Produto.py")
            log_user_action(logger, "Navegação para pesquisa rápida")
    
    with col2:
        if st.button("📊 Ver Dashboard", key="quick_dashboard", use_container_width=True):
            st.switch_page("pages/2_📊_Dashboard_de_Análise.py")
            log_user_action(logger, "Navegação para dashboard")
    
    with col3:
        if st.button("⚔️ Comparar Produtos", key="quick_compare", use_container_width=True):
            st.switch_page("pages/3_⚔️_Comparador_Inteligente.py")
            log_user_action(logger, "Navegação para comparador")


def display_tour_section():
    """Exibe tour guiado das funcionalidades"""
    st.subheader("🎯 Tour Guiado - Conheça as Funcionalidades")
    
    with st.expander("🔍 1. Pesquisar e Adicionar Produtos", expanded=False):
        st.markdown("""
        <div class="feature-card">
            <h4>🔍 Pesquisa Inteligente</h4>
            <p>• Use linguagem natural para buscar produtos</p>
            <p>• IA simula buscas em e-commerces brasileiros</p>
            <p>• Receba ofertas estruturadas com scores de relevância</p>
            <p>• Adicione produtos para monitoramento automático</p>
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("📊 2. Dashboard de Análise", expanded=False):
        st.markdown("""
        <div class="feature-card">
            <h4>📊 Análise Preditiva</h4>
            <p>• Visualize histórico de preços com gráficos interativos</p>
            <p>• Receba resumos inteligentes e análise de sentimento</p>
            <p>• Chatbot contextual com memória de conversa</p>
            <p>• Insights preditivos com forecasts de preços</p>
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("⚔️ 3. Comparador Inteligente", expanded=False):
        st.markdown("""
        <div class="feature-card">
            <h4>⚔️ Comparação Avançada</h4>
            <p>• Compare até 5 produtos lado a lado</p>
            <p>• Recomendações personalizadas baseadas no seu foco</p>
            <p>• Análise de custo-benefício detalhada</p>
            <p>• Histórico de comparações salvas</p>
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("🔔 4. Alertas e Notificações", expanded=False):
        st.markdown("""
        <div class="feature-card">
            <h4>🔔 Alertas Proativos</h4>
            <p>• Configure thresholds inteligentes sugeridos pela IA</p>
            <p>• Notificações por email quando preços caem</p>
            <p>• Dashboard de alertas pendentes</p>
            <p>• Simulação de alertas para testes</p>
        </div>
        """, unsafe_allow_html=True)


def display_recent_alerts():
    """Exibe alertas recentes"""
    try:
        db = SessionLocal()
        with DatabaseTransaction(db) as db_manager:
            triggered_alerts = db_manager.check_price_alerts()
            
            if triggered_alerts:
                st.subheader("🚨 Alertas Ativos")
                
                for alert in triggered_alerts[:3]:  # Mostrar apenas 3 mais recentes
                    savings = alert['threshold_price'] - alert['current_price']
                    
                    st.markdown(f"""
                    <div class="alert-banner">
                        <h4>🎯 {alert['product_name']}</h4>
                        <p><strong>Preço Atual:</strong> {format_currency(alert['current_price'])}</p>
                        <p><strong>Threshold:</strong> {format_currency(alert['threshold_price'])}</p>
                        <p><strong>💰 Economia:</strong> {format_currency(savings)}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                if len(triggered_alerts) > 3:
                    st.info(f"E mais {len(triggered_alerts) - 3} alertas ativos. Acesse a página de Alertas para ver todos.")
            
    except Exception as e:
        logger.error(f"Erro ao verificar alertas: {str(e)}")


def display_ai_insights():
    """Exibe insights gerados pela IA"""
    st.subheader("🤖 Insights da Artemis")
    
    try:
        # Gerar insight geral sobre o sistema
        insight_prompt = f"""
        Você é Artemis, consultora de e-commerce. 
        
        Gere um insight breve e útil sobre monitoramento de preços para o usuário.
        Foque em dicas práticas para economizar e tomar melhores decisões de compra.
        
        Máximo 2 parágrafos, linguagem amigável e direta.
        """
        
        response = gemini_service._make_api_call(insight_prompt)
        insight = response.text.strip()
        
        st.info(f"💡 **Dica da Artemis:** {insight}")
        
    except Exception as e:
        logger.error(f"Erro ao gerar insight: {str(e)}")
        st.info("💡 **Dica da Artemis:** Monitore produtos que você compra regularmente para identificar padrões sazonais e melhores momentos para comprar.")


def main():
    """Função principal da página inicial"""
    try:
        # Inicializar sistema
        initialize_session_state()
        create_tables()
        # Configuração da IA (chave manual) na sidebar
        configure_ai_sidebar()
        
        # Header principal
        display_welcome_section()
        
        # Obter estatísticas
        stats = get_dashboard_stats()
        
        # Cards de estatísticas
        display_stats_cards(stats)
        
        # Gráfico de cobertura
        st.subheader("📈 Visão Geral dos Dados")
        display_coverage_chart(stats)
        
        # Ações rápidas
        display_quick_actions()
        
        # Alertas recentes
        display_recent_alerts()
        
        # Tour guiado
        display_tour_section()
        
        # Insights da IA
        display_ai_insights()
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666; padding: 2rem;">
            <p>🚀 <strong>PriceTrack AI</strong> - Transformando dados em decisões inteligentes</p>
            <p>Desenvolvido com ❤️ usando Streamlit e Google Gemini AI</p>
        </div>
        """, unsafe_allow_html=True)
        
        logger.info("Página inicial carregada com sucesso")
        
    except Exception as e:
        logger.error(f"Erro na página inicial: {str(e)}")
        st.error("Erro ao carregar a página inicial. Verifique os logs para mais detalhes.")


if __name__ == "__main__":
    main()
