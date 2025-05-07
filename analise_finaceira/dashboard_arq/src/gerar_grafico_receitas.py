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
receitas_logger = get_logger("dashboard.grafico_receitas")

def format_currency(value):
    """Formata valores monetários para exibição"""
    # Se for um número, formata normalmente
    if isinstance(value, (int, float)):
        return f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    # Se já for string, retorna como está
    return value

def conectar_banco():
    """Conecta ao banco de dados SQLite."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_path = os.path.join(base_dir, 'banco', 'financas.db')
        receitas_logger.debug(f"=== CONEXÃO COM BANCO DE DADOS ===")
        receitas_logger.debug(f"Diretório base: {base_dir}")
        receitas_logger.debug(f"Caminho do banco de dados: {db_path}")
        receitas_logger.debug(f"Arquivo do banco existe: {os.path.exists(db_path)}")
        
        # Verificar se o diretório do banco existe
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            receitas_logger.warning(f"Diretório do banco de dados não encontrado, criando: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
        
        # Tentar conectar ao banco
        conn = sqlite3.connect(db_path)
        receitas_logger.info("Conexão com o banco de dados estabelecida com sucesso")
        return conn
    except sqlite3.Error as e:
        receitas_logger.error(f"Erro ao conectar ao banco de dados: {e}", exc_info=True)
        raise

def obter_receitas_por_categoria(meses_atras=12):
    """
    Retorna um dicionário com o total de receitas por categoria.
    
    Args:
        meses_atras (int): Número de meses para trás a serem considerados
        
    Returns:
        dict: Dicionário com categorias e valores totais
    """
    conn = None
    try:
        print("\n=== OBTENDO RECEITAS POR CATEGORIA ===")
        print(f"Meses a serem considerados: {meses_atras}")
        
        # Conectar ao banco
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Verificar se a tabela transacoes existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transacoes'")
        if not cursor.fetchone():
            print("AVISO: Tabela 'transacoes' não encontrada no banco de dados.")
            return {}
            
        print("Tabela 'transacoes' encontrada. Continuando...")
        
        # Calcular a data de X meses atrás
        data_limite = (datetime.now() - timedelta(days=30*meses_atras)).strftime('%Y-%m-%d')
        receitas_logger.debug(f"Data limite para consulta: {data_limite}")
        
        # Consulta para obter o total de receitas por categoria no período
        query = """
        SELECT categoria, SUM(valor) as total
        FROM transacoes
        WHERE valor > 0  -- Apenas receitas (valores positivos)
        AND data >= ?  -- Apenas dados do período especificado
        GROUP BY categoria
        ORDER BY total DESC
        """
        
        print("Executando consulta SQL...")
        print(f"Filtrando receitas a partir de: {data_limite} (últimos {meses_atras} meses)")
        cursor.execute(query, (data_limite,))
        resultados = cursor.fetchall()
        
        print(f"Resultados da consulta: {resultados}")
        
        # Converter para dicionário
        receitas_por_categoria = {}
        for categoria, total in resultados:
            receitas_por_categoria[categoria] = total
        receitas_logger.debug(f"Total de registros encontrados: {len(resultados) if resultados else 0}")
        if receitas_por_categoria:
            print(f"Categorias: {list(receitas_por_categoria.keys())}")
            
        return receitas_por_categoria
        
    except sqlite3.Error as e:
        receitas_logger.error(f"Erro ao obter receitas por categoria: {e}", exc_info=True)
        return {}
    finally:
        if conn:
            conn.close()
            print("Conexão com o banco de dados fechada.")

def limpar_arquivos_antigos(diretorio, prefixo='grafico_receitas_', extensao='.html'):
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
                try:
                    caminho_arquivo = os.path.join(diretorio, arquivo)
                    os.remove(caminho_arquivo)
                    receitas_logger.debug(f"Arquivo antigo removido: {caminho_arquivo}")
                except Exception as e:
                    receitas_logger.error(f"Erro ao remover arquivo {arquivo}: {e}", exc_info=True)
    except Exception as e:
        receitas_logger.error(f"Erro ao limpar arquivos antigos: {e}", exc_info=True)

def gerar_grafico_receitas_por_categoria(meses_atras=12):
    """
    Gera um gráfico de rosca profissional com o total de receitas por categoria.
    
    Args:
        meses_atras (int): Número de meses para trás a serem considerados
        
    Returns:
        str: Caminho para o arquivo HTML gerado ou None em caso de erro
    """
    receitas_logger.info(f"Iniciando geração do gráfico de receitas para os últimos {meses_atras} meses...")
    print("\n" + "="*60)
    print("=== INICIANDO GERAÇÃO DO GRÁFICO DE RECEITAS ===")
    print("="*60)
    print(f"Diretório de trabalho: {os.getcwd()}")
    print(f"Arquivo atual: {os.path.abspath(__file__)}")
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
        img_filename = f"grafico_receitas_{timestamp}.html"
        img_path = os.path.abspath(os.path.join(img_dir, img_filename))
        print(f"Salvando novo gráfico de receitas em: {img_path}")
        
        # Verificar se o diretório pai da imagem existe
        if not os.path.exists(os.path.dirname(img_path)):
            print(f"Diretório pai não existe: {os.path.dirname(img_path)}")
            return None
    
        # Obter receitas por categoria
        print(f"Obtendo receitas por categoria (últimos {meses_atras} meses)...")
        receitas_por_categoria = obter_receitas_por_categoria(meses_atras=meses_atras)
        
        if not receitas_por_categoria:
            receitas_logger.warning("Nenhum dado de receita encontrado para o período.")
            return None
            
        # Converter para lista de tuplas e ordenar por valor (decrescente)
        resultados = sorted(receitas_por_categoria.items(), key=lambda x: x[1], reverse=True)
        
        # Criar DataFrame com os resultados
        df = pd.DataFrame(resultados, columns=['Categoria', 'Valor'])
        total = df['Valor'].sum()
        df['Porcentagem'] = (df['Valor'] / total) * 100
        
        # Ordenar por valor para melhor visualização
        df = df.sort_values('Valor', ascending=False)
        
        # Log dos resultados
        print(f"Total de categorias: {len(df)}")
        print(f"Valor total: R$ {total:,.2f}")
        for i, (_, row) in enumerate(df.iterrows(), 1):
            print(f"{i:2d}. {row['Categoria']}: R$ {row['Valor']:,.2f} ({row['Porcentagem']:.1f}%)")
        
        # Usar a mesma paleta de cores do gráfico de despesas
        
        # Criar o gráfico de rosca com Plotly
        fig = px.pie(
            df,
            values='Valor',
            names='Categoria',
            hole=0.5,  # Cria o efeito de rosca
            title=f'DISTRIBUIÇÃO DE RECEITAS POR CATEGORIA<br>'
                  f'<span style="color:gray; font-size:0.8em">Período: Últimos {meses_atras} meses | Total: {format_currency(total)}</span>',
            color_discrete_sequence=px.colors.sequential.Plasma,  # Usando uma paleta diferente do gráfico de despesas
            category_orders={"Categoria": df['Categoria'].tolist()}
        )
        
        # Configurar o layout
        fig.update_layout(
            title={
                'text': f'DISTRIBUIÇÃO DE RECEITAS POR CATEGORIA<br>'
                       f'<span style="color:gray; font-size:0.8em">Período: Últimos {meses_atras} meses | Total: {format_currency(total)}</span>',
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'size': 22, 'color': '#1a5276', 'family': 'Arial, sans-serif'}
            },
            margin=dict(t=120, b=80, l=20, r=20, pad=10),
            plot_bgcolor='white',
            paper_bgcolor='white',
            title_x=0.5,
            showlegend=True,
            legend=dict(
                title=dict(
                    text='<b>CATEGORIAS</b>',
                    font=dict(size=12, color='#1a5276')
                ),
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05,
                font=dict(size=11, color='#1a5276'),
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
            font_color='#1a5276',
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
            text=f"📅 Período: Últimos {meses_atras} meses • 📊 {len(df)} Categorias • "
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
                        'filename': f'receitas_por_categoria_{timestamp}',
                        'height': 800,
                        'width': 1200,
                        'scale': 2
                    },
                    'scrollZoom': True
                },
                default_width='100%',
                default_height='700px'
            )
            print(f"✅ Gráfico de receitas salvo com sucesso em: {img_path}")
        except Exception as e:
            receitas_logger.error(f"Erro ao salvar o gráfico: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            return None
        
        # Verificar se o arquivo foi criado
        if os.path.exists(img_path):
            file_size_kb = os.path.getsize(img_path) / 1024
            print(f"✅ Arquivo gerado com sucesso: {img_path} ({file_size_kb:.1f} KB)")
            return img_path
        else:
            print(f"❌ ERRO: O arquivo não foi criado: {img_path}")
            if os.path.exists(os.path.dirname(img_path)):
                print(f"📁 Conteúdo do diretório: {os.listdir(os.path.dirname(img_path))}")
            else:
                print(f"❌ Diretório não existe: {os.path.dirname(img_path)}")
            return None
            
    except Exception as e:
        receitas_logger.error(f"Erro ao gerar o gráfico: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    # Testar a função
    receitas_logger.info("Iniciando teste da geração de gráfico de receitas")
    caminho_imagem = gerar_grafico_receitas_por_categoria()
    if caminho_imagem:
        receitas_logger.info(f"Gráfico gerado com sucesso: {caminho_imagem}")
    else:
        receitas_logger.error("Falha ao gerar o gráfico.")
