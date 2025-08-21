"""Helper functions for the Travel Planner application."""
import re
import random
import string
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

import httpx

from config.settings import settings
from config.log_config import get_logger

# Initialize logger
logger = get_logger(__name__)

# Currency symbol mapping
CURRENCY_SYMBOLS = {
    'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥',
    'BRL': 'R$', 'CAD': 'C$', 'AUD': 'A$', 'CNY': '¥',
    'INR': '₹', 'MXN': 'MX$', 'RUB': '₽', 'KRW': '₩',
}

def format_currency(amount: float, currency: str = 'USD', show_symbol: bool = True) -> str:
    """Format a monetary amount with currency symbol and proper formatting.
    
    Args:
        amount: The amount to format
        currency: ISO 4217 currency code (default: 'USD')
        show_symbol: Whether to include the currency symbol
        
    Returns:
        Formatted currency string
    """
    # Default to 2 decimal places
    decimals = 2
    
    # Handle currencies that typically don't use decimals
    if currency.upper() in ['JPY', 'KRW', 'VND', 'ISK']:
        decimals = 0
    
    # Format the number with thousands separators and decimal places
    formatted = f"{amount:,.{decimals}f}"
    
    # Add currency symbol if requested
    if show_symbol:
        symbol = CURRENCY_SYMBOLS.get(currency.upper(), f'{currency} ')
        # Handle symbol positioning (most symbols go before the number)
        if symbol in ['$', '€', '£', '¥', '₽', '₩', '₹']:
            return f"{symbol}{formatted}"
        else:
            return f"{formatted} {symbol}"
    
    return formatted

def format_duration(minutes: int) -> str:
    """Format a duration in minutes as a human-readable string.
    
    Args:
        minutes: Duration in minutes
        
    Returns:
        Formatted duration string (e.g., "2h 30m", "45m")
    """
    if not isinstance(minutes, (int, float)) or minutes < 0:
        return "N/A"
    
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{mins}m"

def parse_date(date_str: str, format: str = "%Y-%m-%d") -> Optional[date]:
    """Parse a date string into a date object.
    
    Args:
        date_str: Date string to parse
        format: Format string (default: YYYY-MM-DD)
        
    Returns:
        date object if parsing succeeds, None otherwise
    """
    try:
        return datetime.strptime(date_str, format).date()
    except (ValueError, TypeError):
        return None

def format_date(dt: Union[date, datetime], format: str = "%a, %b %d, %Y") -> str:
    """Format a date or datetime object as a string.
    
    Args:
        dt: date or datetime object to format
        format: Format string (default: "Mon, Jan 01, 2023")
        
    Returns:
        Formatted date string
    """
    if dt is None:
        return ""
    
    if isinstance(dt, datetime):
        return dt.strftime(format)
    elif isinstance(dt, date):
        return dt.strftime(format)
    else:
        return str(dt)

def generate_id(prefix: str = "", length: int = 8) -> str:
    """Generate a random ID with an optional prefix.
    
    Args:
        prefix: Optional prefix for the ID
        length: Length of the random part of the ID
        
    Returns:
        Generated ID string
    """
    chars = string.ascii_letters + string.digits
    random_part = ''.join(random.choices(chars, k=length))
    return f"{prefix}{random_part}" if prefix else random_part

async def fetch_json(url: str, params: Optional[Dict[str, Any]] = None, 
                    headers: Optional[Dict[str, str]] = None,
                    timeout: float = 10.0) -> Any:
    """Fetch JSON data from a URL with retry logic.
    
    Args:
        url: URL to fetch
        params: Query parameters
        headers: Request headers
        timeout: Request timeout in seconds
        
    Returns:
        Parsed JSON response
        
    Raises:
        httpx.HTTPStatusError: If the request fails after retries
    """
    max_retries = 3
    backoff_factor = 0.5
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(max_retries):
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise
                
                # Exponential backoff
                wait_time = backoff_factor * (2 ** attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {wait_time:.1f}s: {e}"
                )
                await asyncio.sleep(wait_time)

def validate_email(email: str) -> bool:
    """Validate an email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if the email is valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def human_readable_size(size_bytes: int) -> str:
    """Convert a size in bytes to a human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string (e.g., "1.5 MB", "42.0 KB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    
    for unit in ['', 'K', 'M', 'G', 'T', 'P']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}B"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"

def get_file_extension(filename: str) -> str:
    """Get the file extension from a filename.
    
    Args:
        filename: The filename to check
        
    Returns:
        The file extension (without the dot), or an empty string if none
    """
    return Path(filename).suffix.lstrip('.').lower()

def is_image_file(filename: str) -> bool:
    """Check if a filename has an image extension.
    
    Args:
        filename: The filename to check
        
    Returns:
        True if the file appears to be an image, False otherwise
    """
    image_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'}
    return get_file_extension(filename) in image_extensions

async def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
        
    Returns:
        Path object for the directory
    """
    path = Path(directory) if isinstance(directory, str) else directory
    path.mkdir(parents=True, exist_ok=True)
    return path
