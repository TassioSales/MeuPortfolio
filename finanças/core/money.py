"""Helpers de dinheiro — Decimal com 2 casas, arredondamento comercial."""
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def q2(value) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def split_installments(total, n: int) -> list[Decimal]:
    """Divide `total` em `n` parcelas de centavos exatos; a última absorve o
    resto para que a soma bata exatamente com o total (100/3 → 33,33 ×2 + 33,34)."""
    total = q2(total)
    if n <= 1:
        return [total]
    base = (total / n).quantize(CENT, rounding=ROUND_HALF_UP)
    parts = [base] * (n - 1)
    parts.append(total - base * (n - 1))
    return parts
