"""
Módulo para geração de relatórios e análises financeiras.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from ..models.ativo import Ativo, HistoricoPreco, Carteira, Alerta
from ..models.usuario import Usuario
from .. import db
from ..utils.logger import logger

class Relatorios:
    """Classe para geração de relatórios e análises financeiras."""
    
    @staticmethod
    def gerar_relatorio_carteira(usuario_id: int) -> Dict:
        """
        Gera um relatório detalhado da carteira do usuário.
        
        Args:
            usuario_id (int): ID do usuário.
            
        Returns:
            Dict: Dados do relatório da carteira.
        """
        try:
            # Obtém os ativos da carteira do usuário
            carteira = Carteira.query.filter_by(usuario_id=usuario_id).all()
            
            if not carteira:
                return {
                    'sucesso': False,
                    'mensagem': 'Nenhum ativo encontrado na carteira.'
                }
            
            # Calcula o valor total da carteira
            valor_total = sum(
                item.quantidade * (Ativo.query.get(item.ativo_id).preco_atual or 0)
                for item in carteira
            )
            
            # Prepara os dados dos ativos
            ativos = []
            for item in carteira:
                ativo = Ativo.query.get(item.ativo_id)
                preco_medio = item.preco_medio
                preco_atual = ativo.preco_atual or preco_medio
                variacao = ((preco_atual - preco_medio) / preco_medio) * 100 if preco_medio else 0
                valor_investido = item.quantidade * preco_medio
                valor_atual = item.quantidade * preco_atual
                lucro_prejuizo = valor_atual - valor_investido
                
                ativos.append({
                    'id': ativo.id,
                    'simbolo': ativo.symbol,
                    'nome': ativo.nome or ativo.symbol,
                    'quantidade': item.quantidade,
                    'preco_medio': preco_medio,
                    'preco_atual': preco_atual,
                    'variacao_percentual': variacao,
                    'valor_investido': valor_investido,
                    'valor_atual': valor_atual,
                    'lucro_prejuizo': lucro_prejuizo,
                    'proporcao_carteira': (valor_atual / valor_total) * 100 if valor_total > 0 else 0,
                    'tipo': ativo.tipo or 'desconhecido',
                    'setor': ativo.setor or 'Não informado'
                })
            
            # Ordena por valor atual (maior para menor)
            ativos_ordenados = sorted(ativos, key=lambda x: x['valor_atual'], reverse=True)
            
            # Calcula totais
            total_investido = sum(item['valor_investido'] for item in ativos)
            total_atual = sum(item['valor_atual'] for item in ativos)
            lucro_prejuizo_total = total_atual - total_investido
            variacao_total = (lucro_prejuizo_total / total_investido * 100) if total_investido > 0 else 0
            
            # Agrupa por tipo de ativo
            por_tipo = {}
            for ativo in ativos:
                tipo = ativo['tipo']
                if tipo not in por_tipo:
                    por_tipo[tipo] = {
                        'valor_total': 0,
                        'proporcao': 0,
                        'lucro_prejuizo': 0,
                        'quantidade_ativos': 0
                    }
                por_tipo[tipo]['valor_total'] += ativo['valor_atual']
                por_tipo[tipo]['lucro_prejuizo'] += ativo['lucro_prejuizo']
                por_tipo[tipo]['quantidade_ativos'] += 1
            
            # Calcula a proporção de cada tipo
            for tipo in por_tipo:
                por_tipo[tipo]['proporcao'] = (por_tipo[tipo]['valor_total'] / total_atual * 100) if total_atual > 0 else 0
            
            # Prepara o resultado
            resultado = {
                'sucesso': True,
                'dados_gerais': {
                    'valor_total': valor_total,
                    'total_investido': total_investido,
                    'total_atual': total_atual,
                    'lucro_prejuizo_total': lucro_prejuizo_total,
                    'variacao_total_percentual': variacao_total,
                    'quantidade_ativos': len(ativos),
                    'data_geracao': datetime.utcnow().isoformat()
                },
                'ativos': ativos_ordenados,
                'resumo_por_tipo': [
                    {
                        'tipo': tipo,
                        'valor_total': dados['valor_total'],
                        'proporcao': dados['proporcao'],
                        'lucro_prejuizo': dados['lucro_prejuizo'],
                        'quantidade_ativos': dados['quantidade_ativos']
                    }
                    for tipo, dados in por_tipo.items()
                ]
            }
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de carteira para o usuário {usuario_id}: {str(e)}")
            return {
                'sucesso': False,
                'mensagem': f'Erro ao gerar relatório: {str(e)}'
            }
    
    @staticmethod
    def gerar_grafico_evolucao_carteira(usuario_id: int, dias: int = 30) -> Dict:
        """
        Gera um gráfico da evolução do valor da carteira ao longo do tempo.
        
        Args:
            usuario_id (int): ID do usuário.
            dias (int, optional): Número de dias para o histórico. Defaults to 30.
            
        Returns:
            Dict: Dados para geração do gráfico.
        """
        try:
            # Obtém os dados históricos da carteira
            # NOTA: Esta é uma implementação simplificada. Em produção, você precisaria
            # rastrear o valor da carteira ao longo do tempo.
            
            # Para este exemplo, vamos simular dados históricos
            data_atual = datetime.utcnow()
            datas = [data_atual - timedelta(days=i) for i in range(dias, -1, -1)]
            
            # Em um cenário real, você buscaria esses dados do banco de dados
            # Aqui estamos apenas simulando dados aleatórios
            np.random.seed(42)  # Para reproduzibilidade
            valores = 10000 + np.cumsum(np.random.randn(len(datas)) * 100)
            
            # Prepara os dados para o gráfico
            dados_grafico = [
                {
                    'data': data.strftime('%Y-%m-%d'),
                    'valor': float(valor)
                }
                for data, valor in zip(datas, valores)
            ]
            
            return {
                'sucesso': True,
                'dados': dados_grafico,
                'periodo': {
                    'inicio': datas[0].strftime('%Y-%m-%d'),
                    'fim': datas[-1].strftime('%Y-%m-%d')
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar gráfico de evolução da carteira: {str(e)}")
            return {
                'sucesso': False,
                'mensagem': f'Erro ao gerar gráfico: {str(e)}'
            }
    
    @staticmethod
    def gerar_relatorio_dividendos(usuario_id: int) -> Dict:
        """
        Gera um relatório de dividendos recebidos pelo usuário.
        
        Args:
            usuario_id (int): ID do usuário.
            
        Returns:
            Dict: Dados do relatório de dividendos.
        """
        try:
            # Em um cenário real, você buscaria os dados de dividendos do banco de dados
            # Aqui estamos apenas simulando dados
            
            # Simula dados de dividendos para os últimos 12 meses
            meses = 12
            data_atual = datetime.utcnow()
            
            # Lista de ativos que pagam dividendos na carteira do usuário
            ativos_com_dividendos = [
                {'simbolo': 'PETR4', 'nome': 'Petrobras', 'tipo': 'acao'},
                {'simbolo': 'VALE3', 'nome': 'Vale', 'tipo': 'acao'},
                {'simbolo': 'ITUB4', 'nome': 'Itaú Unibanco', 'tipo': 'acao'},
            ]
            
            # Gera dados de dividendos simulados
            dividendos = []
            total_dividendos = 0
            
            for ativo in ativos_com_dividendos:
                # Gera 1-3 pagamentos de dividendos no período
                num_pagamentos = np.random.randint(1, 4)
                datas_pagamento = sorted([
                    data_atual - timedelta(days=np.random.randint(0, 365))
                    for _ in range(num_pagamentos)
                ])
                
                for data in datas_pagamento:
                    valor = round(np.random.uniform(0.5, 5.0), 2)
                    quantidade = np.random.randint(10, 100)
                    total = valor * quantidade
                    total_dividendos += total
                    
                    dividendos.append({
                        'data': data.strftime('%Y-%m-%d'),
                        'ativo': ativo['simbolo'],
                        'nome': ativo['nome'],
                        'tipo': ativo['tipo'],
                        'valor_por_acao': valor,
                        'quantidade': quantidade,
                        'total': total
                    })
            
            # Ordena por data (mais recente primeiro)
            dividendos_ordenados = sorted(dividendos, key=lambda x: x['data'], reverse=True)
            
            # Agrupa por ativo
            por_ativo = {}
            for div in dividendos_ordenados:
                ativo = div['ativo']
                if ativo not in por_ativo:
                    por_ativo[ativo] = {
                        'nome': div['nome'],
                        'quantidade_pagamentos': 0,
                        'total_recebido': 0,
                        'media_por_acao': 0
                    }
                por_ativo[ativo]['quantidade_pagamentos'] += 1
                por_ativo[ativo]['total_recebido'] += div['total']
            
            # Calcula a média por ação
            for ativo, dados in por_ativo.items():
                quantidade_media = sum(
                    d['quantidade'] for d in dividendos_ordenados 
                    if d['ativo'] == ativo
                ) / dados['quantidade_pagamentos']
                
                if quantidade_media > 0:
                    por_ativo[ativo]['media_por_acao'] = dados['total_recebido'] / quantidade_media
            
            # Prepara o resultado
            resultado = {
                'sucesso': True,
                'periodo': {
                    'inicio': (data_atual - timedelta(days=365)).strftime('%Y-%m-%d'),
                    'fim': data_atual.strftime('%Y-%m-%d')
                },
                'total_dividendos': round(total_dividendos, 2),
                'quantidade_pagamentos': len(dividendos_ordenados),
                'quantidade_ativos_que_pagaram': len(por_ativo),
                'dividendos': dividendos_ordenados,
                'resumo_por_ativo': [
                    {
                        'ativo': ativo,
                        'nome': dados['nome'],
                        'quantidade_pagamentos': dados['quantidade_pagamentos'],
                        'total_recebido': round(dados['total_recebido'], 2),
                        'media_por_acao': round(dados.get('media_por_acao', 0), 2)
                    }
                    for ativo, dados in por_ativo.items()
                ]
            }
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de dividendos: {str(e)}")
            return {
                'sucesso': False,
                'mensagem': f'Erro ao gerar relatório de dividendos: {str(e)}'
            }
    
    @staticmethod
    def gerar_relatorio_risco(usuario_id: int) -> Dict:
        """
        Gera um relatório de análise de risco da carteira.
        
        Args:
            usuario_id (int): ID do usuário.
            
        Returns:
            Dict: Dados do relatório de risco.
        """
        try:
            # Em um cenário real, você calcularia métricas de risco reais
            # Aqui estamos apenas simulando dados
            
            # Obtém a carteira do usuário
            carteira = Carteira.query.filter_by(usuario_id=usuario_id).all()
            
            if not carteira:
                return {
                    'sucesso': False,
                    'mensagem': 'Nenhum ativo encontrado na carteira.'
                }
            
            # Simula métricas de risco
            risco_total = {
                'valor_total': 100000.00,
                'valor_em_risco': 25000.00,
                'percentual_risco': 25.0,
                'beta_carteira': 1.2,
                'volatilidade_anual': 18.5,
                'sharpe_ratio': 1.4,
                'max_drawdown': -12.3,
                'exposicao_por_setor': {
                    'Financeiro': 35.0,
                    'Energia': 25.0,
                    'Bens Industriais': 15.0,
                    'Consumo Cíclico': 12.0,
                    'Outros': 13.0
                },
                'exposicao_por_tipo': {
                    'Ações': 70.0,
                    'Fundos Imobiliários': 15.0,
                    'Renda Fixa': 10.0,
                    'Criptomoedas': 5.0
                },
                'recomendacoes': [
                    'Considere reduzir a exposição ao setor financeiro, que está acima da média do mercado.',
                    'A alocação em criptomoedas está dentro de uma faixa conservadora.',
                    'O índice Sharpe acima de 1.0 indica um bom retorno ajustado ao risco.'
                ]
            }
            
            # Prepara o resultado
            resultado = {
                'sucesso': True,
                'data_analise': datetime.utcnow().isoformat(),
                'metadados': {
                    'total_ativos': len(carteira),
                    'data_inicio_analise': (datetime.utcnow() - timedelta(days=365)).strftime('%Y-%m-%d'),
                    'data_fim_analise': datetime.utcnow().strftime('%Y-%m-%d')
                },
                'metricas_risco': risco_total,
                'alertas_risco': [
                    {
                        'nivel': 'moderado',
                        'mensagem': 'Exposição elevada ao setor financeiro',
                        'detalhes': '35% da carteira está alocada no setor financeiro, acima da média do mercado (25%).',
                        'recomendacao': 'Considere diversificar para outros setores para reduzir o risco setorial.'
                    },
                    {
                        'nivel': 'baixo',
                        'mensagem': 'Baixa exposição a ativos internacionais',
                        'detalhes': 'Apenas 5% da carteira está em ativos internacionais.',
                        'recomendacao': 'Considere aumentar a exposição a mercados internacionais para maior diversificação.'
                    }
                ]
            }
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de risco: {str(e)}")
            return {
                'sucesso': False,
                'mensagem': f'Erro ao gerar relatório de risco: {str(e)}'
            }

# Exemplo de uso:
if __name__ == "__main__":
    # Exemplo de como usar a classe Relatorios
    relatorios = Relatorios()
    
    # Gera relatório de carteira para o usuário 1
    rel_carteira = relatorios.gerar_relatorio_carteira(1)
    print(f"Relatório de Carteira: {rel_carteira['dados_gerais']}")
    
    # Gera gráfico de evolução
    grafico = relatorios.gerar_grafico_evolucao_carteira(1)
    print(f"Dados do gráfico: {len(grafico['dados'])} pontos")
    
    # Gera relatório de dividendos
    rel_dividendos = relatorios.gerar_relatorio_dividendos(1)
    print(f"Total em dividendos: R$ {rel_dividendos['total_dividendos']:.2f}")
    
    # Gera relatório de risco
    rel_risco = relatorios.gerar_relatorio_risco(1)
    print(f"Métricas de risco: {rel_risco['metricas_risco']}")
