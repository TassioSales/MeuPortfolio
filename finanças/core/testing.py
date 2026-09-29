"""Helpers de teste compartilhados."""
import datetime
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def frozen_today(day: datetime.date):
    """Congela `core.dates.today()` (via timezone.localdate) em `day`."""
    with patch("django.utils.timezone.localdate", return_value=day):
        yield
