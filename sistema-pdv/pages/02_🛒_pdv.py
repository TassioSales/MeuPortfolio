"""
Módulo de Ponto de Venda (PDV) do Sistema PDV
"""
import streamlit as st
import time
from datetime import datetime

# Importa os componentes necessários
from components.sidebar import render_sidebar
from modulos.venda import Venda, ItemVenda
from modulos.produto import Produto
from modulos.cliente import Cliente
from utils.helpers import format_currency
from utils.database import execute_query
from utils.logger import logger

# Configurações da página
st.set_page_config(
    page_title="PDV - Sistema PDV",
    page_icon="🛒",
    layout="wide"
)

def buscar_produto_por_codigo(codigo: str):
    """Busca um produto pelo código de barras ou nome."""
    try:
        # Tenta buscar por código de barras
        produto = Produto.buscar_por_codigo_barras(codigo)
        if produto:
            return produto
        
        # Se não encontrar, tenta buscar pelo nome
        produtos = Produto.buscar_todos(filtro=codigo, apenas_ativos=True)
        if produtos:
            return produtos[0]
            
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar produto: {e}")
        return None

def buscar_cliente_por_documento(documento: str):
    """Busca um cliente por CPF ou nome."""
    try:
        # Remove caracteres não numéricos
        documento_limpo = ''.join(filter(str.isdigit, documento))
        
        # Se tiver 11 dígitos, assume que é CPF
        if len(documento_limpo) == 11:
            cliente = Cliente.buscar_por_cpf(documento_limpo)
            if cliente:
                return cliente
        
        # Se não encontrar ou não for CPF, busca por nome
        clientes = Cliente.buscar_todos(filtro=documento, apenas_ativos=True)
        if clientes:
            return clientes[0]
            
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar cliente: {e}")
        return None

def pdv_page():
    """Renderiza a página do PDV."""
    # Verifica autenticação
    if 'usuario' not in st.session_state:
        st.switch_page("pages/00_🔐_login.py")
        return
    
    # Inicializa a venda na sessão se não existir
    if 'venda_atual' not in st.session_state:
        st.session_state.venda_atual = Venda()
        st.session_state.venda_atual.usuario_id = st.session_state.usuario['id']
        st.session_state.venda_atual.usuario_nome = st.session_state.usuario['nome']
    
    # Título da página
    st.title("🛒 Ponto de Venda")
    st.markdown("---")
    
    # Layout principal com duas colunas
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Seção de busca de produtos
        st.subheader("Adicionar Produto")
        
        # Campo de busca de produto
        produto_input = st.text_input(
            "Código de Barras ou Nome do Produto:",
            placeholder="Passe o produto ou digite o nome/código",
            key="produto_input"
        )
        
        # Se o usuário digitou algo no campo de busca
        if produto_input:
            produto = buscar_produto_por_codigo(produto_input)
            
            if produto:
                # Se encontrou o produto, adiciona à venda
                st.session_state.venda_atual.adicionar_item(produto)
                # Limpa o campo de busca
                st.rerun()
            else:
                st.warning("Produto não encontrado.")
        
        # Lista de produtos da venda atual
        st.subheader("Itens da Venda")
        
        if not st.session_state.venda_atual.itens:
            st.info("Nenhum item adicionado à venda.")
        else:
            # Exibe os itens da venda em uma tabela
            for i, item in enumerate(st.session_state.venda_atual.itens):
                col1_item, col2_item, col3_item, col4_item = st.columns([4, 2, 2, 1])
                
                with col1_item:
                    st.write(f"**{item.produto_nome}")
                
                with col2_item:
                    # Campo para editar a quantidade
                    nova_quantidade = st.number_input(
                        "Qtd",
                        min_value=1,
                        value=item.quantidade,
                        key=f"qtd_{i}",
                        label_visibility="collapsed"
                    )
                    
                    if nova_quantidade != item.quantidade:
                        st.session_state.venda_atual.atualizar_item(i, quantidade=nova_quantidade)
                        st.rerun()
                
                with col3_item:
                    st.write(f"{format_currency(item.preco_unitario)} x {item.quantidade} = {format_currency(item.subtotal + item.desconto)}")
                    
                    # Se houver desconto, exibe o valor com desconto
                    if item.desconto > 0:
                        st.caption(f"Desconto: {format_currency(item.desconto)}")
                
                with col4_item:
                    # Botão para remover o item
                    if st.button("❌", key=f"remover_{i}"):
                        st.session_state.venda_atual.remover_item(i)
                        st.rerun()
            
            st.markdown("---")
            
            # Resumo da venda
            col_resumo1, col_resumo2 = st.columns(2)
            
            with col_resumo1:
                # Campo para adicionar desconto na venda
                desconto_venda = st.number_input(
                    "Desconto na Venda (R$)",
                    min_value=0.0,
                    max_value=st.session_state.venda_atual.subtotal,
                    value=st.session_state.venda_atual.desconto,
                    step=1.0,
                    format="%.2f"
                )
                
                if desconto_venda != st.session_state.venda_atual.desconto:
                    st.session_state.venda_atual.desconto = desconto_venda
                    st.session_state.venda_atual.calcular_totais()
                    st.rerun()
            
            with col_resumo2:
                st.metric("Subtotal", format_currency(st.session_state.venda_atual.subtotal))
                st.metric("Desconto", f"-{format_currency(st.session_state.venda_atual.desconto)}")
                st.metric("Total", format_currency(st.session_state.venda_atual.total), delta_color="off")
    
    with col2:
        # Seção de informações do cliente
        st.subheader("Cliente")
        
        # Campo para buscar cliente
        cliente_input = st.text_input(
            "CPF ou Nome do Cliente:",
            placeholder="Digite o CPF ou nome do cliente",
            key="cliente_input"
        )
        
        # Se o usuário digitou algo no campo de busca
        if cliente_input:
            cliente = buscar_cliente_por_documento(cliente_input)
            
            if cliente:
                st.session_state.venda_atual.cliente_id = cliente.id
                st.session_state.venda_atual.cliente_nome = cliente.nome
                st.success(f"Cliente: {cliente.nome}")
            else:
                st.warning("Cliente não encontrado. Venda será para cliente não identificado.")
                st.session_state.venda_atual.cliente_id = None
                st.session_state.venda_atual.cliente_nome = "Cliente não identificado"
        
        # Se já tem um cliente selecionado
        elif st.session_state.venda_atual.cliente_id:
            st.info(f"Cliente: {st.session_state.venda_atual.cliente_nome}")
        else:
            st.info("Venda para cliente não identificado")
        
        # Botão para novo cliente
        if st.button("Novo Cliente", use_container_width=True):
            st.switch_page("pages/05_👥_clientes.py?novo=1")
        
        # Seção de pagamento
        st.subheader("Pagamento")
        
        # Forma de pagamento
        forma_pagamento = st.selectbox(
            "Forma de Pagamento",
            ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Outro"],
            index=0
        )
        
        # Observações
        observacoes = st.text_area("Observações", height=100)
        
        # Botões de ação
        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            # Botão para cancelar venda
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state.venda_atual = Venda()
                st.session_state.venda_atual.usuario_id = st.session_state.usuario['id']
                st.session_state.venda_atual.usuario_nome = st.session_state.usuario['nome']
                st.rerun()
        
        with col_btn2:
            # Botão para finalizar venda
            if st.button("💳 Finalizar Venda", type="primary", use_container_width=True):
                if not st.session_state.venda_atual.itens:
                    st.error("Adicione pelo menos um item à venda.")
                else:
                    # Atualiza os dados da venda
                    st.session_state.venda_atual.forma_pagamento = forma_pagamento
                    st.session_state.venda_atual.observacoes = observacoes
                    st.session_state.venda_atual.status = "finalizada"
                    
                    # Salva a venda no banco de dados
                    if st.session_state.venda_atual.salvar(st.session_state.usuario['id']):
                        st.success("Venda finalizada com sucesso!")
                        
                        # Exibe o comprovante
                        with st.expander("Ver Comprovante", expanded=True):
                            st.subheader("Comprovante de Venda")
                            st.write(f"**Número:** {st.session_state.venda_atual.codigo}")
                            st.write(f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                            st.write(f"**Vendedor:** {st.session_state.usuario['nome']}")
                            
                            if st.session_state.venda_atual.cliente_nome:
                                st.write(f"**Cliente:** {st.session_state.venda_atual.cliente_nome}")
                            
                            st.markdown("---")
                            
                            # Itens da venda
                            st.write("**Itens:**")
                            for item in st.session_state.venda_atual.itens:
                                st.write(f"- {item.quantidade}x {item.produto_nome}: {format_currency(item.subtotal + item.desconto)}")
                                if item.desconto > 0:
                                    st.caption(f"  Desconto: {format_currency(item.desconto)}")
                            
                            st.markdown("---")
                            
                            # Totais
                            col_total1, col_total2 = st.columns(2)
                            
                            with col_total1:
                                st.write("Subtotal:")
                                if st.session_state.venda_atual.desconto > 0:
                                    st.write("Desconto:")
                                st.write("**Total:**")
                            
                            with col_total2:
                                st.write(f"{format_currency(st.session_state.venda_atual.subtotal)}")
                                if st.session_state.venda_atual.desconto > 0:
                                    st.write(f"-{format_currency(st.session_state.venda_atual.desconto)}")
                                st.write(f"**{format_currency(st.session_state.venda_atual.total)}**")
                            
                            st.markdown("---")
                            st.write(f"**Forma de Pagamento:** {forma_pagamento}")
                            st.write("Obrigado pela preferência!")
                        
                        # Limpa a venda atual após 5 segundos
                        time.sleep(5)
                        st.session_state.venda_atual = Venda()
                        st.session_state.venda_atual.usuario_id = st.session_state.usuario['id']
                        st.session_state.venda_atual.usuario_nome = st.session_state.usuario['nome']
                        st.rerun()
                    else:
                        st.error("Erro ao finalizar a venda. Tente novamente.")
    
    # Barra lateral
    render_sidebar(st.session_state['usuario'])

if __name__ == "__main__":
    pdv_page()
