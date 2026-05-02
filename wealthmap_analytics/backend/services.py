import yfinance as yf
import requests

def get_market_price(ticker: str, asset_type: str) -> float:
    try:
        if asset_type == "CRYPTO":
            # CoinGecko mapping simple heuristic or fallback
            # In a real app we'd map tickers to CoinGecko IDs properly
            mapping = {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "SOL": "solana"
            }
            coin_id = mapping.get(ticker.upper())
            if coin_id:
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=brl"
                response = requests.get(url)
                data = response.json()
                return data.get(coin_id, {}).get("brl", 0.0)
            return 0.0
        else:
            # yfinance handles BR stocks if we append .SA (usually done by the user)
            # Example: PETR4.SA
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
            return 0.0
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return 0.0
