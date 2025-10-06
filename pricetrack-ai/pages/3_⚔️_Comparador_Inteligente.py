"""
⚔️ Comparador Inteligente - PriceTrack AI
Comparação avançada de produtos com recomendações personalizadas
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from core.logger import get_logger, log_user_action
from core.models import create_tables, SessionLocal
from core.database import DatabaseManager, DatabaseTransaction
from core.ai_services import compare_products_list
from core.utils import (
    format_currency, format_percentage, get_price_trend_icon,
    get_recommendation_color, create_price_chart_data
)

# Configurar página
st.set_page_config(
    page_title="Comparador - PriceTrack AI",
    page_icon="⚔️",
    layout="wide"
)

logger = get_logger(__name__)


def initialize_comparison_state():
    """Inicializa estado da comparação"""
    if 'comparison_history' not in st.session_state:
        st.session_state.comparison_history = []
    if 'selected_products' not in st.session_state:
        st.session_state.selected_products = []


def display_product_selector():
    """Exibe seletor de produtos para comparação"""
    st.header("⚔️ Comparador Inteligente")
    st.markdown("Compare produtos lado a lado e receba recomendações personalizadas")
    
    try:
        db = SessionLocal()
        with DatabaseTransaction(db) as db_manager:
            products = db_manager.get_all_products()
            
            if len(products) < 2:
                st.warning("É necessário ter pelo menos 2 produtos para comparação. Adicione mais produtos primeiro!")
                return []
            
            # Seletor múltiplo de produtos
            product_options = {f"{p.product_name} (ID: {p.id})": p for p in products}
            
            selected_names = st.multiselect(
                "Selecione produtos para comparar (mínimo 2, máximo 5):",
                options=list(product_options.keys()),
                default=st.session_state.selected_products,
                help="Escolha entre 2 e 5 produtos para comparação detalhada"
            )
            
            # Converter nomes selecionados em produtos
            selected_products = [product_options[name] for name in selected_names]
            
            # Validar seleção
            if len(selected_products) < 2:
                st.info("Selecione pelo menos 2 produtos para comparação")
                return []
            
            if len(selected_products) > 5:
                st.warning("Máximo de 5 produtos permitidos. Selecionando apenas os primeiros 5.")
                selected_products = selected_products[:5]
            
            st.session_state.selected_products = selected_names
            
            log_user_action(logger, f"Produtos selecionados para comparação: {len(selected_products)}")
            return selected_products
            
    except Exception as e:
        logger.error(f"Erro ao carregar produtos: {str(e)}")
        st.error("Erro ao carregar produtos.")
        return []


def display_user_focus_input():
    """Exibe input para foco do usuário"""
    st.subheader("🎯 Seu Foco na Comparação")
    
    focus_options = [
        "Melhor custo-benefício",
        "Maior qualidade",
        "Menor preço",
        "Melhor para trabalho",
        "Melhor para jogos",
        "Melhor para estudantes",
        "Mais durável",
        "Mais moderno",
        "Análise geral"
    ]
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_focus = st.selectbox(
            "Foco principal:",
            options=focus_options,
            help="Isso ajudará a Artemis a personalizar as recomendações"
        )
    
    with col2:
        custom_focus = st.text_area(
            "Foco personalizado (opcional):",
            placeholder="Ex: Preciso de algo para edição de vídeo, com boa autonomia de bateria e que não seja muito pesado...",
            help="Descreva suas necessidades específicas para recomendações mais precisas"
        )
    
    # Combinar foco selecionado com personalizado
    final_focus = selected_focus
    if custom_focus.strip():
        final_focus = f"{selected_focus}. {custom_focus}"
    
    return final_focus


def display_comparison_table(products):
    """Exibe tabela comparativa básica"""
    st.subheader("📊 Comparação Rápida")
    
    # Preparar dados da tabela
    comparison_data = []
    
    for product in products:
        # Preço atual
        current_price = "N/A"
        if product.price_history:
            latest_price = max(product.price_history, key=lambda x: x.get("date", ""))
            current_price = format_currency(latest_price["price"])
        
        # Threshold
        threshold = format_currency(product.alert_threshold) if product.alert_threshold else "N/A"
        
        # Tags
        tags = product.tags or "Sem tags"
        
        # Rating
        rating = "⭐" * product.user_rating if product.user_rating else "N/A"
        
        comparison_data.append({
            "Produto": product.product_name,
            "Preço Atual": current_price,
            "Threshold": threshold,
            "Tags": tags[:50] + "..." if len(tags) > 50 else tags,
            "Rating": rating
        })
    
    # Exibir tabela
    st.dataframe(
        comparison_data,
        use_container_width=True,
        hide_index=True
    )


def display_price_comparison_chart(products):
    """Exibe gráfico comparativo de preços"""
    if len(products) < 2:
        return
    
    st.subheader("📈 Comparação de Preços")
    
    # Preparar dados para o gráfico
    fig = go.Figure()
    
    colors = px.colors.qualitative.Set3
    
    for i, product in enumerate(products):
        if product.price_history:
            chart_data = create_price_chart_data(product.price_history)
            
            if chart_data['dates'] and chart_data['prices']:
                fig.add_trace(go.Scatter(
                    x=chart_data['dates'],
                    y=chart_data['prices'],
                    mode='lines+markers',
                    name=product.product_name[:30] + "..." if len(product.product_name) > 30 else product.product_name,
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=6)
                ))
    
    if fig.data:
        fig.update_layout(
            title="Evolução de Preços Comparativa",
            xaxis_title="Data",
            yaxis_title="Preço (R$)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Dados de preços insuficientes para gráfico comparativo")


def display_ai_comparison(products, user_focus):
    """Exibe comparação inteligente da IA"""
    st.subheader("🤖 Análise Inteligente da Artemis")
    
    if len(products) < 2:
        st.warning("Selecione pelo menos 2 produtos para análise")
        return
    
    with st.spinner("Artemis está analisando os produtos..."):
        try:
            product_names = [p.product_name for p in products]
            comparison_text = compare_products_list(product_names, user_focus)
            
            # Exibir resultado em markdown
            st.markdown(comparison_text)
            
            # Salvar no histórico
            comparison_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "products": product_names,
                "focus": user_focus,
                "result": comparison_text
            }
            
            st.session_state.comparison_history.append(comparison_entry)
            
            log_user_action(logger, f"Comparação realizada: {len(products)} produtos")
            
        except Exception as e:
            logger.error(f"Erro na comparação IA: {str(e)}")
            st.error("Erro na análise inteligente. Tente novamente.")


def display_comparison_history():
    """Exibe histórico de comparações"""
    if not st.session_state.comparison_history:
        return
    
    st.subheader("📚 Histórico de Comparações")
    
    # Mostrar últimas 5 comparações
    recent_comparisons = st.session_state.comparison_history[-5:]
    
    for i, comparison in enumerate(reversed(recent_comparisons)):
        with st.expander(f"Comparação {len(recent_comparisons) - i} - {comparison['timestamp']}"):
            st.markdown(f"**Produtos:** {', '.join(comparison['products'])}")
            st.markdown(f"**Foco:** {comparison['focus']}")
            
            if st.button(f"Ver Detalhes", key=f"view_{i}"):
                st.markdown(comparison['result'])


def display_recommendation_summary(products, user_focus):
    """Exibe resumo de recomendações"""
    st.subheader("🏆 Resumo de Recomendações")
    
    if len(products) < 2:
        return
    
    # Calcular métricas básicas
    recommendations = []
    
    for product in products:
        score = 0
        reasons = []
        
        # Preço atual
        if product.price_history:
            latest_price = max(product.price_history, key=lambda x: x.get("date", ""))
            current_price = latest_price["price"]
            
            # Comparar com outros produtos
            other_prices = []
            for other in products:
                if other != product and other.price_history:
                    other_latest = max(other.price_history, key=lambda x: x.get("date", ""))
                    other_prices.append(other_latest["price"])
            
            if other_prices:
                avg_price = sum(other_prices) / len(other_prices)
                if current_price < avg_price * 0.9:  # 10% mais barato
                    score += 30
                    reasons.append("Preço competitivo")
                elif current_price > avg_price * 1.1:  # 10% mais caro
                    score -= 20
                    reasons.append("Preço elevado")
        
        # Tags e características
        if product.tags:
            score += 20
            reasons.append("Bem categorizado")
        
        # Rating do usuário
        if product.user_rating and product.user_rating >= 4:
            score += 25
            reasons.append("Bem avaliado")
        
        # Threshold configurado
        if product.alert_threshold and product.alert_threshold > 0:
            score += 15
            reasons.append("Monitoramento ativo")
        
        recommendations.append({
            "product": product,
            "score": score,
            "reasons": reasons
        })
    
    # Ordenar por score
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    # Exibir ranking
    for i, rec in enumerate(recommendations):
        rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}º"
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown(f"### {rank_emoji}")
            st.metric("Score", f"{rec['score']}/100")
        
        with col2:
            st.markdown(f"**{rec['product'].product_name}**")
            
            if rec['reasons']:
                st.markdown("**Pontos fortes:**")
                for reason in rec['reasons']:
                    st.write(f"• {reason}")
            else:
                st.write("Dados insuficientes para análise")


def display_sidebar_tips():
    """Exibe dicas na sidebar"""
    st.sidebar.header("💡 Dicas de Comparação")
    
    st.sidebar.markdown("""
    **🎯 Para melhores comparações:**
    
    • Selecione produtos similares
    • Seja específico no seu foco
    • Considere seu orçamento
    • Analise histórico de preços
    
    **📊 Interpretando resultados:**
    
    • Score alto = Melhor para seu foco
    • Tendência de preços = Padrões sazonais
    • Recomendações = Baseadas em IA
    
    **⚔️ Estratégias de compra:**
    
    • Aguarde quedas de preço
    • Compare em diferentes lojas
    • Considere custo-benefício
    • Monitore alertas ativos
    """)


def main():
    """Função principal do comparador"""
    try:
        # Inicializar
        create_tables()
        initialize_comparison_state()
        
        # Dicas na sidebar
        display_sidebar_tips()
        
        # Seletor de produtos
        products = display_product_selector()
        
        if not products:
            return
        
        # Input de foco
        user_focus = display_user_focus_input()
        
        st.divider()
        
        # Comparação rápida
        display_comparison_table(products)
        
        st.divider()
        
        # Gráfico de preços
        display_price_comparison_chart(products)
        
        st.divider()
        
        # Análise da IA
        display_ai_comparison(products, user_focus)
        
        st.divider()
        
        # Resumo de recomendações
        display_recommendation_summary(products, user_focus)
        
        st.divider()
        
        # Histórico
        display_comparison_history()
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666;">
            <p>⚔️ <strong>Comparação Inteligente</strong> - Decisões baseadas em dados</p>
        </div>
        """, unsafe_allow_html=True)
        
        logger.info("Comparador carregado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro no comparador: {str(e)}")
        st.error("Erro ao carregar comparador. Verifique os logs para mais detalhes.")


if __name__ == "__main__":
    main()
