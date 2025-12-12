import requests
import json

def get_price_manual(symbol):
    print(f"Fetching {symbol} manually...")
    try:
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        print(f"Response Status: {response.status_code}")
        data = response.json()
        result = data['chart']['result'][0]
        meta = result['meta']
        price = meta.get('regularMarketPrice') or meta.get('chartPreviousClose')
        print(f"Price: {price}")
        return price
    except Exception as e:
        print(f"Manual fetch failed for {symbol}: {e}")
        return None

if __name__ == "__main__":
    get_price_manual("MXRF11.SA")
