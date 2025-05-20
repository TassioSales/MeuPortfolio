import pandas as pd
from datetime import datetime
import numpy as np
from scipy.stats import norm

def calcular_retornos(df, coluna_preco='preco'):
    """Calcula os retornos percentuais do DataFrame."""
    df['retorno'] = df[coluna_preco].pct_change()
    return df

def calcular_sharpe_ratio(retornos, taxa_livre_risco=0.05):
    """Calcula o Sharpe Ratio."""
    media = retornos.mean()
    desvio = retornos.std()
    if desvio == 0:
        return 0
    return (media - taxa_livre_risco) / desvio

def calcular_sortino_ratio(retornos, taxa_livre_risco=0.05):
    """Calcula o Sortino Ratio."""
    media = retornos.mean()
    desvio_negativo = retornos[retornos < 0].std()
    if desvio_negativo == 0:
        return 0
    return (media - taxa_livre_risco) / desvio_negativo

def calcular_drawdown(df, coluna_preco='preco'):
    """Calcula o Drawdown máximo."""
    df['pico'] = df[coluna_preco].cummax()
    df['drawdown'] = (df[coluna_preco] - df['pico']) / df['pico']
    return df['drawdown'].min()

def calcular_var(df, coluna_preco='preco', alpha=0.05):
    """Calcula o Value at Risk."""
    retornos = df[coluna_preco].pct_change().dropna()
    return -np.percentile(retornos, alpha * 100)

def calcular_cvar(df, coluna_preco='preco', alpha=0.05):
    """Calcula o Conditional Value at Risk."""
    retornos = df[coluna_preco].pct_change().dropna()
    var = calcular_var(df, coluna_preco, alpha)
    return -retornos[retornos <= -var].mean()

def calcular_quartis(df, coluna='valor'):
    """Calcula os quartis do DataFrame."""
    return df[coluna].quantile([0.25, 0.5, 0.75]).to_dict()

def calcular_correlacao(df):
    """Calcula a matriz de correlação."""
    return df.corr()

def processar_analises(df, data_inicio, data_fim):
    """Processa as análises estatísticas do DataFrame."""
    # Estatísticas básicas
    total_registros = len(df)
    
    # Análise descritiva
    media_valor = df['valor'].mean()
    mediana_valor = df['valor'].median()
    desvio_padrao = df['valor'].std()
    maximo = df['valor'].max()
    minimo = df['valor'].min()
    quartis = df['valor'].quantile([0.25, 0.5, 0.75]).to_dict()
    
    # Análise por categoria
    categorias = df.groupby('categoria')['valor'].agg(['sum', 'count']).to_dict()
    
    # Análise temporal
    melhor_mes = df.groupby(df.index.month)['valor'].sum().idxmax()
    pior_mes = df.groupby(df.index.month)['valor'].sum().idxmin()
    melhor_ano = df.groupby(df.index.year)['valor'].sum().idxmax()
    pior_ano = df.groupby(df.index.year)['valor'].sum().idxmin()
    
    return {
        'basica': {
            'total_registros': total_registros,
            'periodo': f'{data_inicio} a {data_fim}'
        },
        'descritiva': {
            'media_valor': media_valor,
            'mediana_valor': mediana_valor,
            'desvio_padrao': desvio_padrao,
            'maximo': maximo,
            'minimo': minimo,
            'quartis': quartis
        },
        'categorias': categorias,
        'temporal': {
            'melhor_mes': melhor_mes,
            'pior_mes': pior_mes,
            'melhor_ano': melhor_ano,
            'pior_ano': pior_ano
        }
    }
