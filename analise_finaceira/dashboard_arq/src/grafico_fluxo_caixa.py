import os
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger

# Configura o logger para este módulo
fluxo_caixa_logger = get_logger("dashboard.fluxo_caixa")

def format_currency(value):
    """Formata valores monetários para exibição"""
    if isinstance(value, (int, float)):
        return f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return value

def criar_tabela_transacoes(conn):
    """Cria a tabela de transações se ela não existir."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL,
            descricao TEXT,
            valor REAL NOT NULL,
            categoria TEXT,
            tipo TEXT
        )
        """)
        conn.commit()
        fluxo_caixa_logger.info("Tabela 'transacoes' verificada/criada com sucesso.")
    except sqlite3.Error as e:
        fluxo_caixa_logger.error(f"Erro ao criar a tabela 'transacoes': {e}", exc_info=True)
        raise

def conectar_banco():
    """Conecta ao banco de dados SQLite."""
    conn = None
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_dir = os.path.join(base_dir, 'banco')
        db_path = os.path.join(db_dir, 'financas.db')
        
        # Verificar se o diretório do banco existe
        if not os.path.exists(db_dir):
            fluxo_caixa_logger.warning(f"Diretório do banco de dados não encontrado, criando: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
        
        # Verificar se o arquivo do banco existe
        novo_banco = not os.path.exists(db_path)
        fluxo_caixa_logger.debug(f"Novo banco de dados: {novo_banco}")
        
        # Conectar ao banco de dados
        conn = sqlite3.connect(db_path)
        fluxo_caixa_logger.info(f"Conexão com o banco de dados estabelecida: {db_path}")
        
        # Se for um novo banco, criar a estrutura necessária
        if novo_banco:
            fluxo_caixa_logger.info("Criando a estrutura do banco de dados...")
            criar_tabela_transacoes(conn)
        
        return conn
        
    except sqlite3.Error as e:
        fluxo_caixa_logger.error(f"Erro ao conectar ao banco de dados: {e}", exc_info=True)
        if conn:
            conn.close()
        raise
    except Exception as e:
        fluxo_caixa_logger.error(f"Erro inesperado ao conectar ao banco de dados: {e}", exc_info=True)
        if conn:
            conn.close()
        raise

def obter_dados_fluxo_caixa():
    """
    Retorna um DataFrame com os dados de fluxo de caixa mensal.
    
    Returns:
        pd.DataFrame: DataFrame com as colunas 'data', 'receitas', 'despesas', 'saldo'
    """
    fluxo_caixa_logger.info("Obtendo dados do fluxo de caixa")
    fluxo_caixa_logger.debug(f"Diretório de trabalho: {os.getcwd()}")
    fluxo_caixa_logger.debug(f"Arquivo atual: {os.path.abspath(__file__)}")
    
    try:
        fluxo_caixa_logger.info("Obtendo dados de fluxo de caixa")
        fluxo_caixa_logger.debug(f"Diretório de trabalho atual: {os.getcwd()}")
        
        # Caminho para o banco de dados
        db_path = os.path.join('banco', 'financas.db')
        fluxo_caixa_logger.debug(f"Caminho do banco de dados: {os.path.abspath(db_path)}")
        
        # Verificar se o arquivo do banco de dados existe
        if not os.path.exists(db_path):
            fluxo_caixa_logger.error("Arquivo do banco de dados não encontrado!")
            return pd.DataFrame()
        
        fluxo_caixa_logger.info("Conectando ao banco de dados...")
        conn = conectar_banco()
        
        # Primeiro, verificar se a tabela transacoes existe
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = cursor.fetchall()
        fluxo_caixa_logger.debug(f"Tabelas encontradas no banco de dados: {[t[0] for t in tabelas]}")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transacoes'")
        if not cursor.fetchone():
            fluxo_caixa_logger.warning("Nenhum dado de transação encontrado no banco de dados.")
            return pd.DataFrame()
            
        fluxo_caixa_logger.info("Tabela 'transacoes' encontrada. Continuando...")
        
        # Consulta otimizada para obter receitas e despesas por mês
        query = """
        WITH meses AS (
            SELECT date('now', 'start of month', '-' || n || ' months') as data_mes
            FROM (
                SELECT 0 as n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 
                UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 
                UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 
                UNION SELECT 10 UNION SELECT 11
            )
        )
        SELECT 
            strftime('%Y-%m', m.data_mes) as mes,
            COALESCE(
                (SELECT SUM(t.valor) 
                 FROM transacoes t 
                 WHERE t.valor > 0 
                 AND strftime('%Y-%m', t.data) = strftime('%Y-%m', m.data_mes)), 
                0
            ) as receitas,
            COALESCE(
                (SELECT ABS(SUM(t.valor)) 
                 FROM transacoes t 
                 WHERE t.valor < 0 
                 AND strftime('%Y-%m', t.data) = strftime('%Y-%m', m.data_mes)), 
                0
            ) as despesas
        FROM meses m
        ORDER BY m.data_mes;
        """
        
        fluxo_caixa_logger.info("Executando consulta SQL...")
        df = pd.read_sql_query(query, conn)
        
        fluxo_caixa_logger.debug(f"Dados retornados pela consulta SQL ({len(df)} registros):")
        fluxo_caixa_logger.debug(df.head())
        
        # Verificar se há dados
        if df.empty:
            fluxo_caixa_logger.warning("Aviso: Nenhum dado retornado pela consulta SQL")
            return df
            
        # Calcular saldo mensal
        df['saldo'] = df['receitas'] - df['despesas']
        
        # Formatar data para exibição
        df['data_formatada'] = pd.to_datetime(df['mes'] + '-01').dt.strftime('%b/%Y')
        
        fluxo_caixa_logger.info("\nDados após processamento:")
        fluxo_caixa_logger.debug(df[['mes', 'receitas', 'despesas', 'saldo', 'data_formatada']])
        
        return df
        
    except sqlite3.Error as e:
        fluxo_caixa_logger.error(f"Erro ao consultar o banco de dados: {e}", exc_info=True)
        return pd.DataFrame()
    except Exception as e:
        fluxo_caixa_logger.error(f"Erro inesperado: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        if 'conn' in locals():
            conn.close()
            fluxo_caixa_logger.info("Conexão com o banco de dados fechada.")

def limpar_arquivos_antigos(diretorio, prefixo='grafico_fluxo_caixa_', extensao='.html'):
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
                    fluxo_caixa_logger.debug(f"Arquivo removido: {caminho_arquivo}")
                except Exception as e:
                    fluxo_caixa_logger.error(f"Erro ao remover arquivo {caminho_arquivo}: {e}", exc_info=True)
    except Exception as e:
        fluxo_caixa_logger.error(f"Erro ao limpar arquivos antigos: {e}", exc_info=True)

def gerar_grafico_fluxo_caixa():
    """
    Gera um gráfico de fluxo de caixa mensal com base nos dados do banco de dados.
    
    Returns:
        str: Caminho para o arquivo HTML gerado ou None em caso de erro.
    """
    fluxo_caixa_logger.info("Iniciando geração do gráfico de fluxo de caixa")
    fluxo_caixa_logger.debug(f"Diretório de trabalho: {os.getcwd()}")
    fluxo_caixa_logger.debug(f"Arquivo atual: {os.path.abspath(__file__)}")
    
    try:
        fluxo_caixa_logger.info("Iniciando geração do gráfico de fluxo de caixa")
        fluxo_caixa_logger.debug(f"Diretório de trabalho atual: {os.getcwd()}")
        
        # Imprimir informações do ambiente
        fluxo_caixa_logger.debug(f"Diretório de trabalho atual: {os.getcwd()}")
        fluxo_caixa_logger.debug(f"Arquivo atual: {os.path.abspath(__file__)}")
        
        # Verificar se o diretório de imagens existe e tem permissão de escrita
        img_dir = os.path.join('dashboard_arq', 'static', 'img')
        img_abs_path = os.path.abspath(img_dir)
        fluxo_caixa_logger.debug(f"Caminho do diretório de imagens: {img_abs_path}")
        fluxo_caixa_logger.debug(f"Diretório existe: {os.path.exists(img_abs_path)}")
        
        if os.path.exists(img_abs_path):
            fluxo_caixa_logger.debug(f"Permissão de escrita: {os.access(img_abs_path, os.W_OK)}")
        else:
            fluxo_caixa_logger.warning("AVISO: Diretório de imagens não existe! Tentando criar...")
            try:
                os.makedirs(img_abs_path, exist_ok=True)
                fluxo_caixa_logger.info(f"Diretório criado com sucesso em: {img_abs_path}")
                fluxo_caixa_logger.debug(f"Permissão de escrita: {os.access(img_abs_path, os.W_OK)}")
            except Exception as e:
                fluxo_caixa_logger.error(f"ERRO ao criar diretório de imagens: {e}", exc_info=True)
        
        # Verificar se o diretório pai (static) existe
        static_dir = os.path.join('dashboard_arq', 'static')
        static_abs_path = os.path.abspath(static_dir)
        fluxo_caixa_logger.debug(f"Caminho do diretório static: {static_abs_path}")
        fluxo_caixa_logger.debug(f"Diretório existe: {os.path.exists(static_abs_path)}")
        
        if os.path.exists(static_abs_path):
            fluxo_caixa_logger.debug(f"Permissão de escrita: {os.access(static_abs_path, os.W_OK)}")
        else:
            fluxo_caixa_logger.warning("AVISO: Diretório static não existe! Tentando criar...")
            try:
                os.makedirs(static_abs_path, exist_ok=True)
                fluxo_caixa_logger.info(f"Diretório criado com sucesso em: {static_abs_path}")
                fluxo_caixa_logger.debug(f"Permissão de escrita: {os.access(static_abs_path, os.W_OK)}")
            except Exception as e:
                fluxo_caixa_logger.error(f"ERRO ao criar diretório static: {e}", exc_info=True)
        
        # Verificar se o diretório dashboard_arq existe
        dashboard_dir = 'dashboard_arq'
        dashboard_abs_path = os.path.abspath(dashboard_dir)
        fluxo_caixa_logger.debug(f"Caminho do diretório dashboard_arq: {dashboard_abs_path}")
        fluxo_caixa_logger.debug(f"Diretório existe: {os.path.exists(dashboard_abs_path)}")
        
        if os.path.exists(dashboard_abs_path):
            fluxo_caixa_logger.debug(f"Permissão de escrita: {os.access(dashboard_abs_path, os.W_OK)}")
        else:
            fluxo_caixa_logger.error("ERRO CRÍTICO: Diretório dashboard_arq não existe!")
            return None
        
        # Imprimir diretório de trabalho atual
        fluxo_caixa_logger.debug(f"Diretório de trabalho atual: {os.getcwd()}")
        
        # Verificar se o diretório de imagens existe
        img_dir = os.path.join('dashboard_arq', 'static', 'img')
        fluxo_caixa_logger.debug(f"Caminho do diretório de imagens: {os.path.abspath(img_dir)}")
        fluxo_caixa_logger.debug(f"Diretório existe: {os.path.exists(img_dir)}")
        if os.path.exists(img_dir):
            fluxo_caixa_logger.debug(f"Permissão de escrita: {os.access(img_dir, os.W_OK)}")
        
        # Verificar se o diretório pai (static) existe
        static_dir = os.path.join('dashboard_arq', 'static')
        fluxo_caixa_logger.debug(f"Caminho do diretório static: {os.path.abspath(static_dir)}")
        fluxo_caixa_logger.debug(f"Diretório static existe: {os.path.exists(static_dir)}")
        if os.path.exists(static_dir):
            fluxo_caixa_logger.debug(f"Permissão de escrita no static: {os.access(static_dir, os.W_OK)}")
        
        # Verificar se o diretório dashboard_arq existe
        dashboard_dir = 'dashboard_arq'
        fluxo_caixa_logger.debug(f"Caminho do diretório dashboard_arq: {os.path.abspath(dashboard_dir)}")
        fluxo_caixa_logger.debug(f"Diretório dashboard_arq existe: {os.path.exists(dashboard_dir)}")
        if os.path.exists(dashboard_dir):
            fluxo_caixa_logger.debug(f"Permissão de escrita no dashboard_arq: {os.access(dashboard_dir, os.W_OK)}")
        
        # Configurar caminhos
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        img_dir = os.path.join(base_dir, 'dashboard_arq', 'static', 'img')
        
        fluxo_caixa_logger.debug(f"Configuração de diretórios:")
        fluxo_caixa_logger.debug(f"- Diretório base: {base_dir}")
        fluxo_caixa_logger.debug(f"- Diretório de imagens: {img_dir}")
        
        # Garantir que o diretório existe
        try:
            fluxo_caixa_logger.debug(f"=== Verificando diretório de imagens ===")
            fluxo_caixa_logger.debug(f"- Diretório base: {base_dir}")
            fluxo_caixa_logger.debug(f"- Caminho completo do diretório de imagens: {img_dir}")
            fluxo_caixa_logger.debug(f"- Diretório existe antes de criar: {os.path.exists(img_dir)}")
            
            # Criar o diretório se não existir
            os.makedirs(img_dir, exist_ok=True)
            
            fluxo_caixa_logger.debug(f"- Diretório existe após tentativa de criação: {os.path.exists(img_dir)}")
            fluxo_caixa_logger.debug(f"- Permissão de escrita no diretório: {os.access(img_dir, os.W_OK)}")
            
            # Tentar criar um arquivo de teste
            test_file = os.path.join(img_dir, 'teste_permissao.txt')
            try:
                with open(test_file, 'w') as f:
                    f.write('teste')
                os.remove(test_file)
                fluxo_caixa_logger.debug("- Teste de escrita/leitura no diretório bem-sucedido")
            except Exception as e:
                fluxo_caixa_logger.error(f"- ERRO ao testar escrita no diretório: {e}", exc_info=True)
                return None
                
        except Exception as e:
            fluxo_caixa_logger.error(f"ERRO ao criar/acessar diretório: {e}", exc_info=True)
            return None
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        img_filename = f"grafico_fluxo_caixa_{timestamp}.html"
        img_path = os.path.abspath(os.path.join(img_dir, img_filename))
        fluxo_caixa_logger.info(f"Salvando novo gráfico de fluxo de caixa em: {img_path}")
        
        # Verificar se o caminho é válido
        try:
            with open(os.path.join(img_dir, 'teste.txt'), 'w') as f:
                f.write('teste')
            os.remove(os.path.join(img_dir, 'teste.txt'))
            fluxo_caixa_logger.debug("- Teste de escrita/leitura no diretório bem-sucedido")
        except Exception as e:
            fluxo_caixa_logger.error(f"ERRO ao testar escrita no diretório: {e}", exc_info=True)
            return None
        
        # Obter dados
        fluxo_caixa_logger.info("Obtendo dados para o gráfico...")
        df = obter_dados_fluxo_caixa()
        
        if df.empty:
            fluxo_caixa_logger.warning("Nenhum dado disponível para gerar o gráfico de fluxo de caixa.")
            return None
            
        fluxo_caixa_logger.info(f"Dados obtidos com sucesso. Total de registros: {len(df)}")
        fluxo_caixa_logger.debug(df.head())
        
        # Calcular totais para o título
        total_receitas = df['receitas'].sum()
        total_despesas = df['despesas'].sum()
        saldo_total = total_receitas - total_despesas
        
        # Criar o gráfico
        fig = go.Figure()
        
        # Adicionar barras para receitas e despesas
        fig.add_trace(go.Bar(
            x=df['data_formatada'],
            y=df['receitas'],
            name='Receitas',
            marker_color='#2ecc71',
            hovertemplate='<b>%{x}</b><br>Receitas: %{customdata[0]}<extra></extra>',
            customdata=df[['receitas']].apply(lambda x: [format_currency(val) for val in x], axis=1),
            opacity=0.8,
            width=0.4,  # Largura das barras
            marker_line_color='rgba(0,0,0,0.5)',
            marker_line_width=0.5
        ))
        
        fig.add_trace(go.Bar(
            x=df['data_formatada'],
            y=df['despesas'],
            name='Despesas',
            marker_color='#e74c3c',
            hovertemplate='<b>%{x}</b><br>Despesas: %{customdata[0]}<extra></extra>',
            customdata=df[['despesas']].apply(lambda x: [format_currency(val) for val in x], axis=1),
            opacity=0.8,
            width=0.4,  # Largura das barras
            marker_line_color='rgba(0,0,0,0.5)',
            marker_line_width=0.5
        ))
        
        # Adicionar linha de saldo
        fig.add_trace(go.Scatter(
            x=df['data_formatada'],
            y=df['saldo'],
            mode='lines+markers',
            name='Saldo',
            line=dict(color='#3498db', width=3, dash='dot'),
            marker=dict(
                size=8, 
                color='#2980b9',
                line=dict(width=1, color='white')
            ),
            hovertemplate='<b>%{x}</b><br>Saldo: %{customdata[0]}<extra></extra>',
            customdata=df[['saldo']].apply(lambda x: [format_currency(val) for val in x], axis=1),
            yaxis='y2',  # Usar um eixo y secundário para o saldo
            connectgaps=True
        ))
        
        # Configurar layout para ter dois eixos y
        fig.update_layout(
            barmode='group',
            yaxis2=dict(
                title=dict(
                    text='Saldo (R$)',
                    font=dict(color='#3498db', size=12)
                ),
                tickfont=dict(color='#3498db', size=10),
                anchor='x',
                overlaying='y',
                side='right',
                showgrid=False,
                zeroline=False,
                showline=True,
                linecolor='#3498db',
                linewidth=1
            )
        )
        
        # Calcular totais para o título
        total_receitas = df['receitas'].sum()
        total_despesas = df['despesas'].sum()
        saldo_total = df['saldo'].sum()
        
        # Atualizar layout
        fig.update_layout(
            title=dict(
                text=f'FLUXO DE CAIXA MENSAL<br>'
                     f'<span style="color:gray; font-size:0.8em">'
                     f'Receitas: {format_currency(total_receitas)} • '
                     f'Despesas: {format_currency(total_despesas)} • '
                     f'Saldo: {format_currency(saldo_total)}</span>',
                x=0.5,
                xanchor='center',
                y=0.95,
                yanchor='top',
                font=dict(size=16, color='#2c3e50')
            ),
            xaxis=dict(
                title={
                    'text': 'Mês/Ano',
                    'font': {'size': 12, 'color': '#7f8c8d', 'family': 'Arial, sans-serif'},
                    'standoff': 25  # Aumenta o espaço entre o título e os ticks
                },
                tickfont=dict(size=11, color='#7f8c8d'),
                showgrid=False,
                tickangle=-45,
                automargin=True,  # Ajusta automaticamente as margens
                side='bottom',  # Garante que os ticks fiquem na parte inferior
                showline=True,  # Adiciona uma linha no eixo
                linecolor='#e0e0e0',  # Cor da linha do eixo
                linewidth=1,  # Espessura da linha do eixo
                tickmode='array',  # Usa os ticks fornecidos
                tickvals=df['data_formatada'],  # Valores dos ticks
                ticktext=df['data_formatada']  # Rótulos dos ticks
            ),
            yaxis=dict(
                title={
                    'text': 'Valor (R$)',
                    'font': {'size': 14, 'color': '#7f8c8d'}
                },
                tickfont=dict(size=12, color='#7f8c8d'),
                showgrid=True,
                gridcolor='#f1f1f1',
                zeroline=True,
                zerolinecolor='#bdc3c7',
                zerolinewidth=1,
                tickformat='.2f',
                side='left'
            ),
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=50, r=200, t=120, b=100),  # Ajustado para acomodar a legenda à direita
            legend=dict(
                orientation='v',
                yanchor='top',
                y=1,  # Posiciona a legenda no topo do gráfico
                xanchor='right',
                x=1.2,  # Posiciona a legenda à direita do gráfico
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='#ddd',
                borderwidth=1,
                font=dict(size=12, color='#2c3e50'),
                title=dict(text='<b>Legenda:</b>', font=dict(size=12, color='#2c3eda'))
            ),
            barmode='group',
            bargap=0.4,  # Espaço entre as barras
            hoverlabel=dict(
                bgcolor='white',
                font_size=12,
                font_family='Arial'
            )
        )
        
        # Adicionar anotação com a data de atualização
        fig.add_annotation(
            text=f"<i>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>",
            x=0.5,
            y=-0.25,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=10, color="#bdc3c7"),
            align="center"
        )
        
        # Limpar gráficos antigos
        img_dir = os.path.join('dashboard_arq', 'static', 'img')
        limpar_arquivos_antigos(img_dir, prefixo='grafico_fluxo_caixa_')
        
        # Salvar o gráfico como HTML interativo
        print("\n=== Salvando gráfico como HTML ===")
        print(f"- Caminho completo do arquivo: {img_path}")
        print(f"- Diretório existe: {os.path.exists(os.path.dirname(img_path))}")
        print(f"- Permissão de escrita: {os.access(os.path.dirname(img_path), os.W_OK)}")
        
        try:
            # Verificar se o diretório existe antes de tentar salvar
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            
            # Salvar o gráfico
            print("- Iniciando salvamento do gráfico...")
            pio.write_html(
                fig, 
                file=img_path, 
                auto_open=False, 
                include_plotlyjs='cdn',
                full_html=True
            )
            
            # Verificar se o arquivo foi criado
            if os.path.exists(img_path):
                file_size = os.path.getsize(img_path)
                print(f"- Gráfico salvo com sucesso em: {img_path}")
                print(f"- Tamanho do arquivo: {file_size} bytes")
                
                # Verificar se o arquivo tem conteúdo
                if file_size == 0:
                    print("- AVISO: O arquivo foi criado, mas está vazio!")
                    return None
                    
                return img_path
            else:
                print("- ERRO: O arquivo não foi criado!")
                return None
                
        except Exception as e:
            print(f"- ERRO ao salvar o gráfico: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        
    except Exception as e:
        fluxo_caixa_logger.error(f"Erro ao gerar o gráfico de fluxo de caixa: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    # Testar a função
    fluxo_caixa_logger.info("Iniciando teste da geração de gráfico de fluxo de caixa")
    caminho_grafico = gerar_grafico_fluxo_caixa()
    if caminho_grafico:
        fluxo_caixa_logger.info(f"Gráfico gerado com sucesso: {caminho_grafico}")
    else:
        fluxo_caixa_logger.error("Falha ao gerar o gráfico de fluxo de caixa.")
