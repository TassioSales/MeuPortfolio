"""
Serviço para integração com a API do Yahoo Finance.
"""
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import pandas as pd
from ..models.ativo import Ativo, HistoricoPreco
from .. import db
from ..utils.logger import logger

class YFinanceService:
    """Classe para interação com a API do Yahoo Finance."""
    
    @staticmethod
    def get_ticker_info(symbol: str) -> Optional[Dict]:
        """
        Obtém informações detalhadas sobre um ativo.
        
        Args:
            symbol (str): Símbolo do ativo (ex: 'PETR4.SA', 'AAPL')
            
        Returns:
            Optional[Dict]: Dados do ativo ou None em caso de erro
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Obtém informações do ativo
            info = ticker.info
            
            # Obtém o histórico de preços
            hist = ticker.history(period='1d')
            
            if hist.empty:
                logger.warning(f"Nenhum dado disponível para {symbol}")
                return None
            
            # Determina o preço atual e variação
            if not hist.empty:
                close_prices = hist['Close']
                open_prices = hist['Open']
                
                if len(close_prices) > 0:
                    current_price = close_prices.iloc[-1]
                    open_price = open_prices.iloc[0] if len(open_prices) > 0 else current_price
                    price_change = current_price - open_price
                    price_change_pct = (price_change / open_price) * 100 if open_price != 0 else 0
                else:
                    current_price = info.get('regularMarketPrice') or info.get('currentPrice')
                    open_price = info.get('regularMarketOpen')
                    price_change = info.get('regularMarketChange')
                    price_change_pct = info.get('regularMarketChangePercent')
            else:
                current_price = info.get('regularMarketPrice') or info.get('currentPrice')
                open_price = info.get('regularMarketOpen')
                price_change = info.get('regularMarketChange')
                price_change_pct = info.get('regularMarketChangePercent')
            
            # Determina o tipo de ativo
            asset_type = 'acao'
            if info.get('quoteType') == 'CRYPTOCURRENCY':
                asset_type = 'criptomoeda'
            elif info.get('quoteType') == 'ETF':
                asset_type = 'etf'
            elif info.get('quoteType') == 'MUTUALFUND':
                asset_type = 'fundo_imobiliario'
            
            # Determina a moeda
            currency = info.get('currency', 'BRL' if '.SA' in symbol else 'USD')
            
            # Prepara o resultado
            result = {
                'symbol': symbol,
                'nome': info.get('longName', symbol),
                'preco': current_price,
                'variacao': price_change,
                'variacao_percentual': price_change_pct,
                'abertura': open_price,
                'maxima': info.get('dayHigh') or (hist['High'].iloc[-1] if not hist.empty else None),
                'minima': info.get('dayLow') or (hist['Low'].iloc[-1] if not hist.empty else None),
                'fechamento_anterior': info.get('previousClose'),
                'volume': info.get('volume') or (hist['Volume'].iloc[-1] if not hist.empty and 'Volume' in hist.columns else None),
                'volume_medio': info.get('averageVolume'),
                'market_cap': info.get('marketCap'),
                'moeda': currency,
                'tipo': asset_type,
                'setor': info.get('sector', ''),
                'industria': info.get('industry', ''),
                'pais': info.get('country', 'Brasil' if '.SA' in symbol else 'Estados Unidos'),
                'fonte': 'yfinance',
                'atualizacao': datetime.utcnow().isoformat()
            }
            
            # Atualiza ou cria o ativo no banco de dados
            ativo = Ativo.query.filter_by(symbol=symbol, fonte='yfinance').first()
            if not ativo:
                ativo = Ativo(
                    symbol=symbol,
                    nome=result['nome'],
                    fonte='yfinance',
                    tipo=asset_type,
                    setor=result['setor'],
                    empresa=result['nome'],
                    moeda=currency,
                    pais=result['pais']
                )
                db.session.add(ativo)
            
            # Atualiza o preço atual
            ativo.preco_atual = current_price
            ativo.variacao_percentual = price_change_pct
            ativo.volume = result['volume']
            ativo.ultima_atualizacao = datetime.utcnow()
            
            # Adiciona ao histórico
            historico = HistoricoPreco(
                ativo_id=ativo.id,
                preco=current_price,
                volume_24h=result['volume'],
                timestamp=datetime.utcnow()
            )
            db.session.add(historico)
            
            db.session.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao buscar informações do ativo {symbol} no Yahoo Finance: {str(e)}")
            return None
    
    @staticmethod
    def get_historical_data(
        symbol: str, 
        period: str = '1y', 
        interval: str = '1d',
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Optional[Dict]:
        """
        Obtém dados históricos de um ativo.
        
        Args:
            symbol (str): Símbolo do ativo (ex: 'PETR4.SA', 'AAPL')
            period (str): Período dos dados (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max). Defaults to '1y'.
            interval (str): Intervalo dos dados (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo). Defaults to '1d'.
            start_date (datetime, optional): Data de início. Se especificado, sobrepõe o período.
            end_date (datetime, optional): Data de fim. Se não especificado, usa a data atual.
            
        Returns:
            Optional[Dict]: Dados históricos ou None em caso de erro
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Se start_date for fornecido, usa o intervalo de datas
            if start_date:
                end_date = end_date or datetime.now()
                hist = ticker.history(start=start_date, end=end_date, interval=interval)
            else:
                hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                logger.warning(f"Nenhum dado histórico disponível para {symbol}")
                return None
            
            # Converte o DataFrame para uma lista de dicionários
            hist.reset_index(inplace=True)
            hist['Date'] = pd.to_datetime(hist['Date']).dt.tz_localize(None)  # Remove timezone
            
            # Renomeia as colunas para minúsculas
            hist.rename(columns={
                'Date': 'timestamp',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Dividends': 'dividends',
                'Stock Splits': 'splits'
            }, inplace=True)
            
            # Converte para o formato de dicionário
            data = hist.to_dict('records')
            
            return {
                'symbol': symbol,
                'interval': interval,
                'data': data
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados históricos do ativo {symbol} no Yahoo Finance: {str(e)}")
            return None
    
    @staticmethod
    def search_assets(query: str, limit: int = 10) -> List[Dict]:
        """
        Busca ativos no Yahoo Finance.
        
        Args:
            query (str): Termo de busca
            limit (int, optional): Número máximo de resultados. Defaults to 10.
            
        Returns:
            List[Dict]: Lista de ativos encontrados
        """
        try:
            # Usa o módulo de busca do yfinance
            search_results = yf.Tickers(query)
            
            # Obtém os tickers encontrados
            tickers = search_results.tickers
            
            # Limita o número de resultados
            tickers = tickers[:limit]
            
            # Obtém informações básicas de cada ativo
            results = []
            
            for ticker in tickers:
                try:
                    info = ticker.info
                    
                    # Determina o tipo de ativo
                    asset_type = 'ação'
                    if info.get('quoteType') == 'CRYPTOCURRENCY':
                        asset_type = 'criptomoeda'
                    elif info.get('quoteType') == 'ETF':
                        asset_type = 'ETF'
                    elif info.get('quoteType') == 'MUTUALFUND':
                        asset_type = 'fundo_imobiliário'
                    
                    results.append({
                        'symbol': ticker.ticker,
                        'nome': info.get('longName', ticker.ticker),
                        'tipo': asset_type,
                        'exchange': info.get('exchange', ''),
                        'moeda': info.get('currency', 'USD'),
                        'pais': info.get('country', 'Estados Unidos')
                    })
                except Exception as e:
                    logger.warning(f"Erro ao obter informações do ativo {ticker.ticker}: {str(e)}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Erro ao buscar ativos no Yahoo Finance: {str(e)}")
            return []

# Exemplo de uso:
if __name__ == "__main__":
    # Teste de informações de um ativo
    info = YFinanceService.get_ticker_info("PETR4.SA")
    print(f"Informações do ativo: {info}")
    
    # Teste de dados históricos
    historico = YFinanceService.get_historical_data("PETR4.SA", period='1mo', interval='1d')
    print(f"Dados históricos: {len(historico['data']) if historico and 'data' in historico else 0} registros" if historico else "Erro ao buscar histórico")
    
    # Teste de busca
    resultados = YFinanceService.search_assets("petrobras")
    print(f"Resultados da busca: {resultados}")
