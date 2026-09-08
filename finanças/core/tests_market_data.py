from contextlib import contextmanager
from unittest.mock import patch

from django.test import TestCase
from loguru import logger

from .forms import InvestmentForm


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
