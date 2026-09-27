"""Helpers de data — sempre no fuso local (America/Sao_Paulo).

`timezone.now().date()` com USE_TZ=True devolve a data UTC: depois das 21h em
São Paulo o "hoje" já seria amanhã. Use `today()` daqui em todo o código.
"""
import calendar
import datetime

from django.utils import timezone

MONTH_NAMES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}
MONTH_ABBR_PT = {k: v[:3] for k, v in MONTH_NAMES_PT.items()}


def today() -> datetime.date:
    return timezone.localdate()


def add_months(d: datetime.date, n: int, day: int | None = None) -> datetime.date:
    """Soma `n` meses a `d`, preservando o dia (ou `day`) e caindo no último
    dia do mês quando ele não existe (31/01 + 1 mês → 28/02)."""
    month_index = d.month - 1 + n
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    target_day = day if day is not None else d.day
    return datetime.date(year, month, min(target_day, calendar.monthrange(year, month)[1]))


def month_bounds(year: int, month: int) -> tuple[datetime.date, datetime.date]:
    last = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, 1), datetime.date(year, month, last)


def month_start(d: datetime.date) -> datetime.date:
    return d.replace(day=1)


def month_label(d: datetime.date, short: bool = True) -> str:
    names = MONTH_ABBR_PT if short else MONTH_NAMES_PT
    return f"{names[d.month]}/{d.year}"


def iter_months(start: datetime.date, end: datetime.date):
    """Primeiro dia de cada mês entre start e end (inclusive)."""
    cur = month_start(start)
    while cur <= end:
        yield cur
        cur = add_months(cur, 1, day=1)


def parse_date(value) -> datetime.date | None:
    """Aceita ISO (AAAA-MM-DD) ou DD/MM/AAAA; devolve None se inválido."""
    if not value:
        return None
    if isinstance(value, datetime.date):
        return value
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
