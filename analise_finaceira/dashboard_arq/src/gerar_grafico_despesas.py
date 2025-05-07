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
grafico_logger = get_logger("dashboard.grafico_despesas")

def format_currency(value):
    """Formata valores monetários para exibição"""
    # Se for um número, formata normalmente
    return f'R$ {float(value):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def conectar_banco():
    """Conecta ao banco de dados SQLite."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, 'banco', 'financas.db')
    return sqlite3.connect(db_path)

def obter_despesas_por_categoria(meses_atras=12):
    """
    Retorna um dicionário com o total de despesas por categoria.
    
    Args:
        meses_atras (int): Número de meses para trás a serem considerados
        
    Returns:
        dict: Dicionário com categorias e valores totais
    """
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Calcular a data de X meses atrás
        data_limite = (datetime.now() - timedelta(days=30*meses_atras)).strftime('%Y-%m-%d')
        grafico_logger.info(f"Filtrando despesas a partir de: {data_limite} (últimos {meses_atras} meses)")
        
        query = """
        SELECT 
            categoria,
            SUM(ABS(valor)) as total
        FROM transacoes
        WHERE data >= ? 
        AND valor < 0
        GROUP BY categoria
        ORDER BY total DESC
        """
        
        cursor.execute(query, (data_limite,))
        resultados = cursor.fetchall()
        
        # Converter para dicionário
        despesas_por_categoria = {}
        for categoria, total in resultados:
            despesas_por_categoria[categoria] = round(total, 2)
            
        return despesas_por_categoria
        
    except sqlite3.Error as e:
        grafico_logger.error(f"Erro ao obter despesas por categoria: {e}", exc_info=True)
        return {}
    finally:
        if 'conn' in locals():
            conn.close()

def limpar_arquivos_antigos(diretorio, prefixo='grafico_despesas_', extensao='.html'):
    """
    Remove arquivos antigos no diretório especificado que correspondam ao prefixo e extensão.
    
    Args:
        diretorio (str): Caminho do diretório
        prefixo (str): Prefixo dos arquivos a serem removidos
        extensao (str): Extensão dos arquivos a serem removidos
    """
    try:
        if not os.path.exists(diretorio):
            return
            
        # Lista todos os arquivos no diretório
        for arquivo in os.listdir(diretorio):
            if arquivo.startswith(prefixo) and arquivo.endswith(extensao):
                caminho_arquivo = os.path.join(diretorio, arquivo)
                try:
                    os.remove(caminho_arquivo)
                    grafico_logger.debug(f"Arquivo removido: {caminho_arquivo}")
                except Exception as e:
                    grafico_logger.error(f"Erro ao remover arquivo {caminho_arquivo}: {e}", exc_info=True)
    except Exception as e:
        grafico_logger.error(f"Erro ao limpar arquivos antigos: {e}", exc_info=True)

def gerar_grafico_despesas_por_categoria(meses_atras=12):
    """
    Gera um gráfico de pizza profissional com o total de despesas por categoria.
    
    Args:
        meses_atras (int): Número de meses para trás a serem considerados
        
    Returns:
        str: Caminho para o arquivo de imagem gerado ou None em caso de erro
    """
    print("\n" + "="*60)
    print("=== INICIANDO GERAÇÃO DO GRÁFICO DE DESPESAS ===")
    print("="*60)
    print(f"Diretório de trabalho: {os.getcwd()}")
    print(f"Arquivo atual: {os.path.abspath(__file__)}")
    print(f"Meses a serem considerados: {meses_atras}")
    
    try:
        # Configurar caminhos
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        img_dir = os.path.join(base_dir, 'dashboard_arq', 'static', 'img')
        
        # Garantir que o diretório existe
        os.makedirs(img_dir, exist_ok=True)
        
        # Limpar gráficos antigos
        limpar_arquivos_antigos(img_dir)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        img_filename = f"grafico_despesas_{timestamp}.html"
        img_path = os.path.abspath(os.path.join(img_dir, img_filename))
        print(f"Salvando novo gráfico em: {img_path}")
        
        # Verificar se o diretório pai da imagem existe
        if not os.path.exists(os.path.dirname(img_path)):
            print(f"Diretório pai não existe: {os.path.dirname(img_path)}")
            return None
    
        # Registrar início do processo
        grafico_logger.info(f"Iniciando geração do gráfico de despesas para os últimos {meses_atras} meses...")
        # Obter despesas por categoria
        print(f"Obtendo despesas por categoria (últimos {meses_atras} meses)...")
        despesas_por_categoria = obter_despesas_por_categoria(meses_atras=meses_atras)
        
        if not despesas_por_categoria:
            grafico_logger.warning("Nenhum dado de despesa encontrado para o período.")
            return None
            
        # Converter para lista de tuplas e ordenar por valor (decrescente)
        resultados = sorted(despesas_por_categoria.items(), key=lambda x: x[1], reverse=True)
        
        print(f"Resultados encontrados: {len(resultados)}")
        for i, (categoria, total) in enumerate(resultados, 1):
            print(f"{i}. {categoria}: R$ {total:,.2f}")
        
        # Criar DataFrame com os resultados
        df = pd.DataFrame(resultados, columns=['Categoria', 'Valor'])
        total = df['Valor'].sum()
        df['Porcentagem'] = (df['Valor'] / total) * 100
        
        # Ordenar por valor para melhor visualização
        df = df.sort_values('Valor', ascending=False)
        
        # Criar o gráfico de rosca com Plotly
        fig = px.pie(
            df,
            values='Valor',
            names='Categoria',
            hole=0.5,  # Cria o efeito de rosca
            title=f'DESPESAS POR CATEGORIA (ÚLTIMOS {meses_atras} MESES)<br>'
                  f'<span style="color:gray; font-size:0.8em">Total: {format_currency(total)}</span>',
            color_discrete_sequence=px.colors.sequential.Viridis,
            category_orders={"Categoria": df['Categoria'].tolist()}
        )
        
        # Configurar o título separadamente
        fig.update_layout(
            title={
                'text': f'DISTRIBUIÇÃO DE DESPESAS POR CATEGORIA<br>'
                       f'<span style="color:gray; font-size:0.8em">Período: Últimos {meses_atras} meses | Total: {format_currency(total)}</span>',
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'size': 22, 'color': '#2c3e50'}
            },
            margin=dict(t=120, b=80, l=20, r=20, pad=10),
            plot_bgcolor='white',
            paper_bgcolor='white',
            title_x=0.5,
            showlegend=True,
            legend=dict(
                title=dict(
                    text='<b>CATEGORIAS</b>',
                    font=dict(size=12, color='#2c3e50')
                ),
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05,
                font=dict(size=11, color='#34495e'),
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='#e1e4e8',
                borderwidth=1,
                itemclick=False,
                itemdoubleclick=False
            )
        )
        
        # Adicionar coluna formatada
        df['ValorFormatado'] = df['Valor'].apply(lambda x: f'R$ {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        # Adicionar anotações centrais
        fig.add_annotation(
            text=f"<b>{format_currency(total)}</b>",
            x=0.5,
            y=0.5,
            font_size=20,
            font_color='#2c3e50',
            showarrow=False,
            yanchor='middle',
            xref='paper',
            yref='paper'
        )
        
        fig.add_annotation(
            text="<b>Total</b>",
            x=0.5,
            y=0.6,
            font_size=14,
            font_color='#7f8c8d',
            showarrow=False,
            yanchor='bottom',
            xref='paper',
            yref='paper'
        )
        
        # Preparar dados adicionais para o hover
        df['Ranking'] = range(1, len(df) + 1)
        
        # Atualizar traços (slices do gráfico)
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            texttemplate='<b>%{label}</b><br>%{percent:.1%}<br>%{customdata[0]}',
            textfont=dict(
                size=12,
                color='white',
                family='Arial, sans-serif'
            ),
            hovertemplate=(
                '<b>%{label}</b><br>'
                'Valor: %{customdata[0]}<br>'
                'Percentual: %{percent:.1%}<br>'
                'Ranking: %{customdata[1]}° maior<extra></extra>'
            ),
            marker=dict(
                line=dict(color='#ffffff', width=1)
            ),
            customdata=df[['ValorFormatado', 'Ranking']].values,
            rotation=90
        )
        
        # Adicionar informações adicionais no rodapé
        fig.add_annotation(
            text=f"📅 Período: Últimos {meses_atras} meses • "
                 f"📊 {len(df)} Categorias • "
                 f"🔝 Maior: {df['Categoria'].iloc[0]} ({df['Porcentagem'].iloc[0]:.1f}%)",
            x=0.5,
            y=-0.15,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=11, color="#7f8c8d"),
            align="center"
        )
        
        # Adicionar logo ou informação de rodapé
        fig.add_annotation(
            text="<i>Análise Financeira Pessoal</i>",
            x=0.5,
            y=-0.2,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=10, color="#bdc3c7"),
            align="center"
        )
        
        # Configurações adicionais
        fig.update_layout(
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial, sans-serif"
            ),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(t=120, b=100, l=20, r=20, pad=10)
        )
        
        # Salvar o gráfico como HTML interativo
        try:
            fig.write_html(
                img_path,
                full_html=True,  
                include_plotlyjs='cdn',  
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['select2d', 'lasso2d', 'autoScale2d'],
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': f'despesas_por_categoria_{timestamp}',
                        'height': 800,
                        'width': 1200,
                        'scale': 2
                    },
                    'scrollZoom': True
                },
                default_width='100%',
                default_height='700px'
            )
            print(f"✅ Gráfico salvo com sucesso em: {img_path}")
        except Exception as e:
            print(f"❌ Erro ao salvar o gráfico: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        # Verificar se o arquivo foi criado
        if os.path.exists(img_path):
            file_size_kb = os.path.getsize(img_path) / 1024
            print(f"✅ Gráfico interativo salvo com sucesso em: {img_path} ({file_size_kb:.1f} KB)")
            return img_path
        else:
            print(f"❌ ERRO: O arquivo não foi criado: {img_path}")
            if os.path.exists(os.path.dirname(img_path)):
                print(f"📁 Conteúdo do diretório: {os.listdir(os.path.dirname(img_path))}")
            else:
                print(f"❌ Diretório não existe: {os.path.dirname(img_path)}")
            return None
        
    except Exception as e:
        grafico_logger.error(f"Erro ao gerar o gráfico: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    # Testar a função
    grafico_logger.info("Iniciando teste da geração de gráfico de despesas")
    caminho_imagem = gerar_grafico_despesas_por_categoria()
    if caminho_imagem:
        grafico_logger.info(f"Gráfico gerado com sucesso: {caminho_imagem}")
    else:
        grafico_logger.error("Falha ao gerar o gráfico.")
