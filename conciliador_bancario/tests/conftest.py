import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.modelos import Lancamento, Titulo  # noqa: E402


@pytest.fixture
def credito():
    def _credito(id_: str, dia: int, valor: str, descricao: str) -> Lancamento:
        return Lancamento(id=id_, data=date(2026, 3, dia), valor=Decimal(valor), descricao=descricao)

    return _credito


@pytest.fixture
def titulo():
    def _titulo(id_: str, dia: int, valor: str, sacado: str, documento: str = "") -> Titulo:
        return Titulo(
            id=id_, vencimento=date(2026, 3, dia), valor=Decimal(valor), sacado=sacado, documento=documento
        )

    return _titulo
