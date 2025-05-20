import os
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger

# Configura o logger para este módulo
fluxo_caixa_logger = get_logger("dashboard.fluxo_caixa")

def format_currency(value):
    """Formata valores monetários para exibição"""
    # Se for um número, formata normalmente
    return f'R$ {float(value):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def conectar_banco():
    """Conecta ao banco de dados SQLite."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, 'banco', 'financas.db')
    return sqlite3.connect(db_path)

def obter_dados_fluxo_caixa(meses_atras=12):
    """
    Retorna um DataFrame com os dados de receitas e despesas por mês.
    
    Args:
        meses_atras (int): Número de meses para trás a serem considerados
        
    Returns:
        pd.DataFrame: DataFrame com os dados de fluxo de caixa
    """
    try:
        conn = conectar_banco()
        
        # Calcular a data de X meses atrás
        data_limite = (datetime.now() - timedelta(days=30*meses_atras)).strftime('%Y-%m-%d')
        fluxo_caixa_logger.info(f"Filtrando dados a partir de: {data_limite} (últimos {meses_atras} meses)")
        
        # Consulta para obter receitas e despesas por mês
        query = """
        SELECT 
            strftime('%Y-%m', data) as mes,
            SUM(CASE WHEN valor > 0 THEN valor ELSE 0 END) as total_receitas,
            SUM(ABS(CASE WHEN valor < 0 THEN valor ELSE 0 END)) as total_despesas
        FROM transacoes
        WHERE data >= ?
        GROUP BY strftime('%Y-%m', data)
        ORDER BY mes
        """
        
        # Executar a consulta
        fluxo_caixa = pd.read_sql_query(query, conn, params=(data_limite,))
        
        # Calcular o saldo mensal
        fluxo_caixa['saldo'] = fluxo_caixa['total_receitas'] - abs(fluxo_caixa['total_despesas'])
        
        # Converter a coluna 'mes' para datetime para ordenação correta
        fluxo_caixa['mes'] = pd.to_datetime(fluxo_caixa['mes'] + '-01')
        fluxo_caixa = fluxo_caixa.sort_values('mes')
        
        # Formatar a coluna 'mes' para exibição
        fluxo_caixa['mes_formatado'] = fluxo_caixa['mes'].dt.strftime('%b/%Y')
        
        return fluxo_caixa
        
    except Exception as e:
        fluxo_caixa_logger.error(f"Erro ao obter dados de fluxo de caixa: {str(e)}", exc_info=True)
        if 'conn' in locals():
            conn.close()
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def limpar_arquivos_antigos(diretorio, prefixo='grafico_fluxo_caixa_', extensao='.html'):
    """
    Remove arquivos antigos no diretório especificado que correspondam ao prefixo e extensão.
    
    Args:
        diretorio (str): Caminho do diretório
        prefixo (str): Prefixo dos arquivos a serem removidos
        extensao (str): Extensão dos arquivos a serem removidos
    """
    try:
        # Garante que o diretório existe
        os.makedirs(diretorio, exist_ok=True)
        
        # Lista todos os arquivos no diretório
        for arquivo in os.listdir(diretorio):
            if arquivo.startswith(prefixo) and arquivo.endswith(extensao):
                try:
                    caminho_arquivo = os.path.join(diretorio, arquivo)
                    os.remove(caminho_arquivo)
                    fluxo_caixa_logger.debug(f"Arquivo antigo removido: {caminho_arquivo}")
                except Exception as e:
                    fluxo_caixa_logger.warning(f"Falha ao remover arquivo antigo {arquivo}: {str(e)}")
    except Exception as e:
        fluxo_caixa_logger.error(f"Erro ao limpar arquivos antigos: {str(e)}", exc_info=True)

def gerar_grafico_fluxo_caixa(meses_atras=12):
    """
    Gera um gráfico de barras mostrando o fluxo de caixa (receitas, despesas e saldo) por mês.
    
    Args:
        meses_atras (int): Número de meses para trás a serem considerados
        
    Returns:
        str: Caminho para o arquivo HTML gerado ou None em caso de erro
    """
    try:
        fluxo_caixa_logger.info(f"Iniciando geração do gráfico de fluxo de caixa para os últimos {meses_atras} meses")
        
        # Obter os dados
        df = obter_dados_fluxo_caixa(meses_atras)
        
        if df is None or df.empty:
            fluxo_caixa_logger.warning("Nenhum dado encontrado para o período especificado")
            return None
        
        # Criar o gráfico de barras
        fig = go.Figure()
        
        # Adicionar barras de receitas
        fig.add_trace(go.Bar(
            x=df['mes_formatado'],
            y=df['total_receitas'],
            name='Receitas',
            marker_color='#28a745',
            text=df['total_receitas'].apply(format_currency),
            textposition='auto',
            textfont=dict(
                size=10,
            )
        ))
        
        # Adicionar barras de despesas
        fig.add_trace(go.Bar(
            x=df['mes_formatado'],
            y=df['total_despesas'],
            name='Despesas',
            marker_color='#dc3545',
            text=df['total_despesas'].apply(format_currency),
            textposition='auto',
            textfont=dict(
                size=10,
            )
        ))
        
        # Adicionar linha de saldo
        fig.add_trace(go.Scatter(
            x=df['mes_formatado'],
            y=df['saldo'],
            name='Saldo',
            mode='lines+markers+text',
            line=dict(color='#007bff', width=3),
            marker=dict(size=10, symbol='diamond', color='#007bff'),
            text=df['saldo'].apply(format_currency),
            textposition='top center',
            textfont=dict(
                size=10,
                color='#007bff'
            )
        ))
        
        # Atualizar layout
        fig.update_layout(
            title={
                'text': f'<b>Fluxo de Caixa - Últimos {meses_atras} Meses</b>',
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'size': 28, 'family': 'Arial, sans-serif', 'color': '#2c3e50'}
            },
            xaxis_title={
                'text': 'Mês',
                'font': {'size': 18, 'family': 'Arial, sans-serif', 'color': '#2c3e50'}
            },
            yaxis_title={
                'text': 'Valor (R$)',
                'font': {'size': 18, 'family': 'Arial, sans-serif', 'color': '#2c3e50'}
            },
            barmode='group',
            plot_bgcolor='rgba(255,255,255,1)',
            paper_bgcolor='rgba(255,255,255,1)',
            font=dict(family="Arial, sans-serif", size=16, color="#2c3e50"),
            margin=dict(l=100, r=100, t=120, b=100),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=16, family="Arial, sans-serif", color="#2c3e50"),
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='#ddd',
                borderwidth=1
            ),
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='rgba(255,255,255,0.95)',
                font_size=16,
                font_family="Arial, sans-serif",
                font_color='#2c3e50',
                bordercolor='#ddd'
            ),
            height=700,
            width=1200,
            showlegend=True,
            legend_title_text='Legenda',
            legend_title_font=dict(size=16, family="Arial, sans-serif", color="#2c3e50"),
            bargap=0.15,
            bargroupgap=0.1,
            xaxis=dict(
                tickfont=dict(size=16, color='#2c3e50'),
                tickangle=45,
                tickmode='auto',
                nticks=12
            ),
            yaxis=dict(
                tickfont=dict(size=16, color='#2c3e50'),
                gridcolor='#eee',
                gridwidth=1,
                zerolinecolor='#ddd',
                zerolinewidth=2
            )
        )
        
        # Formatar o eixo Y para moeda
        fig.update_yaxes(
            tickprefix='R$ ',
            tickformat=",.2f",
            gridcolor='rgba(0,0,0,0.1)',
            gridwidth=1,
            zeroline=True,
            zerolinecolor='rgba(0,0,0,0.2)',
            zerolinewidth=2,
            tickfont=dict(size=16, family="Arial, sans-serif", color="#2c3e50")
        )
        
        # Criar diretório para os gráficos se não existir
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        img_dir = os.path.join(base_dir, 'dashboard_arq', 'static', 'img')
        os.makedirs(img_dir, exist_ok=True)
        
        # Limpar arquivos antigos
        limpar_arquivos_antigos(img_dir, 'grafico_fluxo_caixa_', '.html')
        
        # Gerar nome do arquivo com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f'grafico_fluxo_caixa_{timestamp}.html'
        caminho_arquivo = os.path.join(img_dir, nome_arquivo)
        
        # Salvar o gráfico como HTML
        try:
            fig.write_html(
                caminho_arquivo,
                full_html=True,
                include_plotlyjs='cdn',
                config={
                    'displayModeBar': True,
                    'scrollZoom': True,
                    'responsive': True,
                    'displaylogo': False
                }
            )
            fluxo_caixa_logger.info(f"Gráfico de fluxo de caixa salvo com sucesso em: {caminho_arquivo}")
            return caminho_arquivo
        except Exception as e:
            fluxo_caixa_logger.error(f"Erro ao salvar o gráfico: {str(e)}", exc_info=True)
            return None
        
        fluxo_caixa_logger.info(f"Gráfico de fluxo de caixa salvo em: {caminho_arquivo}")
        return caminho_arquivo
        
    except Exception as e:
        fluxo_caixa_logger.error(f"Erro ao gerar gráfico de fluxo de caixa: {str(e)}", exc_info=True)
        return None

if __name__ == "__main__":
    # Testar a função
    fluxo_caixa_logger.info("Iniciando teste da geração de gráfico de fluxo de caixa")
    caminho_imagem = gerar_grafico_fluxo_caixa()
    if caminho_imagem:
        fluxo_caixa_logger.info(f"Gráfico gerado com sucesso: {caminho_imagem}")
    else:
        fluxo_caixa_logger.error("Falha ao gerar o gráfico de fluxo de caixa")
