import yfinance as yf
import sys

def test_ticker(symbol):
    print(f"Testing {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        
        # Method 1: Info (often flaky)
        try:
            print("Attempting .info...")
            info = ticker.info
            print(f"Info result keys: {list(info.keys())[:5]}")
        except Exception as e:
            print(f".info failed: {e}")

        # Method 2: History
        print("Attempting .history(period='1d')...")
        history = ticker.history(period="1d")
        if not history.empty:
            print(f"History last close: {history['Close'].iloc[-1]}")
        else:
            print("History is empty.")

        # Method 3: Fast Info (newer yfinance)
        try:
            print("Attempting .fast_info...")
            print(f"Fast info price: {ticker.fast_info.last_price}")
        except Exception as e:
             print(f".fast_info failed: {e}")

    except Exception as e:
        print(f"General failure for {symbol}: {e}")
    print("-" * 30)

if __name__ == "__main__":
    test_ticker("BRL=X")
    test_ticker("MXRF11.SA")
    test_ticker("PETR4.SA")
