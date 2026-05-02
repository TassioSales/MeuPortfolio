import yfinance as yf
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from datetime import datetime, timedelta

def get_historical_data(ticker: str, period="1y", return_ohlc=False):
    """Fetch historical close prices or OHLC dataframe."""
    # Handle crypto ticker suffix for yfinance if it's pure crypto
    # In yfinance, Bitcoin is BTC-USD
    yf_ticker = ticker
    if ticker in ["BTC", "ETH"]:
        yf_ticker = f"{ticker}-USD"
    
    stock = yf.Ticker(yf_ticker)
    hist = stock.history(period=period)
    if hist.empty:
        return pd.DataFrame() if return_ohlc else pd.Series(dtype=float)
    return hist if return_ohlc else hist['Close']

def calculate_risk_metrics(tickers: list):
    """
    Calculate Volatility, Sharpe Ratio, and Correlation Matrix.
    """
    if not tickers:
        return {"volatility": 0, "sharpe_ratio": 0, "correlation": {}}
    
    # Fetch data
    df = pd.DataFrame()
    for t in set(tickers):
        series = get_historical_data(t, period="1y")
        if not series.empty:
            df[t] = series
            
    if df.empty:
        return {"volatility": 0, "sharpe_ratio": 0, "correlation": {}}
        
    # Calculate daily returns
    returns = df.pct_change().fillna(0)
    
    # Annualized Volatility
    volatilities = (returns.std() * np.sqrt(252)).replace([np.inf, -np.inf], 0).fillna(0).to_dict()
    
    # Sharpe Ratio (Risk free rate ~ 10% in Brazil = 0.10)
    risk_free_rate = 0.10
    annual_returns = (returns.mean() * 252)
    sharpes = ((annual_returns - risk_free_rate) / (returns.std() * np.sqrt(252))).replace([np.inf, -np.inf], 0).fillna(0).to_dict()
    
    # Correlation Matrix
    correlation_matrix = returns.corr().fillna(0).to_dict()
    
    # Portfolio aggregated
    avg_volatility = float(np.mean(list(volatilities.values()))) if volatilities else 0
    avg_sharpe = float(np.mean(list(sharpes.values()))) if sharpes else 0
    
    # Markowitz Portfolio Optimization (Maximum Sharpe Ratio)
    optimal_weights = {}
    if len(tickers) > 1 and not df.empty:
        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov() * 252
        num_assets = len(tickers)
        
        def neg_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate):
            p_ret = np.sum(mean_returns * weights)
            p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            return -(p_ret - risk_free_rate) / p_vol
            
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for asset in range(num_assets))
        initial_guess = num_assets * [1. / num_assets,]
        
        try:
            from scipy.optimize import minimize
            result = minimize(neg_sharpe_ratio, initial_guess, args=(mean_returns, cov_matrix, risk_free_rate), method='SLSQP', bounds=bounds, constraints=constraints)
            if result.success:
                optimal_weights = {tickers[i]: round(float(result.x[i]), 4) for i in range(num_assets)}
        except Exception as e:
            print("Optimization Error:", e)

    return {
        "portfolio_volatility": avg_volatility,
        "portfolio_sharpe": avg_sharpe,
        "asset_volatility": volatilities,
        "asset_sharpe": sharpes,
        "correlation": correlation_matrix,
        "optimal_weights": optimal_weights
    }

def forecast_price(ticker: str, days=15):
    """
    Forecast the next `days` price using Polynomial Regression.
    Returns OHLC historical data + SMA + forecasted points.
    """
    df_hist = get_historical_data(ticker, period="2y", return_ohlc=True)
    if df_hist.empty:
        return {"dates": [], "historical": [], "forecast": []}
        
    df = df_hist.reset_index()
    df['Date'] = df['Date'].dt.tz_localize(None)
    
    # Calculate Moving Averages
    df['SMA_50'] = df['Close'].rolling(window=50).mean().bfill()
    df['SMA_200'] = df['Close'].rolling(window=200).mean().bfill()
    
    # We use ordinal dates as features, normalized to start at 0
    min_ordinal = df['Date'].iloc[0].toordinal()
    df['ordinal'] = df['Date'].apply(lambda x: x.toordinal() - min_ordinal)
    
    X = df[['ordinal']].values
    y = df['Close'].values
    
    # Train a Polynomial Ridge Regression
    model = make_pipeline(PolynomialFeatures(degree=3), Ridge())
    model.fit(X, y)
    
    # Generate future dates
    last_date = df['Date'].iloc[-1]
    future_dates = [last_date + timedelta(days=i) for i in range(1, days+1)]
    future_ordinals = np.array([[d.toordinal() - min_ordinal] for d in future_dates])
    
    # Predict
    predictions = model.predict(future_ordinals)
    
    # Format historical OHLC + SMA data
    historical_data = []
    for _, row in df.iterrows():
        historical_data.append({
            "date": row['Date'].strftime("%Y-%m-%d"),
            "open": float(row['Open']),
            "high": float(row['High']),
            "low": float(row['Low']),
            "close": float(row['Close']),
            "sma50": float(row['SMA_50']),
            "sma200": float(row['SMA_200'])
        })
    
    # Forecast line data
    forecast_data = [{"date": historical_data[-1]["date"], "value": historical_data[-1]["close"]}]
    forecast_data += [{"date": d.strftime("%Y-%m-%d"), "value": float(v)} for d, v in zip(future_dates, predictions)]
    
    return {
        "historical": historical_data,
        "forecast": forecast_data
    }
