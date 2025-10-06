"""
📊 Dashboard de Análise - PriceTrack AI
Hub inteligente com visualizações, resumos e chatbot
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from core.logger import get_logger, log_user_action
from core.models import create_tables, SessionLocal
from core.database import DatabaseManager, DatabaseTransaction
from core.ai_services import generate_summary, analyze_reviews, analyze_offer, ask_question
from core.utils import (
    format_currency, format_percentage, get_price_trend_icon,
    get_recommendation_color, create_price_chart_data,
    get_product_status, format_completeness_score
)

# Configurar página
st.set_page_config(
    page_title="Dashboard - PriceTrack AI",
    page_icon="📊",
    layout="wide"
)

logger = get_logger(__name__)


def initialize_chat_state():
    """Inicializa estado do chat"""
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'current_product' not in st.session_state:
        st.session_state.current_product = None


def display_product_selector():
    """Exibe seletor de produtos"""
    st.header("📊 Dashboard de Análise")
    
    try:
        db = SessionLocal()
        with DatabaseTransaction(db) as db_manager:
            products = db_manager.get_all_products()
            
            if not products:
                st.warning("Nenhum produto encontrado. Adicione produtos primeiro!")
                return None
            
            # Seletor de produtos
            product_names = [f"{p.product_name} (ID: {p.id})" for p in products]
            selected_index = st.selectbox(
                "Selecione um produto para análise:",
                range(len(product_names)),
                format_func=lambda x: product_names[x]
            )
            
            selected_product = products[selected_index]
            st.session_state.current_product = selected_product
            
            log_user_action(logger, f"Produto selecionado: {selected_product.product_name}")
            return selected_product
            
    except Exception as e:
        logger.error(f"Erro ao carregar produtos: {str(e)}")
        st.error("Erro ao carregar produtos.")
        return None


def display_product_overview(product):
    """Exibe overview do produto"""
    st.subheader(f"📦 {product.product_name}")
    
    # Status do produto
    status = get_product_status(product)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Status",
            format_completeness_score(status['completeness_score']),
            delta=None
        )
    
    with col2:
        if product.price_history:
            latest_price = max(product.price_history, key=lambda x: x.get("date", ""))
            st.metric("Preço Atual", format_currency(latest_price["price"]))
        else:
            st.metric("Preço Atual", "N/A")
    
    with col3:
        if product.alert_threshold and product.alert_threshold > 0:
            st.metric("Threshold", format_currency(product.alert_threshold))
        else:
            st.metric("Threshold", "N/A")
    
    with col4:
        if product.user_rating:
            stars = "⭐" * product.user_rating
            st.metric("Rating", stars)
        else:
            st.metric("Rating", "N/A")


def display_price_chart(product):
    """Exibe gráfico de preços"""
    if not product.price_history:
        st.info("📈 Histórico de preços não disponível")
        return
    
    st.subheader("📈 Histórico de Preços")
    
    # Preparar dados
    chart_data = create_price_chart_data(product.price_history)
    
    if not chart_data['dates']:
        st.info("Dados insuficientes para gráfico")
        return
    
    # Criar gráfico
    fig = go.Figure()
    
    # Linha de preços
    fig.add_trace(go.Scatter(
        x=chart_data['dates'],
        y=chart_data['prices'],
        mode='lines+markers',
        name='Preço',
        line=dict(color='#667eea', width=3),
        marker=dict(size=8)
    ))
    
    # Linha de tendência
    if len(chart_data['trend']) > 1:
        fig.add_trace(go.Scatter(
            x=chart_data['dates'],
            y=chart_data['trend'],
            mode='lines',
            name='Tendência',
            line=dict(color='#ff6b6b', width=2, dash='dash')
        ))
    
    # Configurar layout
    fig.update_layout(
        title="Evolução do Preço",
        xaxis_title="Data",
        yaxis_title="Preço (R$)",
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Estatísticas do gráfico
    if len(chart_data['prices']) >= 2:
        first_price = chart_data['prices'][0]
        last_price = chart_data['prices'][-1]
        change = last_price - first_price
        change_pct = (change / first_price) * 100 if first_price > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Preço Inicial", format_currency(first_price))
        with col2:
            st.metric("Preço Atual", format_currency(last_price))
        with col3:
            icon = get_price_trend_icon(change_pct)
            st.metric(
                "Variação",
                f"{icon} {format_percentage(change_pct)}",
                delta=f"{format_currency(change)}"
            )


def display_ai_analysis_tabs(product):
    """Exibe abas com análises da IA"""
    tab1, tab2, tab3 = st.tabs(["🤖 Resumo Inteligente", "⭐ Análise de Reviews", "🎯 Avaliação de Oferta"])
    
    with tab1:
        st.subheader("🤖 Resumo Inteligente")
        
        with st.spinner("Artemis está analisando..."):
            try:
                summary = generate_summary(product.product_name)
                st.markdown(summary)
                
                log_user_action(logger, f"Resumo gerado para: {product.product_name}")
                
            except Exception as e:
                logger.error(f"Erro ao gerar resumo: {str(e)}")
                st.error("Erro ao gerar resumo. Tente novamente.")
    
    with tab2:
        st.subheader("⭐ Análise de Reviews")
        
        with st.spinner("Analisando sentimento..."):
            try:
                review_data = analyze_reviews(product.product_name)
                
                # Score de sentimento
                sentiment_score = review_data.get('score_sentimento', 0)
                sentiment_color = "green" if sentiment_score > 0.3 else "red" if sentiment_score < -0.3 else "orange"
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.metric(
                        "Score Sentimento",
                        f"{sentiment_score:.2f}",
                        delta="Positivo" if sentiment_score > 0 else "Negativo"
                    )
                
                with col2:
                    st.metric("Total Reviews", review_data.get('total_reviews', 0))
                
                # Resumo
                st.markdown("**Resumo:**")
                st.write(review_data.get('summary', 'Análise não disponível'))
                
                # Prós e contras
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**✅ Pontos Positivos:**")
                    for pro in review_data.get('pros', []):
                        st.write(f"• {pro}")
                
                with col2:
                    st.markdown("**❌ Pontos Negativos:**")
                    for con in review_data.get('cons', []):
                        st.write(f"• {con}")
                
                log_user_action(logger, f"Análise de reviews para: {product.product_name}")
                
            except Exception as e:
                logger.error(f"Erro na análise de reviews: {str(e)}")
                st.error("Erro na análise de reviews. Tente novamente.")
    
    with tab3:
        st.subheader("🎯 Avaliação de Oferta")
        
        if not product.price_history:
            st.info("Histórico de preços necessário para análise de oferta")
            return
        
        with st.spinner("Avaliando qualidade da oferta..."):
            try:
                latest_price = max(product.price_history, key=lambda x: x.get("date", ""))
                current_price = latest_price["price"]
                
                analysis = analyze_offer(product.price_history, current_price)
                
                # Nota da oferta
                nota = analysis.get('nota', 5.0)
                recomendacao = analysis.get('recomendacao', 'AGUARDAR')
                cor = get_recommendation_color(recomendacao)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Nota da Oferta", f"{nota:.1f}/10")
                
                with col2:
                    st.markdown(f"""
                    <div style="background-color: {cor}; color: white; padding: 10px; border-radius: 5px; text-align: center;">
                        <strong>{recomendacao.replace('_', ' ')}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.metric("Confiança", f"{analysis.get('confianca', 0):.1%}")
                
                # Justificativa
                st.markdown("**Justificativa:**")
                st.write(analysis.get('justificativa', 'Análise não disponível'))
                
                # Previsão
                st.markdown("**Previsão:**")
                st.write(analysis.get('previsao', 'Previsão não disponível'))
                
                dias_mudanca = analysis.get('dias_para_mudanca', 0)
                if dias_mudanca > 0:
                    st.info(f"⏰ Estimativa de mudança: {dias_mudanca} dias")
                
                log_user_action(logger, f"Análise de oferta para: {product.product_name}")
                
            except Exception as e:
                logger.error(f"Erro na análise de oferta: {str(e)}")
                st.error("Erro na análise de oferta. Tente novamente.")


def display_chatbot_section(product):
    """Exibe seção do chatbot"""
    st.subheader("💬 Pergunte à Artemis")
    st.markdown("Faça perguntas sobre o produto e receba respostas inteligentes")
    
    # Inicializar chat se necessário
    if st.session_state.current_product != product:
        st.session_state.chat_messages = []
        st.session_state.current_product = product
    
    # Exibir histórico de mensagens
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Input do usuário
    if question := st.chat_input("Digite sua pergunta sobre o produto..."):
        # Adicionar pergunta do usuário
        st.session_state.chat_messages.append({"role": "user", "content": question})
        
        with st.chat_message("user"):
            st.write(question)
        
        # Gerar resposta da IA
        with st.chat_message("assistant"):
            with st.spinner("Artemis está pensando..."):
                try:
                    answer = ask_question(product.product_name, question)
                    
                    # Adicionar resposta ao histórico
                    st.session_state.chat_messages.append({"role": "assistant", "content": answer})
                    
                    st.write(answer)
                    
                    log_user_action(logger, f"Pergunta feita sobre {product.product_name}: {question[:50]}...")
                    
                except Exception as e:
                    logger.error(f"Erro no chatbot: {str(e)}")
                    st.error("Erro ao processar pergunta. Tente novamente.")
    
    # Botão para limpar chat
    if st.button("🗑️ Limpar Conversa"):
        st.session_state.chat_messages = []
        st.rerun()


def display_predictive_insights(product):
    """Exibe insights preditivos"""
    st.subheader("🔮 Insights Preditivos")
    
    try:
        db = SessionLocal()
        with DatabaseTransaction(db) as db_manager:
            trend_data = db_manager.get_price_trend(product.id, days=7)
            
            if trend_data['days_analyzed'] >= 2:
                trend_pct = trend_data['percentage']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric(
                        "Tendência 7 dias",
                        f"{format_percentage(trend_pct)}",
                        delta=f"{format_currency(trend_data['trend'])}"
                    )
                
                with col2:
                    if trend_pct < -5:
                        prediction = "📉 Preço pode continuar caindo"
                        color = "green"
                    elif trend_pct < 0:
                        prediction = "↘️ Leve queda esperada"
                        color = "lightgreen"
                    elif trend_pct > 5:
                        prediction = "📈 Preço pode subir"
                        color = "red"
                    else:
                        prediction = "➡️ Preço estável"
                        color = "gray"
                    
                    st.markdown(f"""
                    <div style="background-color: {color}; padding: 10px; border-radius: 5px;">
                        <strong>Previsão:</strong> {prediction}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Sugestão de threshold
                if not product.alert_threshold or product.alert_threshold == 0:
                    st.info("💡 Configure um threshold de alerta para receber notificações quando o preço cair!")
                    
                    if st.button("🎯 Sugerir Threshold"):
                        with st.spinner("Calculando threshold ideal..."):
                            try:
                                from core.ai_services import suggest_threshold
                                suggested = suggest_threshold(product.product_name)
                                st.success(f"Threshold sugerido: {format_currency(suggested)}")
                                
                                # Atualizar produto
                                from core.models import ProductUpdate
                                update_data = ProductUpdate(alert_threshold=suggested)
                                db_manager.update_product(product.id, update_data)
                                
                                st.rerun()
                                
                            except Exception as e:
                                logger.error(f"Erro ao sugerir threshold: {str(e)}")
                                st.error("Erro ao calcular threshold")
            else:
                st.info("📊 Mais dados de preços são necessários para insights preditivos")
                
    except Exception as e:
        logger.error(f"Erro nos insights preditivos: {str(e)}")
        st.error("Erro ao calcular insights preditivos")


def main():
    """Função principal do dashboard"""
    try:
        # Inicializar
        create_tables()
        initialize_chat_state()
        
        # Seletor de produtos
        product = display_product_selector()
        
        if not product:
            return
        
        # Overview do produto
        display_product_overview(product)
        
        st.divider()
        
        # Gráfico de preços
        display_price_chart(product)
        
        st.divider()
        
        # Análises da IA
        display_ai_analysis_tabs(product)
        
        st.divider()
        
        # Chatbot
        display_chatbot_section(product)
        
        st.divider()
        
        # Insights preditivos
        display_predictive_insights(product)
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666;">
            <p>🤖 <strong>Artemis</strong> - Sua consultora de e-commerce inteligente</p>
        </div>
        """, unsafe_allow_html=True)
        
        logger.info("Dashboard carregado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro no dashboard: {str(e)}")
        st.error("Erro ao carregar dashboard. Verifique os logs para mais detalhes.")


if __name__ == "__main__":
    main()
