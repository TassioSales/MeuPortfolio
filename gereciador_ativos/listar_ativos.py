import yfinance as yf
import pandas as pd
from datetime import datetime
import time
import sys
from pathlib import Path

# Adiciona o diretório src ao PATH para garantir que os imports funcionem
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import get_logger

logger = get_logger(__name__)

def formatar_moeda(valor):
    """Formata valores monetários"""
    if pd.isna(valor):
        return "N/A"
    try:
        return f"R$ {float(valor):,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")
    except:
        return str(valor)

def obter_info_acao(ticker):
    """Obtém informações detalhadas de um ativo"""
    try:
        ativo = yf.Ticker(ticker)
        info = ativo.info
        
        # Tenta obter o preço atual
        try:
            preco_atual = formatar_moeda(info.get('regularMarketPrice') or info.get('currentPrice', 'N/A'))
        except:
            preco_atual = "N/A"
        
        return {
            'Ticker': ticker,
            'Nome': info.get('longName', info.get('shortName', 'N/A')),
            'Tipo': info.get('quoteType', 'N/A').upper(),
            'Setor': info.get('sector', 'N/A'),
            'Indústria': info.get('industry', 'N/A'),
            'País': info.get('country', 'N/A'),
            'Moeda': info.get('currency', 'N/A'),
            'Preço Atual': preco_atual,
            'Variação 1D': f"{info.get('regularMarketChangePercent', 'N/A')}%" if info.get('regularMarketChangePercent') else 'N/A',
            'Volume': f"{info.get('volume', 'N/A'):,}".replace(",", ".") if info.get('volume') else 'N/A',
            'Mercado': info.get('market', 'N/A'),
            'Exchange': info.get('exchange', 'N/A')
        }
    except Exception as e:
        logger.error(f"Erro ao obter informações para {ticker}", exc_info=True)
        return None

def listar_ativos():
    """Lista diferentes tipos de ativos financeiros"""
    # Dicionário com categorias e exemplos de ativos
    categorias = {
        'Ações Brasileiras': ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA'],
        'Ações EUA': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
        'ETFs': ['IVVB11.SA', 'BOVA11.SA', 'SMAL11.SA', 'SPY', 'QQQ'],
        'Fundos Imobiliários': ['MXRF11.SA', 'HGLG11.SA', 'KNRI11.SA', 'XPML11.SA'],
        'Criptomoedas': ['BTC-USD', 'ETH-USD', 'BNB-USD', 'XRP-USD'],
        'Índices': ['^BVSP', '^GSPC', '^IXIC', '^DJI'],
        'Moedas': ['USDBRL=X', 'EURBRL=X', 'BTCBRL=X'],
        'Commodities': ['GC=F', 'SI=F', 'CL=F', 'NG=F'],
        'Renda Fixa': ['BRL=X', '^TNX', '^TYX', '^FVX'],
        'Ações de Dividendos': ['VZ', 'T', 'PFE', 'KO', 'PG']
    }
    
    logger.info("\n" + "="*80)
    logger.info(f"{'LISTAGEM DE ATIVOS FINANCEIROS':^80}")
    logger.info(f"{'='*80}")
    logger.info(f"{'DATA E HORA':^80} - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info(f"{'='*80}")
    
    # Para cada categoria, busca as informações dos ativos
    for categoria, ativos in categorias.items():
        logger.info(f"\n{' ' + categoria + ' ':=^80}")
        logger.info("-"*80)
        logger.info(f"{'Ativo':<15} | {'Nome':<30} | {'Tipo':<10} | {'Preço Atual':>15} | {'Variação 1D':>12} | {'Setor':<20}")
        logger.info("-"*80)
        
        dados = []
        ativos_validos = []
        for ticker in ativos:
            info = obter_info_acao(ticker)
            if info:
                dados.append(info)
                ativos_validos.append(ticker)
            time.sleep(1)  # Evita sobrecarregar a API
        
        if dados:
            # Cria e exibe a tabela formatada
            df = pd.DataFrame(dados)
            for ativo_info in dados:
                logger.info(f"{ativo_info['Ticker']:<15} | {ativo_info['Nome'][:28]:<30} | {ativo_info['Tipo']:<10} | {ativo_info['Preço Atual']:>15} | {ativo_info['Variação 1D']:>12} | {ativo_info['Setor'][:18]:<20}")
        logger.info("-"*80)
        logger.info(f"Total de ativos listados: {len(ativos_validos)}/{len(ativos)}")
        logger.info("="*80 + "\n")

if __name__ == "__main__":
    try:
        listar_ativos()
    except KeyboardInterrupt:
        print("\nOperação interrompida pelo usuário.")
    except Exception as e:
        print(f"\nOcorreu um erro: {str(e)}")
    finally:
        print("\nConsulta de ativos finalizada.")
