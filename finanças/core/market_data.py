import requests
import logging
import yfinance as yf
from datetime import datetime, timedelta
from functools import lru_cache

logger = logging.getLogger('core')

# BCB Series Codes
SERIES_CDI_MENSAL = 4391  # % a.m.
SERIES_IPCA_MENSAL = 433  # % a.m.
SERIES_IGPM_MENSAL = 189  # % a.m.
SERIES_SELIC_META = 432  # % a.a.

@lru_cache(maxsize=32)
def get_bcb_series(code, start_date_str=None):
    """Fetch series from BCB.
    start_date_str: DD/MM/YYYY
    """
    try:
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json"
        if start_date_str:
            url += f"&dataInicial={start_date_str}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logger.warning(f"BCB API returned status {response.status_code} for code {code}")
            return []
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching BCB series {code}: {e}")
        return []

def get_latest_indicator(code):
    """Get the most recent value from a series."""
    start_date = (datetime.now() - timedelta(days=60)).strftime('%d/%m/%Y')
    series = get_bcb_series(code, start_date)
    if series:
        return float(series[-1]['valor'])
    return 0.0

def calculate_cdi_correction(principal, start_date, percentage_of_cdi=100.0, due_date=None):
    """Calculates the detailed correction by CDI Monthly rates.
    principal: Decimal or float
    start_date: date object
    percentage_of_cdi: float (e.g., 100, 110, 90)
    """
    if not principal or principal <= 0:
        return 0
    if not start_date:
        return principal
    start_str = start_date.strftime('%d/%m/%Y')
    series = get_bcb_series(SERIES_CDI_MENSAL, start_str)
    accumulated_factor = 1.0
    pct_factor = float(percentage_of_cdi) / 100.0
    for item in series:
        val = float(item['valor'])  # % monthly
        effective_rate = val * pct_factor
        accumulated_factor *= (1 + (effective_rate / 100.0))
    return float(principal) * accumulated_factor

def calculate_pre_fixado(principal, start_date, rate_yearly):
    """Calculate constant rate appreciation.
    rate_yearly: % a.a.
    """
    if not principal or not rate_yearly:
        return principal
    days_elapsed = (datetime.now().date() - start_date).days
    if days_elapsed < 0:
        days_elapsed = 0
    rate_decimal = float(rate_yearly) / 100.0
    factor = (1 + rate_decimal) ** (days_elapsed / 365.0)
    return float(principal) * factor

def get_real_time_currency(symbol_pair="USD"):
    """Fetch currency conversion rate.
    Returns rate of 1 unit of the given currency in BRL.
    """
    symbol_pair = symbol_pair.upper().strip()
    
    # Prioritize AwesomeAPI for USD and EUR to avoid YFinance noise/logs
    if symbol_pair in ['USD', 'EUR']:
        try:
            url = f"https://economia.awesomeapi.com.br/json/last/{symbol_pair}-BRL"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                pair_key = f"{symbol_pair}BRL"
                if pair_key in data:
                    return float(data[pair_key]['bid'])
        except Exception as e:
            logger.warning(f"AwesomeAPI failed for {symbol_pair}: {e}")

    # Fallback/Default for other tickers using yfinance
    try:
        ticker_name = 'BRL=X' if symbol_pair == 'USD' else 'EURBRL=X' if symbol_pair == 'EUR' else symbol_pair
        ticker = yf.Ticker(ticker_name)
        price = getattr(ticker.fast_info, 'last_price', None)
        if price:
            return price
        hist = ticker.history(period='1d')
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception as e:
        logger.warning(f"YFinance failed for {symbol_pair}: {e}")

    # Final fallback to AwesomeAPI if yfinance failed for a non-USD/EUR pair (if applicable)
    if symbol_pair not in ['USD', 'EUR']:
         try:
            url = f"https://economia.awesomeapi.com.br/json/last/{symbol_pair}-BRL"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                pair_key = f"{symbol_pair}BRL"
                if pair_key in data:
                    return float(data[pair_key]['bid'])
         except:
             pass

    return None
import logging
import yfinance as yf
from datetime import datetime, timedelta
from functools import lru_cache

logger = logging.getLogger('core')

# BCB Series Codes
SERIES_CDI_MENSAL = 4391 # % a.m.
SERIES_IPCA_MENSAL = 433 # % a.m.
SERIES_IGPM_MENSAL = 189 # % a.m.
SERIES_SELIC_META = 432 # % a.a.

@lru_cache(maxsize=32)
def get_bcb_series(code, start_date_str=None):
    """
    Fetch series from BCB. 
    start_date_str: DD/MM/YYYY
    """
    try:
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json"
        if start_date_str:
            url += f"&dataInicial={start_date_str}"
        
        response = requests.get(url, timeout=10)
        # Handle empty or error response gracefully
        if response.status_code != 200:
            logger.warning(f"BCB API returned status {response.status_code} for code {code}")
            return []
            
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching BCB series {code}: {e}")
        return []

def get_latest_indicator(code):
    """
    Get the most recent value from a series.
    """
    # Fetch last 12 months to be safe
    start_date = (datetime.now() - timedelta(days=60)).strftime('%d/%m/%Y')
    series = get_bcb_series(code, start_date)
    if series:
        return float(series[-1]['valor'])
    return 0.0

def calculate_cdi_correction(principal, start_date, percentage_of_cdi=100.0, due_date=None):
    """
    Calculates the detailed correction by CDI Monthly rates.
    principal: Decimal or float
    start_date: date object
    percentage_of_cdi: float (e.g., 100, 110, 90)
    """
    if not principal or principal <= 0:
        return 0

    if not start_date:
        return principal

    start_str = start_date.strftime('%d/%m/%Y')
    
    # Check if due_date is passed and it is in the past, effectively capping the calculation?
    # For "Current Value", we calculate up to today. 
    # If the investment expired, maybe it should be liquidated (but we just calculate 'theoretical' current value)
    
    series = get_bcb_series(SERIES_CDI_MENSAL, start_str)
    
    accumulated_factor = 1.0
    pct_factor = float(percentage_of_cdi) / 100.0
    
    for item in series:
        # Check if item date is after valid calc date? BCB filter already handles start.
        val = float(item['valor']) # % monthly
        effective_rate = val * pct_factor
        accumulated_factor *= (1 + (effective_rate / 100.0))
        
    return float(principal) * accumulated_factor

def calculate_pre_fixado(principal, start_date, rate_yearly):
    """
    Calculate constant rate appreciation.
    rate_yearly: % a.a.
    """
    if not principal or not rate_yearly: return principal
    
    days_elapsed = (datetime.now().date() - start_date).days
    if days_elapsed < 0: days_elapsed = 0
    
    # Exponential equivalent: (1 + rate)^(days/365)
    rate_decimal = float(rate_yearly) / 100.0
    factor = (1 + rate_decimal) ** (days_elapsed / 365.0)
    
    return float(principal) * factor


