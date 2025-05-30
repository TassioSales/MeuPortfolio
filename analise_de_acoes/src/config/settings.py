import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Database configuration
DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'database', 'acoes.db')
SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Flask configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# API Keys
BRAPI_API_KEY = os.getenv('BRAPI_API_KEY', '')
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'analise_de_acoes.log')

# Default assets
DEFAULT_CRYPTO_ASSETS = [
    {"symbol": "BTCUSDT", "name": "Bitcoin", "source": "binance", "category": "crypto"},
    {"symbol": "ETHUSDT", "name": "Ethereum", "source": "binance", "category": "crypto"},
    {"symbol": "BNBUSDT", "name": "Binance Coin", "source": "binance", "category": "crypto"},
    {"symbol": "XRPUSDT", "name": "Ripple", "source": "binance", "category": "crypto"},
]

DEFAULT_STOCKS_BR = [
    {"symbol": "PETR4", "name": "Petrobras", "source": "brapi", "category": "stocks"},
    {"symbol": "VALE3", "name": "Vale", "source": "brapi", "category": "stocks"},
    {"symbol": "ITUB4", "name": "Itaú Unibanco", "source": "brapi", "category": "stocks"},
    {"symbol": "BBDC4", "name": "Bradesco", "source": "brapi", "category": "stocks"},
]

# API endpoints
BRAPI_BASE_URL = 'https://brapi.dev/api/quote/'
BINANCE_BASE_URL = 'https://api.binance.com/api/v3/'

# Update intervals (in seconds)
PRICE_UPDATE_INTERVAL = 60  # 1 minute
HISTORY_UPDATE_INTERVAL = 3600  # 1 hour

# Theme configuration
THEME = {
    'primary': '#00FF00',  # Green for positive values
    'danger': '#FF0000',   # Red for negative values
    'background': '#1a1a1a',  # Dark background
    'text': '#ffffff',     # White text
    'secondary': '#2a2a2a',  # Slightly lighter dark for cards/panels
    'accent': '#00FF00',   # Accent color for highlights
}
