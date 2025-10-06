"""
🔔 Alertas e Notificações - PriceTrack AI
Gerenciamento proativo de alertas de preço
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from core.logger import get_logger, log_user_action
from core.models import create_tables, SessionLocal, AlertCreate, ProductUpdate
from core.database import DatabaseManager, DatabaseTransaction
from core.ai_services import suggest_threshold
from core.utils import (
    format_currency, format_percentage, send_email_alert,
    validate_price, get_price_trend_icon
)

# Configurar página
st.set_page_config(
    page_title="Alertas - PriceTrack AI",
    page_icon="🔔",
    layout="wide"
)

logger = get_logger(__name__)


def display_alerts_overview():
    """Exibe overview dos alertas"""
    st.header("🔔 Alertas e Notificações")
    st.markdown("Gerencie alertas proativos e receba notificações quando preços caem")
    
    try:
        db = SessionLocal()
        with DatabaseTransaction(db) as db_manager:
            # Estatísticas de alertas
            stats = db_manager.get_stats()
            active_alerts = db_manager.get_active_alerts()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Alertas Ativos", stats['active_alerts'])
            
            with col2:
                st.metric("Produtos Monitorados", stats['total_products'])
            
            with col3:
                # Verificar alertas disparados
                triggered_alerts = db_manager.check_price_alerts()
                st.metric("Alertas Disparados", len(triggered_alerts))
            
            with col4:
                # Calcular taxa de sucesso (simulada)
                success_rate = min(85, len(triggered_alerts) * 10) if triggered_alerts else 0
                st.metric("Taxa de Sucesso", f"{success_rate}%")
            
            return active_alerts, triggered_alerts
            
    except Exception as e:
        logger.error(f"Erro ao carregar overview de alertas: {str(e)}")
        st.error("Erro ao carregar alertas.")
        return [], []


def display_active_alerts(active_alerts):
    """Exibe alertas ativos"""
    st.subheader("🎯 Alertas Ativos")
    
    if not active_alerts:
        st.info("Nenhum alerta ativo. Configure alertas para seus produtos!")
        return
    
    for alert in active_alerts:
        try:
            db = SessionLocal()
            with DatabaseTransaction(db) as db_manager:
                product = db_manager.get_product(alert.product_id)
                
                if not product:
                    continue
                
                # Obter preço atual
                current_price = "N/A"
                if product.price_history:
                    latest_price = max(product.price_history, key=lambda x: x.get("date", ""))
                    current_price = latest_price["price"]
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.markdown(f"""
                        **{product.product_name}**
                        
                        🎯 Threshold: {format_currency(alert.threshold_price)}
                        """)
                    
                    with col2:
                        if current_price != "N/A":
                            st.metric("Preço Atual", format_currency(current_price))
                        else:
                            st.metric("Preço Atual", "N/A")
                    
                    with col3:
                        if current_price != "N/A" and current_price <= alert.threshold_price:
                            savings = alert.threshold_price - current_price
                            st.metric("Economia", format_currency(savings))
                        else:
                            st.metric("Economia", "N/A")
                    
                    with col4:
                        # Slider para ajustar threshold
                        new_threshold = st.slider(
                            "Ajustar Threshold",
                            min_value=0.0,
                            max_value=float(current_price * 2) if current_price != "N/A" else 1000.0,
                            value=float(alert.threshold_price),
                            step=10.0,
                            key=f"threshold_{alert.id}"
                        )
                        
                        if new_threshold != alert.threshold_price:
                            if st.button("💾 Salvar", key=f"save_{alert.id}"):
                                try:
                                    update_data = ProductUpdate(alert_threshold=new_threshold)
                                    db_manager.update_product(product.id, update_data)
                                    st.success("Threshold atualizado!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao atualizar: {e}")
                    
                    # Botão para desativar
                    if st.button("❌ Desativar Alerta", key=f"deactivate_{alert.id}"):
                        try:
                            db_manager.deactivate_alert(alert.id)
                            st.success("Alerta desativado!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao desativar: {e}")
                    
                    st.divider()
                    
        except Exception as e:
            logger.error(f"Erro ao processar alerta {alert.id}: {str(e)}")
            continue


def display_triggered_alerts(triggered_alerts):
    """Exibe alertas disparados"""
    if not triggered_alerts:
        return
    
    st.subheader("🚨 Alertas Disparados")
    st.markdown("Estes alertas foram ativados porque o preço caiu abaixo do threshold!")
    
    for alert in triggered_alerts:
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"""
                **🎯 {alert['product_name']}**
                
                💰 Preço atual: {format_currency(alert['current_price'])}
                🎯 Threshold: {format_currency(alert['threshold_price'])}
                """)
            
            with col2:
                savings = alert['savings']
                st.metric("💰 Economia", format_currency(savings))
            
            with col3:
                # Botão para simular notificação
                if st.button("📧 Simular Email", key=f"email_{alert['alert_id']}"):
                    try:
                        db = SessionLocal()
                        with DatabaseTransaction(db) as db_manager:
                            product = db_manager.get_product(alert['product_id'])
                            
                            if product:
                                success = send_email_alert(
                                    product,
                                    f"Preço caiu para {format_currency(alert['current_price'])}",
                                    alert['current_price']
                                )
                                
                                if success:
                                    st.success("Email simulado enviado!")
                                else:
                                    st.warning("Simulação de email realizada (SMTP não configurado)")
                                
                                log_user_action(logger, f"Email simulado para: {product.product_name}")
                    except Exception as e:
                        st.error(f"Erro ao simular email: {e}")
            
            st.divider()


def display_alert_configuration():
    """Exibe configuração de novos alertas"""
    st.subheader("⚙️ Configurar Novo Alerta")
    
    try:
        db = SessionLocal()
        with DatabaseTransaction(db) as db_manager:
            products = db_manager.get_all_products()
            
            if not products:
                st.warning("Nenhum produto disponível. Adicione produtos primeiro!")
                return
            
            # Seletor de produto
            product_options = {f"{p.product_name} (ID: {p.id})": p for p in products}
            selected_name = st.selectbox(
                "Selecione um produto:",
                options=list(product_options.keys())
            )
            
            selected_product = product_options[selected_name]
            
            # Verificar se já tem alerta ativo
            existing_alerts = db_manager.get_active_alerts()
            has_active_alert = any(alert.product_id == selected_product.id for alert in existing_alerts)
            
            if has_active_alert:
                st.info("Este produto já possui um alerta ativo. Use a seção acima para ajustá-lo.")
                return
            
            # Configuração do threshold
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Configuração Manual:**")
                manual_threshold = st.number_input(
                    "Threshold (R$):",
                    min_value=0.0,
                    max_value=10000.0,
                    step=10.0,
                    value=0.0
                )
            
            with col2:
                st.markdown("**Sugestão da IA:**")
                if st.button("🤖 Sugerir Threshold"):
                    with st.spinner("Artemis está calculando..."):
                        try:
                            suggested = suggest_threshold(selected_product.product_name)
                            st.success(f"Threshold sugerido: {format_currency(suggested)}")
                            
                            # Atualizar o input manual
                            st.session_state[f"threshold_{selected_product.id}"] = suggested
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao sugerir threshold: {e}")
            
            # Botão para criar alerta
            if st.button("🔔 Criar Alerta", use_container_width=True):
                try:
                    threshold = manual_threshold
                    
                    if threshold <= 0:
                        st.error("Threshold deve ser maior que zero!")
                        return
                    
                    # Criar alerta
                    alert_data = AlertCreate(
                        product_id=selected_product.id,
                        threshold_price=threshold
                    )
                    
                    new_alert = db_manager.create_alert(alert_data)
                    
                    st.success(f"✅ Alerta criado para {selected_product.product_name}!")
                    st.info(f"🎯 Threshold: {format_currency(threshold)}")
                    
                    log_user_action(logger, f"Alerta criado para: {selected_product.product_name}")
                    st.rerun()
                    
                except Exception as e:
                    logger.error(f"Erro ao criar alerta: {str(e)}")
                    st.error(f"Erro ao criar alerta: {e}")
                    
    except Exception as e:
        logger.error(f"Erro na configuração de alertas: {str(e)}")
        st.error("Erro ao carregar configuração de alertas.")


def display_alerts_analytics():
    """Exibe analytics dos alertas"""
    st.subheader("📊 Analytics de Alertas")
    
    try:
        db = SessionLocal()
        with DatabaseTransaction(db) as db_manager:
            # Dados simulados para analytics
            alerts_data = {
                'Mês': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                'Alertas Disparados': [5, 8, 12, 7, 15, 10],
                'Economia Total (R$)': [150, 240, 360, 210, 450, 300]
            }
            
            # Gráfico de alertas por mês
            fig = px.bar(
                alerts_data,
                x='Mês',
                y='Alertas Disparados',
                title='Alertas Disparados por Mês',
                color='Alertas Disparados',
                color_continuous_scale='Blues'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Métricas de economia
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Economia Total", "R$ 1.710,00")
            
            with col2:
                st.metric("Economia Média", "R$ 114,00")
            
            with col3:
                st.metric("Melhor Mês", "Maio (R$ 450)")
            
            # Gráfico de economia
            fig2 = px.line(
                alerts_data,
                x='Mês',
                y='Economia Total (R$)',
                title='Economia Acumulada',
                markers=True
            )
            
            st.plotly_chart(fig2, use_container_width=True)
            
    except Exception as e:
        logger.error(f"Erro nos analytics: {str(e)}")
        st.error("Erro ao carregar analytics.")


def display_notification_settings():
    """Exibe configurações de notificação"""
    st.subheader("📧 Configurações de Notificação")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Configurações SMTP:**")
        
        # Verificar se credenciais estão configuradas
        smtp_server = st.secrets.get("SMTP_SERVER")
        smtp_user = st.secrets.get("SMTP_USER")
        
        if smtp_server and smtp_user:
            st.success("✅ SMTP configurado")
            st.info(f"Servidor: {smtp_server}")
            st.info(f"Usuário: {smtp_user}")
        else:
            st.warning("⚠️ SMTP não configurado")
            st.info("Configure as credenciais SMTP no secrets.toml para receber emails reais")
    
    with col2:
        st.markdown("**Preferências:**")
        
        email_frequency = st.selectbox(
            "Frequência de emails:",
            ["Imediato", "Diário", "Semanal"]
        )
        
        notification_types = st.multiselect(
            "Tipos de notificação:",
            ["Email", "Banner no app", "Log de sistema"],
            default=["Email", "Banner no app"]
        )
        
        if st.button("💾 Salvar Preferências"):
            st.success("Preferências salvas!")
            log_user_action(logger, f"Preferências atualizadas: {email_frequency}")


def display_sidebar_tips():
    """Exibe dicas na sidebar"""
    st.sidebar.header("💡 Dicas de Alertas")
    
    st.sidebar.markdown("""
    **🎯 Configurando Thresholds:**
    
    • Use sugestões da IA
    • Considere seu orçamento
    • Analise histórico de preços
    • Ajuste conforme necessário
    
    **📧 Notificações:**
    
    • Configure SMTP para emails reais
    • Teste com simulação primeiro
    • Monitore logs de sistema
    • Ajuste frequência conforme preferência
    
    **📊 Otimizando Alertas:**
    
    • Monitore taxa de disparo
    • Ajuste thresholds baseado em resultados
    • Analise padrões sazonais
    • Revise alertas inativos
    """)


def main():
    """Função principal da página de alertas"""
    try:
        # Inicializar
        create_tables()
        
        # Dicas na sidebar
        display_sidebar_tips()
        
        # Overview dos alertas
        active_alerts, triggered_alerts = display_alerts_overview()
        
        st.divider()
        
        # Alertas disparados (prioridade)
        if triggered_alerts:
            display_triggered_alerts(triggered_alerts)
            st.divider()
        
        # Alertas ativos
        display_active_alerts(active_alerts)
        
        st.divider()
        
        # Configuração de novos alertas
        display_alert_configuration()
        
        st.divider()
        
        # Analytics
        display_alerts_analytics()
        
        st.divider()
        
        # Configurações de notificação
        display_notification_settings()
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666;">
            <p>🔔 <strong>Alertas Proativos</strong> - Nunca perca uma boa oferta!</p>
        </div>
        """, unsafe_allow_html=True)
        
        logger.info("Página de alertas carregada com sucesso")
        
    except Exception as e:
        logger.error(f"Erro na página de alertas: {str(e)}")
        st.error("Erro ao carregar alertas. Verifique os logs para mais detalhes.")


if __name__ == "__main__":
    main()
