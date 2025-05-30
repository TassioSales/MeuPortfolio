"""
Módulo de geração de relatórios da carteira de investimentos.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal
import pandas as pd

from src.models.carteira import Carteira, ItemCarteira
from src.models.ativo import Ativo
from src.utils.logger import get_logger

logger = get_logger(__name__)

class RelatorioService:
    """
    Serviço para geração de relatórios da carteira de investimentos.
    """
    
    @staticmethod
    def gerar_resumo_carteira(carteira: Carteira) -> Dict[str, Any]:
        """
        Gera um resumo da carteira com totais e distribuição por tipo de ativo.
        
        Args:
            carteira: Instância da Carteira
            
        Returns:
            Dict[str, Any]: Dicionário com o resumo da carteira
        """
        total_geral, totais_por_tipo = carteira.calcular_valor_total()
        
        distribuicao_tipos = []
        for tipo, valor in totais_por_tipo.items():
            percentual = (float(valor) / float(total_geral) * 100) if total_geral > 0 else 0.0
            distribuicao_tipos.append({
                'tipo': tipo,
                'valor': float(valor),
                'percentual': round(float(percentual), 2)
            })
        
        distribuicao_tipos.sort(key=lambda x: x['valor'], reverse=True)
        
        total_investido = sum(item.valor_total for item in carteira.itens.values() if item.valor_total is not None)
        resultado_bruto = float(total_geral) - float(total_investido) if total_geral is not None else 0.0
        resultado_percentual = (resultado_bruto / float(total_investido) * 100) if total_investido > 0 else 0.0
        
        return {
            'nome_carteira': carteira.nome,
            'data_geracao': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'total_investido': float(total_investido),
            'valor_atual': float(total_geral) if total_geral is not None else 0.0,
            'resultado_bruto': round(resultado_bruto, 2),
            'resultado_percentual': round(float(resultado_percentual), 2),
            'total_ativos': len(carteira.itens),
            'distribuicao_tipos': distribuicao_tipos,
            'moeda_principal': 'BRL'
        }

    @staticmethod
    def gerar_relatorio_detalhado(carteira: Carteira) -> Dict[str, Any]:
        """
        Gera um relatório detalhado da carteira com informações de cada ativo.
        
        Args:
            carteira: Instância da Carteira
            
        Returns:
            Dict[str, Any]: Dicionário com o relatório detalhado
        """
        resumo = RelatorioService.gerar_resumo_carteira(carteira)
        
        ativos_detalhados = []
        if not carteira.itens:
            resumo['ativos_detalhados'] = []
            return resumo
            
        for item in sorted(carteira.itens.values(), key=lambda x: x.ativo.tipo if hasattr(x, 'ativo') and x.ativo else ''):
            if not hasattr(item, 'ativo') or item.ativo is None:
                continue
                
            ativo = item.ativo
            valor_total = float(item.valor_total) if item.valor_total is not None else 0.0
            valor_atual = float(item.valor_atual) if item.valor_atual is not None else 0.0
            resultado = float(item.resultado) if item.resultado is not None else 0.0
            resultado_percentual = float(item.resultado_percentual) if item.resultado_percentual is not None else 0.0
            
            detalhes = {}
            if hasattr(ativo, 'dados_mercado') and ativo.dados_mercado:
                detalhes = {
                    'variacao_dia': ativo.dados_mercado.get('regularMarketChangePercent', 0.0),
                    'dividend_yield': ativo.dados_mercado.get('dividendYield', 0.0),
                    'lucro_por_acao': ativo.dados_mercado.get('lucroPorAcao', 0.0),
                    'valor_mercado': ativo.dados_mercado.get('valorDeMercado', 0.0)
                }
            
            ativo_info = {
                'ticker': ativo.ticker,
                'nome': ativo.nome,
                'tipo': ativo.tipo,
                'setor': ativo.setor or 'N/A',
                'quantidade': float(item.quantidade) if item.quantidade is not None else 0.0,
                'preco_medio': float(item.preco_medio) if item.preco_medio is not None else 0.0,
                'preco_atual': float(ativo.preco_atual) if ativo.preco_atual is not None else 0.0,
                'valor_total': round(valor_total, 2),
                'valor_atual': round(valor_atual, 2),
                'resultado_bruto': round(resultado, 2),
                'resultado_percentual': round(resultado_percentual, 2),
                'moeda': ativo.moeda or 'BRL',
                'ultima_atualizacao': ativo.ultima_atualizacao.strftime('%d/%m/%Y %H:%M') if hasattr(ativo, 'ultima_atualizacao') and ativo.ultima_atualizacao else 'N/A',
                'detalhes': detalhes
            }
            
            ativos_detalhados.append(ativo_info)
        
        resumo['ativos_detalhados'] = ativos_detalhados
        return resumo
    
    @staticmethod
    def exportar_para_excel(carteira: Carteira, caminho_arquivo: str) -> bool:
        """
        Exporta a carteira para um arquivo Excel.
        
        Args:
            carteira: Instância da Carteira
            caminho_arquivo: Caminho completo do arquivo Excel a ser gerado
            
        Returns:
            bool: True se a exportação foi bem-sucedida, False caso contrário
        """
        try:
            relatorio = RelatorioService.gerar_relatorio_detalhado(carteira)
            
            with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
                resumo_data = {
                    'Métrica': [
                        'Nome da Carteira',
                        'Data de Geração',
                        'Valor Total Investido',
                        'Valor Atual da Carteira',
                        'Resultado Bruto',
                        'Resultado Percentual (%)',
                        'Total de Ativos'
                    ],
                    'Valor': [
                        relatorio['nome_carteira'],
                        relatorio['data_geracao'],
                        round(relatorio['total_investido'], 2),
                        round(relatorio['valor_atual'], 2),
                        round(relatorio['resultado_bruto'], 2),
                        round(relatorio['resultado_percentual'], 2),
                        relatorio['total_ativos']
                    ]
                }
                
                df_resumo = pd.DataFrame(resumo_data)
                df_resumo.to_excel(writer, sheet_name='Resumo', index=False)
                
                if relatorio['distribuicao_tipos']:
                    df_distribuicao = pd.DataFrame(relatorio['distribuicao_tipos'])
                    df_distribuicao.to_excel(writer, sheet_name='Distribuição por Tipo', index=False)
                
                if 'ativos_detalhados' in relatorio and relatorio['ativos_detalhados']:
                    df_ativos = pd.DataFrame(relatorio['ativos_detalhados'])
                    if 'detalhes' in df_ativos.columns:
                        df_ativos = df_ativos.drop(columns=['detalhes'])
                    df_ativos.to_excel(writer, sheet_name='Ativos', index=False)
                
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = max(len(str(cell.value or '')) for cell in column)
                        worksheet.column_dimensions[column[0].column_letter].width = min((max_length + 2) * 1.2, 30)
            
            return True
            
        except Exception as e:
            print(f"Erro ao exportar para Excel: {str(e)}")
            return False
    
    @staticmethod
    def gerar_analise_performance(carteira: Carteira) -> Dict[str, Any]:
        """
        Gera uma análise de performance da carteira.
        
        Args:
            carteira: Instância da Carteira
            
        Returns:
            Dict[str, Any]: Dicionário com a análise de performance
        """
        relatorio = RelatorioService.gerar_relatorio_detalhado(carteira)
        
        analise = {
            'melhores_ativos': [],
            'piores_ativos': [],
            'maiores_posicoes': [],
            'maiores_rendimentos': [],
            'maiores_perdas': []
        }
        
        if 'ativos_detalhados' not in relatorio or not relatorio['ativos_detalhados']:
            return analise
        
        ativos_validos = [a for a in relatorio['ativos_detalhados'] if a['valor_atual'] is not None]
        
        if not ativos_validos:
            return analise
        
        ativos_ordenados = sorted(
            ativos_validos, 
            key=lambda x: x['resultado_percentual'] if x['resultado_percentual'] is not None else float('-inf'),
            reverse=True
        )
        
        analise['melhores_ativos'] = ativos_ordenados[:3]
        analise['piores_ativos'] = ativos_ordenados[-3:][::-1] if len(ativos_ordenados) >= 3 else ativos_ordenados[::-1]
        
        analise['maiores_posicoes'] = sorted(
            ativos_validos,
            key=lambda x: x['valor_total'] if x['valor_total'] is not None else 0.0,
            reverse=True
        )[:5]
        
        ativos_com_resultado = [a for a in ativos_validos if a['resultado_bruto'] is not None]
        analise['maiores_rendimentos'] = sorted(
            [a for a in ativos_com_resultado if a['resultado_bruto'] > 0],
            key=lambda x: x['resultado_bruto'],
            reverse=True
        )[:3]
        
        analise['maiores_perdas'] = sorted(
            [a for a in ativos_com_resultado if a['resultado_bruto'] < 0],
            key=lambda x: x['resultado_bruto']
        )[:3]
        
        return analise