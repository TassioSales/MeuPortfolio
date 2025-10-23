"""
Dashboard Principal do Sistema PDV
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Importa os componentes necessários
from components.sidebar import render_sidebar
from utils.database import execute_query
from utils.helpers import format_currency
from utils.logger import logger

# Configurações da página
st.set_page_config(
    page_title="Dashboard - Sistema PDV",
    page_icon="📊",
    layout="wide"
)

def carregar_metricas():
    """Carrega as métricas para o dashboard."""
    try:
        # Obtém a data de 30 dias atrás
        data_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Total de vendas no período
        total_vendas = execute_query(
            """
            SELECT COALESCE(SUM(total), 0) as total
            FROM vendas
            WHERE data_venda >= ? AND status = 'finalizada'
            """,
            (data_inicio,),
            fetch="value"
        ) or 0
        
        # Total de clientes
        total_clientes = execute_query(
            "SELECT COUNT(*) FROM clientes WHERE ativo = 1",
            fetch="value"
        ) or 0
        
        # Total de produtos com estoque baixo
        estoque_baixo = execute_query(
            "SELECT COUNT(*) FROM produtos WHERE estoque <= estoque_minimo AND ativo = 1",
            fetch="value"
        ) or 0
        
        # Total de vendas hoje
        hoje = datetime.now().strftime('%Y-%m-%d')
        vendas_hoje = execute_query(
            """
            SELECT COUNT(*) 
            FROM vendas 
            WHERE DATE(data_venda) = ? AND status = 'finalizada'
            """,
            (hoje,),
            fetch="value"
        ) or 0
        
        return {
            'total_vendas': total_vendas,
            'total_clientes': total_clientes,
            'estoque_baixo': estoque_baixo,
            'vendas_hoje': vendas_hoje
        }
    except Exception as e:
        logger.error(f"Erro ao carregar métricas: {e}")
        return {
            'total_vendas': 0,
            'total_clientes': 0,
            'estoque_baixo': 0,
            'vendas_hoje': 0
        }

def carregar_grafico_vendas():
    """Carrega o gráfico de vendas dos últimos 30 dias."""
    try:
        # Obtém as vendas dos últimos 30 dias
        data = execute_query(
            """
            SELECT 
                DATE(data_venda) as data,
                COUNT(*) as quantidade,
                SUM(total) as valor_total
            FROM vendas
            WHERE data_venda >= DATE('now', '-30 days')
              AND status = 'finalizada'
            GROUP BY DATE(data_venda)
            ORDER BY data
            """,
            fetch="all"
        )
        
        if not data:
            return None
            
        # Converte para DataFrame
        df = pd.DataFrame(data, columns=['data', 'quantidade', 'valor_total'])
        
        # Cria o gráfico de linha
        fig = px.line(
            df, 
            x='data', 
            y='valor_total',
            title='Vendas dos Últimos 30 Dias',
            labels={'data': 'Data', 'valor_total': 'Valor Total (R$)', 'quantidade': 'Quantidade'},
            markers=True
        )
        
        # Adiciona a quantidade de vendas como texto nos pontos
        fig.update_traces(
            text=df['quantidade'],
            textposition='top center',
            hovertemplate=
                '<b>Data:</b> %{x|%d/%m/%Y}<br>' +
                '<b>Valor Total:</b> R$ %{y:,.2f}<br>' +
                '<b>Vendas:</b> %{text}<extra></extra>'
        )
        
        # Formata o eixo Y como moeda
        fig.update_layout(
            yaxis_tickprefix='R$ ',
            yaxis_tickformat=',.2f',
            xaxis_tickformat='%d/%m',
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=40, b=20),
            height=400
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Erro ao carregar gráfico de vendas: {e}")
        return None

def carregar_produtos_mais_vendidos():
    """Carrega os produtos mais vendidos."""
    try:
        # Obtém os produtos mais vendidos
        data = execute_query(
            """
            SELECT 
                p.nome as produto,
                SUM(iv.quantidade) as quantidade,
                SUM(iv.subtotal) as total_vendido
            FROM itens_venda iv
            JOIN produtos p ON iv.produto_id = p.id
            JOIN vendas v ON iv.venda_id = v.id
            WHERE v.status = 'finalizada'
            GROUP BY p.id, p.nome
            ORDER BY quantidade DESC
            LIMIT 5
            """,
            fetch="all"
        )
        
        if not data:
            return None
            
        # Converte para DataFrame
        df = pd.DataFrame(data, columns=['produto', 'quantidade', 'total_vendido'])
        
        # Formata o valor total
        df['total_formatado'] = df['total_vendido'].apply(
            lambda x: f'R$ {x:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')
        )
        
        return df
        
    except Exception as e:
        logger.error(f"Erro ao carregar produtos mais vendidos: {e}")
        return None

def dashboard_page():
    """Renderiza a página do dashboard."""
    # Verifica autenticação
    if 'usuario' not in st.session_state:
        st.switch_page("pages/00_🔐_login.py")
        return
    
    # Título da página
    st.title("📊 Dashboard")
    st.markdown("---")
    
    # Carrega os dados
    with st.spinner("Carregando dados..."):
        metricas = carregar_metricas()
        grafico_vendas = carregar_grafico_vendas()
        produtos_mais_vendidos = carregar_produtos_mais_vendidos()
    
    # Seção de métricas
    st.subheader("Visão Geral")
    
    # Layout com 4 colunas para as métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total em Vendas (30 dias)", format_currency(metricas['total_vendas']))
    
    with col2:
        st.metric("Total de Clientes", metricas['total_clientes'])
    
    with col3:
        st.metric("Produtos com Estoque Baixo", metricas['estoque_baixo'])
    
    with col4:
        st.metric("Vendas Hoje", metricas['vendas_hoje'])
    
    # Gráfico de vendas
    st.subheader("Desempenho de Vendas")
    if grafico_vendas:
        st.plotly_chart(grafico_vendas, use_container_width=True)
    else:
        st.info("Nenhum dado de venda disponível para exibição.")
    
    # Tabela de produtos mais vendidos
    st.subheader("Produtos Mais Vendidos")
    if produtos_mais_vendidos is not None and not produtos_mais_vendidos.empty:
        # Estiliza a tabela
        st.dataframe(
            produtos_mais_vendidos[['produto', 'quantidade', 'total_formatado']],
            column_config={
                'produto': 'Produto',
                'quantidade': 'Quantidade',
                'total_formatado': 'Total Vendido'
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Nenhum dado de produto vendido disponível.")
    
    # Seção de ações rápidas
    st.subheader("Ações Rápidas")
    
    # Layout com 3 colunas para os botões de ação
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Nova Venda", use_container_width=True):
            st.switch_page("pages/02_🛒_pdv.py")
    
    with col2:
        if st.button("Gerenciar Estoque", use_container_width=True):
            st.switch_page("pages/03_📦_estoque.py")
    
    with col3:
        if st.button("Ver Relatórios", use_container_width=True):
            st.switch_page("pages/04_📊_relatorios.py")
    
    # Barra lateral
    render_sidebar(st.session_state['usuario'])

if __name__ == "__main__":
    dashboard_page()
