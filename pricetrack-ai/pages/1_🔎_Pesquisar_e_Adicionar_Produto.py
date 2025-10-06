"""
🔍 Página de Pesquisa e Adição de Produtos
Funcionalidades avançadas de busca e monitoramento
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from core.logger import get_logger, log_user_action
from core.models import create_tables, SessionLocal, ProductCreate, AlertCreate
from core.database import DatabaseManager, DatabaseTransaction
from core.ai_services import search_products, generate_tags, suggest_threshold
from core.utils import (
    validate_product_name, validate_price, validate_budget,
    format_currency, format_percentage, parse_tags
)

# Async helpers
import asyncio
from typing import Tuple

# Configurar página
st.set_page_config(
    page_title="Pesquisar Produtos - PriceTrack AI",
    page_icon="🔍",
    layout="wide"
)

logger = get_logger(__name__)


def display_search_section():
    """Exibe seção de pesquisa de produtos"""
    st.header("🔍 Pesquisar Produtos")
    st.markdown("Use linguagem natural para buscar produtos em e-commerces brasileiros")
    
    # Input de pesquisa
    search_query = st.text_input(
        "Digite o nome ou descrição do produto:",
        placeholder="Ex: iPhone 15 Pro Max 256GB, notebook gamer RTX 4060, fone bluetooth..."
    )
    
    if search_query:
        log_user_action(logger, f"Pesquisa iniciada: {search_query}")
        
        with st.spinner("🔍 Artemis está pesquisando..."):
            try:
                # Buscar produtos usando IA
                products = search_products(search_query)
                
                if products:
                    st.success(f"✅ Encontrados {len(products)} produtos!")
                    
                    # Exibir resultados
                    for i, product in enumerate(products):
                        with st.container():
                            col1, col2, col3 = st.columns([3, 1, 1])
                            
                            with col1:
                                st.markdown(f"""
                                **{product['name']}**
                                
                                📍 {product['store']} | 📝 {product['description']}
                                
                                🏷️ Disponibilidade: {product['availability']}
                                """)
                            
                            with col2:
                                st.metric(
                                    "Preço",
                                    format_currency(product['price']),
                                    delta=None
                                )
                            
                            with col3:
                                # Score de relevância
                                score = product.get('score', 0.5)
                                score_color = "green" if score >= 0.7 else "orange" if score >= 0.5 else "red"
                                
                                st.markdown(f"""
                                <div style="text-align: center;">
                                    <h4 style="color: {score_color};">{score:.1f}</h4>
                                    <p>Score</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Botão para adicionar
                            if st.button(f"➕ Adicionar ao Monitoramento", key=f"add_{i}"):
                                add_product_to_monitoring(product)
                            
                            st.divider()
                
                else:
                    st.warning("Nenhum produto encontrado. Tente uma busca mais específica.")
                    
            except Exception as e:
                logger.error(f"Erro na pesquisa: {str(e)}")
                st.error("Erro ao pesquisar produtos. Tente novamente.")


def add_product_to_monitoring(product_data):
    """Adiciona produto ao monitoramento"""
    try:
        # Validar dados do produto
        product_name = validate_product_name(product_data['name'])
        price = validate_price(product_data['price'])
        
        # Verificar se produto já existe
        db = SessionLocal()
        with DatabaseTransaction(db) as db_manager:
            existing_product = db_manager.get_product_by_name(product_name)
            
            if existing_product:
                st.warning(f"Produto '{product_name}' já está sendo monitorado!")
                return
            
            # Executar geração de tags e threshold em paralelo usando threads via asyncio
            async def _gen_tags_and_threshold(name: str, current_price: float) -> Tuple[str, float]:
                tags_task = asyncio.to_thread(generate_tags, name)
                thr_task = asyncio.to_thread(suggest_threshold, name, current_price * 0.8)
                return await asyncio.gather(tags_task, thr_task)

            def _run_async(coro):
                try:
                    return asyncio.run(coro)
                except RuntimeError:
                    # Caso já exista um loop ativo, use um novo loop isolado
                    loop = asyncio.new_event_loop()
                    try:
                        return loop.run_until_complete(coro)
                    finally:
                        loop.close()

            with st.status("Processando IA (tags e threshold)...", expanded=False) as status:
                try:
                    tags, suggested_threshold = _run_async(_gen_tags_and_threshold(product_name, price))
                    status.update(label="IA concluída", state="complete")
                except Exception as e:
                    status.update(label="Falha ao processar IA", state="error")
                    logger.error(f"Falha concurrente (tags/threshold) para '{product_name}': {type(e).__name__}: {e}")
                    # Fallback síncrono individual
                    with st.spinner("🏷️ Gerando tags..."):
                        tags = generate_tags(product_name)
                    with st.spinner("🎯 Calculando threshold ideal..."):
                        suggested_threshold = suggest_threshold(product_name, price * 0.8)
            
            # Criar produto
            product_create = ProductCreate(
                product_name=product_name,
                tags=tags,
                alert_threshold=suggested_threshold,
                user_rating=None
            )
            
            new_product = db_manager.create_product(product_create)
            
            # Adicionar preço inicial ao histórico
            db_manager.update_price_history(new_product.id, price)
            
            st.success(f"✅ Produto '{product_name}' adicionado com sucesso!")
            st.info(f"🏷️ Tags: {tags}")
            st.info(f"🎯 Threshold sugerido: {format_currency(suggested_threshold)}")
            
            log_user_action(logger, f"Produto adicionado: {product_name}")
            
    except Exception as e:
        logger.error(f"Erro ao adicionar produto: {type(e).__name__}: {e}")
        st.error(f"Erro ao adicionar produto: {type(e).__name__}: {e}")


def display_manual_add_section():
    """Exibe seção para adição manual de produtos"""
    st.header("➕ Adicionar Produto Manualmente")
    st.markdown("Adicione produtos diretamente sem pesquisa")
    
    with st.form("add_product_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            product_name = st.text_input(
                "Nome do Produto:",
                placeholder="Ex: Samsung Galaxy S24 Ultra"
            )
            
            current_price = st.text_input(
                "Preço Atual (R$):",
                placeholder="Ex: 2999.90"
            )
        
        with col2:
            budget = st.text_input(
                "Orçamento (R$) - Opcional:",
                placeholder="Ex: 2500.00"
            )
            
            custom_tags = st.text_input(
                "Tags Personalizadas (separadas por vírgula):",
                placeholder="Ex: smartphone, android, 256gb"
            )
        
        submitted = st.form_submit_button("➕ Adicionar Produto", use_container_width=True)
        
        if submitted:
            try:
                # Validar inputs
                if not product_name:
                    st.error("Nome do produto é obrigatório!")
                    return
                
                # Validar preço
                try:
                    price = validate_price(current_price)
                except Exception as e:
                    st.error(f"Preço inválido: {e}")
                    return
                
                # Validar orçamento
                budget_value = validate_budget(budget) if budget else None
                
                # Verificar se produto já existe
                db = SessionLocal()
                with DatabaseTransaction(db) as db_manager:
                    existing_product = db_manager.get_product_by_name(product_name)
                    
                    if existing_product:
                        st.warning(f"Produto '{product_name}' já está sendo monitorado!")
                        return
                    
                    # Gerar tags se não fornecidas
                    if not custom_tags:
                        # Paralelizar com threshold se possível
                        async def _gen_tags_and_threshold(name: str, budget_or_price: float):
                            tags_task = asyncio.to_thread(generate_tags, name)
                            thr_task = asyncio.to_thread(suggest_threshold, name, budget_or_price)
                            return await asyncio.gather(tags_task, thr_task)

                        def _run_async(coro):
                            try:
                                return asyncio.run(coro)
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                try:
                                    return loop.run_until_complete(coro)
                                finally:
                                    loop.close()

                        with st.status("Processando IA (tags e threshold)...", expanded=False) as status:
                            try:
                                tags, suggested_threshold = _run_async(_gen_tags_and_threshold(product_name, budget_value or price * 0.8))
                                status.update(label="IA concluída", state="complete")
                            except Exception as e:
                                status.update(label="Falha ao processar IA", state="error")
                                logger.error(f"Falha concurrente (tags/threshold) manual para '{product_name}': {type(e).__name__}: {e}")
                                # Fallback
                                with st.spinner("🏷️ Gerando tags..."):
                                    tags = generate_tags(product_name)
                                with st.spinner("🎯 Calculando threshold ideal..."):
                                    suggested_threshold = suggest_threshold(product_name, budget_value or price * 0.8)
                    else:
                        tags = custom_tags

                    # Se não veio do bloco acima (quando custom_tags fornecido), calcule threshold aqui
                    if custom_tags:
                        with st.spinner("🎯 Calculando threshold ideal..."):
                            suggested_threshold = suggest_threshold(product_name, budget_value or price * 0.8)
                    
                    # Criar produto
                    product_create = ProductCreate(
                        product_name=product_name,
                        tags=tags,
                        alert_threshold=suggested_threshold,
                        user_rating=None
                    )
                    
                    new_product = db_manager.create_product(product_create)
                    
                    # Adicionar preço inicial
                    db_manager.update_price_history(new_product.id, price)
                    
                    st.success(f"✅ Produto '{product_name}' adicionado com sucesso!")
                    
                    # Exibir detalhes
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.info(f"🏷️ Tags: {tags}")
                    with col2:
                        st.info(f"💰 Preço: {format_currency(price)}")
                    with col3:
                        st.info(f"🎯 Threshold: {format_currency(suggested_threshold)}")
                    
                    log_user_action(logger, f"Produto adicionado manualmente: {product_name}")
                    
            except Exception as e:
                logger.error(f"Erro ao adicionar produto manualmente: {type(e).__name__}: {e}")
                st.error(f"Erro ao adicionar produto: {type(e).__name__}: {e}")


def display_recent_additions():
    """Exibe produtos adicionados recentemente"""
    st.header("📋 Produtos Adicionados Recentemente")
    
    try:
        db = SessionLocal()
        with DatabaseTransaction(db) as db_manager:
            recent_products = db_manager.get_all_products(limit=10)
            
            if recent_products:
                for product in recent_products:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                        
                        with col1:
                            st.markdown(f"""
                            **{product.product_name}**
                            
                            🏷️ {product.tags or 'Sem tags'}
                            """)
                        
                        with col2:
                            if product.price_history:
                                latest_price = max(product.price_history, key=lambda x: x.get("date", ""))
                                st.metric("Preço", format_currency(latest_price["price"]))
                            else:
                                st.metric("Preço", "N/A")
                        
                        with col3:
                            if product.alert_threshold and product.alert_threshold > 0:
                                st.metric("Threshold", format_currency(product.alert_threshold))
                            else:
                                st.metric("Threshold", "N/A")
                        
                        with col4:
                            if st.button("📊 Ver", key=f"view_{product.id}"):
                                st.switch_page("pages/2_📊_Dashboard_de_Análise.py")
                                log_user_action(logger, f"Navegação para produto: {product.product_name}")
                        
                        st.divider()
            else:
                st.info("Nenhum produto adicionado ainda. Use a pesquisa acima para começar!")
                
    except Exception as e:
        logger.error(f"Erro ao carregar produtos recentes: {str(e)}")
        st.error("Erro ao carregar produtos recentes.")


def display_search_tips():
    """Exibe dicas de pesquisa"""
    st.sidebar.header("💡 Dicas de Pesquisa")
    
    st.sidebar.markdown("""
    **🔍 Para melhores resultados:**
    
    • Seja específico: "iPhone 15 Pro Max 256GB" vs "iPhone"
    • Inclua especificações: "notebook gamer RTX 4060"
    • Use termos técnicos: "SSD NVMe 1TB"
    • Experimente sinônimos: "fone bluetooth" ou "headphone sem fio"
    
    **📊 Score de Relevância:**
    
    • 🟢 0.7-1.0: Produto exato, marca conhecida
    • 🟡 0.5-0.7: Produto similar, boa qualidade
    • 🔴 0.0-0.5: Produto genérico ou irrelevante
    
    **🎯 Threshold de Alerta:**
    
    A Artemis sugere thresholds baseados em:
    • Tipo de produto
    • Preço atual
    • Seu orçamento (se fornecido)
    • Tendências de mercado
    """)


def main():
    """Função principal da página"""
    try:
        # Inicializar banco
        create_tables()
        
        # Header
        st.title("🔍 Pesquisar e Adicionar Produtos")
        st.markdown("Encontre produtos e configure monitoramento inteligente com a Artemis")
        
        # Dicas na sidebar
        display_search_tips()
        
        # Seções principais
        display_search_section()
        
        st.divider()
        
        display_manual_add_section()
        
        st.divider()
        
        display_recent_additions()
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666;">
            <p>💡 <strong>Dica:</strong> Produtos com tags e histórico de preços oferecem análises mais precisas!</p>
        </div>
        """, unsafe_allow_html=True)
        
        logger.info("Página de pesquisa carregada com sucesso")
        
    except Exception as e:
        logger.error(f"Erro na página de pesquisa: {str(e)}")
        st.error("Erro ao carregar a página. Verifique os logs para mais detalhes.")


if __name__ == "__main__":
    main()
