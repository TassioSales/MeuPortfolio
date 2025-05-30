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
        
        # Converte total_geral para Decimal para garantir consistência
        total_geral_decimal = Decimal(str(total_geral)) if total_geral is not None else Decimal('0')
        
        distribuicao_tipos = []
        for tipo, valor in totais_por_tipo.items():
            valor_decimal = Decimal(str(valor))
            percentual = (valor_decimal / total_geral_decimal * Decimal('100')) if total_geral_decimal > Decimal('0') else Decimal('0')
            distribuicao_tipos.append({
                'tipo': tipo,
                'valor': float(valor_decimal),
                'percentual': float(percentual.quantize(Decimal('0.01')))
            })
        
        distribuicao_tipos.sort(key=lambda x: x['valor'], reverse=True)
        
        # Calcula o total investido como Decimal
        total_investido = sum(
            Decimal(str(item.valor_total)) 
            for item in carteira.itens.values() 
            if item.valor_total is not None
        )
        
        # Calcula resultados como Decimal
        resultado_bruto = total_geral_decimal - total_investido if total_geral is not None else Decimal('0')
        resultado_percentual = (
            (resultado_bruto / total_investido * Decimal('100')) 
            if total_investido > Decimal('0') 
            else Decimal('0')
        )
        
        return {
            'nome_carteira': carteira.nome,
            'data_geracao': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'total_investido': float(total_investido.quantize(Decimal('0.01'))),
            'valor_atual': float(total_geral_decimal.quantize(Decimal('0.01'))) if total_geral is not None else 0.0,
            'resultado_bruto': float(resultado_bruto.quantize(Decimal('0.01'))),
            'resultado_percentual': float(resultado_percentual.quantize(Decimal('0.01'))),
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
            # Converte os valores para Decimal primeiro para manter a precisão
            valor_total = Decimal(str(item.valor_total)) if item.valor_total is not None else Decimal('0')
            valor_atual = Decimal(str(item.valor_atual)) if item.valor_atual is not None else Decimal('0')
            resultado = Decimal(str(item.resultado)) if item.resultado is not None else Decimal('0')
            resultado_percentual = Decimal(str(item.resultado_percentual)) if item.resultado_percentual is not None else Decimal('0')
            
            detalhes = {}
            if hasattr(ativo, 'dados_mercado') and ativo.dados_mercado:
                detalhes = {
                    'variacao_dia': ativo.dados_mercado.get('regularMarketChangePercent', 0.0),
                    'dividend_yield': ativo.dados_mercado.get('dividendYield', 0.0),
                    'lucro_por_acao': ativo.dados_mercado.get('lucroPorAcao', 0.0),
                    'valor_mercado': ativo.dados_mercado.get('valorDeMercado', 0.0)
                }
            
            # Converte para float apenas no final, para exibição
            ativo_info = {
                'ticker': ativo.ticker,
                'nome': ativo.nome,
                'tipo': ativo.tipo,
                'setor': ativo.setor or 'N/A',
                'quantidade': float(item.quantidade) if item.quantidade is not None else 0.0,
                'preco_medio': float(item.preco_medio) if item.preco_medio is not None else 0.0,
                'preco_atual': float(ativo.preco_atual) if ativo.preco_atual is not None else 0.0,
                'moeda': ativo.moeda or 'BRL',
                'ultima_atualizacao': ativo.ultima_atualizacao.strftime('%d/%m/%Y %H:%M') if hasattr(ativo, 'ultima_atualizacao') and ativo.ultima_atualizacao else 'N/A',
                'detalhes': detalhes,
                'valor_total': float(valor_total.quantize(Decimal('0.01'))),
                'valor_atual': float(valor_atual.quantize(Decimal('0.01'))),
                'resultado': float(resultado.quantize(Decimal('0.01'))),
                'resultado_percentual': float(resultado_percentual.quantize(Decimal('0.01')))
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
                # Formata os valores numéricos para garantir precisão
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
                        float(Decimal(str(relatorio['total_investido'])).quantize(Decimal('0.01'))),
                        float(Decimal(str(relatorio['valor_atual'])).quantize(Decimal('0.01'))) if relatorio['valor_atual'] is not None else 0.0,
                        float(Decimal(str(relatorio['resultado_bruto'])).quantize(Decimal('0.01'))),
                        float(Decimal(str(relatorio['resultado_percentual'])).quantize(Decimal('0.01'))),
                        int(relatorio['total_ativos'])
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