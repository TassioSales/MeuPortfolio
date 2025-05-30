import logging
import yfinance as yf
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from functools import lru_cache
import re
from enum import Enum
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# Assuming these are defined in your project
from src.models.ativo import Ativo
from src.utils.logger import get_logger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)

class AssetType(str, Enum):
    STOCK = 'Ação'
    FII = 'Fundo Imobiliário'
    ETF = 'ETF'
    CRYPTO = 'Criptomoeda'
    FIXED_INCOME = 'Renda Fixa'
    DERIVATIVE = 'Derivativo'
    FOREX = 'Câmbio'
    COMMODITY = 'Commodity'
    FUND = 'Fundo de Investimento'
    REAL_ASSET = 'Ativo Real'
    INDEX = 'Índice'

@dataclass
class AssetInfo:
    symbol: str
    name: str
    price: float
    currency: str
    asset_type: str
    market: str = ''
    sector: str = ''
    industry: str = ''
    description: str = ''
    variation: float = 0.0
    volume: float = 0.0
    market_cap: float = 0.0
    suffix: str = ''
    last_updated: datetime = None

    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'price': self.price,
            'currency': self.currency,
            'type': self.asset_type,
            'market': self.market,
            'sector': self.sector,
            'industry': self.industry,
            'description': self.description,
            'variation': self.variation,
            'volume': self.volume,
            'market_cap': self.market_cap,
            'suffix': self.suffix,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class Market:
    B3 = ('B3', 'BRL')
    NYSE = ('NYSE', 'USD')
    NASDAQ = ('NASDAQ', 'USD')
    CRYPTO = ('Crypto', 'USD')
    FOREX = ('Forex', 'USD')
    COMMODITY = ('Commodity', 'USD')
    GLOBAL = ('Global', 'USD')

class AssetClassifier:
    STOCK_PATTERNS = [r'^[A-Z]{4}[0-9]{1,2}$', r'^[A-Z]{1,5}$']
    FII_PATTERNS = [r'^[A-Z]{4}11$']
    ETF_PATTERNS = [r'^[A-Z]{4}11$', r'^[A-Z]{1,5}$']
    CRYPTO_PATTERNS = [r'^[A-Z]+-?[A-Z]+$']
    DERIVATIVE_PATTERNS = [r'^[A-Z]+[0-9]+[A-Z]$']
    FOREX_PATTERNS = [r'^[A-Z]{3}[A-Z]{3}=X$']
    COMMODITY_PATTERNS = [r'^[A-Z]{1,4}\d{0,2}$']
    FUND_PATTERNS = [r'^[A-Z]{4}\d{2}$']

    @classmethod
    def classify_asset(cls, symbol: str) -> Tuple[str, str]:
        symbol = symbol.upper().strip()
        if symbol in ['CDI', 'SELIC', 'IPCA', 'TESOURO', 'CDB', 'LCI', 'LCA', 'CRI', 'CRA']:
            return AssetType.FIXED_INCOME, Market.B3[0]
        if any(re.match(p, symbol) for p in cls.FII_PATTERNS):
            return AssetType.FII, Market.B3[0]
        if any(re.match(p, symbol) for p in cls.STOCK_PATTERNS):
            return AssetType.STOCK, Market.B3[0]
        if any(re.match(p, symbol) for p in cls.ETF_PATTERNS):
            return AssetType.ETF, Market.B3[0]
        if any(re.match(p, symbol) for p in cls.CRYPTO_PATTERNS):
            return AssetType.CRYPTO, Market.CRYPTO[0]
        if any(re.match(p, symbol) for p in cls.DERIVATIVE_PATTERNS):
            return AssetType.DERIVATIVE, Market.B3[0]
        if any(re.match(p, symbol) for p in cls.FOREX_PATTERNS):
            return AssetType.FOREX, Market.FOREX[0]
        if any(re.match(p, symbol) for p in cls.COMMODITY_PATTERNS):
            return AssetType.COMMODITY, Market.COMMODITY[0]
        if any(re.match(p, symbol) for p in cls.FUND_PATTERNS):
            return AssetType.FUND, Market.B3[0]
        if symbol.startswith('REAL_'):
            return AssetType.REAL_ASSET, Market.GLOBAL[0]
        return AssetType.STOCK, Market.B3[0]

class YFinanceService:
    CURRENCY_SYMBOLS = {'BRL': 'R$', 'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'BTC': '₿'}
    YAHOO_TO_ASSET_TYPE = {
        'EQUITY': AssetType.STOCK,
        'ETF': AssetType.ETF,
        'CRYPTOCURRENCY': AssetType.CRYPTO,
        'CURRENCY': AssetType.FOREX,
        'FUTURE': AssetType.DERIVATIVE,
        'INDEX': AssetType.INDEX,
        'MUTUALFUND': AssetType.FUND,
        'EQUITY/REIT': AssetType.FII
    }

    @classmethod
    @lru_cache(maxsize=500)
    def _create_asset_info(cls, yf_ticker: yf.Ticker, symbol: str) -> Optional[AssetInfo]:
        try:
            info = yf_ticker.info
            if not info or 'symbol' not in info:
                logger.warning(f"No info returned for {symbol}")
                return None

            quote_type = info.get('quoteType', '').upper()
            asset_type = cls.YAHOO_TO_ASSET_TYPE.get(quote_type, AssetType.STOCK)
            if asset_type == AssetType.STOCK and 'Real Estate' in info.get('longBusinessSummary', ''):
                asset_type = AssetType.FII

            market = Market.B3[0]
            currency = info.get('currency', 'BRL')
            if currency == 'USD':
                market = Market.NYSE[0] if info.get('exchange') == 'NYQ' else Market.NASDAQ[0]
            elif asset_type == AssetType.CRYPTO:
                market = Market.CRYPTO[0]
                currency = 'USD'
            elif asset_type == AssetType.FOREX:
                market = Market.FOREX[0]
            elif asset_type in [AssetType.DERIVATIVE, AssetType.COMMODITY]:
                market = Market.COMMODITY[0]

            price = next((info.get(f) for f in ['regularMarketPrice', 'currentPrice', 'previousClose', 'open', 'bid', 'ask'] if info.get(f) is not None), 0.0)
            return AssetInfo(
                symbol=symbol,
                name=info.get('longName', info.get('shortName', symbol)),
                price=price,
                currency=currency,
                asset_type=asset_type,
                market=market,
                sector=info.get('sector', ''),
                industry=info.get('industry', ''),
                variation=info.get('regularMarketChangePercent', 0.0),
                volume=info.get('volume', 0.0),
                market_cap=info.get('marketCap', 0.0),
                suffix='%' if asset_type == AssetType.FIXED_INCOME else '',
                last_updated=datetime.now(),
                description=info.get('longBusinessSummary', '')
            )
        except Exception as e:
            logger.error(f"Erro ao criar AssetInfo para {symbol}: {str(e)}")
            return None

    @classmethod
    def _get_yfinance_ticker(cls, symbol: str) -> Tuple[Optional[yf.Ticker], str]:
        symbol = symbol.upper().strip()
        if not symbol:
            logger.warning("Empty symbol provided")
            return None, symbol

        # Fixed income assets
        if symbol in ['CDI', 'SELIC', 'IPCA', 'CDB', 'LCI', 'LCA', 'CRI', 'CRA']:
            return None, symbol

        # Handle crypto and forex pairs
        if '-' in symbol and len(symbol.split('-')) == 2:
            base, quote = symbol.split('-')
            formats = [
                f"{base}-{quote}",  # ETH-BRL
                f"{base}{quote}",   # ETHBRL
                f"{base}{quote}=X", # ETHBRL=X
                f"{base}-USD",      # ETH-USD
                f"{base}-BTC"       # ETH-BTC
            ]
            for fmt in formats:
                try:
                    ticker = yf.Ticker(fmt)
                    if ticker.info and 'symbol' in ticker.info:
                        logger.debug(f"Valid ticker format found: {fmt}")
                        return ticker, fmt
                except Exception as e:
                    logger.debug(f"Failed ticker format {fmt}: {str(e)}")
                    continue
            logger.warning(f"No valid ticker format found for {symbol}")
            return None, symbol

        # Handle crypto without pair
        if symbol.isalpha() and len(symbol) <= 10:
            formats = [f"{symbol}-USD", f"{symbol}-BRL", f"{symbol}-BTC", symbol]
            for fmt in formats:
                try:
                    ticker = yf.Ticker(fmt)
                    if ticker.info and 'symbol' in ticker.info:
                        logger.debug(f"Valid crypto ticker format found: {fmt}")
                        return ticker, fmt
                except Exception as e:
                    logger.debug(f"Failed crypto ticker format {fmt}: {str(e)}")
                    continue

        # Handle Brazilian stocks/ETFs/FIIs
        if not any(symbol.endswith(s) for s in ['.SA', '.NY', '.NQ']):
            try:
                ticker = yf.Ticker(f"{symbol}.SA")
                if ticker.info and 'symbol' in ticker.info:
                    return ticker, f"{symbol}.SA"
            except:
                pass

        # Try raw symbol
        try:
            ticker = yf.Ticker(symbol)
            if ticker.info and 'symbol' in ticker.info:
                return ticker, symbol
        except Exception as e:
            logger.error(f"Failed to fetch ticker {symbol}: {str(e)}")
        return None, symbol

    @classmethod
    def _get_crypto_fallback(cls, symbol: str) -> Optional[AssetInfo]:
        """Fallback to CoinGecko API for cryptocurrencies"""
        try:
            base = symbol.split('-')[0].lower() if '-' in symbol else symbol.lower()
            quote = symbol.split('-')[1].lower() if '-' in symbol else 'usd'
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={base}&vs_currencies={quote}"
            session = requests.Session()
            retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
            session.mount('https://', HTTPAdapter(max_retries=retries))
            response = session.get(url, timeout=5)
            data = response.json()
            if base in data and quote in data[base]:
                price = data[base][quote]
                return AssetInfo(
                    symbol=symbol.upper(),
                    name=f"{base.upper()} ({quote.upper()})",
                    price=price,
                    currency=quote.upper(),
                    asset_type=AssetType.CRYPTO,
                    market=Market.CRYPTO[0],
                    sector='Cryptocurrency',
                    last_updated=datetime.now(),
                    description=f"Cryptocurrency {base.upper()} priced in {quote.upper()}"
                )
            return None
        except Exception as e:
            logger.error(f"CoinGecko fallback failed for {symbol}: {str(e)}")
            return None

    @classmethod
    def _get_fixed_income_info(cls, symbol: str) -> Optional[AssetInfo]:
        symbol = symbol.upper()
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))

        try:
            if symbol == 'SELIC':
                response = session.get('https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados/ultimos/1?formato=json', timeout=5)
                data = response.json()
                rate = float(data[0]['valor']) / 100 if data else 0.0
                return AssetInfo(
                    symbol=symbol,
                    name='Taxa SELIC',
                    price=rate,
                    currency='BRL',
                    asset_type=AssetType.FIXED_INCOME,
                    market=Market.B3[0],
                    sector='Renda Fixa',
                    suffix='%',
                    last_updated=datetime.now(),
                    description='Taxa básica de juros brasileira'
                )
            elif symbol == 'CDI':
                response = session.get('https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados/ultimos/1?formato=json', timeout=5)
                data = response.json()
                rate = float(data[0]['valor']) / 100 if data else 0.0
                return AssetInfo(
                    symbol=symbol,
                    name='CDI (Taxa DI)',
                    price=rate,
                    currency='BRL',
                    asset_type=AssetType.FIXED_INCOME,
                    market=Market.B3[0],
                    sector='Renda Fixa',
                    suffix='%',
                    last_updated=datetime.now(),
                    description='Taxa de juros interbancária'
                )
            elif symbol == 'IPCA':
                response = session.get('https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/1?formato=json', timeout=5)
                data = response.json()
                rate = float(data[0]['valor']) / 100 if data else 0.0
                return AssetInfo(
                    symbol=symbol,
                    name='IPCA (Índice de Preços)',
                    price=rate,
                    currency='BRL',
                    asset_type=AssetType.FIXED_INCOME,
                    market=Market.B3[0],
                    sector='Renda Fixa',
                    suffix='%',
                    last_updated=datetime.now(),
                    description='Índice oficial de inflação'
                )
            elif symbol in ['CDB', 'LCI', 'LCA', 'CRI', 'CRA']:
                return AssetInfo(
                    symbol=symbol,
                    name=f"{symbol} (Título Privado)",
                    price=0.0,  # Requires specific issuer data
                    currency='BRL',
                    asset_type=AssetType.FIXED_INCOME,
                    market=Market.B3[0],
                    sector='Renda Fixa',
                    suffix='%',
                    last_updated=datetime.now(),
                    description=f"Título de renda fixa ({symbol})"
                )
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar {symbol} from BCB: {str(e)}")
            return None

    @classmethod
    def _get_real_asset_info(cls, symbol: str) -> Optional[AssetInfo]:
        symbol = symbol.upper()
        if not symbol.startswith('REAL_'):
            return None
        try:
            name = symbol.replace('REAL_', '').replace('_', ' ')
            return AssetInfo(
                symbol=symbol,
                name=f"Ativo Real: {name}",
                price=0.0,  # Requires external valuation
                currency='USD',
                asset_type=AssetType.REAL_ASSET,
                market=Market.GLOBAL[0],
                sector='Ativos Reais',
                last_updated=datetime.now(),
                description=f"Ativo real ({name})"
            )
        except Exception as e:
            logger.error(f"Erro ao processar ativo real {symbol}: {str(e)}")
            return None

    @classmethod
    def buscar_ativo(cls, ticker: str) -> Optional[Ativo]:
        try:
            ticker = ticker.strip().upper()
            if not ticker:
                logger.warning("No ticker provided")
                return None

            # Fixed income
            fixed_income_info = cls._get_fixed_income_info(ticker)
            if fixed_income_info:
                return cls._convert_to_ativo(fixed_income_info)

            # Real assets
            real_asset_info = cls._get_real_asset_info(ticker)
            if real_asset_info:
                return cls._convert_to_ativo(real_asset_info)

            # Yahoo Finance
            yf_ticker, formatted_symbol = cls._get_yfinance_ticker(ticker)
            if yf_ticker:
                asset_info = cls._create_asset_info(yf_ticker, formatted_symbol)
                if asset_info:
                    return cls._convert_to_ativo(asset_info)

            # Crypto fallback
            if '-' in ticker or ticker.isalpha():
                crypto_info = cls._get_crypto_fallback(ticker)
                if crypto_info:
                    return cls._convert_to_ativo(crypto_info)

            logger.warning(f"No data found for ticker {ticker}")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar ativo {ticker}: {str(e)}")
            return None

    @classmethod
    def _convert_to_ativo(cls, asset_info: AssetInfo) -> Ativo:
        dados_mercado = {
            'setor': asset_info.sector,
            'industria': asset_info.industry,
            'marketCap': asset_info.market_cap,
            'volume': asset_info.volume,
            'variacao': asset_info.variation,
            'sufixo': asset_info.suffix,
            'mercado': asset_info.market,
            'moeda': asset_info.currency,
            'ultima_atualizacao': asset_info.last_updated.isoformat() if asset_info.last_updated else None,
            'descricao': asset_info.description
        }
        dados_mercado = {k: v for k, v in dados_mercado.items() if v is not None}
        return Ativo(
            ticker=asset_info.symbol,
            nome=asset_info.name,
            tipo=asset_info.asset_type,
            setor=asset_info.sector,
            preco_atual=asset_info.price,
            moeda=asset_info.currency,
            dados_mercado=dados_mercado
        )

    @classmethod
    def buscar_multiplos_ativos(cls, tickers: List[str]) -> Dict[str, Optional[Ativo]]:
        resultados = {t: None for t in tickers}
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(cls.buscar_ativo, t): t for t in tickers}
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    resultados[ticker] = future.result()
                except Exception as e:
                    logger.error(f"Erro ao buscar {ticker}: {str(e)}")
        return resultados

    @classmethod
    def buscar_historico(cls, ticker: str, periodo: str = '1y', intervalo: str = '1d') -> Optional[Dict[str, Any]]:
        try:
            ticker = ticker.upper()
            if ticker in ['CDI', 'SELIC', 'IPCA', 'CDB', 'LCI', 'LCA', 'CRI', 'CRA']:
                return cls._gerar_historico_renda_fixa(ticker, periodo, intervalo)
            if ticker.startswith('REAL_'):
                return {'ticker': ticker, 'periodo': periodo, 'intervalo': intervalo, 'dados': []}

            yf_ticker, formatted_symbol = cls._get_yfinance_ticker(ticker)
            if not yf_ticker:
                logger.warning(f"No ticker found for historical data: {ticker}")
                return None

            hist = yf_ticker.history(period=periodo, interval=intervalo)
            if hist.empty:
                logger.warning(f"No historical data for {formatted_symbol}")
                return None

            dados = {
                'ticker': formatted_symbol,
                'periodo': periodo,
                'intervalo': intervalo,
                'dados': [
                    {
                        'data': idx.strftime('%Y-%m-%d'),
                        'abertura': float(row['Open']),
                        'maxima': float(row['High']),
                        'minima': float(row['Low']),
                        'fechamento': float(row['Close']),
                        'fechamento_ajustado': float(row['Close']),
                        'volume': int(row['Volume'])
                    } for idx, row in hist.iterrows()
                ]
            }
            return dados
        except Exception as e:
            logger.error(f"Erro ao buscar histórico para {ticker}: {str(e)}")
            return None

    @classmethod
    def _gerar_historico_renda_fixa(cls, ticker: str, periodo: str = '1y', intervalo: str = '1d') -> Dict[str, Any]:
        try:
            asset_info = cls._get_fixed_income_info(ticker.upper())
            if not asset_info:
                return {'ticker': ticker, 'periodo': periodo, 'intervalo': intervalo, 'dados': []}

            periodos = {'1d': 1, '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180, '1y': 365, '2y': 730, '5y': 1825}
            dias = periodos.get(periodo, 365)
            hoje = datetime.now()
            data_inicio = hoje - timedelta(days=dias)
            datas = []
            data_atual = data_inicio

            while data_atual <= hoje:
                if data_atual.weekday() < 5:
                    datas.append(data_atual.strftime('%Y-%m-%d'))
                data_atual += timedelta(days=1)

            if intervalo == '1wk':
                datas = [d for d in datas if datetime.strptime(d, '%Y-%m-%d').weekday() == 4]
            elif intervalo == '1mo':
                datas = [d for d in datas if datetime.strptime(d, '%Y-%m-%d').day == 1]

            dados = []
            preco_base = asset_info.price
            for data in datas:
                preco = preco_base
                dados.append({
                    'data': data,
                    'abertura': round(preco, 4),
                    'maxima': round(preco * 1.005, 4),
                    'minima': round(preco * 0.995, 4),
                    'fechamento': round(preco, 4),
                    'fechamento_ajustado': round(preco, 4),
                    'volume': 0
                })

            return {'ticker': ticker, 'periodo': periodo, 'intervalo': intervalo, 'dados': dados}
        except Exception as e:
            logger.error(f"Erro ao gerar histórico para {ticker}: {str(e)}")
            return None