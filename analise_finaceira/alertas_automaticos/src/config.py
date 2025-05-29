"""
Configurações do módulo de alertas automáticos.
"""

# Configurações gerais
CONFIG = {
    # Configurações gerais
    'zscore_limite': 2.0,  # Limite reduzido para capturar mais anomalias
    'min_transacoes_grupo': 5,  # Mínimo de transações para análise de grupo
    'db_path': 'D:/Github/MeuPortfolio/analise_finaceira/banco/financas.db',  # Caminho para o banco de dados
    'debug': True,  # Ativa logs detalhados
    'limite_iqr': 1.0,  # Reduz o fator IQR para ser menos restritivo
    'percentil_baixo': 0.01,  # Percentil inferior para detecção de outliers
    'percentil_alto': 0.99,   # Percentil superior para detecção de outliers
    'min_transacoes_percentil': 5,  # Mínimo de transações para cálculo de percentis
    
    # Configurações de análise de proporção despesa/receita
    'meses_analise_proporcao': 12,  # Número de meses para análise histórica
    'limite_proporcao_alerta': 0.8,  # 80% - Gera alerta amarelo quando a proporção atinge este valor
    'limite_proporcao_critico': 1.0,  # 100% - Gera alerta vermelho quando a proporção atinge este valor
    'tendencia_alerta_proporcao': 0.1,  # 10% - Alerta se a proporção estiver aumentando mais que 10% ao mês
    'min_meses_analise_proporcao': 3  # Mínimo de meses necessários para análise
}

# Caminhos dos arquivos
PATHS = {
    'logger': 'D:/Github/MeuPortfolio/analise_finaceira/logger.py'
}
