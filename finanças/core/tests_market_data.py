from contextlib import contextmanager
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from loguru import logger

from .forms import InvestmentForm
from .market_data import get_bcb_series, get_latest_indicator


@contextmanager
def capture_loguru(level="WARNING"):
    """Capture Loguru log messages emitted within the block.

    Loguru bypasses stdlib `logging` entirely (it's the other way around --
    the InterceptHandler in settings.py forwards stdlib logging INTO Loguru),
    so Django's `assertLogs` cannot see Loguru output. This attaches a
    temporary sink instead.
    """
    captured = []
    sink_id = logger.add(lambda message: captured.append(str(message)), level=level)
    try:
        yield captured
    finally:
        logger.remove(sink_id)


class InvestmentFormLoggingTests(TestCase):
    def test_yfinance_lookup_failure_is_logged_not_swallowed(self):
        with patch("core.forms.yf.Ticker", side_effect=RuntimeError("yfinance down")):
            with capture_loguru() as captured:
                form = InvestmentForm(data={
                    "category_type": "VARIABLE",
                    "symbol": "PETR4",
                    "name": "",
                    "quantity": "10",
                    "purchase_price": "R$ 30,00",
                    "date": "2026-01-10",
                    "create_transaction": True,
                })
                form.is_valid()

        self.assertTrue(any("yfinance" in message for message in captured))


class BcbSeriesCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("core.market_data.requests.get")
    def test_series_is_cached_and_not_refetched_within_ttl(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{"data": "01/01/2026", "valor": "1.0"}]

        first = get_bcb_series(999, "01/01/2026")
        second = get_bcb_series(999, "01/01/2026")

        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(first, second)

    @patch("core.market_data.get_bcb_series", return_value=[])
    def test_get_latest_indicator_logs_when_falling_back_to_zero(self, mock_series):
        with capture_loguru() as captured:
            value = get_latest_indicator(432)
        self.assertEqual(value, 0.0)
        self.assertTrue(any("no data" in message.lower() for message in captured))
