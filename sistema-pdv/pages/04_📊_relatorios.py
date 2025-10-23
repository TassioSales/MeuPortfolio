import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from modulos import Venda, Produto, Cliente
from utils.helpers import format_currency, format_date

def relatorios_page():
    """Página de relatórios do sistema PDV"""
    st.title("📊 Relatórios")
    
    # Verifica se o usuário está autenticado
    if 'user' not in st.session_state:
        st.warning("Por favor, faça login para acessar esta página.")
        st.stop()
    
    # Filtros de data
    st.sidebar.header("Filtros")
    
    # Opções de período
    periodo = st.sidebar.selectbox(
        "Período",
        ["Hoje", "Ontem", "Últimos 7 dias", "Este mês", "Mês passado", "Personalizado"]
    )
    
    hoje = datetime.now().date()
    data_inicio = hoje
    data_fim = hoje
    
    # Define as datas com base no período selecionado
    if periodo == "Hoje":
        data_inicio = hoje
        data_fim = hoje
    elif periodo == "Ontem":
        data_inicio = hoje - timedelta(days=1)
        data_fim = data_inicio
    elif periodo == "Últimos 7 dias":
        data_inicio = hoje - timedelta(days=6)
        data_fim = hoje
    elif periodo == "Este mês":
        data_inicio = hoje.replace(day=1)
        data_fim = hoje
    elif periodo == "Mês passado":
        primeiro_dia_mes_atual = hoje.replace(day=1)
        ultimo_dia_mes_passado = primeiro_dia_mes_atual - timedelta(days=1)
        data_inicio = ultimo_dia_mes_passado.replace(day=1)
        data_fim = ultimo_dia_mes_passado
    else:  # Personalizado
        col1, col2 = st.sidebar.columns(2)
        with col1:
            data_inicio = st.date_input("Data inicial", hoje - timedelta(days=30))
        with col2:
            data_fim = st.date_input("Data final", hoje)
    
    # Ajusta o horário para incluir o dia inteiro
    data_inicio = datetime.combine(data_inicio, datetime.min.time())
    data_fim = datetime.combine(data_fim, datetime.max.time())
    
    # Filtros adicionais
    st.sidebar.subheader("Filtros Adicionais")
    
    # Opção de agrupamento
    agrupamento = st.sidebar.selectbox(
        "Agrupar por",
        ["Dia", "Semana", "Mês", "Ano", "Produto", "Categoria", "Cliente", "Vendedor"]
    )
    
    # Filtro de status
    status = st.sidebar.multiselect(
        "Status da Venda",
        ["Todas", "Concluída", "Cancelada", "Devolvida"],
        default=["Concluída"]
    )
    
    # Filtro de forma de pagamento
    formas_pagamento = st.sidebar.multiselect(
        "Forma de Pagamento",
        ["Todas", "Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Boleto"],
        default=["Todas"]
    )
    
    # Busca as vendas no período
    vendas = Venda.buscar_por_periodo(data_inicio, data_fim)
    
    # Aplica filtros adicionais
    if "Todas" not in status:
        vendas = [v for v in vendas if v.status in status]
    
    if "Todas" not in formas_pagamento:
        vendas = [v for v in vendas if v.forma_pagamento in formas_pagamento]
    
    # Verifica se existem vendas no período
    if not vendas:
        st.warning("Nenhuma venda encontrada para o período e filtros selecionados.")
        return
    
    # Converte para DataFrame para facilitar a manipulação
    df_vendas = pd.DataFrame([v.to_dict() for v in vendas])
    
    # Converte as colunas de data
    df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])
    
    # Cálculos básicos
    total_vendas = len(vendas)
    valor_total = df_vendas['valor_total'].sum()
    ticket_medio = valor_total / total_vendas if total_vendas > 0 else 0
    
    # Exibe métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Vendas", total_vendas)
    with col2:
        st.metric("Valor Total", format_currency(valor_total))
    with col3:
        st.metric("Ticket Médio", format_currency(ticket_medio))
    
    # Gráfico de vendas ao longo do tempo
    st.subheader("Vendas ao Longo do Tempo")
    
    # Agrupa os dados conforme selecionado
    if agrupamento == "Dia":
        df_agrupado = df_vendas.groupby(pd.Grouper(key='data_venda', freq='D')).agg({
            'id': 'count',
            'valor_total': 'sum'
        }).reset_index()
        df_agrupado.rename(columns={'id': 'quantidade'}, inplace=True)
        df_agrupado['data'] = df_agrupado['data_venda'].dt.strftime('%d/%m/%Y')
    elif agrupamento == "Semana":
        df_agrupado = df_vendas.groupby(pd.Grouper(key='data_venda', freq='W-MON')).agg({
            'id': 'count',
            'valor_total': 'sum'
        }).reset_index()
        df_agrupado.rename(columns={'id': 'quantidade'}, inplace=True)
        df_agrupado['data'] = 'Semana de ' + df_agrupado['data_venda'].dt.strftime('%d/%m/%Y')
    elif agrupamento == "Mês":
        df_agrupado = df_vendas.groupby(pd.Grouper(key='data_venda', freq='M')).agg({
            'id': 'count',
            'valor_total': 'sum'
        }).reset_index()
        df_agrupado.rename(columns={'id': 'quantidade'}, inplace=True)
        df_agrupado['data'] = df_agrupado['data_venda'].dt.strftime('%m/%Y')
    elif agrupamento == "Ano":
        df_agrupado = df_vendas.groupby(pd.Grouper(key='data_venda', freq='Y')).agg({
            'id': 'count',
            'valor_total': 'sum'
        }).reset_index()
        df_agrupado.rename(columns={'id': 'quantidade'}, inplace=True)
        df_agrupado['data'] = df_agrupado['data_venda'].dt.strftime('%Y')
    elif agrupamento in ["Produto", "Categoria"]:
        # Para agrupar por produto ou categoria, precisamos dos itens de venda
        itens_venda = []
        for venda in vendas:
            for item in venda.itens:
                produto = Produto.buscar_por_id(item.produto_id)
                if produto:
                    itens_venda.append({
                        'venda_id': venda.id,
                        'produto_id': produto.id,
                        'produto_nome': produto.nome,
                        'categoria': produto.categoria,
                        'quantidade': item.quantidade,
                        'preco_unitario': item.preco_unitario,
                        'desconto': item.desconto,
                        'subtotal': item.subtotal(),
                        'data_venda': venda.data_venda
                    })
        
        df_itens = pd.DataFrame(itens_venda)
        
        if agrupamento == "Produto":
            df_agrupado = df_itens.groupby('produto_nome').agg({
                'quantidade': 'sum',
                'subtotal': 'sum'
            }).reset_index()
            df_agrupado.rename(columns={'produto_nome': 'descricao'}, inplace=True)
        else:  # Categoria
            df_agrupado = df_itens.groupby('categoria').agg({
                'quantidade': 'sum',
                'subtotal': 'sum'
            }).reset_index()
            df_agrupado.rename(columns={'categoria': 'descricao'}, inplace=True)
            
        # Ordena por valor total
        df_agrupado = df_agrupado.sort_values('subtotal', ascending=False)
        
    elif agrupamento == "Cliente":
        # Agrupa por cliente
        clientes_vendas = []
        for venda in vendas:
            cliente = Cliente.buscar_por_id(venda.cliente_id) if venda.cliente_id else None
            clientes_vendas.append({
                'cliente_id': venda.cliente_id,
                'cliente_nome': cliente.nome if cliente else 'Consumidor Final',
                'valor_total': venda.valor_total,
                'quantidade': 1
            })
        
        df_clientes = pd.DataFrame(clientes_vendas)
        df_agrupado = df_clientes.groupby('cliente_nome').agg({
            'quantidade': 'sum',
            'valor_total': 'sum'
        }).reset_index()
        df_agrupado.rename(columns={'cliente_nome': 'descricao', 'valor_total': 'subtotal'}, inplace=True)
        df_agrupado = df_agrupado.sort_values('subtotal', ascending=False)
    
    # Exibe o gráfico
    if agrupamento in ["Dia", "Semana", "Mês", "Ano"]:
        fig = px.bar(
            df_agrupado, 
            x='data', 
            y='valor_total',
            labels={'data': 'Data', 'valor_total': 'Valor Total'},
            title=f'Vendas por {agrupamento}'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Gráfico de barras para categorias, produtos, etc.
        fig = px.bar(
            df_agrupado.head(10),  # Limita a 10 itens para melhor visualização
            x='descricao', 
            y='subtotal',
            labels={'descricao': agrupamento, 'subtotal': 'Valor Total'},
            title=f'Vendas por {agrupamento} (Top 10)',
            color='subtotal',
            color_continuous_scale='Blues'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabela com os dados detalhados
    st.subheader("Detalhes das Vendas")
    
    # Prepara os dados para exibição
    dados_exibicao = []
    for venda in vendas:
        cliente = Cliente.buscar_por_id(venda.cliente_id) if venda.cliente_id else None
        vendedor = venda.vendedor_nome or "Sistema"
        
        dados_exibicao.append({
            "ID": venda.id,
            "Data": format_date(venda.data_venda),
            "Cliente": cliente.nome if cliente else "Consumidor Final",
            "Itens": len(venda.itens),
            "Valor Total": format_currency(venda.valor_total),
            "Desconto": format_currency(venda.desconto_total),
            "Forma de Pagamento": venda.forma_pagamento,
            "Status": venda.status,
            "Vendedor": vendedor
        })
    
    # Exibe a tabela
    df_detalhes = pd.DataFrame(dados_exibicao)
    st.dataframe(
        df_detalhes,
        column_config={
            "ID": st.column_config.NumberColumn("ID", format="%d"),
            "Data": "Data",
            "Cliente": "Cliente",
            "Itens": st.column_config.NumberColumn("Itens", format="%d"),
            "Valor Total": "Valor Total",
            "Desconto": "Desconto",
            "Forma de Pagamento": "Pagamento",
            "Status": "Status",
            "Vendedor": "Vendedor"
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Botão para exportar relatório
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("📥 Exportar para Excel"):
            # Cria um arquivo Excel em memória
            output = pd.ExcelWriter('relatorio_vendas.xlsx', engine='xlsxwriter')
            df_detalhes.to_excel(output, index=False, sheet_name='Vendas')
            
            # Adiciona uma aba com o resumo
            resumo = pd.DataFrame({
                'Métrica': ['Total de Vendas', 'Valor Total', 'Ticket Médio'],
                'Valor': [total_vendas, valor_total, ticket_medio],
                'Observação': ['', format_currency(valor_total), format_currency(ticket_medio)]
            })
            resumo.to_excel(output, index=False, sheet_name='Resumo')
            
            # Fecha o writer e salva o arquivo
            output.close()
            
            # Força o download do arquivo
            with open('relatorio_vendas.xlsx', 'rb') as f:
                st.download_button(
                    label="⬇️ Baixar Arquivo Excel",
                    data=f,
                    file_name=f"relatorio_vendas_{hoje.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    # Seção de relatórios adicionais
    st.subheader("Relatórios Adicionais")
    
    # Abas para diferentes tipos de relatórios
    tab1, tab2, tab3 = st.tabs(["📈 Vendas por Vendedor", "📦 Produtos Mais Vendidos", "👥 Clientes"])
    
    with tab1:
        # Relatório de vendas por vendedor
        vendedores = {}
        for venda in vendas:
            vendedor = venda.vendedor_nome or "Sistema"
            if vendedor not in vendedores:
                vendedores[vendedor] = {
                    'quantidade': 0,
                    'valor_total': 0.0
                }
            vendedores[vendedor]['quantidade'] += 1
            vendedores[vendedor]['valor_total'] += venda.valor_total
        
        if vendedores:
            df_vendedores = pd.DataFrame([
                {
                    'Vendedor': v,
                    'Vendas': dados['quantidade'],
                    'Valor Total': dados['valor_total'],
                    'Ticket Médio': dados['valor_total'] / dados['quantidade'] if dados['quantidade'] > 0 else 0
                }
                for v, dados in vendedores.items()
            ])
            
            # Ordena por valor total
            df_vendedores = df_vendedores.sort_values('Valor Total', ascending=False)
            
            # Exibe o gráfico
            fig = px.pie(
                df_vendedores,
                values='Valor Total',
                names='Vendedor',
                title='Distribuição de Vendas por Vendedor',
                hole=0.3
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Exibe a tabela
            st.dataframe(
                df_vendedores,
                column_config={
                    "Vendedor": "Vendedor",
                    "Vendas": st.column_config.NumberColumn("Nº Vendas", format="%d"),
                    "Valor Total": st.column_config.NumberColumn(
                        "Valor Total",
                        format="R$ %.2f"
                    ),
                    "Ticket Médio": st.column_config.NumberColumn(
                        "Ticket Médio",
                        format="R$ %.2f"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Nenhum dado de vendedor disponível.")
    
    with tab2:
        # Relatório de produtos mais vendidos
        produtos_vendidos = {}
        for venda in vendas:
            for item in venda.itens:
                produto = Produto.buscar_por_id(item.produto_id)
                if produto:
                    if produto.id not in produtos_vendidos:
                        produtos_vendidos[produto.id] = {
                            'nome': produto.nome,
                            'categoria': produto.categoria,
                            'quantidade': 0,
                            'valor_total': 0.0
                        }
                    produtos_vendidos[produto.id]['quantidade'] += item.quantidade
                    produtos_vendidos[produto.id]['valor_total'] += item.subtotal()
        
        if produtos_vendidos:
            df_produtos = pd.DataFrame([
                {
                    'Produto': dados['nome'],
                    'Categoria': dados['categoria'],
                    'Quantidade': dados['quantidade'],
                    'Valor Total': dados['valor_total'],
                    'Preço Médio': dados['valor_total'] / dados['quantidade'] if dados['quantidade'] > 0 else 0
                }
                for _, dados in produtos_vendidos.items()
            ])
            
            # Ordena por quantidade vendida
            df_produtos = df_produtos.sort_values('Quantidade', ascending=False)
            
            # Exibe o gráfico dos 10 mais vendidos
            fig = px.bar(
                df_produtos.head(10),
                x='Produto',
                y='Quantidade',
                color='Categoria',
                title='Top 10 Produtos Mais Vendidos',
                labels={'Produto': '', 'Quantidade': 'Quantidade Vendida'}
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Exibe a tabela completa
            st.dataframe(
                df_produtos,
                column_config={
                    "Produto": "Produto",
                    "Categoria": "Categoria",
                    "Quantidade": st.column_config.NumberColumn("Qtd. Vendida", format="%d"),
                    "Valor Total": st.column_config.NumberColumn(
                        "Valor Total",
                        format="R$ %.2f"
                    ),
                    "Preço Médio": st.column_config.NumberColumn(
                        "Preço Médio",
                        format="R$ %.2f"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Nenhum dado de produto vendido disponível.")
    
    with tab3:
        # Relatório de clientes
        clientes = {}
        for venda in vendas:
            if venda.cliente_id:
                cliente = Cliente.buscar_por_id(venda.cliente_id)
                if cliente:
                    if cliente.id not in clientes:
                        clientes[cliente.id] = {
                            'nome': cliente.nome,
                            'email': cliente.email,
                            'telefone': cliente.telefone,
                            'quantidade_compras': 0,
                            'valor_total_gasto': 0.0,
                            'ultima_compra': None
                        }
                    clientes[cliente.id]['quantidade_compras'] += 1
                    clientes[cliente.id]['valor_total_gasto'] += venda.valor_total
                    if not clientes[cliente.id]['ultima_compra'] or venda.data_venda > clientes[cliente.id]['ultima_compra']:
                        clientes[cliente.id]['ultima_compra'] = venda.data_venda
        
        if clientes:
            df_clientes = pd.DataFrame([
                {
                    'Cliente': dados['nome'],
                    'Email': dados['email'],
                    'Telefone': dados['telefone'],
                    'Compras': dados['quantidade_compras'],
                    'Valor Total Gasto': dados['valor_total_gasto'],
                    'Ticket Médio': dados['valor_total_gasto'] / dados['quantidade_compras'] if dados['quantidade_compras'] > 0 else 0,
                    'Última Compra': format_date(dados['ultima_compra']) if dados['ultima_compra'] else 'N/A'
                }
                for _, dados in clientes.items()
            ])
            
            # Ordena por valor total gasto
            df_clientes = df_clientes.sort_values('Valor Total Gasto', ascending=False)
            
            # Exibe o gráfico dos 10 melhores clientes
            fig = px.bar(
                df_clientes.head(10),
                x='Cliente',
                y='Valor Total Gasto',
                title='Top 10 Clientes por Valor Gasto',
                labels={'Cliente': '', 'Valor Total Gasto': 'Valor Total Gasto (R$)'}
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Exibe a tabela completa
            st.dataframe(
                df_clientes,
                column_config={
                    "Cliente": "Cliente",
                    "Email": "E-mail",
                    "Telefone": "Telefone",
                    "Compras": st.column_config.NumberColumn("Nº Compras", format="%d"),
                    "Valor Total Gasto": st.column_config.NumberColumn(
                        "Valor Total Gasto",
                        format="R$ %.2f"
                    ),
                    "Ticket Médio": st.column_config.NumberColumn(
                        "Ticket Médio",
                        format="R$ %.2f"
                    ),
                    "Última Compra": "Última Compra"
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Nenhum dado de cliente disponível.")

# Se este arquivo for executado diretamente
if __name__ == "__main__":
    relatorios_page()
