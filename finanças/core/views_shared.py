"""Shared utilities and SSL fix used across all view modules."""
import os
import shutil
import tempfile

import certifi
import requests
import yfinance as yf
from loguru import logger as log


def fix_ssl():
    """Work around SSL errors when the certifi path contains non-ASCII chars."""
    ca_bundle = certifi.where()
    is_path_problematic = any(ord(c) > 127 for c in ca_bundle) or " " in ca_bundle
    if is_path_problematic:
        temp_cert = os.path.join(tempfile.gettempdir(), "cacert_finance.pem")
        try:
            shutil.copy(ca_bundle, temp_cert)
            os.environ["CURL_CA_BUNDLE"] = temp_cert
            os.environ["REQUESTS_CA_BUNDLE"] = temp_cert
        except Exception as e:
            log.warning(f"Failed to copy SSL cert: {e}")
    else:
        os.environ["CURL_CA_BUNDLE"] = ca_bundle
        os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle


fix_ssl()


def get_price_manual(symbol: str):
    """Fallback price fetch via Yahoo Finance chart API."""
    try:
        url = (
            f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
            "?interval=1d&range=1d"
        )
        headers = {"User-Agent": "Mozilla/5.0"}
        data = requests.get(url, headers=headers, timeout=5).json()
        meta = data["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
        return price, meta.get("currency")
    except Exception as e:
        log.debug(f"Manual fetch failed for {symbol}: {e}")
        return None, None
