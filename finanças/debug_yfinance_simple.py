import yfinance as yf
import sys

# Silence yfinance loggers
import logging
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

def test_ticker(symbol):
    print(f"TESTING: {symbol}")
    ticker = yf.Ticker(symbol)
    
    # Check History
    try:
        hist = ticker.history(period="1d")
        if not hist.empty:
            print(f"HISTORY: OK ({hist['Close'].iloc[-1]})")
        else:
            print("HISTORY: EMPTY")
    except Exception as e:
        print(f"HISTORY: ERROR ({e})")

    # Check Fast Info
    try:
        price = ticker.fast_info.last_price
        print(f"FAST_INFO: OK ({price})")
    except Exception as e:
        print(f"FAST_INFO: ERROR ({e})")

if __name__ == "__main__":
    test_ticker("BRL=X")
    test_ticker("MXRF11.SA")
