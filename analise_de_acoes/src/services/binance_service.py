"""
Serviço para integração com a API da Binance.
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import logging
from ..models.ativo import Ativo, HistoricoPreco
from .. import db
from ..utils.logger import logger

class BinanceService:
    """Classe para interação com a API da Binance."""
    
    BASE_URL = "https://api.binance.com/api/v3"
    
    @classmethod
    def get_price(cls, symbol: str) -> Optional[Dict]:
        """
        Obtém o preço atual de um ativo na Binance.
        
        Args:
            symbol (str): Símbolo do ativo (ex: 'BTCUSDT')
            
        Returns:
            Optional[Dict]: Dados do ativo ou None em caso de erro
        """
        try:
            url = f"{cls.BASE_URL}/ticker/price"
            params = {'symbol': symbol}
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Atualiza ou cria o ativo no banco de dados
            ativo = Ativo.query.filter_by(symbol=symbol, fonte='binance').first()
            if not ativo:
                ativo = Ativo(
                    symbol=symbol,
                    nome=symbol.replace('USDT', ''),
                    fonte='binance',
                    tipo='criptomoeda'
                )
                db.session.add(ativo)
            
            # Atualiza o preço atual
            ativo.preco_atual = float(data['price'])
            ativo.ultima_atualizacao = datetime.utcnow()
            
            # Adiciona ao histórico
            historico = HistoricoPreco(
                ativo_id=ativo.id,
                preco=float(data['price']),
                volume_24h=0,  # A API não retorna volume nesta rota
                timestamp=datetime.utcnow()
            )
            db.session.add(historico)
            
            db.session.commit()
            
            return {
                'symbol': symbol,
                'preco': float(data['price']),
                'fonte': 'binance',
                'atualizacao': datetime.utcnow().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar preço na Binance para {symbol}: {str(e)}")
            return None
    
    @classmethod
    def get_historical_data(cls, symbol: str, interval: str = '1h', limit: int = 24) -> List[Dict]:
        """
        Obtém dados históricos de um ativo.
        
        Args:
            symbol (str): Símbolo do ativo (ex: 'BTCUSDT')
            interval (str): Intervalo dos dados (1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            limit (int): Número de registros a retornar (máx 1000)
            
        Returns:
            List[Dict]: Lista de dados históricos
        """
        try:
            url = f"{cls.BASE_URL}/klines"
            end_time = int(datetime.now().timestamp() * 1000)
            
            # Calcula o tempo de início com base no intervalo
            interval_map = {
                '1m': 60 * 1000,
                '5m': 5 * 60 * 1000,
                '15m': 15 * 60 * 1000,
                '30m': 30 * 60 * 1000,
                '1h': 60 * 60 * 1000,
                '2h': 2 * 60 * 60 * 1000,
                '4h': 4 * 60 * 60 * 1000,
                '6h': 6 * 60 * 60 * 1000,
                '8h': 8 * 60 * 60 * 1000,
                '12h': 12 * 60 * 60 * 1000,
                '1d': 24 * 60 * 60 * 1000,
                '3d': 3 * 24 * 60 * 60 * 1000,
                '1w': 7 * 24 * 60 * 60 * 1000,
                '1M': 30 * 24 * 60 * 60 * 1000
            }
            
            if interval not in interval_map:
                raise ValueError(f"Intervalo inválido. Use um dos seguintes: {', '.join(interval_map.keys())}")
            
            start_time = end_time - (interval_map[interval] * limit)
            
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': start_time,
                'endTime': end_time,
                'limit': limit
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            # Converte a resposta para o formato esperado
            klines = response.json()
            historical_data = []
            
            for k in klines:
                historical_data.append({
                    'timestamp': datetime.fromtimestamp(k[0] / 1000),
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                    'close_time': datetime.fromtimestamp(k[6] / 1000),
                    'quote_volume': float(k[7]),
                    'trades': k[8],
                    'taker_buy_base': float(k[9]),
                    'taker_buy_quote': float(k[10])
                })
            
            return historical_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar dados históricos na Binance para {symbol}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar dados históricos na Binance: {str(e)}")
            return []
    
    @classmethod
    def get_24h_stats(cls, symbol: str) -> Optional[Dict]:
        """
        Obtém estatísticas de 24 horas para um ativo.
        
        Args:
            symbol (str): Símbolo do ativo (ex: 'BTCUSDT')
            
        Returns:
            Optional[Dict]: Estatísticas ou None em caso de erro
        """
        try:
            url = f"{cls.BASE_URL}/ticker/24hr"
            params = {'symbol': symbol}
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'symbol': data['symbol'],
                'price_change': float(data['priceChange']),
                'price_change_percent': float(data['priceChangePercent']),
                'weighted_avg_price': float(data['weightedAvgPrice']),
                'prev_close_price': float(data['prevClosePrice']),
                'last_price': float(data['lastPrice']),
                'bid_price': float(data['bidPrice']),
                'ask_price': float(data['askPrice']),
                'open_price': float(data['openPrice']),
                'high_price': float(data['highPrice']),
                'low_price': float(data['lowPrice']),
                'volume': float(data['volume']),
                'quote_volume': float(data['quoteVolume']),
                'open_time': datetime.fromtimestamp(data['openTime'] / 1000),
                'close_time': datetime.fromtimestamp(data['closeTime'] / 1000),
                'first_id': data['firstId'],
                'last_id': data['lastId'],
                'count': data['count']
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar estatísticas de 24h na Binance para {symbol}: {str(e)}")
            return None

# Exemplo de uso:
if __name__ == "__main__":
    # Teste de obtenção de preço
    btc_price = BinanceService.get_price("BTCUSDT")
    print(f"Preço do BTC: {btc_price}")
    
    # Teste de obtenção de dados históricos
    btc_history = BinanceService.get_historical_data("BTCUSDT", interval='1h', limit=24)
    print(f"Dados históricos (últimas 24h): {len(btc_history)} registros")
    
    # Teste de estatísticas de 24h
    btc_stats = BinanceService.get_24h_stats("BTCUSDT")
    print(f"Variação 24h: {btc_stats['price_change_percent']}%" if btc_stats else "Erro ao buscar estatísticas")
