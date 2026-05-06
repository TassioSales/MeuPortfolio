import yfinance as yf
import httpx
import asyncio
from typing import Optional
from app.services.ml_service import fallback_history

async def get_market_price(ticker: str, asset_type: str) -> float:
    try:
        if asset_type == "CRYPTO":
            mapping = {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "SOL": "solana"
            }
            coin_id = mapping.get(ticker.upper())
            if coin_id:
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=brl"
                async with httpx.AsyncClient() as client:
                    response = await client.get(url)
                    data = response.json()
                    price = float(data.get(coin_id, {}).get("brl", 0.0))
                    return price if price > 0 else fallback_price(ticker)
            return fallback_price(ticker)
        else:
            # yfinance doesn't have a native async API, so we run it in a thread
            loop = asyncio.get_event_loop()
            price = await loop.run_in_executor(None, _fetch_yfinance_price, ticker)
            return price if price > 0 else fallback_price(ticker)
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return fallback_price(ticker)

def _fetch_yfinance_price(ticker: str) -> float:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return 0.0
    except:
        return fallback_price(ticker)

def fallback_price(ticker: str) -> float:
    try:
        hist = fallback_history(ticker, points=64)
        return float(hist["Close"].iloc[-1])
    except Exception:
        return 1.0

async def search_yahoo_assets(q: str):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={q}"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers, timeout=5)
            data = res.json()
            results = []
            for quote in data.get('quotes', []):
                q_type = quote.get('quoteType', '')
                if q_type in ['EQUITY', 'ETF', 'MUTUALFUND', 'CRYPTOCURRENCY', 'INDEX']:
                    asset_type = "CRYPTO" if q_type == 'CRYPTOCURRENCY' else ("FII" if "FII" in quote.get('shortname', '') else "STOCK")
                    results.append({
                        "ticker": quote.get('symbol'),
                        "name": quote.get('shortname', quote.get('longname', 'Desconhecido')),
                        "asset_type": asset_type
                    })
            return results[:8]
    except Exception as e:
        print("Search error:", e)
        return []
