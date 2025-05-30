"""
Serviço de integração com o Yahoo Finance.
"""
import yfinance as yf
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from src.models.ativo import Ativo
from src.utils.logger import get_logger

logger = get_logger(__name__)

class YFinanceService:
    """
    Serviço para buscar informações de ativos no Yahoo Finance.
    """
    
    # Mapeamento de tipos de ativos do Yahoo Finance para nomes amigáveis
    TIPOS_ATIVOS = {
        'EQUITY': 'Ação',
        'ETF': 'ETF',
        'MUTUALFUND': 'Fundo de Investimento',
        'CRYPTOCURRENCY': 'Criptomoeda',
        'CURRENCY': 'Moeda',
        'FUTURE': 'Contrato Futuro',
        'INDEX': 'Índice',
        'OPTION': 'Opção',
    }
    
    @classmethod
    def _criar_ativo(cls, acao: yf.Ticker, ticker: str) -> Optional[Ativo]:
        """
        Cria um objeto Ativo a partir dos dados do Yahoo Finance.
        
        Args:
            acao: Objeto Ticker do yfinance
            ticker: Código do ativo
            
        Returns:
            Optional[Ativo]: Objeto Ativo com as informações ou None se não encontrado
        """
        try:
            info = acao.info
            if not info:
                return None
                
            # Mapeia os dados para o modelo Ativo
            tipo = cls.TIPOS_ATIVOS.get(info.get('quoteType', '').upper(), 'Outro')
            
            # Obtém o preço atual (tenta diferentes campos possíveis)
            preco_atual = (
                info.get('regularMarketPrice') or 
                info.get('currentPrice') or 
                info.get('previousClose')
            )
            
            # Prepara os dados de mercado
            dados_mercado = {
                'setor': info.get('sector'),
                'industria': info.get('industry'),
                'pais': info.get('country'),
                'marketCap': info.get('marketCap'),
                'volume': info.get('volume'),
                'averageVolume': info.get('averageVolume'),
                'dividendYield': info.get('dividendYield'),
                'trailingEps': info.get('trailingEps'),
                'trailingPE': info.get('trailingPE'),
                'regularMarketChange': info.get('regularMarketChange'),
                'regularMarketChangePercent': info.get('regularMarketChangePercent'),
                'dayLow': info.get('dayLow'),
                'dayHigh': info.get('dayHigh'),
                'open': info.get('open'),
                'previousClose': info.get('previousClose'),
                'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
                'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
                'ebitda': info.get('ebitda'),
                'totalDebt': info.get('totalDebt'),
                'longBusinessSummary': info.get('longBusinessSummary')
            }
            
            # Remove valores None do dicionário
            dados_mercado = {k: v for k, v in dados_mercado.items() if v is not None}
            
            return Ativo(
                ticker=ticker,
                nome=info.get('longName', info.get('shortName', ticker)),
                tipo=tipo,
                setor=info.get('sector'),
                preco_atual=preco_atual,
                moeda=info.get('currency', 'BRL'),
                dados_mercado=dados_mercado
            )
            
        except Exception as e:
            logger.error(f"Erro ao criar objeto Ativo para {ticker}", exc_info=True)
            return None
    
    @classmethod
    def buscar_ativo(cls, ticker: str) -> Optional[Ativo]:
        """
        Busca informações de um ativo no Yahoo Finance.
        
        Args:
            ticker: Código do ativo (ex: PETR4.SA, AAPL, BTC-USD, USD-BRL)
            
        Returns:
            Optional[Ativo]: Objeto Ativo com as informações ou None se não encontrado
        """
        try:
            logger.info(f"Buscando ativo: {ticker}")
            ticker_upper = ticker.upper()
            
            # Mapeamento de índices de renda fixa brasileiros
            renda_fixa = {
                'CDI': {
                    'nome': 'CDI (Taxa DI)',
                    'preco': 0.10,  # Valor aproximado diário (ajustar conforme necessário)
                    'moeda': '%',
                    'tipo': 'Renda Fixa',
                    'variacao': 0.0
                },
                'SELIC': {
                    'nome': 'Taxa SELIC',
                    'preco': 10.25,  # Valor atual da SELIC (ajustar conforme necessário)
                    'moeda': '%',
                    'tipo': 'Renda Fixa',
                    'variacao': 0.0
                },
                'IPCA': {
                    'nome': 'IPCA (Índice de Preços)',
                    'preco': 0.5,  # Valor mensal aproximado (ajustar conforme necessário)
                    'moeda': '%',
                    'tipo': 'Renda Fixa',
                    'variacao': 0.0
                },
                'PREFIXADO': {
                    'nome': 'Título Prefixado',
                    'preco': 100.0,  # Valor base (ajustar conforme necessário)
                    'moeda': 'BRL',
                    'tipo': 'Renda Fixa',
                    'variacao': 0.0
                }
            }
            
            # Verifica se é um índice de renda fixa
            if ticker_upper in renda_fixa:
                print(f"Índice de renda fixa encontrado: {ticker_upper}")
                dados = renda_fixa[ticker_upper]
                return Ativo(
                    ticker=ticker_upper,
                    nome=dados['nome'],
                    preco_atual=dados['preco'],
                    moeda=dados['moeda'],
                    tipo=dados['tipo'],
                    variacao_dia=dados['variacao']
                )
                
            # Mapeamento de pares de moedas comuns
            pares_moedas = {
                'USD-BRL': 'BRL=X',        # Dólar para Real
                'EUR-BRL': 'EURBRL=X',     # Euro para Real
                'BTC-USD': 'BTC-USD',      # Bitcoin para Dólar
                'ETH-USD': 'ETH-USD',      # Ethereum para Dólar
                'USDT-USD': 'USDT-USD',    # Tether para Dólar
                'USDC-USD': 'USDC-USD',    # USD Coin para Dólar
                'BUSD-USD': 'BUSD-USD',    # Binance USD para Dólar
                'DAI-USD': 'DAI-USD'      # DAI para Dólar
            }
            
            # Verifica se é um par de moedas conhecido
            if ticker_upper in pares_moedas:
                ticker = pares_moedas[ticker_upper]
                logger.debug(f"Convertido para par de moedas conhecido: {ticker}")
            # Verifica se é uma criptomoeda (ex: BTC-USD, USDT-USD)
            elif '-' in ticker and len(ticker.split('-')) == 2:
                moeda1, moeda2 = ticker_upper.split('-')
                
                # Lista de criptomoedas estáveis conhecidas
                stablecoins = ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP']
                
                # Se for uma stablecoin em relação ao dólar, mantém o formato original
                if moeda1 in stablecoins and moeda2 == 'USD':
                    logger.debug(f"Mantendo formato para stablecoin: {ticker_upper}")
                    ticker = ticker_upper
                # Se for outra criptomoeda, tenta o formato padrão
                else:
                    # Tenta primeiro o formato original
                    try:
                        acao = yf.Ticker(ticker_upper)
                        if acao.info:
                            ticker = ticker_upper
                            logger.debug(f"Tentando formato invertido para criptomoeda: {ticker}")
                            return cls._criar_ativo(acao, ticker)
                    except Exception as e:
                        logger.error(f"Erro ao buscar criptomoeda no formato original: {e}", exc_info=True)
                    
                    # Se não encontrar, tenta inverter o par
                    try:
                        novo_ticker = f"{moeda1}{moeda2}=X"
                        acao = yf.Ticker(novo_ticker)
                        if acao.info:
                            ticker = novo_ticker
                            logger.debug(f"Convertido para par de moedas: {ticker}")
                            return cls._criar_ativo(acao, ticker)
                    except Exception as e:
                        logger.error(f"Erro ao buscar criptomoeda no formato invertido: {e}", exc_info=True)
                    
                    # Se nenhum formato funcionar, mantém o original
                    ticker = ticker_upper
                    logger.debug(f"Usando formato original como último recurso: {ticker}")
            # Se não tiver sufixo, adiciona .SA (assumindo que é ação brasileira)
            elif not any(ext in ticker_upper for ext in ['.SA', '.TO', '.V', '.AX']):
                ticker = f"{ticker}.SA"
                logger.debug(f"Adicionado sufixo .SA: {ticker}")
            
            # Busca os dados
            acao = yf.Ticker(ticker)
            return cls._criar_ativo(acao, ticker)
            
        except Exception as e:
            logger.error(f"Erro ao buscar ativo {ticker_upper}: {str(e)}", exc_info=True)
            return None
    
    @classmethod
    def buscar_multiplos_ativos(cls, tickers: List[str]) -> Dict[str, Optional[Ativo]]:
        """
        Busca informações de múltiplos ativos de forma otimizada.
        
        Args:
            tickers: Lista de códigos de ativos
            
        Returns:
            Dict[str, Optional[Ativo]]: Dicionário com ticker como chave e Ativo como valor
        """
        resultado = {}
        
        # Processa em lotes para evitar sobrecarga
        lote = []
        for ticker in tickers:
            lote.append(ticker)
            if len(lote) >= 10:  # Limite de 10 requisições por lote
                for t in lote:
                    resultado[t] = cls.buscar_ativo(t)
                    time.sleep(0.5)  # Delay para evitar bloqueio
                lote = []
        
        # Processa o último lote se necessário
        for t in lote:
            resultado[t] = cls.buscar_ativo(t)
            time.sleep(0.5)
        
        return resultado
    
    @classmethod
    def buscar_historico(
        cls, 
        ticker: str, 
        periodo: str = '1y',
        intervalo: str = '1d'
    ) -> Optional[Dict[str, Any]]:
        """
        Busca histórico de preços de um ativo.
        
        Args:
            ticker: Código do ativo
            periodo: Período de tempo (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            intervalo: Intervalo entre os preços (1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            Optional[Dict[str, Any]]: Dicionário com os dados históricos ou None em caso de erro
        """
        try:
            acao = yf.Ticker(ticker)
            historico = acao.history(period=periodo, interval=intervalo)
            
            if historico.empty:
                return None
                
            # Converte o DataFrame para um dicionário
            dados = {
                'ticker': ticker,
                'periodo': periodo,
                'intervalo': intervalo,
                'dados': []
            }
            
            for data, linha in historico.iterrows():
                dados['dados'].append({
                    'data': data.strftime('%Y-%m-%d'),
                    'abertura': float(linha['Open']) if 'Open' in linha else None,
                    'maxima': float(linha['High']) if 'High' in linha else None,
                    'minima': float(linha['Low']) if 'Low' in linha else None,
                    'fechamento': float(linha['Close']) if 'Close' in linha else None,
                    'fechamento_ajustado': float(linha['Adj Close']) if 'Adj Close' in linha else None,
                    'volume': int(linha['Volume']) if 'Volume' in linha else None,
                })
                
            return dados
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico para {ticker}: {str(e)}", exc_info=True)
            return None
