from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from scipy.stats import norm, pearsonr
from ..models import Transacao


class AnaliseEstatisticaService:
    def __init__(self, db_session):
        self.db_session = db_session

    # Informações Gerais
    def obter_informacoes_gerais(self, transacoes: pd.DataFrame) -> Dict:
        """Obtém informações gerais sobre o conjunto de dados."""
        if transacoes.empty:
            return {}

        return {
            'numero_registros': len(transacoes),
            'periodo_analise': {
                'data_inicio': transacoes['data'].min().strftime('%Y-%m-%d'),
                'data_fim': transacoes['data'].max().strftime('%Y-%m-%d')
            },
            'numero_ativos': len(transacoes['ativo'].unique()),
            'ativos_com_ganhos': len(transacoes[transacoes['valor'] > 0]['ativo'].unique()),
            'ativos_com_losses': len(transacoes[transacoes['valor'] < 0]['ativo'].unique())
        }

    # Estatísticas Descritivas
    def calcular_estatisticas_descritivas(self, transacoes: pd.DataFrame) -> Dict:
        """Calcula estatísticas descritivas básicas das transações."""
        if transacoes.empty:
            return {}

        # Calcular retornos percentuais
        retornos = transacoes['valor'].pct_change()
        retornos = retornos.dropna()  # Remover primeiro valor NaN

        estatisticas = {
            'quantidade': len(retornos),
            'media_retorno': retornos.mean(),
            'mediana_retorno': retornos.median(),
            'desvio_padrao_retorno': retornos.std(),
            'minimo_retorno': retornos.min(),
            'maximo_retorno': retornos.max(),
            'quartis_retorno': retornos.quantile([0.25, 0.5, 0.75]).tolist(),
            'valor_total': transacoes['valor'].sum(),
            'valor_medio': transacoes['valor'].mean(),
            'valor_mediana': transacoes['valor'].median(),
            'desvio_padrao_valor': transacoes['valor'].std(),
            'minimo_valor': transacoes['valor'].min(),
            'maximo_valor': transacoes['valor'].max(),
            'quartis_valor': transacoes['valor'].quantile([0.25, 0.5, 0.75]).tolist()
        }
        return estatisticas

    # Análise de Risco
    def calcular_sharpe_ratio(self, transacoes: pd.DataFrame, taxa_livre_risco: float = 0.05) -> float:
        """Calcula o Sharpe Ratio."""
        if transacoes.empty:
            return 0

        retornos = transacoes['valor'].pct_change()
        retorno_medio = retornos.mean()
        desvio_padrao = retornos.std()
        
        if desvio_padrao == 0:
            return 0

        return (retorno_medio - taxa_livre_risco) / desvio_padrao

    def calcular_sortino_ratio(self, transacoes: pd.DataFrame, taxa_livre_risco: float = 0.05) -> float:
        """Calcula o Sortino Ratio."""
        if transacoes.empty:
            return 0

        retornos = transacoes['valor'].pct_change()
        retornos_negativos = retornos[retornos < 0]
        desvio_padrao_negativo = retornos_negativos.std()
        
        if desvio_padrao_negativo == 0:
            return 0

        return (retornos.mean() - taxa_livre_risco) / desvio_padrao_negativo

    def calcular_drawdown_maximo(self, transacoes: pd.DataFrame) -> Dict:
        """Calcula o Drawdown Máximo."""
        if transacoes.empty:
            return {'drawdown': 0, 'periodo': 'N/A'}

        capital = transacoes['valor'].cumsum()
        maximo_acumulado = capital.cummax()
        drawdown = (capital - maximo_acumulado) / maximo_acumulado
        
        max_drawdown = drawdown.min()
        periodo = {
            'inicio': transacoes.index[drawdown.idxmin()],
            'fim': transacoes.index[maximo_acumulado.idxmax()]
        }
        
        return {
            'drawdown': max_drawdown,
            'periodo': periodo
        }

    def calcular_volatilidade(self, transacoes: pd.DataFrame) -> float:
        """Calcula a volatilidade anualizada."""
        if transacoes.empty:
            return 0

        retornos = transacoes['valor'].pct_change()
        volatilidade_diaria = retornos.std()
        return volatilidade_diaria * np.sqrt(252)  # Anualizando para 252 dias úteis

    def calcular_var(self, transacoes: pd.DataFrame, nivel_confianca: float = 0.95) -> float:
        """Calcula o Valor em Risco (VaR)."""
        if transacoes.empty:
            return 0

        retornos = transacoes['valor'].pct_change()
        return norm.ppf(1 - nivel_confianca) * retornos.std()

    def calcular_cvar(self, transacoes: pd.DataFrame, nivel_confianca: float = 0.95) -> float:
        """Calcula o Conditional Value at Risk (CVaR)."""
        if transacoes.empty:
            return 0

        retornos = transacoes['valor'].pct_change()
        var = self.calcular_var(transacoes, nivel_confianca)
        perdas = retornos[retornos <= var]
        return perdas.mean()

    def calcular_probabilidade_perda(self, transacoes: pd.DataFrame, nivel_perda: float) -> float:
        """Calcula a probabilidade de uma perda específica."""
        if transacoes.empty:
            return 0

        retornos = transacoes['valor'].pct_change()
        return (retornos < -nivel_perda).mean()

    # Análise Temporal
    def analisar_periodos(self, transacoes: pd.DataFrame) -> Dict:
        """Analisa métricas temporais."""
        if transacoes.empty:
            return {}

        # Agrupar por período
        transacoes['mes'] = pd.to_datetime(transacoes['data']).dt.to_period('M')
        transacoes['ano'] = pd.to_datetime(transacoes['data']).dt.to_period('Y')
        
        # Calcular retornos por período
        retornos_mensais = transacoes.groupby('mes')['valor'].sum().pct_change()
        retornos_anuais = transacoes.groupby('ano')['valor'].sum().pct_change()
        
        return {
            'melhor_mes': {
                'periodo': transacoes.groupby('mes')['valor'].sum().idxmax().strftime('%Y-%m'),
                'retorno': retornos_mensais.max(),
                'valor': transacoes.groupby('mes')['valor'].sum().max()
            },
            'pior_mes': {
                'periodo': transacoes.groupby('mes')['valor'].sum().idxmin().strftime('%Y-%m'),
                'retorno': retornos_mensais.min(),
                'valor': transacoes.groupby('mes')['valor'].sum().min()
            },
            'melhor_ano': {
                'periodo': transacoes.groupby('ano')['valor'].sum().idxmax().strftime('%Y'),
                'retorno': retornos_anuais.max(),
                'valor': transacoes.groupby('ano')['valor'].sum().max()
            },
            'pior_ano': {
                'periodo': transacoes.groupby('ano')['valor'].sum().idxmin().strftime('%Y'),
                'retorno': retornos_anuais.min(),
                'valor': transacoes.groupby('ano')['valor'].sum().min()
            },
            'retornos_periodo': {
                'diario': transacoes['valor'].pct_change().mean(),
                'semanal': transacoes.resample('W')['valor'].sum().pct_change().mean(),
                'mensal': retornos_mensais.mean(),
                'anual': retornos_anuais.mean()
            },
            'frequencia_operacoes': {
                'diaria': transacoes.groupby(pd.Grouper(key='data', freq='D')).size().mean(),
                'semanal': transacoes.groupby(pd.Grouper(key='data', freq='W')).size().mean(),
                'mensal': transacoes.groupby(pd.Grouper(key='data', freq='M')).size().mean()
            }
        }

    # Análise por Ativo
    def analisar_ativos(self, transacoes: pd.DataFrame, n: int = 5) -> Dict:
        """Analisa métricas por ativo."""
        if transacoes.empty:
            return {}

        # Calcular retornos por ativo
        retornos_por_ativo = transacoes.groupby('ativo')['valor'].pct_change()
        retornos_por_ativo = retornos_por_ativo.dropna()
        
        return {
            'top_ativos_retorno': transacoes.groupby('ativo')['valor'].pct_change().mean().nlargest(n).to_dict(),
            'top_ativos_risco': retornos_por_ativo.groupby('ativo').std().nlargest(n).to_dict(),
            'distribuicao_tipo': transacoes.groupby('tipo')['valor'].sum().to_dict()
        }

    # Análise de Performance
    def analisar_performance(self, transacoes: pd.DataFrame) -> Dict:
        """Analisa métricas de performance."""
        if transacoes.empty:
            return {}

        operacoes_ganhadoras = transacoes[transacoes['valor'] > 0]
        operacoes_perdedoras = transacoes[transacoes['valor'] < 0]
        
        return {
            'taxa_acerto': len(operacoes_ganhadoras) / len(transacoes),
            'proporcao_ganhos_losses': operacoes_ganhadoras['valor'].sum() / abs(operacoes_perdedoras['valor'].sum()),
            'retorno_medio': {
                'ganhador': operacoes_ganhadoras['valor'].mean(),
                'perdedor': operacoes_perdedoras['valor'].mean()
            }
        }

    # Análise de Capital
    def analisar_capital(self, transacoes: pd.DataFrame) -> Dict:
        """Analisa métricas relacionadas ao capital."""
        if transacoes.empty:
            return {}

        capital = transacoes['valor'].cumsum()
        
        return {
            'valor_inicial': transacoes['valor'].iloc[0],
            'valor_final': transacoes['valor'].iloc[-1],
            'taxa_retorno': (transacoes['valor'].iloc[-1] - transacoes['valor'].iloc[0]) / transacoes['valor'].iloc[0],
            'drawdown_capital': self.calcular_drawdown_maximo(transacoes)
        }

    # Análise de Frequência
    def analisar_frequencia(self, transacoes: pd.DataFrame) -> Dict:
        """Analisa frequência de operações."""
        if transacoes.empty:
            return {}

        transacoes['hora'] = pd.to_datetime(transacoes['data']).dt.hour
        transacoes['dia_semana'] = pd.to_datetime(transacoes['data']).dt.day_name()
        
        return {
            'media_operacoes': {
                'diaria': len(transacoes) / len(transacoes['data'].unique()),
                'semanal': len(transacoes) / (len(transacoes['data'].unique()) / 7),
                'mensal': len(transacoes) / (len(transacoes['data'].unique()) / 30)
            },
            'horario_comum': transacoes['hora'].mode()[0],
            'dia_semana_comum': transacoes['dia_semana'].mode()[0]
        }

    # Análise de Correlação
    def analisar_correlacao(self, transacoes: pd.DataFrame) -> Dict:
        """Analisa correlações entre diferentes métricas."""
        if transacoes.empty:
            return {}

        # Correlação entre diferentes tipos de ativos
        retornos_por_tipo = transacoes.groupby('tipo')['valor'].pct_change()
        correlacao_ativos = retornos_por_tipo.corr()
        
        # Correlação entre volume e preço
        correlacoes = {}
        if 'volume' in transacoes.columns:
            correlacao_volume_preco = pearsonr(transacoes['volume'], transacoes['valor'])[0]
            correlacoes['volume_preco'] = correlacao_volume_preco
        
        # Adicionar correlações entre indicadores técnicos
        if 'indicador1' in transacoes.columns and 'indicador2' in transacoes.columns:
            correlacao_indicadores = pearsonr(transacoes['indicador1'], transacoes['indicador2'])[0]
            correlacoes['indicadores'] = correlacao_indicadores
        
        return {
            'correlacao_ativos': correlacao_ativos,
            'correlacoes': correlacoes
        }

    def analisar(self, data_inicio: str, data_fim: str, tipos_analise: List[str]) -> Dict:
        """Realiza a análise estatística conforme os tipos solicitados."""
        try:
            # Converter datas
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
            
            # Filtrar transações pelo período
            transacoes = pd.DataFrame([
                (t.data, t.valor, t.ativo, t.tipo)
                for t in self.db_session.query(Transacao)
                if data_inicio <= t.data <= data_fim
            ], columns=['data', 'valor', 'ativo', 'tipo'])
            
            if transacoes.empty:
                return {'mensagem': 'Nenhuma transação encontrada no período selecionado'}

            # Inicializar resultados
            resultados = {}
            
            # Realizar análises conforme os tipos solicitados
            for tipo in tipos_analise:
                if tipo == 'basica':
                    resultados['basica'] = self.obter_informacoes_gerais(transacoes)
                elif tipo == 'descritiva':
                    resultados['descritiva'] = self.calcular_estatisticas_descritivas(transacoes)
                elif tipo == 'sharpe':
                    resultados['sharpe'] = self.calcular_sharpe_ratio(transacoes)
                elif tipo == 'sortino':
                    resultados['sortino'] = self.calcular_sortino_ratio(transacoes)
                elif tipo == 'drawdown':
                    resultados['drawdown'] = self.calcular_drawdown_maximo(transacoes)
                elif tipo == 'volatilidade':
                    resultados['volatilidade'] = self.calcular_volatilidade(transacoes)
                elif tipo == 'var':
                    resultados['var'] = self.calcular_var(transacoes)
                elif tipo == 'cvar':
                    resultados['cvar'] = self.calcular_cvar(transacoes)
                elif tipo == 'prob_perda':
                    resultados['prob_perda'] = self.calcular_probabilidade_perda(transacoes, 0.01)
                elif tipo == 'periodo':
                    resultados['periodo'] = self.analisar_periodos(transacoes)
                elif tipo == 'ativos':
                    resultados['ativos'] = self.analisar_ativos(transacoes)
                elif tipo == 'performance':
                    resultados['performance'] = self.analisar_performance(transacoes)
                elif tipo == 'capital':
                    resultados['capital'] = self.analisar_capital(transacoes)
                elif tipo == 'frequencia':
                    resultados['frequencia'] = self.analisar_frequencia(transacoes)
                elif tipo == 'correlacao':
                    resultados['correlacao'] = self.analisar_correlacao(transacoes)

            return {'sucesso': True, 'resultados': resultados}
            
        except Exception as e:
            return {'sucesso': False, 'mensagem': str(e)}
