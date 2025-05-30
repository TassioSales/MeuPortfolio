"""
Serviço para integração com a API da Brapi.
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from ..models.ativo import Ativo, HistoricoPreco
from .. import db
from ..utils.logger import logger

class BrapiService:
    """Classe para interação com a API da Brapi."""
    
    BASE_URL = "https://brapi.dev/api"
    
    def __init__(self, api_key: str = None):
        """
        Inicializa o serviço com uma chave de API opcional.
        
        Args:
            api_key (str, optional): Chave de API da Brapi. Defaults to None.
        """
        self.api_key = api_key
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Realiza uma requisição para a API da Brapi.
        
        Args:
            endpoint (str): Endpoint da API
            params (Dict, optional): Parâmetros da requisição. Defaults to None.
            
        Returns:
            Optional[Dict]: Resposta da API ou None em caso de erro
        """
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            
            # Adiciona a chave de API aos parâmetros, se fornecida
            if self.api_key:
                if params is None:
                    params = {}
                params['token'] = self.api_key
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para a Brapi ({endpoint}): {str(e)}")
            return None
    
    def get_quote(self, symbols: str) -> Optional[Dict]:
        """
        Obtém cotações de um ou mais ativos.
        
        Args:
            symbols (str): Símbolos dos ativos separados por vírgula (ex: 'PETR4,VALE3')
            
        Returns:
            Optional[Dict]: Dados das cotações ou None em caso de erro
        """
        try:
            # Remove espaços e converte para maiúsculas
            symbols = symbols.replace(' ', '').upper()
            
            # Limita a 5 ativos por requisição (limite da API gratuita)
            symbol_list = symbols.split(',')
            if len(symbol_list) > 5:
                logger.warning(f"A API da Brapi suporta no máximo 5 ativos por requisição. Usando os 5 primeiros.")
                symbol_list = symbol_list[:5]
            
            symbols = ','.join(symbol_list)
            
            endpoint = f"quote/{symbols}"
            
            params = {
                'range': '1d',
                'interval': '1d',
                'fundamental': 'false',
                'dividends': 'false'
            }
            
            data = self._make_request(endpoint, params)
            
            if not data or 'results' not in data:
                return None
            
            # Processa os resultados
            results = []
            
            for item in data['results']:
                symbol = item['symbol']
                
                # Atualiza ou cria o ativo no banco de dados
                ativo = Ativo.query.filter_by(symbol=symbol, fonte='brapi').first()
                if not ativo:
                    ativo = Ativo(
                        symbol=symbol,
                        nome=item.get('longName', symbol),
                        fonte='brapi',
                        tipo='acao',
                        setor=item.get('sector', ''),
                        empresa=item.get('longName', '')
                    )
                    db.session.add(ativo)
                
                # Atualiza o preço atual
                ativo.preco_atual = item.get('regularMarketPrice')
                ativo.variacao_percentual = item.get('regularMarketChangePercent')
                ativo.volume = item.get('regularMarketVolume')
                ativo.ultima_atualizacao = datetime.utcnow()
                
                # Adiciona ao histórico
                historico = HistoricoPreco(
                    ativo_id=ativo.id,
                    preco=item.get('regularMarketPrice'),
                    volume_24h=item.get('regularMarketVolume', 0),
                    timestamp=datetime.utcnow()
                )
                db.session.add(historico)
                
                db.session.commit()
                
                # Prepara o resultado
                result = {
                    'symbol': symbol,
                    'nome': item.get('longName', symbol),
                    'preco': item.get('regularMarketPrice'),
                    'variacao': item.get('regularMarketChange'),
                    'variacao_percentual': item.get('regularMarketChangePercent'),
                    'abertura': item.get('regularMarketOpen'),
                    'maxima': item.get('regularMarketDayHigh'),
                    'minima': item.get('regularMarketDayLow'),
                    'fechamento_anterior': item.get('regularMarketPreviousClose'),
                    'volume': item.get('regularMarketVolume'),
                    'volume_medio': item.get('averageDailyVolume3Month'),
                    'market_cap': item.get('marketCap'),
                    'moeda': item.get('currency', 'BRL'),
                    'fonte': 'brapi',
                    'atualizacao': datetime.utcnow().isoformat()
                }
                
                results.append(result)
            
            return {'results': results}
            
        except Exception as e:
            logger.error(f"Erro ao processar cotação da Brapi: {str(e)}")
            return None
    
    def get_historical_data(self, symbol: str, range: str = '1mo', interval: str = '1d') -> Optional[Dict]:
        """
        Obtém dados históricos de um ativo.
        
        Args:
            symbol (str): Símbolo do ativo (ex: 'PETR4')
            range (str, optional): Período dos dados (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max). Defaults to '1mo'.
            interval (str, optional): Intervalo dos dados (1d, 1wk, 1mo). Defaults to '1d'.
            
        Returns:
            Optional[Dict]: Dados históricos ou None em caso de erro
        """
        try:
            endpoint = f"quote/{symbol}"
            
            params = {
                'range': range,
                'interval': interval,
                'fundamental': 'false',
                'dividends': 'false'
            }
            
            data = self._make_request(endpoint, params)
            
            if not data or 'results' not in data or not data['results']:
                return None
            
            # A API retorna os dados históricos no campo 'historicalDataPrice'
            historical_data = data['results'][0].get('historicalDataPrice', [])
            
            # Processa os dados históricos
            result = []
            
            for item in historical_data:
                # Verifica se é um dicionário (formato mais recente da API)
                if isinstance(item, dict):
                    timestamp = item.get('date')
                    open_price = item.get('open')
                    high = item.get('high')
                    low = item.get('low')
                    close = item.get('close')
                    volume = item.get('volume', 0)
                    
                    # Converte o timestamp de milissegundos para datetime
                    if timestamp:
                        timestamp = datetime.fromtimestamp(timestamp)
                    
                    result.append({
                        'timestamp': timestamp,
                        'open': open_price,
                        'high': high,
                        'low': low,
                        'close': close,
                        'volume': volume
                    })
            
            return {
                'symbol': symbol,
                'interval': interval,
                'data': result
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados históricos na Brapi para {symbol}: {str(e)}")
            return None
    
    def search_assets(self, query: str) -> Optional[Dict]:
        """
        Busca ativos na Brapi.
        
        Args:
            query (str): Termo de busca
            
        Returns:
            Optional[Dict]: Resultados da busca ou None em caso de erro
        """
        try:
            endpoint = "available"
            
            data = self._make_request(endpoint)
            
            if not data or 'stocks' not in data:
                return None
            
            # Filtra os resultados pela query
            query = query.upper()
            results = [
                stock for stock in data['stocks'] 
                if query in stock.upper()
            ]
            
            return {
                'query': query,
                'count': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar ativos na Brapi: {str(e)}")
            return None

# Exemplo de uso:
if __name__ == "__main__":
    # Cria uma instância do serviço (opcional: passar a chave da API)
    brapi = BrapiService()
    
    # Teste de cotação
    cotacao = brapi.get_quote("PETR4,VALE3,ITUB4")
    print(f"Cotações: {cotacao}")
    
    # Teste de dados históricos
    historico = brapi.get_historical_data("PETR4", range='1y', interval='1d')
    print(f"Dados históricos: {len(historico['data']) if historico and 'data' in historico else 0} registros" if historico else "Erro ao buscar histórico")
