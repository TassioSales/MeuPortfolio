import yfinance as yf
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from datetime import datetime, timedelta

def get_historical_data(ticker: str, period="1y"):
    """Fetch historical close prices."""
    # Handle crypto ticker suffix for yfinance if it's pure crypto
    # In yfinance, Bitcoin is BTC-USD or BTC-BRL
    yf_ticker = ticker
    if ticker in ["BTC", "ETH"]:
        yf_ticker = f"{ticker}-BRL"
    
    stock = yf.Ticker(yf_ticker)
    hist = stock.history(period=period)
    if hist.empty:
        return pd.Series(dtype=float)
    return hist['Close']

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
    returns = df.pct_change().dropna()
    
    # Annualized Volatility (assuming 252 trading days)
    # For portfolio, we just average individual volatilities for simplicity, 
    # or calculate portfolio volatility if weights were given.
    # Here we return a dictionary of individual volatilities
    volatilities = (returns.std() * np.sqrt(252)).to_dict()
    
    # Sharpe Ratio (Risk free rate ~ 10% in Brazil = 0.10)
    risk_free_rate = 0.10
    annual_returns = (returns.mean() * 252)
    sharpes = ((annual_returns - risk_free_rate) / (returns.std() * np.sqrt(252))).to_dict()
    
    # Correlation Matrix
    correlation_matrix = returns.corr().fillna(0).to_dict()
    
    # Portfolio aggregated (simple average for the dashboard)
    avg_volatility = np.mean(list(volatilities.values()))
    avg_sharpe = np.mean(list(sharpes.values()))
    
    return {
        "portfolio_volatility": avg_volatility,
        "portfolio_sharpe": avg_sharpe,
        "asset_volatility": volatilities,
        "asset_sharpe": sharpes,
        "correlation": correlation_matrix
    }

def forecast_price(ticker: str, days=30):
    """
    Forecast the next `days` price using Polynomial Regression on time series.
    Returns the historical data points + forecasted points.
    """
    series = get_historical_data(ticker, period="2y")
    if series.empty:
        return {"dates": [], "historical": [], "forecast": []}
        
    # Prepare data for sklearn
    df = series.reset_index()
    # Ensure datetime format and remove timezone for easier handling
    df['Date'] = df['Date'].dt.tz_localize(None)
    
    # We use ordinal dates as features
    df['ordinal'] = df['Date'].apply(lambda x: x.toordinal())
    
    X = df[['ordinal']].values
    y = df['Close'].values
    
    # Train a Polynomial Ridge Regression
    model = make_pipeline(PolynomialFeatures(degree=3), Ridge())
    model.fit(X, y)
    
    # Generate future dates
    last_date = df['Date'].iloc[-1]
    future_dates = [last_date + timedelta(days=i) for i in range(1, days+1)]
    future_ordinals = np.array([[d.toordinal()] for d in future_dates])
    
    # Predict
    predictions = model.predict(future_ordinals)
    
    # Format output
    historical_data = [{"date": row['Date'].strftime("%Y-%m-%d"), "value": row['Close']} for _, row in df.iterrows()]
    forecast_data = [{"date": d.strftime("%Y-%m-%d"), "value": float(v)} for d, v in zip(future_dates, predictions)]
    
    return {
        "historical": historical_data,
        "forecast": forecast_data
    }
