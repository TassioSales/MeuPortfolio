"""
Módulo de Gerenciamento de Estoque do Sistema PDV
"""
import streamlit as st
import pandas as pd
from datetime import datetime

# Importa os componentes necessários
from components.sidebar import render_sidebar
from modulos.produto import Produto
from modulos.categoria import Categoria
from utils.helpers import format_currency
from utils.logger import logger

# Configurações da página
st.set_page_config(
    page_title="Estoque - Sistema PDV",
    page_icon="📦",
    layout="wide"
)

def carregar_produtos(filtro: str = "", categoria_id: int = None):
    """Carrega a lista de produtos com filtros."""
    try:
        return Produto.buscar_todos(filtro=filtro, categoria_id=categoria_id, apenas_ativos=True)
    except Exception as e:
        logger.error(f"Erro ao carregar produtos: {e}")
        return []

def carregar_categorias():
    """Carrega a lista de categorias."""
    try:
        return Categoria.buscar_todos()
    except Exception as e:
        logger.error(f"Erro ao carregar categorias: {e}")
        return []

def exibir_formulario_produto(produto=None):
    """Exibe o formulário para adicionar/editar um produto."""
    is_edicao = produto is not None
    
    with st.form(key="form_produto", clear_on_submit=not is_edicao):
        col1, col2 = st.columns(2)
        
        with col1:
            # Dados básicos
            nome = st.text_input("Nome do Produto*", value=produto.nome if is_edicao else "")
            descricao = st.text_area("Descrição", value=produto.descricao if is_edicao else "")
            
            # Categoria
            categorias = carregar_categorias()
            categoria_id = st.selectbox(
                "Categoria*",
                options=[c.id for c in categorias],
                format_func=lambda x: next((c.nome for c in categorias if c.id == x), "Selecione..."),
                index=next((i for i, c in enumerate(categorias) 
                          if is_edicao and c.id == produto.categoria_id), 0)
            )
            
            # Código de barras
            codigo_barras = st.text_input(
                "Código de Barras",
                value=produto.codigo_barras if is_edicao else ""
            )
        
        with col2:
            # Preços
            preco_compra = st.number_input(
                "Preço de Custo*",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=float(produto.preco_compra) if is_edicao else 0.0
            )
            
            preco_venda = st.number_input(
                "Preço de Venda*",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=float(produto.preco_venda) if is_edicao else 0.0
            )
            
            # Estoque
            col_estoque1, col_estoque2 = st.columns(2)
            with col_estoque1:
                estoque_atual = st.number_input(
                    "Estoque Atual*",
                    min_value=0,
                    step=1,
                    value=produto.estoque if is_edicao else 0
                )
            
            with col_estoque2:
                estoque_minimo = st.number_input(
                    "Estoque Mínimo",
                    min_value=0,
                    step=1,
                    value=produto.estoque_minimo if is_edicao else 5
                )
            
            # Status
            ativo = st.checkbox("Ativo", value=produto.ativo if is_edicao else True)
        
        # Botões do formulário
        col_btn1, col_btn2 = st.columns([1, 3])
        
        with col_btn1:
            submit_button = st.form_submit_button(
                "Salvar" if is_edicao else "Adicionar Produto",
                type="primary",
                use_container_width=True
            )
        
        with col_btn2:
            if st.form_submit_button("Cancelar", use_container_width=True):
                st.session_state.pop('produto_editando', None)
                st.rerun()
        
        # Processa o formulário quando enviado
        if submit_button:
            if not nome or preco_compra <= 0 or preco_venda <= 0:
                st.error("Preencha todos os campos obrigatórios (*).")
                return None
            
            try:
                if is_edicao:
                    # Atualiza o produto existente
                    produto.nome = nome
                    produto.descricao = descricao
                    produto.categoria_id = categoria_id
                    produto.codigo_barras = codigo_barras or None
                    produto.preco_compra = preco_compra
                    produto.preco_venda = preco_venda
                    produto.estoque = estoque_atual
                    produto.estoque_minimo = estoque_minimo
                    produto.ativo = ativo
                else:
                    # Cria um novo produto
                    produto = Produto(
                        nome=nome,
                        descricao=descricao,
                        categoria_id=categoria_id,
                        codigo_barras=codigo_barras or None,
                        preco_compra=preco_compra,
                        preco_venda=preco_venda,
                        estoque=estoque_atual,
                        estoque_minimo=estoque_minimo,
                        ativo=ativo
                    )
                
                # Salva o produto
                if produto.salvar():
                    st.success("Produto salvo com sucesso!")
                    st.session_state.pop('produto_editando', None)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Erro ao salvar o produto. Tente novamente.")
            
            except Exception as e:
                logger.error(f"Erro ao salvar produto: {e}")
                st.error(f"Erro ao salvar o produto: {e}")

def exibir_tabela_produtos(produtos):
    """Exibe a tabela de produtos com opções de edição/exclusão."""
    if not produtos:
        st.info("Nenhum produto encontrado.")
        return
    
    # Converte para DataFrame para exibição
    dados = []
    for p in produtos:
        dados.append({
            "ID": p.id,
            "Código": p.codigo_barras or "-",
            "Nome": p.nome,
            "Categoria": p.categoria_nome or "Sem categoria",
            "Estoque": p.estoque,
            "Estoque Mín.": p.estoque_minimo,
            "Preço Custo": p.preco_compra,
            "Preço Venda": p.preco_venda,
            "Status": "Ativo" if p.ativo else "Inativo"
        })
    
    df = pd.DataFrame(dados)
    
    # Formatação condicional para o estoque
    def estilo_linha(row):
        estilo = []
        if row['Estoque'] <= row['Estoque Mín.']:
            estilo.append('background-color: #FFF3CD')  # Amarelo claro para estoque baixo
        if not row['Status'] == 'Ativo':
            estilo.append('opacity: 0.7')  # Opacidade reduzida para itens inativos
        return ['; '.join(estilo)] * len(row)
    
    # Aplica o estilo
    styled_df = df.style.apply(estilo_linha, axis=1)
    
    # Exibe a tabela estilizada
    st.dataframe(
        styled_df,
        column_config={
            "ID": None,  # Oculta a coluna ID
            "Preço Custo": st.column_config.NumberColumn(
                "Custo (R$)",
                format="R$ %.2f"
            ),
            "Preço Venda": st.column_config.NumberColumn(
                "Venda (R$)",
                format="R$ %.2f"
            ),
        },
        hide_index=True,
        use_container_width=True,
        height=min(400, 35 * (len(produtos) + 1)),
        column_order=["Nome", "Categoria", "Código", "Estoque", "Estoque Mín.", "Custo (R$)", "Venda (R$)", "Status"]
    )
    
    # Adiciona botões de ação para cada produto
    for i, produto in enumerate(produtos):
        col1, col2, _ = st.columns([1, 1, 8])
        
        with col1:
            if st.button(f"✏️ Editar", key=f"editar_{i}", use_container_width=True):
                st.session_state['produto_editando'] = produto
                st.rerun()
        
        with col2:
            if st.button(f"🗑️ Excluir", key=f"excluir_{i}", use_container_width=True):
                if produto.excluir():
                    st.success("Produto removido com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Erro ao remover o produto.")

def estoque_page():
    """Renderiza a página de gerenciamento de estoque."""
    # Verifica autenticação
    if 'usuario' not in st.session_state:
        st.switch_page("pages/00_🔐_login.py")
        return
    
    # Verifica permissão (apenas admin pode gerenciar estoque)
    if st.session_state.usuario.get('role') != 'admin':
        st.error("Você não tem permissão para acessar esta página.")
        return
    
    # Título da página
    st.title("📦 Gerenciamento de Estoque")
    st.markdown("---")
    
    # Verifica se há um produto sendo editado
    if 'produto_editando' in st.session_state:
        st.button("← Voltar para a lista", on_click=lambda: st.session_state.pop('produto_editando', None))
        exibir_formulario_produto(st.session_state['produto_editando'])
        return
    
    # Filtros
    st.subheader("Filtrar Produtos")
    
    col_filtro1, col_filtro2 = st.columns(2)
    
    with col_filtro1:
        # Campo de busca
        termo_busca = st.text_input("Buscar por nome ou código:", "")
    
    with col_filtro2:
        # Filtro por categoria
        categorias = carregar_categorias()
        categoria_selecionada = st.selectbox(
            "Filtrar por categoria:",
            options=[None] + [c.id for c in categorias],
            format_func=lambda x: next((c.nome for c in categorias if c.id == x), "Todas as categorias"),
            index=0
        )
    
    # Botão para adicionar novo produto
    if st.button("➕ Adicionar Novo Produto", use_container_width=True):
        st.session_state['produto_editando'] = None
        st.rerun()
    
    # Carrega e exibe os produtos
    produtos = carregar_produtos(termo_busca, categoria_selecionada)
    exibir_tabela_produtos(produtos)
    
    # Seção de relatórios
    st.markdown("---")
    st.subheader("Relatórios de Estoque")
    
    col_rel1, col_rel2 = st.columns(2)
    
    with col_rel1:
        if st.button("📊 Produtos com Estoque Baixo", use_container_width=True):
            produtos_baixo_estoque = [p for p in produtos if p.estoque <= p.estoque_minimo]
            if produtos_baixo_estoque:
                st.subheader("Produtos com Estoque Abaixo do Mínimo")
                exibir_tabela_produtos(produtos_baixo_estoque)
            else:
                st.success("Nenhum produto com estoque abaixo do mínimo.")
    
    with col_rel2:
        if st.button("📝 Relatório Completo", use_container_width=True):
            # Gera um relatório em formato de tabela
            st.subheader("Relatório Completo de Estoque")
            st.dataframe(
                pd.DataFrame([{
                    "Total de Produtos": len(produtos),
                    "Produtos Ativos": sum(1 for p in produtos if p.ativo),
                    "Produtos Inativos": sum(1 for p in produtos if not p.ativo),
                    "Produtos com Estoque Baixo": sum(1 for p in produtos if p.estoque <= p.estoque_minimo),
                    "Valor Total em Estoque": sum(p.estoque * p.preco_compra for p in produtos if p.ativo)
                }]),
                use_container_width=True,
                hide_index=True
            )
    
    # Barra lateral
    render_sidebar(st.session_state['usuario'])

if __name__ == "__main__":
    import time  # Importação necessária para o time.sleep
    estoque_page()
