"""
Módulo para análise de transações financeiras e detecção de anomalias.
"""
import pandas as pd
import numpy as np
from datetime import datetime
import json
import sqlite3
import os
import sys
import pytz
from scipy import stats
from statsmodels.tsa.arima.model import ARIMA
from sklearn.cluster import KMeans
import warnings

# Adiciona o diretório raiz ao path para importar o logger
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, LogLevel
from .config import CONFIG

class AnalisadorFinanceiro:
    """
    Classe responsável por realizar análises financeiras e detectar anomalias
    nos dados de transações financeiras.
    """
    
    def executar_analises(self):
        """
        Executa todas as análises disponíveis e retorna os alertas gerados.
        """
        self.alertas = []  # Limpa alertas anteriores
        self.logger.info("Iniciando execução de todas as análises.")
        
        try:
            # Carrega os dados do banco de dados
            if not self.carregar_dados():
                self.logger.error("Falha ao carregar dados para análise")
                return []
                
            # Lista de métodos de análise a serem executados
            metodos_analise = [
                self.calcular_zscore_por_categoria,
                self.identificar_outliers_por_percentil,
                self.calcular_ema_por_categoria,
                self.analisar_limite_orcamentario,
                self.analisar_desvio_padrao_mensal,
                self.analisar_proporcao_despesa_receita,
                self.analisar_crescimento_mensal,
                self.calcular_hhi,
                self.analisar_correlacao_categorias,
                self.calcular_anova_categorias,
                self.calcular_teste_t_por_tipo,
                self.calcular_regressao_linear,
                self.prever_arima,
                self.calcular_roi_por_ativo,
                self.calcular_sharpe_ratio,
                self.analisar_volatilidade_mensal,
                self.detectar_saldo_negativo,
                self.analisar_liquidez,
                self.detectar_fraudes,
                self.analisar_sazonalidade,
                self.calcular_beta_por_ativo,
                self.calcular_var,
                self.analisar_forma_pagamento,
                self.analisar_margem_lucro,
                self.analisar_ciclo_operacional,
                self.analisar_risco_operacional
            ]
            
            # Executa cada método de análise
            for i, metodo in enumerate(metodos_analise, 1):
                try:
                    nome_metodo = metodo.__name__
                    self.logger.info(f"Executando análise #{i}: {nome_metodo}")
                    metodo()  # Executa o método de análise
                    self.logger.info(f"Análise {nome_metodo} concluída. Total de alertas: {len(self.alertas)}")
                except Exception as e:
                    self.logger.error(f"Erro ao executar análise {i} ({nome_metodo}): {str(e)}", exc_info=True)
                    continue
                    
            self.logger.info(f"Execução de todas as análises concluída. Total de {len(self.alertas)} alertas gerados.")
            return self.alertas
            
        except Exception as e:
            self.logger.error(f"Erro inesperado na execução das análises: {str(e)}", exc_info=True)
            return []
    
    def __init__(self, db_path=None):
        """
        Inicializa o analisador financeiro.
        
        Args:
            db_path: Caminho para o banco de dados SQLite
        """
        self.db_path = db_path or CONFIG['db_path']
        self.df = pd.DataFrame()
        self.df_empty = True  # Flag para indicar se o DataFrame está vazio
        self.alertas = []
        self.logger = get_logger('analisador_financeiro')
        self.logger.level(LogLevel.DEBUG)
        self.logger.info("Nível de log configurado para DEBUG no AnalisadorFinanceiro")
    
    def carregar_dados(self):
        """
        Carrega os dados da tabela de transações do banco de dados.
        Retorna True se os dados foram carregados com sucesso, False caso contrário.
        """
        try:
            self.logger.info(f"Conectando ao banco de dados: {self.db_path}")
            conn = sqlite3.connect(self.db_path)
            self.df_empty = True  # Reseta o flag antes de carregar novos dados
            
            # Verifica se a tabela transacoes existe
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transacoes';")
            if not cursor.fetchone():
                self.logger.error("Tabela 'transacoes' não encontrada no banco de dados.")
                return False
                
            # Verifica as colunas existentes na tabela
            cursor.execute("PRAGMA table_info(transacoes)")
            colunas_existentes = [col[1] for col in cursor.fetchall()]
            
            if not colunas_existentes:
                self.logger.error("Nenhuma coluna encontrada na tabela 'transacoes'.")
                return False
                
            self.logger.info(f"Colunas encontradas na tabela transacoes: {', '.join(colunas_existentes)}")
            
            # Verifica se há registros na tabela
            cursor.execute("SELECT COUNT(*) FROM transacoes")
            total_registros = cursor.fetchone()[0]
            self.logger.info(f"Total de registros na tabela 'transacoes': {total_registros}")
            
            if total_registros == 0:
                self.logger.warning("A tabela 'transacoes' está vazia.")
                return False
            
            # Mapeamento de colunas para a consulta (apenas as que existem)
            mapeamento_colunas = {
                'id': 'id',
                'data': 'data',
                'descricao': 'descricao',
                'valor': 'valor',
                'categoria': 'categoria',
                'tipo': 'tipo',
                'preco': 'preco',
                'quantidade': 'quantidade',
                'tipo_operacao': 'tipo_operacao',
                'taxa': 'taxa',
                'ativo': 'ativo',
                'forma_pagamento': 'forma_pagamento',
                'indicador1': 'indicador1',
                'indicador2': 'indicador2',
                'data_importacao': 'data_importacao',
                'upload_id': 'upload_id'
            }
            
            # Filtra apenas as colunas que existem na tabela
            colunas_select = []
            for col_db, col_alias in mapeamento_colunas.items():
                if col_db in colunas_existentes:
                    colunas_select.append(f"{col_db} as {col_alias}")
            
            query = f"""
            SELECT 
                {', '.join(colunas_select)}
            FROM transacoes
            """
            
            self.logger.info(f"Executando consulta:\n{query}")
            
            # Carrega os dados em um DataFrame
            self.df = pd.read_sql_query(query, conn)
            
            if self.df.empty:
                self.logger.warning("Nenhum dado encontrado na tabela de transações.")
                return False
                
            # Converte a coluna de data para datetime
            try:
                if 'data' in self.df.columns:
                    self.logger.info("Convertendo coluna 'data' para datetime...")
                    self.df['data'] = pd.to_datetime(self.df['data'])
                    
                    # Ordena por data
                    self.logger.info("Ordenando dados por data...")
                    self.df = self.df.sort_values('data')
                    
                    # Filtra apenas as transações válidas (não nulas e com valor numérico)
                    self.logger.info("Filtrando transações válidas...")
                    self.df = self.df[~self.df['valor'].isna()]
                    
                    # Converte valores para numérico, tratando strings com vírgula como decimal
                    self.logger.info("Convertendo valores para numérico...")
                    self.df['valor'] = pd.to_numeric(
                        self.df['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True),
                        errors='coerce'
                    )
                    
                    # Remove valores infinitos
                    self.logger.info("Removendo valores infinitos...")
                    self.df = self.df[~self.df['valor'].isin([np.inf, -np.inf])]
                    
                    if not self.df.empty:
                        ano_inicial = self.df['data'].min().year
                        ano_final = self.df['data'].max().year
                        self.logger.info(f"Dados carregados de {ano_inicial} a {ano_final} com {len(self.df)} registros.")
                        self.df_empty = False
                        return True  # Retorna True aqui para indicar sucesso
                    else:
                        self.logger.warning("Nenhum dado válido encontrado após a filtragem.")
                        return False
            except Exception as e:
                self.logger.error(f"Erro ao processar os dados: {str(e)}", exc_info=True)
                return False
            
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao acessar o banco de dados: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Erro inesperado ao carregar dados: {str(e)}", exc_info=True)
            return False
    
    def calcular_zscore_por_categoria(self):
        """
        Calcula o Z-Score por categoria e tipo, gerando alertas para valores atípicos.
        """
        try:
            self.logger.info("Iniciando cálculo de Z-Score por categoria e tipo.")
            
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['categoria', 'tipo', 'valor']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean['valor_absoluto'] = df_clean['valor'].abs()
            df_clean = df_clean[df_clean['valor_absoluto'] > 0]
            
            self.logger.info(f"Total de transações para análise: {len(df_clean)}")
            self.logger.info(f"categorias únicas: {df_clean['categoria'].nunique()}")
            self.logger.info(f"tipos únicos: {df_clean['tipo'].nunique()}")
            
            for (categoria, tipo), grupo in df_clean.groupby(['categoria', 'tipo']):
                try:
                    if len(grupo) < CONFIG['min_transacoes_grupo']:
                        self.logger.debug(f"Grupo {categoria}/{tipo} com menos de {CONFIG['min_transacoes_grupo']} transações. Ignorado.")
                        continue
                    
                    self.logger.info(f"Analisando grupo: {categoria}/{tipo} com {len(grupo)} transações")
                    
                    q1 = grupo['valor'].quantile(0.25)
                    q3 = grupo['valor'].quantile(0.75)
                    iqr = q3 - q1
                    lim_inf = q1 - CONFIG['limite_iqr'] * iqr
                    lim_sup = q3 + CONFIG['limite_iqr'] * iqr
                    
                    self.logger.info(f"IQR: {iqr:.2f}, Limites: [{lim_inf:.2f}, {lim_sup:.2f}]")
                    
                    grupo_filtrado = grupo[
                        (grupo['valor'] >= lim_inf) & 
                        (grupo['valor'] <= lim_sup)
                    ].copy()
                    
                    self.logger.info(f"Transações após filtro IQR: {len(grupo_filtrado)}/{len(grupo)}")
                    
                    if len(grupo_filtrado) < CONFIG['min_transacoes_grupo']:
                        self.logger.info(f"Grupo {categoria}/{tipo} com menos de {CONFIG['min_transacoes_grupo']} transações após filtro IQR.")
                        continue
                    
                    valores_absolutos = grupo_filtrado['valor_absoluto']
                    media = valores_absolutos.mean()
                    mediana = valores_absolutos.median()
                    desvio_padrao = valores_absolutos.std() or 1e-10
                    
                    self.logger.info(f"Estatísticas - Média: {media:.2f}, Mediana: {mediana:.2f}, Desvio Padrão: {desvio_padrao:.2f}")
                    
                    grupo_filtrado['zscore'] = (valores_absolutos - media) / desvio_padrao
                    limite_z = CONFIG['zscore_limite']
                    outliers = grupo_filtrado[abs(grupo_filtrado['zscore']) > limite_z]
                    
                    self.logger.info(f"Encontrados {len(outliers)} outliers com Z-Score > {limite_z}")
                    
                    for _, row in outliers.iterrows():
                        data_ocorrencia = row.get('data', pd.Timestamp.now(tz='America/Sao_Paulo'))
                        data_formatada = data_ocorrencia.strftime('%d/%m/%Y') if not pd.isna(data_ocorrencia) else "data desconhecida"
                        
                        alerta = {
                            'titulo': f"Anomalia em {categoria}",
                            'descricao': (
                                f"Valor atípico detectado: R${row['valor']:,.2f} em {categoria} "
                                f"({tipo}) com Z-Score de {row['zscore']:.2f} em {data_formatada}. "
                                f"Média do grupo: R${media:,.2f}, Desvio padrão: R${desvio_padrao:,.2f}"
                            ),
                            'tipo': 'anomalia',
                            'prioridade': 'alta' if abs(row['ZScore']) > 3.0 else 'media',
                            'status': 'pendente',
                            'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'data_atualizacao': None,
                            'data_ocorrencia': data_ocorrencia.strftime('%Y-%m-%d %H:%M:%S') if not pd.isna(data_ocorrencia) else None,
                            'categoria': categoria,
                            'valor': float(row['valor']),
                            'origem': 'Z-Score',
                            'dados_adicionais': json.dumps({
                                'zscore': float(row['ZScore']),
                                'tipo': tipo,
                                'data': data_ocorrencia.isoformat() if not pd.isna(data_ocorrencia) else None,
                                'media_grupo': float(media),
                                'mediana_grupo': float(mediana),
                                'desvio_padrao': float(desvio_padrao),
                                'total_transacoes_grupo': len(grupo),
                                'total_transacoes_filtradas': len(grupo_filtrado)
                            }, ensure_ascii=False),
                            'automatico': 1,
                            'transacao_id': row.get('Transacao_ID')
                        }
                        self.alertas.append(alerta)
                        self.logger.info(f"Alerta gerado: {alerta['titulo']} (Z-Score: {row['ZScore']:.2f})")
                        
                except Exception as e:
                    self.logger.error(f"Erro ao processar grupo {categoria}/{tipo}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Cálculo de Z-Score concluído. Gerados {len(self.alertas)} alertas.")
            return self.alertas
            
        except Exception as e:
            self.logger.error(f"Erro inesperado no cálculo de Z-Score: {e}", exc_info=True)
            return []
    
    def identificar_outliers_por_percentil(self):
        """
        Identifica valores atípicos com base nos percentis 1% e 99% por categoria e tipo.
        """
        try:
            self.logger.info("Iniciando identificação de outliers por percentil.")
            
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['categoria', 'tipo', 'valor']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf])]
            
            for (categoria, tipo), grupo in df_clean.groupby(['categoria', 'tipo']):
                try:
                    if len(grupo) < CONFIG['min_transacoes_percentil']:
                        self.logger.debug(f"Grupo {categoria}/{tipo} tem apenas {len(grupo)} transações. Mínimo necessário: {CONFIG['min_transacoes_percentil']}")
                        continue
                    
                    p1 = grupo['valor'].quantile(CONFIG['percentil_baixo'])
                    p99 = grupo['valor'].quantile(CONFIG['percentil_alto'])
                    outliers = grupo[(grupo['valor'] < p1) | (grupo['valor'] > p99)]
                    
                    for _, row in outliers.iterrows():
                        valor = float(row['valor'])
                        data_ocorrencia = row.get('data', pd.Timestamp.now(tz='America/Sao_Paulo'))
                        prioridade = 'alta' if (valor < p1 and (p1 - valor) > 3 * (p99 - p1)) or (valor > p99 and (valor - p99) > 3 * (p99 - p1)) else 'media'
                        data_ocorrencia_str = data_ocorrencia.strftime('%Y-%m-%d %H:%M:%S')
                        data_descricao = data_ocorrencia.strftime('%Y-%m-%d')
                        
                        valor_formatado = f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        p1_formatado = f"{p1:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        p99_formatado = f"{p99:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        
                        alerta = {
                            'titulo': f"Outlier em {categoria}",
                            'descricao': f"Valor fora do percentil esperado: R${valor_formatado} em {categoria} ({tipo}) em {data_descricao}. "
                                       f"Intervalo: R${p1_formatado} a R${p99_formatado}.",
                            'tipo': 'anomalia',
                            'prioridade': prioridade,
                            'status': 'pendente',
                            'data_ocorrencia': data_ocorrencia_str,
                            'categoria': categoria,
                            'valor': valor,
                            'origem': 'Percentil',
                            'dados_adicionais': json.dumps({
                                'p1': float(p1),
                                'p99': float(p99),
                                'tipo': tipo,
                                'total_transacoes_grupo': len(grupo),
                                'percentil_baixo': CONFIG['percentil_baixo'],
                                'percentil_alto': CONFIG['percentil_alto']
                            }, ensure_ascii=False),
                            'automatico': 1,
                            'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'data_atualizacao': None,
                            'transacao_id': row.get('id')
                        }
                        self.alertas.append(alerta)
                        self.logger.info(f"Alerta gerado: {alerta['titulo']} (Valor: R${valor:,.2f}, Intervalo: R${p1:,.2f}-{p99:,.2f})")
                        
                except Exception as e:
                    self.logger.error(f"Erro ao processar grupo {categoria}/{tipo}: {e}", exc_info=True)
                    continue
            
            total_alertas = len([alerta for alerta in self.alertas if alerta.get('origem') == 'Percentil'])
            self.logger.info(f"Identificação de outliers por percentil concluída. Gerados {total_alertas} alertas.")
            return self.alertas
            
        except Exception as e:
            self.logger.error(f"Erro inesperado na identificação de outliers por percentil: {e}", exc_info=True)
            return []
    
    def calcular_ema_por_categoria(self):
        """
        Calcula a Média Móvel Exponencial (EMA) por categoria e tipo, gerando alertas para valores excedentes.
        """
        try:
            self.logger.info("Iniciando cálculo de EMA por categoria e tipo.")
            
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['categoria', 'tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, 0])]
            df_clean = df_clean.sort_values('data')
            
            alertas_gerados = 0
            for (categoria, tipo), grupo in df_clean.groupby(['categoria', 'tipo']):
                try:
                    if len(grupo) < CONFIG.get('min_transacoes_ema', 10):
                        self.logger.debug(f"Grupo {categoria}/{tipo} com menos de {CONFIG.get('min_transacoes_ema', 10)} transações. Ignorado.")
                        continue
                    
                    self.logger.info(f"Analisando grupo: {categoria}/{tipo} com {len(grupo)} transações")
                    
                    span = CONFIG.get('ema_span', 12)
                    grupo['EMA'] = grupo['valor'].ewm(span=span, adjust=False).mean()
                    grupo['Diff_Pct'] = (grupo['valor'] - grupo['EMA']) / grupo['EMA']
                    limite_diff = CONFIG.get('limite_ema_diff', 0.5)
                    excedentes = grupo[grupo['Diff_Pct'] > limite_diff]
                    
                    self.logger.info(f"Encontradas {len(excedentes)} transações que excedem a EMA em mais de {limite_diff*100:.0f}%")
                    
                    for _, row in excedentes.iterrows():
                        data_ocorrencia = row['data']
                        valor = float(row['valor'])
                        ema = float(row['EMA'])
                        diff_pct = float(row['Diff_Pct'])
                        
                        valor_formatado = f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        ema_formatada = f"{ema:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        diff_pct_formatada = f"{diff_pct*100:.2f}%"
                        
                        alerta = {
                            'titulo': f"Pico em {categoria}",
                            'descricao': (
                                f"Valor excede a EMA em {diff_pct_formatada}: R${valor_formatado} "
                                f"em {categoria} ({tipo}) em {data_ocorrencia.strftime('%d/%m/%Y')}. "
                                f"EMA: R${ema_formatada}."
                            ),
                            'tipo': 'tendencia',
                            'prioridade': 'media',
                            'status': 'pendente',
                            'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'data_atualizacao': None,
                            'data_ocorrencia': data_ocorrencia.strftime('%Y-%m-%d %H:%M:%S'),
                            'categoria': categoria,
                            'valor': valor,
                            'origem': 'EMA',
                            'dados_adicionais': json.dumps({
                                'ema': ema,
                                'diff_pct': diff_pct,
                                'tipo': tipo,
                                'data_ocorrencia': data_ocorrencia.isoformat(),
                                'total_transacoes_grupo': len(grupo),
                                'ema_span': span
                            }, ensure_ascii=False),
                            'automatico': 1,
                            'transacao_id': row.get('Transacao_ID')
                        }
                        self.alertas.append(alerta)
                        alertas_gerados += 1
                        self.logger.info(f"Alerta gerado: {alerta['titulo']} (Valor: R${valor:,.2f}, EMA: R${ema:,.2f}, Diferença: {diff_pct*100:.2f}%)")
                        
                except Exception as e:
                    self.logger.error(f"Erro ao processar grupo {categoria}/{tipo}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Cálculo de EMA concluído. Gerados {alertas_gerados} alertas.")
            return self.alertas
            
        except Exception as e:
            self.logger.error(f"Erro inesperado no cálculo de EMA: {e}", exc_info=True)
            return []
    
    def analisar_limite_orcamentario(self):
        """
        Analisa se a soma mensal de transações por categoria excede a média histórica.
        
        Esta análise considera:
        - Diferentes tipos de despesas (despesa, saída, pagamento, etc.)
        - Tendência de crescimento nos últimos meses
        - Comparação com percentis históricos
        - Detecção de aumentos súbitos
        """
        try:
            self.logger.info("Iniciando análise de limite orçamentário.")
            
            # Configurações com valores padrão
            config = {
                'meses_historico': CONFIG.get('meses_historico_orcamento', 6),  # Número de meses para análise histórica
                'limite_excesso': CONFIG.get('limite_excesso_orcamento', 0.2),  # 20% acima da média
                'limite_excesso_grave': CONFIG.get('limite_excesso_grave', 0.5),  # 50% acima da média
                'percentil_alerta': CONFIG.get('percentil_alerta_orcamento', 0.9),  # 90º percentil
                'tipos_despesa': CONFIG.get('tipos_despesa', ['despesa', 'saída', 'pagamento', 'débito']),
                'categorias_ignorar': CONFIG.get('categorias_ignorar_orcamento', [])
            }
            
            self.logger.debug(f"Configurações: {config}")
            
            if self.df_empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            # Pré-processamento dos dados
            df_clean = self.df.dropna(subset=['categoria', 'tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan, 0])]  # Remove valores inválidos e zeros
            
            if df_clean.empty:
                self.logger.warning("Nenhum dado válido para análise após limpeza.")
                return []
                
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['mes_ano'] = df_clean['data'].dt.to_period('M')
            df_clean = df_clean.sort_values('data')
            
            # Filtra apenas despesas (considerando múltiplos sinônimos)
            mask_tipo = df_clean['tipo'].str.lower().isin([t.lower() for t in config['tipos_despesa']])
            df_despesas = df_clean[mask_tipo].copy()
            
            if df_despesas.empty:
                tipos_encontrados = df_clean['tipo'].unique()
                self.logger.warning(f"Nenhuma despesa encontrada. tipos encontrados: {tipos_encontrados}")
                return []
            
            # Remove categorias que devem ser ignoradas
            if config['categorias_ignorar']:
                mask_ignorar = ~df_despesas['categoria'].str.lower().isin([c.lower() for c in config['categorias_ignorar']])
                df_despesas = df_despesas[mask_ignorar].copy()
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            mes_anterior = (mes_atual - 1).to_timestamp()
            alertas_gerados = 0
            
            # Agrupa por categoria para análise
            for categoria, grupo_cat in df_despesas.groupby('categoria'):
                try:
                    # Agrupa por mês e calcula totais
                    soma_mensal = grupo_cat.groupby('mes_ano')['valor'].sum().sort_index()
                    
                    # Verifica dados suficientes
                    if len(soma_mensal) < config['meses_historico'] + 1:  # +1 para incluir mês atual
                        self.logger.debug(f"categoria {categoria} com apenas {len(soma_mensal)} meses de dados. Mínimo necessário: {config['meses_historico'] + 1}")
                        continue
                    
                    # Separa histórico e mês atual
                    if mes_atual in soma_mensal.index:
                        valor_atual = abs(soma_mensal[mes_atual])
                        dados_historicos = soma_mensal[soma_mensal.index < mes_atual].tail(config['meses_historico'])
                    else:
                        self.logger.debug(f"Nenhum dado para o mês atual ({mes_atual}) em {categoria}.")
                        continue
                    
                    if len(dados_historicos) < config['meses_historico']:
                        self.logger.debug(f"Dados históricos insuficientes para {categoria}: {len(dados_historicos)} meses")
                        continue
                    
                    # Cálculos estatísticos
                    media_historica = abs(dados_historicos.mean())
                    mediana_historica = abs(dados_historicos.median())
                    desvio_padrao = abs(dados_historicos.std())
                    percentil_90 = abs(np.percentile(dados_historicos, 90))
                    
                    # Limites para alertas
                    limite_leve = media_historica * (1 + config['limite_excesso'])
                    limite_grave = media_historica * (1 + config['limite_excesso_grave'])
                    
                    # Verifica tendência de crescimento
                    if len(dados_historicos) >= 3:  # Precisa de pelo menos 3 pontos para calcular tendência
                        x = np.arange(len(dados_historicos))
                        coef = np.polyfit(x, dados_historicos, 1)
                        tendencia = coef[0]  # Coeficiente angular da reta
                        tendencia_pct = (tendencia / media_historica) * 100 if media_historica > 0 else 0
                    else:
                        tendencia = 0
                        tendencia_pct = 0
                    
                    # Verifica se deve gerar alerta
                    alerta_gerado = False
                    motivo = ""
                    prioridade = 'baixa'
                    
                    # Verifica excedeu limite grave
                    if valor_atual > limite_grave:
                        alerta_gerado = True
                        prioridade = 'alta'
                        motivo = f"Excedeu o limite grave de {config['limite_excesso_grave']*100:.0f}% acima da média"
                    # Verifica excedeu limite normal
                    elif valor_atual > limite_leve:
                        alerta_gerado = True
                        prioridade = 'media'
                        motivo = f"Excedeu o limite de {config['limite_excesso']*100:.0f}% acima da média"
                    # Verifica se está acima do percentil 90
                    elif valor_atual > percentil_90:
                        alerta_gerado = True
                        prioridade = 'baixa'
                        motivo = f"Valor acima do {config['percentil_alerta']*100:.0f}º percentil histórico"
                    # Verifica tendência de crescimento acentuada
                    elif tendencia_pct > 20:  # +20% de crescimento por mês
                        alerta_gerado = True
                        prioridade = 'media'
                        motivo = f"Tendência de crescimento acentuado (+{tendencia_pct:.1f}% ao mês)"
                    
                    if alerta_gerado:
                        # Calcula métricas adicionais
                        pct_excesso = ((valor_atual - media_historica) / media_historica * 100) if media_historica > 0 else float('inf')
                        
                        # Formata valores para exibição
                        def formatar_moeda(valor):
                            return f"R$ {abs(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        
                        # Monta descrição detalhada
                        descricao = (
                            f"Despesa em {categoria} {motivo}.\n"
                            f"• Valor atual: {formatar_moeda(valor_atual)}\n"
                            f"• Média histórica: {formatar_moeda(media_historica)} (últimos {len(dados_historicos)} meses)\n"
                            f"• Mediana: {formatar_moeda(mediana_historica)}\n"
                            f"• Desvio padrão: {formatar_moeda(desvio_padrao)}"
                        )
                        
                        if tendencia_pct != 0:
                            descricao += f"\n• Tendência: {'+' if tendencia_pct > 0 else ''}{tendencia_pct:.1f}% ao mês"
                        
                        # Cria alerta
                        alerta = {
                            'titulo': f"{'ALERTA GRAVE: ' if prioridade == 'alta' else ''}Excesso Orçamentário em {categoria}",
                            'descricao': descricao,
                            'tipo': 'orcamento',
                            'prioridade': prioridade,
                            'status': 'pendente',
                            'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'data_atualizacao': None,
                            'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                            'categoria': categoria,
                            'valor': float(valor_atual),
                            'origem': 'Análise Orçamentária',
                            'dados_adicionais': json.dumps({
                                'media_historica': float(media_historica),
                                'mediana_historica': float(mediana_historica),
                                'desvio_padrao': float(desvio_padrao),
                                'percentil_90': float(percentil_90),
                                'pct_excesso': round(pct_excesso, 2),
                                'tendencia_mensal_pct': round(tendencia_pct, 2),
                                'meses_analisados': len(dados_historicos),
                                'limite_leve': float(limite_leve),
                                'limite_grave': float(limite_grave),
                                'mes_referencia': str(mes_atual)
                            }, ensure_ascii=False),
                            'automatico': 1,
                            'transacao_id': None
                        }
                        self.alertas.append(alerta)
                        alertas_gerados += 1
                        self.logger.info(f"Alerta gerado: {alerta['descricao']}")
                    else:
                        self.logger.debug(f"Sem alerta para {categoria} - Dentro do limite orçamentário")
                        
                except Exception as e:
                    self.logger.error(f"Erro ao processar categoria {categoria}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Análise de limite orçamentário concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
            
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de limite orçamentário: {e}", exc_info=True)
            return []

    def analisar_desvio_padrao_mensal(self):
        """
        Analisa desvios significativos nos padrões de gastos mensais por categoria.
        
        Esta análise verifica se os valores atuais estão dentro de limites estatísticos
        calculados com base no histórico, considerando:
        - Média móvel e desvio padrão
        - Percentis históricos
        - Tendência de crescimento
        - Comparação com meses anteriores
        
        Gera alertas para:
        - Valores acima de 2 desvios padrão da média (Alerta Amarelo)
        - Valores acima de 3 desvios padrão (Alerta Vermelho)
        - Tendências de crescimento preocupantes
        - Valores acima do percentil 95 histórico
        """
        try:
            self.logger.info("🔍 Iniciando análise de desvio padrão mensal aprofundada...")
            
            # Configurações
            config = {
                'meses_analise': CONFIG.get('meses_analise_desvio', 12),  # Meses para análise histórica
                'limite_leve': CONFIG.get('limite_desvio_leve', 2.0),     # 2 desvios padrão
                'limite_grave': CONFIG.get('limite_desvio_grave', 3.0),    # 3 desvios padrão
                'percentil_alerta': CONFIG.get('percentil_alerta_desvio', 0.95),  # 95º percentil
                'tendencia_alerta': CONFIG.get('tendencia_alerta', 0.2),   # 20% de crescimento mensal
                'min_transacoes': CONFIG.get('min_transacoes_analise', 5)  # Mínimo de transações para análise
            }
            
            self.logger.debug(f"Configurações: {config}")
            
            # Validação inicial dos dados
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("❌ DataFrame vazio ou sem coluna 'valor'")
                return []

            # Pré-processamento dos dados
            df_clean = self.df.dropna(subset=['categoria', 'tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan, 0])]  # Remove valores inválidos e zeros
            
            if df_clean.empty:
                self.logger.warning("⚠️ Nenhum dado válido após limpeza")
                return []
                
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['mes'] = df_clean['data'].dt.to_period('M')
            df_clean = df_clean.sort_values('data')
            
            # Filtra apenas despesas (considerando múltiplos sinônimos)
            tipos_despesa = CONFIG.get('tipos_despesa', ['despesa', 'saída', 'pagamento', 'débito'])
            mask_tipo = df_clean['tipo'].str.lower().isin([t.lower() for t in tipos_despesa])
            df_despesas = df_clean[mask_tipo].copy()
            
            if df_despesas.empty:
                self.logger.warning(f"ℹ️ Nenhuma despesa encontrada. tipos encontrados: {df_clean['tipo'].unique()}")
                return []
            
            # Remove categorias ignoradas
            categorias_ignorar = CONFIG.get('categorias_ignorar_desvio', [])
            if categorias_ignorar:
                mask_ignorar = ~df_despesas['categoria'].str.lower().isin([c.lower() for c in categorias_ignorar])
                df_despesas = df_despesas[mask_ignorar].copy()
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            mes_anterior = (mes_atual - 1).to_timestamp()
            alertas_gerados = 0
            
            # Função para formatar valores monetários
            def formatar_moeda(valor):
                return f"R$ {abs(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            # Agrupa por categoria para análise
            for categoria, grupo_cat in df_despesas.groupby('categoria'):
                try:
                    # Agrupa por mês e calcula totais
                    soma_mensal = grupo_cat.groupby('mes')['valor'].sum().sort_index()
                    
                    # Verifica dados suficientes
                    if len(soma_mensal) < config['min_transacoes']:
                        self.logger.debug(f"ℹ️ categoria {categoria} com apenas {len(soma_mensal)} meses de dados. Mínimo: {config['min_transacoes']}")
                        continue
                    
                    # Separa histórico e mês atual
                    if mes_atual in soma_mensal.index:
                        valor_atual = abs(soma_mensal[mes_atual])
                        dados_historicos = soma_mensal[soma_mensal.index < mes_atual].tail(config['meses_analise'])
                    else:
                        self.logger.debug(f"ℹ️ Nenhum dado para o mês atual ({mes_atual}) em {categoria}")
                        continue
                    
                    if len(dados_historicos) < 3:  # Mínimo para análise estatística
                        self.logger.debug(f"ℹ️ Dados históricos insuficientes para {categoria}: {len(dados_historicos)} meses")
                        continue
                    
                    # Cálculos estatísticos
                    media_historica = abs(dados_historicos.mean())
                    mediana_historica = abs(dados_historicos.median())
                    desvio_padrao = abs(dados_historicos.std()) or 0.01  # Evita divisão por zero
                    coef_variacao = (desvio_padrao / media_historica) * 100 if media_historica > 0 else 0
                    
                    # Limites para alertas
                    limite_leve = media_historica + (config['limite_leve'] * desvio_padrao)
                    limite_grave = media_historica + (config['limite_grave'] * desvio_padrao)
                    percentil_95 = abs(np.percentile(dados_historicos, 95))
                    
                    # Verifica tendência de crescimento (regressão linear)
                    if len(dados_historicos) >= 3:
                        x = np.arange(len(dados_historicos))
                        coef = np.polyfit(x, dados_historicos, 1)
                        tendencia = coef[0]  # Coeficiente angular
                        tendencia_pct = (tendencia / media_historica) * 100 if media_historica > 0 else 0
                    else:
                        tendencia = 0
                        tendencia_pct = 0
                    
                    # Verifica se deve gerar alerta
                    alerta_gerado = False
                    motivo = ""
                    prioridade = 'baixa'
                    sugestao = ""
                    
                    # Verifica excedeu limite grave (3 desvios)
                    if valor_atual > limite_grave:
                        alerta_gerado = True
                        prioridade = 'alta'
                        motivo = f"Valor excedeu {config['limite_grave']} desvios padrão da média"
                        sugestao = "Verifique se houve algum gasto atípico ou erro de lançamento."
                    # Verifica excedeu limite leve (2 desvios)
                    elif valor_atual > limite_leve:
                        alerta_gerado = True
                        prioridade = 'media'
                        motivo = f"Valor excedeu {config['limite_leve']} desvios padrão da média"
                        sugestao = "Acompanhe de perto esta categoria nos próximos dias."
                    # Verifica se está acima do percentil 95
                    elif valor_atual > percentil_95:
                        alerta_gerado = True
                        prioridade = 'baixa'
                        motivo = f"Valor acima do {config['percentil_alerta']*100:.0f}º percentil histórico"
                        sugestao = "Pode ser um valor sazonalmente alto, mas merece atenção."
                    # Verifica tendência de crescimento acentuada
                    elif tendencia_pct > (config['tendencia_alerta'] * 100):
                        alerta_gerado = True
                        prioridade = 'media' if tendencia_pct > 30 else 'baixa'
                        motivo = f"Tendência de crescimento de {tendencia_pct:.1f}% ao mês"
                        sugestao = "Verifique se esse crescimento é esperado ou se há algum problema."
                    
                    if alerta_gerado:
                        # Cálculo de métricas adicionais
                        pct_acima_media = ((valor_atual - media_historica) / media_historica * 100) if media_historica > 0 else float('inf')
                        
                        # Monta descrição detalhada
                        descricao = (
                            f"🔍 **Análise de Desvio Padrão - {categoria}**\n\n"
                            f"📊 **Valor Atual:** {formatar_moeda(valor_atual)}\n"
                            f"📈 **Média Histórica:** {formatar_moeda(media_historica)} (últimos {len(dados_historicos)} meses)\n"
                            f"📉 **Mediana:** {formatar_moeda(mediana_historica)}\n"
                            f"📏 **Desvio Padrão:** {formatar_moeda(desvio_padrao)} (CV: {coef_variacao:.1f}%)\n\n"
                            f"🚨 **Motivo do Alerta:** {motivo}\n"
                            f"📌 **Sugestão:** {sugestao}\n\n"
                            f"🔢 **Detalhes Técnicos:**\n"
                            f"• Limite Leve ({config['limite_leve']}σ): {formatar_moeda(limite_leve)}\n"
                            f"• Limite Grave ({config['limite_grave']}σ): {formatar_moeda(limite_grave)}\n"
                            f"• Percentil 95: {formatar_moeda(percentil_95)}\n"
                            f"• Tendência Mensal: {'+' if tendencia_pct > 0 else ''}{tendencia_pct:.1f}%"
                        )
                        
                        # Cria alerta
                        alerta = {
                            'titulo': f"{'⚠️ ' if prioridade == 'media' else '🚨 '}Desvio em {categoria}",
                            'descricao': descricao,
                            'tipo': 'anomalia',
                            'prioridade': prioridade,
                            'status': 'pendente',
                            'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'data_atualizacao': None,
                            'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                            'categoria': categoria,
                            'valor': float(valor_atual),
                            'origem': 'Análise de Desvio Padrão',
                            'dados_adicionais': json.dumps({
                                'media_historica': float(media_historica),
                                'mediana_historica': float(mediana_historica),
                                'desvio_padrao': float(desvio_padrao),
                                'coef_variacao': round(coef_variacao, 2),
                                'percentil_95': float(percentil_95),
                                'pct_acima_media': round(pct_acima_media, 2),
                                'tendencia_mensal_pct': round(tendencia_pct, 2),
                                'limite_leve': float(limite_leve),
                                'limite_grave': float(limite_grave),
                                'meses_analisados': len(dados_historicos),
                                'mes_referencia': str(mes_atual)
                            }, ensure_ascii=False),
                            'automatico': 1,
                            'transacao_id': None,
                            'id_origem': f"desvio_{categoria.lower().replace(' ', '_')}_{mes_atual}"
                        }
                        
                        self.alertas.append(alerta)
                        alertas_gerados += 1
                        self.logger.info(f"✅ Alerta gerado para {categoria}: {motivo} (Prioridade: {prioridade})")
                    else:
                        self.logger.debug(f"ℹ️ Sem alerta para {categoria} - Dentro dos limites estatísticos")
                        
                except Exception as e:
                    self.logger.error(f"❌ Erro ao processar categoria {categoria}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"✅ Análise de desvio padrão concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
            
        except Exception as e:
            self.logger.error(f"❌ Erro inesperado na análise de desvio padrão: {e}", exc_info=True)
            return []

    def analisar_proporcao_despesa_receita(self):
        """
        Analisa a relação entre despesas e receitas ao longo do tempo, identificando
        padrões preocupantes como:
        - Proporção despesa/receita acima dos limites definidos
        - Tendência de crescimento da proporção
        - Meses com saldo negativo
        - Variações sazonais significativas
        - Quedas bruscas de receita
        - Aumento acelerado de despesas
        
        Gera alertas para:
        - Proporção acima de 70% (Alerta Amarelo)
        - Proporção acima de 90% (Alerta Vermelho)
        - Proporção acima de 100% (Alerta Crítico)
        - Aumento de mais de 5% na proporção em relação à média
        - Quedas de receita superiores a 10%
        - Aumento de despesas superior a 15% em relação à média
        """
        try:
            self.logger.info("📊 Iniciando análise avançada de proporção despesa/receita...")
            
            # Configurações mais sensíveis
            config = {
                'meses_analise': CONFIG.get('meses_analise_proporcao', 12),
                'limite_atenção': 0.7,  # 70% - Gera alerta amarelo
                'limite_alerta': CONFIG.get('limite_proporcao_alerta', 0.9),  # 90% - Gera alerta laranja
                'limite_critico': CONFIG.get('limite_proporcao_critico', 1.0),  # 100% - Gera alerta vermelho
                'tendencia_alerta': 0.05,  # 5% de aumento mês a mês
                'queda_receita_alerta': 0.1,  # 10% de queda na receita
                'aumento_despesa_alerta': 0.15,  # 15% de aumento nas despesas
                'min_meses_analise': 3,
                'limite_historico': 1.2  # 120% da média histórica
            }
            
            self.logger.debug(f"Configurações: {config}")
            
            # Validação inicial dos dados
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("❌ DataFrame vazio ou sem coluna 'valor'")
                return []
            
            # Pré-processamento dos dados
            df_clean = self.df.dropna(subset=['tipo', 'valor', 'data', 'categoria']).copy()
            
            # Converte valores para numérico, tratando caracteres especiais
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            
            # Remove valores inválidos e zera valores negativos para despesas
            mask = ~df_clean['valor'].isin([np.inf, -np.inf, np.nan, 0])
            df_clean = df_clean[mask].copy()
            
            # Garante que despesas tenham valores positivos e receitas mantenham o sinal
            df_clean.loc[df_clean['tipo'].str.lower().isin(['despesa', 'saída', 'pagamento']), 'valor'] = \
                df_clean.loc[df_clean['tipo'].str.lower().isin(['despesa', 'saída', 'pagamento']), 'valor'].abs()
            
            # Converte datas e extrai mês/ano
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['mes'] = df_clean['data'].dt.to_period('M')
            
            # Agrupa por mês e tipo (despesa/receita)
            soma_por_tipo = df_clean.groupby(['mes', 'tipo'])['valor'].sum().unstack().fillna(0)
            
            # Verifica se existem dados de despesa e receita
            if 'despesa' not in soma_por_tipo.columns or 'receita' not in soma_por_tipo.columns:
                self.logger.warning("⚠️ tipos 'despesa' ou 'receita' ausentes nos dados. Colunas encontradas: " + 
                                  f"{soma_por_tipo.columns.tolist()}")
                return []
            
            # Adiciona colunas para outros tipos de despesas
            if 'saída' in soma_por_tipo.columns:
                soma_por_tipo['despesa'] += soma_por_tipo.get('saída', 0)
            if 'pagamento' in soma_por_tipo.columns:
                soma_por_tipo['despesa'] += soma_por_tipo.get('pagamento', 0)
            
            # Calcula a proporção mensal (despesa/receita)
            soma_por_tipo['proporcao'] = (soma_por_tipo['despesa'] / 
                                        soma_por_tipo['receita'].replace(0, np.nan)).fillna(0)
            
            # Calcula variação mensal
            soma_por_tipo['variacao_receita'] = soma_por_tipo['receita'].pct_change() * 100
            soma_por_tipo['variacao_despesa'] = soma_por_tipo['despesa'].pct_change() * 100
            
            # Remove meses sem receita para evitar distorções
            df_proporcao = soma_por_tipo[soma_por_tipo['receita'] > 0].copy()
            
            # Ordena por data
            df_proporcao = df_proporcao.sort_index()
            
            # Verifica se há dados suficientes para análise
            if len(df_proporcao) < config['min_meses_analise']:
                self.logger.warning(f"⚠️ Dados insuficientes para análise. Mínimo necessário: {config['min_meses_analise']} meses com receita. Encontrados: {len(df_proporcao)}")
                return []
            
            # Obtém o mês atual e o mês anterior
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            mes_anterior = (mes_atual - 1).to_timestamp().to_period('M')
            alertas_gerados = 0
            
            # Função para formatar valores monetários
            def formatar_moeda(valor):
                return f"R$ {abs(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            # Verifica se temos dados para o mês atual
            if mes_atual in df_proporcao.index:
                mes_atual_data = df_proporcao.loc[mes_atual]
                dados_mes_anterior = df_proporcao.loc[mes_anterior] if mes_anterior in df_proporcao.index else None
                
                proporcao_atual = mes_atual_data['proporcao']
                despesa_atual = mes_atual_data['despesa']
                receita_atual = mes_atual_data['receita']
                
                # Calcula métricas históricas (últimos N meses)
                historico = df_proporcao[df_proporcao.index < mes_atual].tail(config['meses_analise'])
                
                if len(historico) >= 3:  # Mínimo para análise de tendência
                    # Estatísticas básicas
                    media_historica = historico['proporcao'].mean()
                    mediana_historica = historico['proporcao'].median()
                    desvio_padrao = historico['proporcao'].std() or 0.01
                    max_historico = historico['proporcao'].max()
                    min_historico = historico['proporcao'].min()
                    
                    # Análise de tendência (regressão linear)
                    x = np.arange(len(historico))
                    coef = np.polyfit(x, historico['proporcao'], 1)
                    tendencia = coef[0]  # Coeficiente angular (variação por mês)
                    
                    # Previsão para o próximo mês
                    previsao_prox_mes = coef[0] * len(historico) + coef[1]
                    
                    # Calcula variação em relação à média histórica
                    variacao_media = (proporcao_atual - media_historica) / media_historica if media_historica > 0 else 0
                    
                    # Verifica variação na receita e despesas
                    variacao_receita = mes_atual_data.get('variacao_receita', 0)
                    variacao_despesa = mes_atual_data.get('variacao_despesa', 0)
                    
                    # Verifica se há dados do mês anterior para comparação
                    if dados_mes_anterior is not None:
                        variacao_mensal = (proporcao_atual / dados_mes_anterior['proporcao'] - 1) if dados_mes_anterior['proporcao'] > 0 else 0
                    else:
                        variacao_mensal = 0
                    
                    # Identifica alertas com base em múltiplos critérios
                    alertas_detectados = []
                    prioridade = 'baixa'
                    sugestoes = []
                    
                    # 1. Verifica níveis de alerta baseados na proporção
                    if proporcao_atual >= config['limite_critico']:
                        alertas_detectados.append(f"Proporção crítica de {proporcao_atual:.1%} (acima de {config['limite_critico']:.0%})")
                        prioridade = 'crítico'
                        sugestoes.append("As despesas ultrapassaram as receitas. Revisão urgente necessária.")
                    elif proporcao_atual >= config['limite_alerta']:
                        alertas_detectados.append(f"Proporção elevada de {proporcao_atual:.1%} (acima de {config['limite_alerta']:.0%})")
                        prioridade = 'alta' if prioridade != 'crítico' else prioridade
                        sugestoes.append(f"Considere reduzir despesas ou aumentar receitas para manter a proporção abaixo de {config['limite_alerta']:.0%}.")
                    elif proporcao_atual >= config['limite_atenção']:
                        alertas_detectados.append(f"Proporção em atenção: {proporcao_atual:.1%} (acima de {config['limite_atenção']:.0%})")
                        prioridade = 'média' if prioridade not in ['alta', 'crítico'] else prioridade
                        sugestoes.append(f"Monitore de perto, a proporção está se aproximando do limite de alerta de {config['limite_alerta']:.0%}.")
                        sugestao = "Atenção: as despesas estão próximas de ultrapassar as receitas."
                    # 2. Verifica tendência de piora
                    if tendencia > config['tendencia_alerta']:
                        alertas_detectados.append(f"Tendência de piora: aumento de {tendencia*100:.1f}% ao mês na proporção")
                        if prioridade == 'baixa':
                            prioridade = 'média'
                        sugestoes.append("Analise os motivos do crescimento acelerado das despesas em relação às receitas.")
                    
                    # 3. Verifica queda brusca na receita
                    if variacao_receita < -config['queda_receita_alerta'] * 100:  # Multiplica por 100 pois está em percentual
                        alertas_detectados.append(f"Queda significativa na receita: {variacao_receita:.1f}% em relação ao mês anterior")
                        if prioridade in ['baixa', 'média']:
                            prioridade = 'alta' if prioridade == 'baixa' else 'média'
                        sugestoes.append(f"Investigue os motivos da queda de {abs(variacao_receita):.1f}% na receita.")
                    
                    # 4. Verifica aumento acelerado nas despesas
                    if variacao_despesa > config['aumento_despesa_alerta'] * 100:  # Multiplica por 100 pois está em percentual
                        alertas_detectados.append(f"Aumento significativo nas despesas: {variacao_despesa:.1f}% em relação ao mês anterior")
                        if prioridade in ['baixa', 'média']:
                            prioridade = 'alta' if prioridade == 'baixa' else 'média'
                        sugestoes.append(f"Avalie o aumento de {variacao_despesa:.1f}% nas despesas em relação ao mês anterior.")
                    
                    # 5. Verifica se a proporção atual está muito acima da média histórica
                    if proporcao_atual > media_historica * config['limite_historico']:
                        alertas_detectados.append(f"Proporção atual {proporcao_atual:.1%} está {((proporcao_atual/media_historica)-1):.1%} acima da média histórica")
                        if prioridade == 'baixa':
                            prioridade = 'média'
                        sugestoes.append(f"A proporção atual está significativamente acima da média histórica de {media_historica:.1%}.")
                    
                    # Se nenhum alerta foi disparado, verifica se está tudo normal
                    if not alertas_detectados and proporcao_atual > 0:
                        self.logger.debug(f"✅ Proporção dentro dos limites aceitáveis: {proporcao_atual:.1%}")
                        return self.alertas
                    
                    # Prepara mensagem de motivo concatenando todos os alertas
                    motivo = " | ".join(alertas_detectados)
                    sugestao = " ".join(sugestoes) if sugestoes else ""
                    
                    # Adiciona informações adicionais à sugestão
                    if sugestao:
                        sugestao += " "
                    
                    sugestao += f"Média histórica: {media_historica:.1%} | Mês anterior: {dados_mes_anterior['proporcao']:.1%} | Variação: {variacao_mensal:+.1%}."
                    
                    # Define o título do alerta com base na prioridade
                    if prioridade == 'crítico':
                        titulo = f"🚨 CRÍTICO: Proporção Despesa/Receita em {proporcao_atual:.1%}"
                    elif prioridade == 'alta':
                        titulo = f"⚠️ ALTO: Proporção Despesa/Receita em {proporcao_atual:.1%}"
                    elif prioridade == 'média':
                        titulo = f"🔔 ATENÇÃO: Proporção Despesa/Receita em {proporcao_atual:.1%}"
                    else:
                        titulo = f"ℹ️ Proporção Despesa/Receita em {proporcao_atual:.1%}"
                    # Formata a mensagem do alerta
                    saldo = receita_atual - despesa_atual
                    saldo_mensagem = "(DÉFICIT)" if saldo < 0 else "(SUPERÁVIT)"
                    
                    # Formata a descrição detalhada
                    descricao = (
                        f"📊 **ANÁLISE FINANCEIRA DETALHADA - {mes_atual}**\n\n"
                        f"📈 **RESUMO**\n"
                        f"• Receita Total: {formatar_moeda(receita_atual)}\n"
                        f"• Despesa Total: {formatar_moeda(despesa_atual)}\n"
                        f"• Saldo: {formatar_moeda(saldo)} {saldo_mensagem}\n"
                        f"• Proporção Atual: {proporcao_atual:.1%} (Despesas/Receitas)\n\n"
                        
                        f"📊 **HISTÓRICO** (últimos {len(historico)} meses)\n"
                        f"• Média Histórica: {media_historica:.1%}\n"
                        f"• Variação Mensal: {'+' if tendencia >= 0 else ''}{tendencia*100:.1f}%\n"
                        f"• Previsão Próximo Mês: {previsao_prox_mes:.1%}\n"
                        f"• Mínimo Histórico: {min_historico:.1%}\n"
                        f"• Máximo Histórico: {max_historico:.1%}\n\n"
                        
                        f"📉 **VARIAÇÕES**\n"
                        f"• Receita vs Mês Anterior: {variacao_receita:+.1f}%\n"
                        f"• Despesas vs Mês Anterior: {variacao_despesa:+.1f}%\n"
                        f"• Proporção vs Média: {variacao_media:+.1f}%\n\n"
                        
                        f"🚨 **ALERTAS**\n"
                    )
                    
                    # Adiciona cada alerta em uma nova linha
                    for i, alerta in enumerate(alertas_detectados, 1):
                        descricao += f"{i}. {alerta}\n"
                    
                    # Adiciona sugestões
                    if sugestoes:
                        descricao += "\n💡 **SUGESTÕES**\n"
                        for i, sugest in enumerate(sugestoes, 1):
                            descricao += f"{i}. {sugest}\n"
                    
                    # Adiciona métricas adicionais
                    descricao += "\n🔍 **MÉTRICAS ADICIONAIS**\n"
                    descricao += f"• Desvio Padrão: {desvio_padrao:.4f}\n"
                    descricao += f"• Mediana Histórica: {mediana_historica:.1%}\n"
                    descricao += f"• Valor Mínimo Histórico: {min_historico:.1%}\n"
                    descricao += f"• Valor Máximo Histórico: {max_historico:.1%}\n"
                    
                    # Adiciona análise de tendência
                    if abs(tendencia) > 0.01:  # Se a tendência for significativa
                        tendencia_texto = "alta" if tendencia > 0 else "queda"
                        descricao += f"• Tendência: {abs(tendencia)*100:.1f}% de {tendencia_texto} mensal\n"
                    
                    # Adiciona previsão para o próximo mês
                    if previsao_prox_mes > 0:
                        descricao += f"• Previsão Próximo Mês: {previsao_prox_mes:.1%}\n"
                        
                        # Cria o alerta com todas as informações
                        alerta = {
                            'titulo': titulo,
                            'descricao': descricao,
                            'tipo': 'orcamento',
                            'prioridade': prioridade,
                            'status': 'pendente',
                            'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'data_atualizacao': None,
                            'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                            'categoria': 'Geral',
                            'valor': float(proporcao_atual),
                            'origem': 'Análise de Proporção',
                            'dados_adicionais': json.dumps({
                                'proporcao_atual': float(proporcao_atual),
                                'despesa_atual': float(despesa_atual),
                                'receita_atual': float(receita_atual),
                                'saldo_atual': float(receita_atual - despesa_atual),
                                'media_historica': float(media_historica),
                                'mediana_historica': float(mediana_historica),
                                'desvio_padrao': float(desvio_padrao),
                                'max_historico': float(max_historico),
                                'min_historico': float(min_historico),
                                'tendencia_mensal': float(tendencia),
                                'previsao_prox_mes': float(previsao_prox_mes),
                                'variacao_receita': float(variacao_receita),
                                'variacao_despesa': float(variacao_despesa),
                                'variacao_mensal': float(variacao_mensal),
                                'meses_analisados': len(historico),
                                'mes_referencia': str(mes_atual),
                                'alertas_gerados': alertas_detectados,
                                'sugestoes': sugestoes
                            }, ensure_ascii=False, indent=2),
                            'automatico': 1,
                            'transacao_id': None,
                            'id_origem': f"proporcao_{mes_atual}"
                        }
                        
                        # Adiciona o alerta à lista de alertas
                        if proporcao_atual > 0:
                            self.alertas.append(alerta)
                            alertas_gerados += 1
                            self.logger.info(f"✅ Alerta de proporção gerado: {motivo}")
                            
                            # Log detalhado para depuração
                            self.logger.debug(f"📊 Detalhes do alerta gerado:")
                            self.logger.debug(f"- Título: {titulo}")
                            self.logger.debug(f"- Prioridade: {prioridade}")
                            self.logger.debug(f"- Proporção Atual: {proporcao_atual:.1%}")
                            self.logger.debug(f"- Média Histórica: {media_historica:.1%}")
                            self.logger.debug(f"- Variação Mensal: {variacao_mensal:+.1%}")
                            self.logger.debug(f"- Alertas Detectados: {len(alertas_detectados)}")
                        else:
                            self.logger.warning("⚠️ Proporção inválida (zero ou negativa)")
                    else:
                        self.logger.warning(f"⚠️ Dados insuficientes para análise de tendência: {len(historico)} meses (mínimo: 3)")
                else:
                    self.logger.warning(f"⚠️ Sem dados para o mês atual ({mes_atual}) na análise de proporção")
                
                # Log de resumo da análise
                if alertas_gerados > 0:
                    self.logger.info(f"📋 Análise de proporção concluída. {alertas_gerados} alertas gerados com sucesso!")
                    
                    # Log dos tipos de alertas gerados
                    tipos_alertas = {}
                    for a in self.alertas[-alertas_gerados:]:  # Pega apenas os alertas gerados nesta execução
                        tipo = a['prioridade']
                        tipos_alertas[tipo] = tipos_alertas.get(tipo, 0) + 1
                    
                    for tipo, qtd in tipos_alertas.items():
                        self.logger.info(f"   • {qtd} alerta(s) de prioridade {tipo.upper()}")
                    
                    # Log da proporção média
                    proporcao_media = sum(a['valor'] for a in self.alertas[-alertas_gerados:]) / alertas_gerados
                    self.logger.info(f"   • Proporção média dos alertas: {proporcao_media:.1%}")
                else:
                    self.logger.info("📊 Nenhum alerta gerado na análise de proporção.")
                    
                    # Se não houve alertas mas temos dados, loga um resumo
                    if len(df_proporcao) > 0 and mes_atual in df_proporcao.index:
                        ultima_proporcao = df_proporcao.loc[mes_atual, 'proporcao']
                        self.logger.info(f"   • Proporção atual: {ultima_proporcao:.1%} (dentro dos limites aceitáveis)")
                
                return self.alertas
                
        except Exception as e:
            erro_msg = f"❌ Erro na análise de proporção: {str(e)}"
            self.logger.error(erro_msg, exc_info=True)
            
        # Tenta adicionar um alerta de erro
        try:
            alerta_erro = {
                'titulo': "🚨 ERRO: Falha na Análise de Proporção",
                'descricao': f"Ocorreu um erro ao analisar a proporção despesa/receita:\n\n{str(e)}\n\nVerifique os logs para mais detalhes.",
                'tipo': 'erro',
                'prioridade': 'alta',
                'status': 'pendente',
                'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                'categoria': 'Sistema',
                'valor': 0,
                'origem': 'Análise de Proporção',
                'dados_adicionais': json.dumps({
                    'erro': str(e),
                    'tipo_erro': type(e).__name__,
                    'traceback': traceback.format_exc(),
                    'data_erro': pd.Timestamp.now(tz='America/Sao_Paulo').isoformat()
                }, ensure_ascii=False, indent=2),
                'automatico': 1,
                'id_origem': f"erro_proporcao_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
            }
            self.alertas.append(alerta_erro)
            self.logger.info("✅ Alerta de erro gerado para notificar a falha na análise.")
        except Exception as inner_e:
            self.logger.error(f"❌ Falha ao gerar alerta de erro: {str(inner_e)}")
        
        return []

    def analisar_crescimento_mensal(self):
        """
        Detecta crescimento anormal na soma mensal por categoria.
        """
        try:
            self.logger.info("Iniciando análise de crescimento mensal.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['categoria', 'tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            df_clean = df_clean.sort_values('data')
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            alertas_gerados = 0
            
            for (categoria, tipo), grupo in df_clean.groupby(['categoria', 'tipo']):
                try:
                    if tipo != 'despesa':
                        continue
                    soma_mensal = grupo.groupby('Mes')['valor'].sum().sort_index()
                    if len(soma_mensal) < 2:
                        self.logger.debug(f"Grupo {categoria}/{tipo} com menos de 2 meses de dados.")
                        continue
                    if mes_atual in soma_mensal.index:
                        valor_atual = abs(soma_mensal[mes_atual])
                        valor_anterior = abs(soma_mensal[soma_mensal.index[-2]]) if len(soma_mensal) >= 2 else 0
                        if valor_anterior > 0:
                            crescimento_pct = (valor_atual - valor_anterior) / valor_anterior
                            if crescimento_pct > CONFIG.get('limite_crescimento', 0.2):
                                valor_formatado = f"{valor_atual:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                                anterior_formatado = f"{valor_anterior:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                                alerta = {
                                    'titulo': f"Crescimento Anormal em {categoria}",
                                    'descricao': (
                                        f"Crescimento de {crescimento_pct*100:.2f}% em {categoria} ({tipo}) em {mes_atual}. "
                                        f"Valor atual: R${valor_formatado}, Anterior: R${anterior_formatado}."
                                    ),
                                    'tipo': 'tendencia',
                                    'prioridade': 'media',
                                    'status': 'pendente',
                                    'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                                    'data_atualizacao': None,
                                    'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                                    'categoria': categoria,
                                    'valor': float(valor_atual),
                                    'origem': 'Crescimento Mensal',
                                    'dados_adicionais': json.dumps({
                                        'crescimento_pct': float(crescimento_pct),
                                        'valor_anterior': float(valor_anterior),
                                        'tipo': tipo,
                                        'mes_referencia': str(mes_atual)
                                    }, ensure_ascii=False),
                                    'automatico': 1,
                                    'transacao_id': None
                                }
                                self.alertas.append(alerta)
                                alertas_gerados += 1
                                self.logger.info(f"Alerta gerado: {alerta['titulo']} (Crescimento: {crescimento_pct*100:.2f}%)")
                
                except Exception as e:
                    self.logger.error(f"Erro ao processar grupo {categoria}/{tipo}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Análise de crescimento mensal concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de crescimento mensal: {e}", exc_info=True)
            return []

    def calcular_hhi(self):
        """
        Calcula o Índice Herfindahl-Hirschman para concentração de gastos.
        """
        try:
            self.logger.info("Iniciando cálculo de HHI.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['categoria', 'valor']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean = df_clean[df_clean['tipo'] == 'despesa']
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            df_mes = df_clean[df_clean['Mes'] == mes_atual]
            
            if df_mes.empty:
                self.logger.warning(f"Nenhum dado para o mês atual {mes_atual}.")
                return []
            
            # Aplicar abs() apenas nos valores antes de somar
            df_mes['valor_Abs'] = df_mes['valor'].abs()
            total_gasto = df_mes['valor_Abs'].sum()
            
            if total_gasto == 0:
                self.logger.warning("Total de gastos no mês atual é zero.")
                return []
            
            # Agrupar e somar os valores absolutos
            soma_por_categoria = df_mes.groupby('categoria')['valor_Abs'].sum()
            proporcoes = (soma_por_categoria / total_gasto) ** 2
            hhi = proporcoes.sum()
            
            alertas_gerados = 0
            if hhi > CONFIG.get('limite_hhi', 0.25):
                hhi_formatado = f"{hhi:.4f}"
                alerta = {
                    'titulo': 'Alta Concentração de Gastos',
                    'descricao': (
                        f"Índice HHI de {hhi_formatado} indica alta concentração de gastos em {mes_atual}. "
                        f"Total gasto: R${total_gasto:,.2f}."
                    ),
                    'tipo': 'risco',
                    'prioridade': 'media',
                    'status': 'pendente',
                    'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                    'data_atualizacao': None,
                    'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'categoria': None,
                    'valor': float(total_gasto),
                    'origem': 'HHI',
                    'dados_adicionais': json.dumps({
                        'hhi': float(hhi),
                        'total_gasto': float(total_gasto),
                        'mes_referencia': str(mes_atual),
                        'categorias': soma_por_categoria.index.tolist()
                    }, ensure_ascii=False),
                    'automatico': 1,
                    'transacao_id': None
                }
                self.alertas.append(alerta)
                alertas_gerados += 1
                self.logger.info(f"Alerta gerado: {alerta['titulo']} (HHI: {hhi:.4f})")
            
            self.logger.info(f"Cálculo de HHI concluído. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado no cálculo de HHI: {e}", exc_info=True)
            return []

    def analisar_correlacao_categorias(self):
        """
        Detecta correlações anormais entre gastos de categorias.
        """
        try:
            self.logger.info("Iniciando análise de correlação entre categorias.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['categoria', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            df_clean = df_clean[df_clean['tipo'] == 'despesa']
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            df_mes = df_clean[df_clean['Mes'] == mes_atual]
            
            if len(df_mes['categoria'].unique()) < 2:
                self.logger.warning("Menos de duas categorias disponíveis para correlação.")
                return []
            
            pivot = df_mes.pivot_table(values='valor', index='Mes', columns='categoria', aggfunc='sum', fill_value=0)
            correlacao = pivot.corr()
            
            alertas_gerados = 0
            limite_correlacao = CONFIG.get('limite_correlacao', 0.8)
            for cat1 in correlacao.columns:
                for cat2 in correlacao.columns:
                    if cat1 < cat2:
                        corr = correlacao.loc[cat1, cat2]
                        if abs(corr) > limite_correlacao:
                            alerta = {
                                'titulo': f"Correlação Alta entre {cat1} e {cat2}",
                                'descricao': (
                                    f"Correlação de {corr:.2f} entre {cat1} e {cat2} em {mes_atual}. "
                                    f"Possível dependência nos gastos."
                                ),
                                'tipo': 'anomalia',
                                'prioridade': 'media',
                                'status': 'pendente',
                                'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                                'data_atualizacao': None,
                                'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                                'categoria': None,
                                'valor': 0.0,
                                'origem': 'Correlação categorias',
                                'dados_adicionais': json.dumps({
                                    'correlacao': float(corr),
                                    'categoria_1': cat1,
                                    'categoria_2': cat2,
                                    'mes_referencia': str(mes_atual)
                                }, ensure_ascii=False),
                                'automatico': 1,
                                'transacao_id': None
                            }
                            self.alertas.append(alerta)
                            alertas_gerados += 1
                            self.logger.info(f"Alerta gerado: {alerta['titulo']} (Correlação: {corr:.2f})")
            
            self.logger.info(f"Análise de correlação concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de correlação: {e}", exc_info=True)
            return []

    def calcular_anova_categorias(self):
        """
        Realiza teste ANOVA para diferenças entre categorias.
        """
        try:
            self.logger.info("Iniciando análise ANOVA por categorias.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['categoria', 'valor']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean = df_clean[df_clean['tipo'] == 'despesa']
            
            if len(df_clean['categoria'].unique()) < 2:
                self.logger.warning("Menos de duas categorias para ANOVA.")
                return []
            
            grupos = [grupo['valor'].values for _, grupo in df_clean.groupby('categoria')]
            if any(len(g) < 2 for g in grupos):
                self.logger.warning("Alguma categoria tem menos de 2 transações para ANOVA.")
                return []
            
            f_stat, p_valor = stats.f_oneway(*grupos)
            alertas_gerados = 0
            if p_valor < CONFIG.get('limite_pvalor', 0.05):
                alerta = {
                    'titulo': 'Diferenças Significativas entre categorias',
                    'descricao': (
                        f"Teste ANOVA detectou diferenças significativas (p-valor: {p_valor:.4f}) "
                        f"entre categorias em despesas."
                    ),
                    'tipo': 'anomalia',
                    'prioridade': 'media',
                    'status': 'pendente',
                    'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                    'data_atualizacao': None,
                    'data_ocorrencia': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                    'categoria': None,
                    'valor': 0.0,
                    'origem': 'ANOVA categorias',
                    'dados_adicionais': json.dumps({
                        'p_valor': float(p_valor),
                        'f_stat': float(f_stat),
                        'categorias': df_clean['categoria'].unique().tolist()
                    }, ensure_ascii=False),
                    'automatico': 1,
                    'transacao_id': None
                }
                self.alertas.append(alerta)
                alertas_gerados += 1
                self.logger.info(f"Alerta gerado: {alerta['titulo']} (p-valor: {p_valor:.4f})")
            
            self.logger.info(f"Análise ANOVA concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise ANOVA: {e}", exc_info=True)
            return []

    def calcular_teste_t_por_tipo(self):
        """
        Compara médias de despesa vs. receita com teste T.
        """
        try:
            self.logger.info("Iniciando teste T por tipo.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['tipo', 'valor']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            
            despesas = df_clean[df_clean['tipo'] == 'despesa']['valor'].values
            receitas = df_clean[df_clean['tipo'] == 'receita']['valor'].values
            
            if len(despesas) < 2 or len(receitas) < 2:
                self.logger.warning("Dados insuficientes para teste T entre despesa e receita.")
                return []
            
            t_stat, p_valor = stats.ttest_ind(despesas, receitas, equal_var=False)
            alertas_gerados = 0
            if p_valor < CONFIG.get('limite_pvalor', 0.05):
                alerta = {
                    'titulo': 'Diferença Significativa entre Despesa e Receita',
                    'descricao': (
                        f"Teste T detectou diferença significativa (p-valor: {p_valor:.4f}) "
                        f"entre médias de despesa e receita."
                    ),
                    'tipo': 'anomalia',
                    'prioridade': 'media',
                    'status': 'pendente',
                    'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                    'data_atualizacao': None,
                    'data_ocorrencia': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                    'categoria': None,
                    'valor': 0.0,
                    'origem': 'Teste T tipos',
                    'dados_adicionais': json.dumps({
                        'p_valor': float(p_valor),
                        't_stat': float(t_stat),
                        'media_despesa': float(np.mean(despesas)),
                        'media_receita': float(np.mean(receitas))
                    }, ensure_ascii=False),
                    'automatico': 1,
                    'transacao_id': None
                }
                self.alertas.append(alerta)
                alertas_gerados += 1
                self.logger.info(f"Alerta gerado: {alerta['titulo']} (p-valor: {p_valor:.4f})")
            
            self.logger.info(f"Teste T concluído. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado no teste T: {e}", exc_info=True)
            return []

    def calcular_regressao_linear(self):
        """
        Detecta desvios de tendências lineares em gastos mensais.
        """
        try:
            self.logger.info("Iniciando análise de regressão linear.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['categoria', 'tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            df_clean = df_clean[df_clean['tipo'] == 'despesa']
            
            alertas_gerados = 0
            for (categoria, tipo), grupo in df_clean.groupby(['categoria', 'tipo']):
                try:
                    soma_mensal = grupo.groupby('Mes')['valor'].sum().reset_index()
                    if len(soma_mensal) < 6:
                        self.logger.debug(f"Grupo {categoria}/{tipo} com menos de 6 meses de dados.")
                        continue
                    
                    soma_mensal['Mes_Idx'] = range(len(soma_mensal))
                    X = soma_mensal['Mes_Idx'].values.reshape(-1, 1)
                    y = soma_mensal['valor'].values
                    slope, intercept = np.polyfit(soma_mensal['Mes_Idx'], y, 1)
                    pred = slope * soma_mensal['Mes_Idx'] + intercept
                    residuos = y - pred
                    
                    limite_residuo = CONFIG.get('limite_residuo', 2.0) * np.std(residuos)
                    mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
                    if str(mes_atual) in soma_mensal['Mes'].astype(str).values:
                        idx = soma_mensal[soma_mensal['Mes'].astype(str) == str(mes_atual)].index[0]
                        residuo = residuos[idx]
                        valor_atual = y[idx]
                        if abs(residuo) > limite_residuo:
                            valor_formatado = f"{valor_atual:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                            pred_formatado = f"{pred[idx]:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                            alerta = {
                                'titulo': f"Desvio de Tendência em {categoria}",
                                'descricao': (
                                    f"Valor de R${valor_formatado} em {categoria} ({tipo}) em {mes_atual} "
                                    f"desvia da tendência linear (Predito: R${pred_formatado})."
                                ),
                                'tipo': 'tendencia',
                                'prioridade': 'media',
                                'status': 'pendente',
                                'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                                'data_atualizacao': None,
                                'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                                'categoria': categoria,
                                'valor': float(valor_atual),
                                'origem': 'Regressão Linear',
                                'dados_adicionais': json.dumps({
                                    'residuo': float(residuo),
                                    'valor_predito': float(pred[idx]),
                                    'tipo': tipo,
                                    'mes_referencia': str(mes_atual)
                                }, ensure_ascii=False),
                                'automatico': 1,
                                'transacao_id': None
                            }
                            self.alertas.append(alerta)
                            alertas_gerados += 1
                            self.logger.info(f"Alerta gerado: {alerta['titulo']} (Resíduo: {residuo:.2f})")
                
                except Exception as e:
                    self.logger.error(f"Erro ao processar grupo {categoria}/{tipo}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Análise de regressão linear concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de regressão linear: {e}", exc_info=True)
            return []

    def prever_arima(self):
        """
        Gera previsões com ARIMA e alerta para valores fora do intervalo de confiança.
        """
        try:
            self.logger.info("Iniciando previsão ARIMA.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['categoria', 'tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            df_clean = df_clean[df_clean['tipo'] == 'despesa']
            
            alertas_gerados = 0
            for (categoria, tipo), grupo in df_clean.groupby(['categoria', 'tipo']):
                try:
                    soma_mensal = grupo.groupby('Mes')['valor'].sum().sort_index()
                    if len(soma_mensal) < 12:
                        self.logger.debug(f"Grupo {categoria}/{tipo} com menos de 12 meses para ARIMA.")
                        continue
                    
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        model = ARIMA(soma_mensal.values, order=(1,1,1)).fit()
                        forecast = model.forecast(steps=1)
                        conf_int = model.get_forecast(steps=1).conf_int(alpha=0.05)
                        valor_atual = soma_mensal[-1]
                        lower_bound, upper_bound = conf_int[0]
                        
                        if valor_atual < lower_bound or valor_atual > upper_bound:
                            valor_formatado = f"{valor_atual:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                            forecast_formatado = f"{forecast[0]:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                            alerta = {
                                'titulo': f"Previsão Anormal em {categoria}",
                                'descricao': (
                                    f"Valor de R${valor_formatado} em {categoria} ({tipo}) em {soma_mensal.index[-1]} "
                                    f"está fora do intervalo previsto: R${lower_bound:,.2f} a R${upper_bound:,.2f}."
                                ),
                                'tipo': 'previsao',
                                'prioridade': 'alta',
                                'status': 'pendente',
                                'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                                'data_atualizacao': None,
                                'data_ocorrencia': pd.Timestamp(soma_mensal.index[-1].start_time).strftime('%Y-%m-%d %H:%M:%S'),
                                'categoria': categoria,
                                'valor': float(valor_atual),
                                'origem': 'ARIMA',
                                'dados_adicionais': json.dumps({
                                    'valor_previsto': float(forecast[0]),
                                    'intervalo_confianca': [float(lower_bound), float(upper_bound)],
                                    'tipo': tipo,
                                    'mes_referencia': str(soma_mensal.index[-1])
                                }, ensure_ascii=False),
                                'automatico': 1,
                                'transacao_id': None
                            }
                            self.alertas.append(alerta)
                            alertas_gerados += 1
                            self.logger.info(f"Alerta gerado: {alerta['titulo']} (Valor: R${valor_atual:,.2f})")
                
                except Exception as e:
                    self.logger.error(f"Erro ao processar grupo {categoria}/{tipo}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Previsão ARIMA concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na previsão ARIMA: {e}", exc_info=True)
            return []

    def calcular_roi_por_ativo(self):
        """
        Calcula o Retorno sobre Investimento (ROI) por ativo com tratamento robusto para diferentes cenários.
        
        Melhorias implementadas:
        - Validação de dados de entrada
        - Tratamento para valores ausentes ou inválidos
        - Limite mínimo de investimento para evitar divisão por zero
        - Análise histórica para contexto adicional
        - Logs detalhados para diagnóstico
        """
        try:
            self.logger.info("🔍 Iniciando cálculo de ROI por ativo...")
            
            # Verifica se as colunas necessárias existem
            colunas_necessarias = ['ativo', 'valor', 'data', 'tipo_operacao']
            if not all(col in self.df.columns for col in colunas_necessarias):
                colunas_faltando = [col for col in colunas_necessarias if col not in self.df.columns]
                self.logger.warning(f"⚠️ Colunas necessárias não encontradas: {', '.join(colunas_faltando)}")
                return []
                
            # Filtra apenas as transações de investimento (compras e vendas)
            df_investimentos = self.df[self.df['tipo_operacao'].str.contains('investimento|compra|venda', case=False, na=False)].copy()
            
            if df_investimentos.empty:
                self.logger.info("ℹ️ Nenhuma transação de investimento encontrada.")
                return []
                
            # Converte valores para numérico
            df_investimentos['valor'] = pd.to_numeric(
                df_investimentos['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True),
                errors='coerce'
            )
            
            # Remove valores inválidos
            df_investimentos = df_investimentos[~df_investimentos['valor'].isin([np.nan, np.inf, -np.inf])]
            
            # Conversão de data
            df_investimentos['data'] = pd.to_datetime(df_investimentos['data'], errors='coerce')
            df_investimentos = df_investimentos[df_investimentos['data'].notna()]
            
            if df_investimentos.empty:
                self.logger.warning("⚠️ Nenhum dado válido após a limpeza.")
                return []
                
            # Adiciona coluna de mês para agrupamento
            df_investimentos['mes'] = df_investimentos['data'].dt.to_period('M')
            
            # Agrupa por ativo e mês para calcular o ROI
            df_agrupado = df_investimentos.groupby(['ativo', 'mes']).agg({
                'valor': 'sum',
                'quantidade': 'sum',
                'preco': 'mean'
            }).reset_index()
            
            # Calcula o ROI para cada ativo
            df_agrupado['roi'] = df_agrupado.groupby('ativo')['valor'].pct_change() * 100
            
            # Filtra apenas os ROIs válidos
            df_roi = df_agrupado[df_agrupado['roi'].notna()]
            
            if df_roi.empty:
                self.logger.info("ℹ️ Não foi possível calcular o ROI para nenhum ativo.")
                return []
                
            # Ordena por ROI decrescente
            df_roi = df_roi.sort_values('roi', ascending=False)
            
            # Prepara os alertas
            alertas = []
            for _, row in df_roi.iterrows():
                alerta = {
                    'tipo': 'ROI',
                    'titulo': f"ROI para {row['ativo']}",
                    'descricao': f"Retorno sobre Investimento de {row['roi']:.2f}% para o ativo {row['ativo']} no mês {row['mes']}",
                    'valor': float(row['roi']),
                    'data_ocorrencia': row['mes'].to_timestamp().strftime('%Y-%m-%d'),
                    'prioridade': 'alta' if abs(row['roi']) > 10 else 'media',
                    'categoria': 'investimento',
                    'status': 'pendente'
                }
                alertas.append(alerta)
                
            self.logger.info(f"✅ Cálculo de ROI concluído. {len(alertas)} alertas gerados.")
            return alertas
            
            if df_clean.empty:
                self.logger.warning("⚠️ Nenhum dado válido após limpeza.")
                return []
                
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            meses_analise = 3  # Número de meses para análise histórica
            alertas_gerados = 0
            
            # Limite mínimo de investimento para considerar o cálculo (ajustado por categoria)
            LIMITES_MINIMOS = {
                'CDB': 1000.0,     # Investimentos mais robustos
                'Ações': 100.0,    # Ações individuais
                'FII': 100.0,      # Fundos Imobiliários
                'Cripto': 50.0,    # Criptomoedas
                'default': 50.0    # Valor padrão para outros ativos
            }
            
            self.logger.info(f"📊 Analisando ROI para {df_clean['ativo'].nunique()} ativos...")
            
            for ativo, grupo in df_clean.groupby('ativo'):
                try:
                    self.logger.debug(f"📈 Processando ativo: {ativo}")
                    
                    # Filtra para o mês atual
                    df_mes = grupo[grupo['Mes'] == mes_atual]
                    if df_mes.empty:
                        self.logger.debug(f"  ℹ️  Sem dados para o mês atual {mes_atual}")
                        continue
                    
                    # Calcula investimento e retorno
                    investimento = abs(df_mes[df_mes['tipo'] == 'despesa']['valor'].sum())
                    retorno = df_mes[df_mes['tipo'] == 'receita']['valor'].sum()
                    
                    # Obtém o limite mínimo com base no tipo de ativo
                    limite_minimo = next(
                        (limite for chave, limite in LIMITES_MINIMOS.items() 
                         if chave.lower() in ativo.lower() and chave != 'default'),
                        LIMITES_MINIMOS['default']
                    )
                    
                    # Validação de investimento mínimo
                    if investimento < limite_minimo:
                        self.logger.debug(f"  ℹ️  Investimento R${investimento:.2f} abaixo do mínimo (R${limite_minimo:.2f}) para {ativo}")
                        continue
                    
                    # Cálculo do ROI com proteção contra divisão por zero
                    # Considera apenas se houver investimento significativo
                    if investimento > 0:
                        # Se não houver retorno no mês, verifica se é um investimento novo
                        if retorno == 0:
                            # Verifica se é um investimento recorrente (já teve retorno em meses anteriores)
                            tem_historico_positivo = any(
                                (grupo[(grupo['Mes'] < mes_atual) & (grupo['tipo'] == 'receita')]['valor'] > 0).any()
                                for _ in range(3)  # Verifica nos últimos 3 meses
                            )
                            
                            if tem_historico_positivo:
                                # Investimento recorrente sem retorno no mês
                                roi = -1.0  # -100% de ROI
                            else:
                                # Novo investimento, ainda sem retorno esperado
                                self.logger.debug(f"  ℹ️  Investimento em {ativo} ainda não teve retorno (investimento novo)")
                                continue
                        else:
                            # Cálculo normal do ROI
                            roi = (retorno - investimento) / investimento
                    else:
                        # Investimento zero ou negativo
                        self.logger.debug(f"  ℹ️  Investimento zero ou negativo para {ativo}")
                        continue
                    
                    # Análise histórica para contexto
                    meses_analisados = 6  # Aumentado para 6 meses para melhor contexto
                    meses_anteriores = grupo[grupo['Mes'] < mes_atual].sort_values('Mes', ascending=False)
                    roi_historico = []
                    
                    if not meses_anteriores.empty:
                        for mes, mes_grupo in meses_anteriores.groupby('Mes'):
                            inv = abs(mes_grupo[mes_grupo['tipo'] == 'despesa']['valor'].sum())
                            ret = mes_grupo[mes_grupo['tipo'] == 'receita']['valor'].sum()
                            if inv >= limite_minimo:
                                roi_hist = (ret - inv) / inv if inv > 0 else float('-inf')
                                roi_historico.append(roi_hist)
                            if len(roi_historico) >= meses_analisados:
                                break
                    
                    # Cálculo da média do ROI histórico (se disponível)
                    roi_medio = np.mean(roi_historico) if roi_historico else None
                    
                    # Determina a prioridade com base no ROI e desvio histórico
                    if roi_medio is not None:
                        desvio_roi = abs(roi - roi_medio) if roi_medio != 0 else abs(roi)
                        
                        # Ajusta a prioridade com base no ROI atual e histórico
                        if roi <= -0.5:  # ROI de -50% ou pior
                            prioridade = 'alta'
                        elif roi <= -0.2:  # ROI entre -20% e -50%
                            prioridade = 'media'
                        elif desvio_roi > 0.5:  # Desvio forte em relação à média
                            prioridade = 'media' if roi > 0 else 'alta'
                        else:
                            prioridade = 'baixa'
                    else:
                        # Sem histórico, prioridade baseada apenas no ROI atual
                        if roi <= -0.5:
                            prioridade = 'alta'
                        elif roi <= -0.2:
                            prioridade = 'media'
                        else:
                            prioridade = 'baixa'
                    
                    # Verifica se o ROI está abaixo do limite configurado
                    # Ajusta o limite mínimo com base no histórico
                    limite_roi = CONFIG.get('limite_roi', 0.0)
                    
                    # Se houver histórico, ajusta o limite com base na média histórica
                    if roi_historico:
                        roi_medio_historico = np.mean(roi_historico)
                        # Se a média histórica for melhor que o limite padrão, usa 50% da média
                        if roi_medio_historico > limite_roi:
                            limite_roi = max(limite_roi, roi_medio_historico * 0.5)
                    
                    # Considera apenas ROIs negativos ou abaixo do limite
                    if roi < max(limite_roi, -0.05):  # Mínimo de -5% de ROI para alerta
                        # Formatação para exibição
                        investimento_fmt = f"R$ {investimento:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        retorno_fmt = f"R$ {retorno:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        roi_percent = roi * 100
                        
                        # Mensagem descritiva com contexto histórico
                        contexto_historico = ""
                        if roi_historico:
                            roi_medio_pct = np.mean(roi_historico) * 100
                            contexto_historico = (
                                f" Média histórica: {roi_medio_pct:+.2f}% nos últimos {len(roi_historico)} meses."
                            )
                        
                        # Cria o alerta
                        alerta = {
                            'titulo': f"ROI de {roi_percent:+.2f}% em {ativo}",
                            'descricao': (
                                f"ROI de {roi_percent:+.2f}% em {ativo} no mês {mes_atual}. "
                                f"Investimento: {investimento_fmt}, Retorno: {retorno_fmt}."
                                f"{contexto_historico}"
                            ),
                            'tipo': 'investimento',
                            'prioridade': prioridade,
                            'status': 'pendente',
                            'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'data_atualizacao': None,
                            'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                            'categoria': 'Investimentos',
                            'valor': float(retorno - investimento),
                            'origem': 'Análise de ROI',
                            'dados_adicionais': json.dumps({
                                'roi': float(roi),
                                'investimento': float(investimento),
                                'retorno': float(retorno),
                                'ativo': ativo,
                                'mes_referencia': str(mes_atual),
                                'roi_historico': [float(r) for r in roi_historico] if roi_historico else None,
                                'roi_medio_historico': float(roi_medio) if roi_medio is not None else None,
                                'limite_roi': float(limite_roi)
                            }, ensure_ascii=False),
                            'automatico': 1,
                            'transacao_id': None
                        }
                        
                        self.alertas.append(alerta)
                        alertas_gerados += 1
                        self.logger.info(f"✅ Alerta gerado para {ativo}: ROI {roi_percent:+.2f}% "
                                      f"(Investimento: {investimento_fmt}, Retorno: {retorno_fmt})")
                    
                except Exception as e:
                    self.logger.error(f"❌ Erro ao processar ativo {ativo}: {str(e)}", exc_info=True)
                    continue
            
            self.logger.info(f"✅ Análise de ROI concluída. Gerados {alertas_gerados} alertas para {df_clean['ativo'].nunique()} ativos.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"❌ Erro inesperado no cálculo de ROI: {str(e)}", exc_info=True)
            return []

    def calcular_sharpe_ratio(self):
        """
        Calcula o Sharpe Ratio por ativo.
        """
        try:
            self.logger.info("Iniciando cálculo de Sharpe Ratio.")
            if self.df.empty or 'valor' not in self.df.columns or 'ativo' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem colunas 'valor' ou 'ativo'.")
                return []
            
            df_clean = self.df.dropna(subset=['ativo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            
            alertas_gerados = 0
            for ativo, grupo in df_clean.groupby('ativo'):
                try:
                    retornos = grupo.groupby('Mes')['valor'].sum().pct_change().dropna()
                    if len(retornos) < 6:
                        self.logger.debug(f"ativo {ativo} com menos de 6 meses de retornos.")
                        continue
                    
                    media_retorno = retornos.mean()
                    desvio_retorno = retornos.std() or 0.01
                    sharpe = media_retorno / desvio_retorno * np.sqrt(12)  # Anualizado
                    if sharpe < CONFIG.get('limite_sharpe', 1.0):
                        alerta = {
                            'titulo': f"Sharpe Ratio Baixo em {ativo}",
                            'descricao': (
                                f"Sharpe Ratio de {sharpe:.2f} em {ativo}. "
                                f"Retorno médio mensal: {media_retorno*100:.2f}%, Volatilidade: {desvio_retorno*100:.2f}%."
                            ),
                            'tipo': 'investimento',
                            'prioridade': 'media',
                            'status': 'pendente',
                            'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'data_atualizacao': None,
                            'data_ocorrencia': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'categoria': None,
                            'valor': 0.0,
                            'origem': 'Sharpe Ratio',
                            'dados_adicionais': json.dumps({
                                'sharpe_ratio': float(sharpe),
                                'media_retorno': float(media_retorno),
                                'desvio_retorno': float(desvio_retorno),
                                'ativo': ativo
                            }, ensure_ascii=False),
                            'automatico': 1,
                            'transacao_id': None
                        }
                        self.alertas.append(alerta)
                        alertas_gerados += 1
                        self.logger.info(f"Alerta gerado: {alerta['titulo']} (Sharpe: {sharpe:.2f})")
                
                except Exception as e:
                    self.logger.error(f"Erro ao processar ativo {ativo}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Cálculo de Sharpe Ratio concluído. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado no cálculo de Sharpe Ratio: {e}", exc_info=True)
            return []

    def analisar_volatilidade_mensal(self):
        """
        Detecta meses com alta volatilidade em gastos.
        """
        try:
            self.logger.info("Iniciando análise de volatilidade mensal.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['categoria', 'tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            df_clean = df_clean[df_clean['tipo'] == 'despesa']
            
            alertas_gerados = 0
            for (categoria, tipo), grupo in df_clean.groupby(['categoria', 'tipo']):
                try:
                    soma_mensal = grupo.groupby('Mes')['valor'].sum().sort_index()
                    if len(soma_mensal) < 6:
                        self.logger.debug(f"Grupo {categoria}/{tipo} com menos de 6 meses de dados.")
                        continue
                    
                    volatilidade = soma_mensal.pct_change().std() * np.sqrt(12)  # Anualizada
                    if volatilidade > CONFIG.get('limite_volatilidade', 0.5):
                        mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
                        valor_atual = soma_mensal[mes_atual] if mes_atual in soma_mensal.index else 0
                        valor_formatado = f"{valor_atual:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        alerta = {
                            'titulo': f"Alta Volatilidade em {categoria}",
                            'descricao': (
                                f"Volatilidade anualizada de {volatilidade:.2f} em {categoria} ({tipo}) em {mes_atual}. "
                                f"Valor atual: R${valor_formatado}."
                            ),
                            'tipo': 'risco',
                            'prioridade': 'media',
                            'status': 'pendente',
                            'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'data_atualizacao': None,
                            'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                            'categoria': categoria,
                            'valor': float(valor_atual),
                            'origem': 'Volatilidade Mensal',
                            'dados_adicionais': json.dumps({
                                'volatilidade': float(volatilidade),
                                'tipo': tipo,
                                'mes_referencia': str(mes_atual)
                            }, ensure_ascii=False),
                            'automatico': 1,
                            'transacao_id': None
                        }
                        self.alertas.append(alerta)
                        alertas_gerados += 1
                        self.logger.info(f"Alerta gerado: {alerta['titulo']} (Volatilidade: {volatilidade:.2f})")
                
                except Exception as e:
                    self.logger.error(f"Erro ao processar grupo {categoria}/{tipo}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Análise de volatilidade mensal concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de volatilidade: {e}", exc_info=True)
            return []

    def detectar_saldo_negativo(self):
        """
        Detecta meses com saldo (receita - despesa) negativo.
        """
        try:
            self.logger.info("Iniciando detecção de saldo negativo.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            soma_por_tipo = df_clean.groupby(['Mes', 'tipo'])['valor'].sum().unstack().fillna(0)
            
            alertas_gerados = 0
            if mes_atual in soma_por_tipo.index:
                despesa = abs(soma_por_tipo.loc[mes_atual, 'despesa'] if 'despesa' in soma_por_tipo.columns else 0)
                receita = soma_por_tipo.loc[mes_atual, 'receita'] if 'receita' in soma_por_tipo.columns else 0
                saldo = receita - despesa
                if saldo < 0:
                    saldo_formatado = f"{abs(saldo):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    despesa_formatada = f"{despesa:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    receita_formatada = f"{receita:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    alerta = {
                        'titulo': 'Saldo Negativo Detectado',
                        'descricao': (
                            f"Saldo negativo de R${saldo_formatado} em {mes_atual}. "
                            f"Despesa: R${despesa_formatada}, Receita: R${receita_formatada}."
                        ),
                        'tipo': 'orcamento',
                        'prioridade': 'alta',
                        'status': 'pendente',
                        'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                        'data_atualizacao': None,
                        'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                        'categoria': None,
                        'valor': float(saldo),
                        'origem': 'Saldo Negativo',
                        'dados_adicionais': json.dumps({
                            'saldo': float(saldo),
                            'despesa': float(despesa),
                            'receita': float(receita),
                            'mes_referencia': str(mes_atual)
                        }, ensure_ascii=False),
                        'automatico': 1,
                        'transacao_id': None
                    }
                    self.alertas.append(alerta)
                    alertas_gerados += 1
                    self.logger.info(f"Alerta gerado: {alerta['titulo']} (Saldo: R${saldo:,.2f})")
            
            self.logger.info(f"Detecção de saldo negativo concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na detecção de saldo negativo: {e}", exc_info=True)
            return []

    def analisar_liquidez(self):
        """
        Verifica a liquidez (receitas/despesas de curto prazo).
        """
        try:
            self.logger.info("Iniciando análise de liquidez.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            df_mes = df_clean[df_clean['Mes'] == mes_atual]
            
            if df_mes.empty:
                self.logger.warning(f"Nenhum dado para o mês atual {mes_atual}.")
                return []
            
            receitas = df_mes[df_mes['tipo'] == 'receita']['valor'].sum()
            despesas = abs(df_mes[df_mes['tipo'] == 'despesa']['valor'].sum())
            
            alertas_gerados = 0
            if despesas > 0:
                razao_liquidez = receitas / despesas
                if razao_liquidez < CONFIG.get('limite_liquidez', 1.0):
                    receitas_formatada = f"{receitas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    despesas_formatada = f"{despesas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    alerta = {
                        'titulo': 'Baixa Liquidez Detectada',
                        'descricao': (
                            f"Razão de liquidez de {razao_liquidez:.2f} em {mes_atual}. "
                            f"Receitas: R${receitas_formatada}, Despesas: R${despesas_formatada}."
                        ),
                        'tipo': 'risco',
                        'prioridade': 'alta',
                        'status': 'pendente',
                        'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                        'data_atualizacao': None,
                        'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                        'categoria': None,
                        'valor': float(receitas - despesas),
                        'origem': 'Liquidez',
                        'dados_adicionais': json.dumps({
                            'razao_liquidez': float(razao_liquidez),
                            'receitas': float(receitas),
                            'despesas': float(despesas),
                            'mes_referencia': str(mes_atual)
                        }, ensure_ascii=False),
                        'automatico': 1,
                        'transacao_id': None
                    }
                    self.alertas.append(alerta)
                    alertas_gerados += 1
                    self.logger.info(f"Alerta gerado: {alerta['titulo']} (Liquidez: {razao_liquidez:.2f})")
            
            self.logger.info(f"Análise de liquidez concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de liquidez: {e}", exc_info=True)
            return []

    def clusterizar_transacoes(self):
        """
        Aplica clustering para identificar padrões anormais nas transações.
        """
        try:
            self.logger.info("Iniciando clusterização de transações.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Dia'] = df_clean['data'].dt.day
            df_clean['Hora'] = df_clean['data'].dt.hour
            
            if len(df_clean) < CONFIG.get('min_transacoes_cluster', 50):
                self.logger.warning(f"Menos de {CONFIG.get('min_transacoes_cluster', 50)} transações para clusterização.")
                return []
            
            X = df_clean[['valor', 'Dia', 'Hora']].values
            kmeans = KMeans(n_clusters=CONFIG.get('n_clusters', 3), random_state=42).fit(X)
            df_clean['Cluster'] = kmeans.labels_
            
            cluster_sizes = df_clean['Cluster'].value_counts()
            pequenos_clusters = cluster_sizes[cluster_sizes < CONFIG.get('limite_cluster_tamanho', 5)].index
            
            alertas_gerados = 0
            for _, row in df_clean[df_clean['Cluster'].isin(pequenos_clusters)].iterrows():
                valor_formatado = f"{row['valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                data_formatada = row['data'].strftime('%d/%m/%Y %H:%M')
                alerta = {
                    'titulo': 'Transação em Cluster Anormal',
                    'descricao': (
                        f"Transação de R${valor_formatado} em {data_formatada} pertence a um cluster pequeno "
                        f"(Cluster {row['Cluster']})."
                    ),
                    'tipo': 'anomalia',
                    'prioridade': 'media',
                    'status': 'pendente',
                    'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                    'data_atualizacao': None,
                    'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'categoria': row.get('categoria'),
                    'valor': float(row['valor']),
                    'origem': 'Clusterização',
                    'dados_adicionais': json.dumps({
                        'cluster': int(row['Cluster']),
                        'tamanho_cluster': int(cluster_sizes[row['Cluster']]),
                        'dia': int(row['Dia']),
                        'hora': int(row['Hora'])
                    }, ensure_ascii=False),
                    'automatico': 1,
                    'transacao_id': row.get('Transacao_ID')
                }
                self.alertas.append(alerta)
                alertas_gerados += 1
                self.logger.info(f"Alerta gerado: {alerta['titulo']} (Cluster: {row['Cluster']})")
            
            self.logger.info(f"Clusterização de transações concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na clusterização: {e}", exc_info=True)
            return []

    def detectar_fraudes(self):
        """
        Identifica transações potencialmente fraudulentas com base em padrões.
        """
        try:
            self.logger.info("Iniciando detecção de fraudes...")
            if self.df.empty or 'valor' not in self.df.columns or 'data' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem colunas 'valor' ou 'data'.")
                return []
                
            # Define o mês atual para referência
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
                
            df_clean = self.df.dropna(subset=['valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            
            alertas_gerados = 0
            for idx, row in df_clean.iterrows():
                valor = abs(row['valor'])
                hora = row['data'].hour
                if valor > CONFIG.get('limite_fraude_valor', 5000) and (hora < 6 or hora > 22):
                    valor_formatado = f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    data_formatada = row['data'].strftime('%d/%m/%Y %H:%M')
                    alerta = {
                        'titulo': 'Possível Fraude Detectada',
                        'descricao': (
                            f"Transação de R${valor_formatado} em {data_formatada} realizada em horário atípico "
                            f"(fora do intervalo 06:00-22:00)."
                        ),
                        'tipo': 'fraude',
                        'prioridade': 'alta',
                        'status': 'pendente',
                        'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                        'data_atualizacao': None,
                        'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                        'categoria': row.get('categoria'),
                        'valor': float(valor),
                        'origem': 'Detecção de Fraudes',
                        'dados_adicionais': json.dumps({
                            'hora': int(hora),
                            'valor': float(valor)
                        }, ensure_ascii=False),
                        'automatico': 1,
                        'transacao_id': row.get('Transacao_ID')
                    }
                    self.alertas.append(alerta)
                    alertas_gerados += 1
                    self.logger.info(f"Alerta gerado: {alerta['titulo']} (Valor: R${valor:,.2f}, Hora: {hora})")
            
            self.logger.info(f"Detecção de fraudes concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na detecção de fraudes: {e}", exc_info=True)
            return []

    def analisar_sazonalidade(self, meses_minimos=3):
        """
        Detecta padrões sazonais anormais em despesas.
        
        Args:
            meses_minimos (int): Número mínimo de meses necessários para análise. Default: 3
        """
        try:
            self.logger.info("Iniciando análise de sazonalidade.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['categoria', 'tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.month
            df_clean = df_clean[df_clean['tipo'] == 'despesa']
            
            if df_clean.empty:
                self.logger.warning("Nenhuma despesa encontrada para análise de sazonalidade.")
                return []
                
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').month
            alertas_gerados = 0
            
            for (categoria, tipo), grupo in df_clean.groupby(['categoria', 'tipo']):
                try:
                    # Agrupa por mês e calcula a soma dos valores
                    soma_por_mes = grupo.groupby('Mes')['valor'].sum()
                    
                    # Verifica se temos dados suficientes
                    if len(soma_por_mes) < meses_minimos:
                        self.logger.debug(f"Grupo {categoria}/{tipo} com apenas {len(soma_por_mes)} meses de dados (mínimo: {meses_minimos}).")
                        continue
                    
                    # Calcula métricas de tendência
                    media_sazonal = soma_por_mes.mean()
                    desvio_sazonal = soma_por_mes.std() or 0.01
                    mediana_sazonal = soma_por_mes.median()
                    
                    # Calcula o valor atual (mês atual) ou o último mês disponível
                    valor_atual = soma_por_mes.get(mes_atual, soma_por_mes.iloc[-1] if not soma_por_mes.empty else 0)
                    
                    # Ajusta o limiar com base no número de meses disponíveis
                    fator_ajuste = min(1.0, len(soma_por_mes) / 6.0)  # Reduz a sensibilidade para poucos dados
                    limite_superior = media_sazonal + (CONFIG.get('limite_sazonalidade', 2.0) * desvio_sazonal * fator_ajuste)
                    limite_inferior = media_sazonal - (CONFIG.get('limite_sazonalidade', 2.0) * desvio_sazonal * fator_ajuste)
                    
                    # Verifica se o valor atual está fora dos limites
                    if valor_atual > limite_superior or valor_atual < limite_inferior:
                        # Formata os valores para exibição
                        valor_formatado = f"{abs(valor_atual):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        limite_formatado = f"{limite_superior:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        
                        # Determina o tipo de alerta com base no desvio
                        if valor_atual > limite_superior:
                            tipo_alerta = 'alta'
                            percentual_acima = ((valor_atual/media_sazonal)-1)*100
                            descricao = f"Despesa de R${valor_formatado} em {categoria} no mês {mes_atual} está {percentual_acima:.1f}% acima da média mensal (R${media_sazonal:,.2f})."
                        else:
                            tipo_alerta = 'baixa'
                            percentual_abaixo = (1 - (valor_atual/media_sazonal))*100
                            descricao = f"Despesa de R${valor_formatado} em {categoria} no mês {mes_atual} está {percentual_abaixo:.1f}% abaixo da média mensal (R${media_sazonal:,.2f})."
                            
                        # Adiciona contexto adicional se tivermos poucos dados
                        if len(soma_por_mes) < 6:
                            descricao += f" (Análise baseada em apenas {len(soma_por_mes)} meses de dados - resultados podem variar com mais dados históricos)"
                        
                        alerta = {
                            'titulo': f"Sazonalidade Anormal em {categoria} - {tipo_alerta.upper()}",
                            'descricao': descricao,
                            'tipo': 'sazonalidade',
                            'prioridade': 'media' if tipo_alerta == 'baixa' else 'alta',
                            'status': 'pendente',
                            'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'data_atualizacao': None,
                            'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                            'categoria': categoria,
                            'valor': float(valor_atual),
                            'origem': 'Sazonalidade',
                            'dados_adicionais': json.dumps({
                                'media_sazonal': float(media_sazonal),
                                'desvio_sazonal': float(desvio_sazonal),
                                'limite': float(limite),
                                'mes': mes_atual
                            }, ensure_ascii=False),
                            'automatico': 1,
                            'transacao_id': None
                        }
                        self.alertas.append(alerta)
                        alertas_gerados += 1
                        self.logger.info(f"Alerta gerado: {alerta['titulo']} (Valor: R${valor_atual:,.2f})")
                
                except Exception as e:
                    self.logger.error(f"Erro ao processar grupo {categoria}/{tipo}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Análise de sazonalidade concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de sazonalidade: {e}", exc_info=True)
            return []

    def calcular_beta_por_ativo(self, meses_minimos=3):
        """
        Calcula o Beta de ativos em relação a um índice de referência.
        
        Args:
            meses_minimos (int): Número mínimo de meses necessários para o cálculo. Default: 3
        """
        try:
            self.logger.info(f"Iniciando cálculo de Beta por ativo (mínimo de {meses_minimos} meses).")
            if self.df.empty or 'valor' not in self.df.columns or 'ativo' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem colunas 'valor' ou 'ativo'.")
                return []
            
            # Pré-processamento dos dados
            df_clean = self.df.dropna(subset=['ativo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            
            # Ordena por data para garantir a sequência correta
            df_clean = df_clean.sort_values('data')
            
            alertas_gerados = 0
            for ativo, grupo in df_clean.groupby('ativo'):
                try:
                    # Agrupa por mês e calcula a soma dos valores
                    valores_mensais = grupo.groupby('Mes')['valor'].sum()
                    
                    # Calcula os retornos mensais
                    retornos = valores_mensais.pct_change().dropna()
                    
                    # Verifica se temos dados suficientes
                    if len(retornos) < meses_minimos:
                        self.logger.debug(f"ativo {ativo} com apenas {len(retornos)} meses de retornos (mínimo: {meses_minimos}).")
                        continue
                    
                    # Simulação de retornos do mercado (exemplo simplificado)
                    # Em um cenário real, você usaria um índice de mercado real
                    np.random.seed(42)  # Para resultados reproduzíveis
                    fator_mercado = 1.1  # Fator de correlação com o mercado
                    ruido = np.random.normal(0, 0.05, len(retornos))  # Ruído aleatório
                    mercado = (retornos * fator_mercado) + ruido
                    
                    # Calcula a covariância e a variância
                    cov = np.cov(retornos, mercado)[0, 1]
                    var_mercado = np.var(mercado, ddof=1)
                    
                    # Evita divisão por zero
                    if var_mercado == 0:
                        self.logger.warning(f"Variância do mercado próxima de zero para o ativo {ativo}.")
                        continue
                    
                    # Calcula o Beta e métricas adicionais
                    beta = cov / var_mercado if var_mercado != 0 else 0
                    
                    # Calcula métricas adicionais para análise
                    correlacao = np.corrcoef(retornos, mercado)[0, 1]
                    volatilidade_ativo = np.std(retornos, ddof=1) * np.sqrt(12)  # Anualizada
                    
                    # Determina o perfil de risco baseado no Beta
                    if beta > 1.5:
                        perfil_risco = "MUITO AGRESSIVO"
                        prioridade = 'alta'
                    elif beta > 1.0:
                        perfil_risco = "AGRESSIVO"
                        prioridade = 'media'
                    elif beta > 0.5:
                        perfil_risco = "MODERADO"
                        prioridade = 'baixa'
                    elif beta > 0:
                        perfil_risco = "CONSERVADOR"
                        prioridade = 'baixa'
                    else:
                        perfil_risco = "DEFENSIVO"
                        prioridade = 'media'  # Beta negativo pode ser intencional
                    
                    # Gera alerta se o Beta estiver fora da faixa esperada ou se for um ativo novo
                    if abs(beta) > 1.5 or abs(beta) < 0.5 or len(retornos) < 6:
                        # Contexto adicional para ativos com poucos dados
                        contexto_adicional = ""
                        if len(retornos) < 6:
                            confiabilidade = min(50 + (len(retornos) * 10), 90)  # 60% para 3 meses, 90% para 6+ meses
                            contexto_adicional = f" Análise baseada em apenas {len(retornos)} meses (confiabilidade: {confiabilidade}%)."
                        
                        alerta = {
                            'titulo': f"Beta {perfil_risco} para {ativo}",
                            'descricao': (
                                f"Beta: {beta:.2f} (faixa esperada: 0.5-1.5). "
                                f"Correlação com mercado: {correlacao:.2f}. "
                                f"Volatilidade anualizada: {volatilidade_ativo*100:.1f}%.{contexto_adicional}"
                            ),
                            'tipo': 'risco',
                            'prioridade': prioridade,
                            'status': 'pendente',
                            'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'data_atualizacao': None,
                            'categoria': ativo,
                            'valor': beta,
                            'transacao_id': f"beta_{ativo}_{pd.Timestamp.now().strftime('%Y%m%d')}",
                            'data_ocorrencia': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'metadados': json.dumps({
                                'correlacao': float(correlacao),
                                'volatilidade_anual': float(volatilidade_ativo),
                                'meses_analisados': len(retornos),
                                'data_inicio': str(valores_mensais.index.min()),
                                'data_fim': str(valores_mensais.index.max())
                            }),
                            'origem': 'Beta ativo',
                            'dados_adicionais': json.dumps({
                                'beta': float(beta),
                                'ativo': ativo,
                                'perfil_risco': perfil_risco,
                                'correlacao': float(correlacao),
                                'volatilidade_anual': float(volatilidade_ativo)
                            }, ensure_ascii=False),
                            'automatico': 1,
                            'transacao_id': f"beta_{ativo}_{pd.Timestamp.now().strftime('%Y%m%d')}"
                        }
                        self.alertas.append(alerta)
                        alertas_gerados += 1
                        self.logger.info(f"Alerta gerado: {alerta['titulo']} (Beta: {beta:.2f})")
                
                except Exception as e:
                    self.logger.error(f"Erro ao processar ativo {ativo}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Cálculo de Beta concluído. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado no cálculo de Beta: {e}", exc_info=True)
            return []

    def calcular_var(self, meses_minimos=3, nivel_confianca=95):
        """
        Calcula o Value at Risk (VaR) para despesas mensais.
        
        Args:
            meses_minimos (int): Número mínimo de meses necessários para o cálculo. Default: 3
            nivel_confianca (int): Nível de confiança para o VaR (90, 95, 99). Default: 95
        """
        try:
            self.logger.info(f"Iniciando cálculo de VaR (mínimo de {meses_minimos} meses, {nivel_confianca}% de confiança).")
            
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            # Valida o nível de confiança
            if nivel_confianca not in [90, 95, 99]:
                self.logger.warning(f"Nível de confiança {nivel_confianca}% inválido. Usando 95%.")
                nivel_confianca = 95
                
            percentil = 100 - nivel_confianca
            
            # Pré-processamento dos dados
            df_clean = self.df.dropna(subset=['categoria', 'tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            
            # Filtra apenas despesas e agrupa por mês
            df_despesas = df_clean[df_clean['tipo'] == 'despesa']
            if df_despesas.empty:
                self.logger.warning("Nenhuma despesa encontrada para cálculo de VaR.")
                return []
            
            # Calcula o total de despesas por mês
            soma_mensal = df_despesas.groupby('Mes')['valor'].sum().sort_index()
            
            # Verifica se temos dados suficientes
            if len(soma_mensal) < meses_minimos:
                self.logger.warning(f"Apenas {len(soma_mensal)} meses de dados disponíveis (mínimo: {meses_minimos}).")
                return []
            
            # Calcula os retornos percentuais
            retornos = soma_mensal.pct_change().dropna()
            
            # Calcula métricas de risco
            media_retorno = retornos.mean()
            desvio_padrao = retornos.std()
            
            # Calcula o VaR paramétrico e histórico
            var_parametrico = -stats.norm.ppf(percentil/100) * desvio_padrao
            var_historico = -np.percentile(retornos, percentil)
            
            # Usa o maior entre os dois métodos para ser mais conservador
            var_final = max(var_parametrico, var_historico)
            
            # Obtém o mês atual e o último retorno disponível
            mes_atual = retornos.index[-1]
            ultimo_retorno = retornos.iloc[-1]
            valor_atual = abs(soma_mensal[mes_atual])
            
            alertas_gerados = 0
            
            # Verifica se o último retorno está abaixo do VaR
            if ultimo_retorno < -var_final:
                # Calcula a confiabilidade com base na quantidade de dados
                confiabilidade = min(90, 50 + (len(retornos) * 5))  # 65% para 3 meses, 90% para 8+ meses
                
                # Contexto adicional para poucos dados
                contexto_adicional = ""
                if len(retornos) < 6:
                    contexto_adicional = f" Análise baseada em apenas {len(retornos)} meses (confiabilidade: {confiabilidade}%)."
                
                # Formatação de valores para exibição
                valor_formatado = f"{valor_atual:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                
                alerta = {
                    'titulo': f'Alerta de Risco Financeiro - VaR {nivel_confianca}%',
                    'descricao': (
                        f"Retorno mensal de {ultimo_retorno*100:+.2f}% está abaixo do VaR {nivel_confianca}% ({-var_final*100:.2f}%).\n"
                        f"• Valor mensal: R$ {valor_formatado}\n"
                        f"• Média histórica: {media_retorno*100:+.2f}%\n"
                        f"• Volatilidade: {desvio_padrao*100:.2f}%{contexto_adicional}"
                    ),
                    'tipo': 'risco',
                    'prioridade': 'alta' if nivel_confianca >= 95 else 'media',
                    'status': 'pendente',
                    'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                    'data_atualizacao': None,
                    'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-01'),
                    'categoria': 'Risco Financeiro',
                    'valor': float(valor_atual),
                    'origem': 'VaR',
                    'dados_adicionais': json.dumps({
                        'var_nivel_confianca': nivel_confianca,
                        'var_parametrico': float(var_parametrico),
                        'var_historico': float(var_historico),
                        'retorno_atual': float(ultimo_retorno),
                        'media_retorno': float(media_retorno),
                        'volatilidade': float(desvio_padrao),
                        'meses_analisados': len(retornos),
                        'data_inicio': str(soma_mensal.index.min()),
                        'data_fim': str(soma_mensal.index.max())
                    }, ensure_ascii=False),
                    'automatico': 1,
                    'transacao_id': f"var_{mes_atual}_{nivel_confianca}"
                }
                self.alertas.append(alerta)
                alertas_gerados += 1
                self.logger.info(f"Alerta gerado: {alerta['titulo']} (VaR {nivel_confianca}%: {-var_final:.2%})")
            
            self.logger.info(f"Cálculo de VaR concluído. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado no cálculo de VaR: {e}", exc_info=True)
            return []

    def calcular_drawdown(self):
        """
        Calcula o Drawdown máximo em investimentos.
        """
        try:
            self.logger.info("Iniciando cálculo de Drawdown.")
            if self.df.empty or 'valor' not in self.df.columns or 'ativo' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem colunas 'valor' ou 'ativo'.")
                return []
            
            df_clean = self.df.dropna(subset=['ativo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            
            alertas_gerados = 0
            for ativo, grupo in df_clean.groupby('ativo'):
                try:
                    retornos = grupo.groupby('Mes')['valor'].sum().cumsum()
                    if len(retornos) < 6:
                        self.logger.debug(f"ativo {ativo} com menos de 6 meses de dados.")
                        continue
                    
                    pico = retornos.cummax()
                    drawdown = (retornos - pico) / pico
                    max_drawdown = drawdown.min()
                    if max_drawdown < -CONFIG.get('limite_drawdown', 0.2):
                        mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
                        valor_atual = retornos[mes_atual] if mes_atual in retornos.index else 0
                        valor_formatado = f"{valor_atual:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        alerta = {
                            'titulo': f"Drawdown Elevado em {ativo}",
                            'descricao': (
                                f"Drawdown máximo de {max_drawdown*100:.2f}% em {ativo}. "
                                f"Valor atual: R${valor_formatado}."
                            ),
                            'tipo': 'investimento',
                            'prioridade': 'alta',
                            'status': 'pendente',
                            'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                            'data_atualizacao': None,
                            'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-01'),
                            'categoria': None,
                            'valor': float(valor_atual),
                            'origem': 'Drawdown',
                            'dados_adicionais': json.dumps({
                                'max_drawdown': float(max_drawdown),
                                'ativo': ativo,
                                'mes_referencia': str(mes_atual)
                            }, ensure_ascii=False),
                            'automatico': 1,
                            'transacao_id': None
                        }
                        self.alertas.append(alerta)
                        alertas_gerados += 1
                        self.logger.info(f"Alerta gerado: {alerta['titulo']} (Drawdown: {max_drawdown*100:.2f}%)")
                
                except Exception as e:
                    self.logger.error(f"Erro ao processar ativo {ativo}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Cálculo de Drawdown concluído. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado no cálculo de Drawdown: {e}", exc_info=True)
            return []

    def analisar_forma_pagamento(self):
        """
        Detecta mudanças anormais na forma de pagamento.
        """
        try:
            self.logger.info("Iniciando análise de forma de pagamento.")
            if self.df.empty or 'valor' not in self.df.columns or 'forma_pagamento' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem colunas 'valor' ou 'forma_pagamento'.")
                return []
                
            df_clean = self.df.dropna(subset=['valor', 'forma_pagamento']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['mes'] = df_clean['data'].dt.to_period('M')
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            df_mes = df_clean[df_clean['mes'] == mes_atual]
            df_historico = df_clean[df_clean['mes'] < mes_atual]
            
            if df_mes.empty or df_historico.empty:
                self.logger.warning("Dados insuficientes para análise de forma de pagamento.")
                return []
            
            freq_atual = df_mes['forma_pagamento'].value_counts(normalize=True)
            freq_historica = df_historico['forma_pagamento'].value_counts(normalize=True)
            
            alertas_gerados = 0
            for forma in freq_atual.index:
                diff = freq_atual.get(forma, 0) - freq_historica.get(forma, 0)
                if diff > CONFIG.get('limite_forma_pagamento', 0.3):
                    alerta = {
                        'titulo': f"Mudança na Forma de Pagamento {forma}",
                        'descricao': (
                            f"Uso de {forma} aumentou em {diff*100:.2f}% em {mes_atual} "
                            f"em relação à média histórica."
                        ),
                        'tipo': 'comportamento',
                        'prioridade': 'media',
                        'status': 'pendente',
                        'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                        'data_atualizacao': None,
                        'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-01'),
                        'categoria': None,
                        'valor': 0.0,
                        'origem': 'Forma Pagamento',
                        'dados_adicionais': json.dumps({
                            'forma_pagamento': forma,
                            'diferenca': float(diff),
                            'frequencia_atual': float(freq_atual.get(forma, 0)),
                            'mes_referencia': str(mes_atual)
                        }, ensure_ascii=False),
                        'automatico': 1,
                        'transacao_id': None
                    }
                    self.alertas.append(alerta)
                    alertas_gerados += 1
                    self.logger.info(f"Alerta gerado: {alerta['titulo']} (Diferença: {diff*100:.2f}%)")
            
            self.logger.info(f"Análise de forma de pagamento concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de forma de pagamento: {e}", exc_info=True)
            return []

    def analisar_frequencia_transacoes(self):
        """
        Detecta aumento anormal na frequência de transações.
        """
        try:
            self.logger.info("Iniciando análise de frequência de transações.")
            if self.df.empty or 'data' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'data'.")
                return []
            
            df_clean = self.df.dropna(subset=['data']).copy()
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['mes'] = df_clean['data'].dt.to_period('M')
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            contagem_mensal = df_clean.groupby('mes').size()
            
            if len(contagem_mensal) < 6:
                self.logger.warning("Menos de 6 meses de dados para análise de frequência.")
                return []
            
            media_historica = contagem_mensal[contagem_mensal.index < mes_atual].mean()
            desvio_historico = contagem_mensal[contagem_mensal.index < mes_atual].std() or 0.01
            contagem_atual = contagem_mensal.get(mes_atual, 0)
            limite = media_historica + CONFIG.get('limite_frequencia', 2.0) * desvio_historico
            
            alertas_gerados = 0
            if contagem_atual > limite:
                alerta = {
                    'titulo': 'Frequência de Transações Anormal',
                    'descricao': (
                        f"Frequência de {contagem_atual} transações em {mes_atual} excede o limite de {limite:.0f} "
                        f"(média histórica: {media_historica:.0f})."
                    ),
                    'tipo': 'comportamento',
                    'prioridade': 'media',
                    'status': 'pendente',
                    'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                    'data_atualizacao': None,
                    'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-01'),
                    'categoria': None,
                    'valor': 0.0,
                    'origem': 'Frequência Transações',
                    'dados_adicionais': json.dumps({
                        'contagem_atual': int(contagem_atual),
                        'media_historica': float(media_historica),
                        'desvio_historico': float(desvio_historico),
                        'mes_referencia': str(mes_atual)
                    }, ensure_ascii=False),
                    'automatico': 1,
                    'transacao_id': None
                }
                self.alertas.append(alerta)
                alertas_gerados += 1
                self.logger.info(f"Alerta gerado: {alerta['titulo']} (Frequência: {contagem_atual})")
            
            self.logger.info(f"Análise de frequência de transações concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de frequência: {e}", exc_info=True)
            return []

    def analisar_concentracao_categoria(self):
        """
        Detecta categorias com concentração anormal de gastos.
        """
        try:
            self.logger.info("Iniciando análise de concentração por categoria.")
            if self.df.empty or 'valor' not in self.df.columns or 'categoria' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem colunas necessárias ('valor' ou 'categoria').")
                return []
            
            df_clean = self.df.dropna(subset=['categoria', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['mes'] = df_clean['data'].dt.to_period('M')
            df_clean = df_clean[df_clean['tipo_operacao'] == 'despesa']
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            df_mes = df_clean[df_clean['mes'] == mes_atual]
            
            if df_mes.empty:
                self.logger.warning(f"Nenhum dado para o mês atual {mes_atual}.")
                return []
            
            total_gasto = abs(df_mes['valor'].sum())
            if total_gasto == 0:
                self.logger.warning("Valor total gasto é zero.")
                return []
                
            soma_por_categoria = abs(df_mes.groupby('categoria')['valor'].sum())
            proporcoes = soma_por_categoria / total_gasto
            
            alertas_gerados = 0
            for categoria, proporcao in proporcoes.items():
                if proporcao > CONFIG.get('limite_concentracao_categoria', 0.5):
                    valor_formatado = f"{soma_por_categoria[categoria]:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    alerta = {
                        'titulo': f"Concentração Alta em {categoria}",
                        'descricao': (
                            f"categoria {categoria} representa {proporcao*100:.2f}% dos gastos em {mes_atual}. "
                            f"Valor: R${valor_formatado}."
                        ),
                        'tipo': 'orcamento',
                        'prioridade': 'media',
                        'status': 'pendente',
                        'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                        'data_atualizacao': None,
                        'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-01'),
                        'categoria': categoria,
                        'valor': float(soma_por_categoria[categoria]),
                        'origem': 'Concentração categoria',
                        'dados_adicionais': json.dumps({
                            'proporcao': float(proporcao),
                            'total_gasto': float(total_gasto),
                            'mes_referencia': str(mes_atual)
                        }, ensure_ascii=False),
                        'automatico': 1,
                        'transacao_id': None
                    }
                    self.alertas.append(alerta)
                    alertas_gerados += 1
                    self.logger.info(f"Alerta gerado: {alerta['titulo']} (Proporção: {proporcao*100:.2f}%)")
            
            self.logger.info(f"Análise de concentração por categoria concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de concentração: {e}", exc_info=True)
            return []

    def analisar_indicadores_financeiros(self):
        """
        Avalia indicadores financeiros personalizados.
        """
        try:
            self.logger.info("Iniciando análise de indicadores financeiros.")
            if self.df.empty or 'indicador_1' not in self.df.columns or 'indicador_2' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem colunas 'indicador_1' ou 'indicador_2'.")
                return []
            
            df_clean = self.df.dropna(subset=['indicador_1', 'indicador_2', 'data']).copy()
            df_clean['indicador_1'] = pd.to_numeric(df_clean['indicador_1'], errors='coerce')
            df_clean['indicador_2'] = pd.to_numeric(df_clean['indicador_2'], errors='coerce')
            df_clean = df_clean[~df_clean[['indicador_1', 'indicador_2']].isin([np.inf, -np.inf, np.nan]).any(axis=1)]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['mes'] = df_clean['data'].dt.to_period('M')
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            df_mes = df_clean[df_clean['mes'] == mes_atual]
            
            if df_mes.empty:
                self.logger.warning(f"Nenhum dado para o mês atual {mes_atual}.")
                return []
            
            media_ind1 = df_mes['indicador_1'].mean()
            media_ind2 = df_mes['indicador_2'].mean()
            
            alertas_gerados = 0
            if media_ind1 > CONFIG.get('limite_indicador_1', 100) or media_ind2 > CONFIG.get('limite_indicador_2', 50):
                alerta = {
                    'titulo': 'Indicadores Financeiros Anormais',
                    'descricao': (
                        f"Indicador 1: {media_ind1:.2f}, Indicador 2: {media_ind2:.2f} em {mes_atual} "
                        f"excedem os limites configurados."
                    ),
                    'tipo': 'risco',
                    'prioridade': 'media',
                    'status': 'pendente',
                    'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                    'data_atualizacao': None,
                    'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-01'),
                    'categoria': None,
                    'valor': 0.0,
                    'origem': 'Indicadores Financeiros',
                    'dados_adicionais': json.dumps({
                        'indicador_1': float(media_ind1),
                        'indicador_2': float(media_ind2),
                        'mes_referencia': str(mes_atual)
                    }, ensure_ascii=False),
                    'automatico': 1,
                    'transacao_id': None
                }
                self.alertas.append(alerta)
                alertas_gerados += 1
                self.logger.info(f"Alerta gerado: {alerta['titulo']} (Indicador 1: {media_ind1:.2f}, Indicador 2: {media_ind2:.2f})")
            
            self.logger.info(f"Análise de indicadores financeiros concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de indicadores: {e}", exc_info=True)
            return []

    def analisar_alavancagem(self):
        """
        Detecta níveis elevados de alavancagem financeira.
        """
        try:
            self.logger.info("Iniciando análise de alavancagem.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            df_mes = df_clean[df_clean['Mes'] == mes_atual]
            
            if df_mes.empty:
                self.logger.warning(f"Nenhum dado para o mês atual {mes_atual}.")
                return []
            
            divida = abs(df_mes[df_mes['tipo'] == 'despesa']['valor'].sum())
            patrimonio = df_mes[df_mes['tipo'] == 'receita']['valor'].sum()
            
            alertas_gerados = 0
            if patrimonio > 0:
                razao_alavancagem = divida / patrimonio
                if razao_alavancagem > CONFIG.get('limite_alavancagem', 2.0):
                    divida_formatada = f"{divida:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    patrimonio_formatado = f"{patrimonio:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    alerta = {
                        'titulo': 'Alavancagem Elevada',
                        'descricao': (
                            f"Razão de alavancagem de {razao_alavancagem:.2f} em {mes_atual}. "
                            f"Dívida: R${divida_formatada}, Patrimônio: R${patrimonio_formatado}."
                        ),
                        'tipo': 'risco',
                        'prioridade': 'alta',
                        'status': 'pendente',
                        'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                        'data_atualizacao': None,
                        'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-01'),
                        'categoria': None,
                        'valor': float(divida),
                        'origem': 'Alavancagem',
                        'dados_adicionais': json.dumps({
                            'razao_alavancagem': float(razao_alavancagem),
                            'divida': float(divida),
                            'patrimonio': float(patrimonio),
                            'mes_referencia': str(mes_atual)
                        }, ensure_ascii=False),
                        'automatico': 1,
                        'transacao_id': None
                    }
                    self.alertas.append(alerta)
                    alertas_gerados += 1
                    self.logger.info(f"Alerta gerado: {alerta['titulo']} (Alavancagem: {razao_alavancagem:.2f})")
            
            self.logger.info(f"Análise de alavancagem concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de alavancagem: {e}", exc_info=True)
            return []

    def analisar_margem_lucro(self):
        """
        Avalia a margem de lucro (receita - despesa) / receita.
        """
        try:
            self.logger.info("Iniciando análise de margem de lucro.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            df_mes = df_clean[df_clean['Mes'] == mes_atual]
            
            if df_mes.empty:
                self.logger.warning(f"Nenhum dado para o mês atual {mes_atual}.")
                return []
            
            receitas = df_mes[df_mes['tipo'] == 'receita']['valor'].sum()
            despesas = abs(df_mes[df_mes['tipo'] == 'despesa']['valor'].sum())
            
            alertas_gerados = 0
            if receitas > 0:
                margem_lucro = (receitas - despesas) / receitas
                if margem_lucro < CONFIG.get('limite_margem_lucro', 0.1):
                    receitas_formatada = f"{receitas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    despesas_formatada = f"{despesas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    alerta = {
                        'titulo': 'Margem de Lucro Baixa',
                        'descricao': (
                            f"Margem de lucro de {margem_lucro*100:.2f}% em {mes_atual}. "
                            f"Receitas: R${receitas_formatada}, Despesas: R${despesas_formatada}."
                        ),
                        'tipo': 'orcamento',
                        'prioridade': 'alta',
                        'status': 'pendente',
                        'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                        'data_atualizacao': None,
                        'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-01'),
                        'categoria': None,
                        'valor': float(receitas - despesas),
                        'origem': 'Margem Lucro',
                        'dados_adicionais': json.dumps({
                            'margem_lucro': float(margem_lucro),
                            'receitas': float(receitas),
                            'despesas': float(despesas),
                            'mes_referencia': str(mes_atual)
                        }, ensure_ascii=False),
                        'automatico': 1,
                        'transacao_id': None
                    }
                    self.alertas.append(alerta)
                    alertas_gerados += 1
                    self.logger.info(f"Alerta gerado: {alerta['titulo']} (Margem: {margem_lucro*100:.2f}%)")
            
            self.logger.info(f"Análise de margem de lucro concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de margem de lucro: {e}", exc_info=True)
            return []

    def analisar_ciclo_operacional(self):
        """
        Avalia o ciclo operacional (tempo entre despesas e receitas).
        """
        try:
            self.logger.info("Iniciando análise de ciclo operacional.")
            if self.df.empty or 'valor' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'valor'.")
                return []
            
            df_clean = self.df.dropna(subset=['tipo', 'valor', 'data']).copy()
            df_clean['valor'] = pd.to_numeric(
                df_clean['valor'].astype(str).str.replace(r'[^\d.-]', '', regex=True), 
                errors='coerce'
            )
            df_clean = df_clean[~df_clean['valor'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['Mes'] = df_clean['data'].dt.to_period('M')
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            df_mes = df_clean[df_clean['Mes'] == mes_atual]
            
            if df_mes.empty:
                self.logger.warning(f"Nenhum dado para o mês atual {mes_atual}.")
                return []
            
            despesas = df_mes[df_mes['tipo'] == 'despesa'].copy()
            receitas = df_mes[df_mes['tipo'] == 'receita'].copy()
            
            if despesas.empty or receitas.empty:
                self.logger.warning("Faltam despesas ou receitas no mês atual.")
                return []
            
            media_data_despesa = despesas['data'].mean()
            media_data_receita = receitas['data'].mean()
            ciclo_dias = (media_data_receita - media_data_despesa).days
            
            alertas_gerados = 0
            if ciclo_dias > CONFIG.get('limite_ciclo_operacional', 30):
                alerta = {
                    'titulo': 'Ciclo Operacional Longo',
                    'descricao': (
                        f"Ciclo operacional de {ciclo_dias} dias em {mes_atual} excede o limite. "
                        f"Média de despesas: {media_data_despesa.strftime('%d/%m/%Y')}, "
                        f"Média de receitas: {media_data_receita.strftime('%d/%m/%Y')}."
                    ),
                    'tipo': 'operacional',
                    'prioridade': 'media',
                    'status': 'pendente',
                    'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                    'data_atualizacao': None,
                    'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-01'),
                    'categoria': None,
                    'valor': 0.0,
                    'origem': 'Ciclo Operacional',
                    'dados_adicionais': json.dumps({
                        'ciclo_dias': float(ciclo_dias),
                        'data_despesa': media_data_despesa.isoformat(),
                        'data_receita': media_data_receita.isoformat(),
                        'mes_referencia': str(mes_atual)
                    }, ensure_ascii=False),
                    'automatico': 1,
                    'transacao_id': None
                }
                self.alertas.append(alerta)
                alertas_gerados += 1
                self.logger.info(f"Alerta gerado: {alerta['titulo']} (Ciclo: {ciclo_dias} dias)")
            
            self.logger.info(f"Análise de ciclo operacional concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de ciclo operacional: {e}", exc_info=True)
            return []

    def analisar_risco_operacional(self):
        """
        Avalia riscos operacionais com base em taxas e indicadores.
        """
        try:
            self.logger.info("Iniciando análise de risco operacional.")
            if self.df.empty or 'taxa' not in self.df.columns:
                self.logger.warning("DataFrame vazio ou sem coluna 'taxa'.")
                return []
            
            df_clean = self.df.dropna(subset=['taxa', 'data']).copy()
            df_clean['taxa'] = pd.to_numeric(df_clean['taxa'], errors='coerce')
            df_clean = df_clean[~df_clean['taxa'].isin([np.inf, -np.inf, np.nan])]
            df_clean['data'] = pd.to_datetime(df_clean['data'])
            df_clean['mes'] = df_clean['data'].dt.to_period('M')
            
            mes_atual = pd.Timestamp.now(tz='America/Sao_Paulo').to_period('M')
            df_mes = df_clean[df_clean['mes'] == mes_atual]
            
            if df_mes.empty:
                self.logger.warning(f"Nenhum dado para o mês atual {mes_atual}.")
                return []
            
            media_taxa = df_mes['taxa'].mean()
            
            alertas_gerados = 0
            if media_taxa > CONFIG.get('limite_taxa', 0.05):
                alerta = {
                    'titulo': 'Risco Operacional Elevado',
                    'descricao': f"Média de taxas de {media_taxa:.4f} em {mes_atual} excede o limite de {CONFIG.get('limite_taxa', 0.05):.4f}.",
                    'tipo': 'risco',
                    'prioridade': 'media',
                    'status': 'pendente',
                    'data_criacao': pd.Timestamp.now(tz='America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S'),
                    'data_atualizacao': None,
                    'data_ocorrencia': pd.Timestamp(mes_atual.start_time).strftime('%Y-%m-01'),
                    'categoria': None,
                    'valor': 0.0,
                    'origem': 'Risco Operacional',
                    'dados_adicionais': json.dumps({
                        'media_taxa': float(media_taxa),
                        'mes_referencia': str(mes_atual)
                    }, ensure_ascii=False),
                    'automatico': 1,
                    'transacao_id': None
                }
                self.alertas.append(alerta)
                alertas_gerados += 1
                self.logger.info(f"Alerta gerado: {alerta['titulo']} (Taxa: {media_taxa:.4f})")
            
            self.logger.info(f"Análise de risco operacional concluída. Gerados {alertas_gerados} alertas.")
            return self.alertas
        
        except Exception as e:
            self.logger.error(f"Erro inesperado na análise de risco operacional: {e}", exc_info=True)
            return []

    def executar_analises(self):
        """
        Executa todas as análises financeiras disponíveis e retorna os alertas gerados."""
        try:
            self.logger.info("Iniciando execução de todas as análises financeiras.")
            self.alertas = []
            
            if not self.carregar_dados():
                self.logger.error("Falha ao carregar dados. Análises não executadas.")
                return []
                
            analises = [
                self.calcular_zscore_por_categoria,
                self.identificar_outliers_por_percentil,
                self.calcular_ema_por_categoria,
                self.analisar_limite_orcamentario,
                self.analisar_desvio_padrao_mensal,
                self.analisar_proporcao_despesa_receita,
                self.analisar_crescimento_mensal,
                self.calcular_hhi,
                self.analisar_correlacao_categorias,
                self.calcular_anova_categorias,
                self.calcular_teste_t_por_tipo,
                self.calcular_regressao_linear,
                self.prever_arima,
                self.calcular_roi_por_ativo,
                self.calcular_sharpe_ratio,
                self.analisar_volatilidade_mensal,
                self.detectar_saldo_negativo,
                self.analisar_liquidez,
                self.detectar_fraudes,
                self.analisar_sazonalidade,
                self.calcular_beta_por_ativo,
                self.calcular_var,
                self.analisar_forma_pagamento,
                self.analisar_margem_lucro,
                self.analisar_ciclo_operacional,
                self.analisar_risco_operacional,
                
            ]
            
            alertas_gerados = 0
            for idx, analise in enumerate(analises, 1):
                try:
                    self.logger.info(f"Executando análise #{idx}: {analise.__name__}")
                    alertas = analise()
                    if alertas:  # Verifica se alertas não é None
                        alertas_gerados += len([al for al in alertas if al.get('origem') == analise.__name__])
                        self.logger.info(f"Análise {analise.__name__} concluída com {len(alertas)} alertas gerados.")
                    else:
                        self.logger.info(f"Análise {analise.__name__} concluída sem alertas gerados.")
                except Exception as e:
                    self.logger.error(f"Erro ao executar análise {idx} ({analise.__name__}): {e}", exc_info=True)
                    continue
                
            self.logger.info(f"Execução de todas as análises concluída. Total de {alertas_gerados} alertas gerados.")
            return self.alertas
            
        except Exception as e:
            self.logger.error(f"Erro inesperado ao executar análises: {e}", exc_info=True)
            return []