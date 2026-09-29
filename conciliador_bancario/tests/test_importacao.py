from datetime import date
from decimal import Decimal

import pytest

from core.importacao import CsvInvalido, ler_titulos_csv


def test_le_cabecalho_padrao():
    csv = "id,vencimento,valor,sacado,documento\nT1,2026-03-10,1500.00,Padaria do João,998877"
    t = ler_titulos_csv(csv)[0]
    assert (t.id, t.vencimento, t.valor, t.sacado) == ("T1", date(2026, 3, 10), Decimal("1500.00"), "Padaria do João")


@pytest.mark.parametrize("cabecalho", ["cliente", "Razao Social", "PAGADOR", "devedor"])
def test_aceita_sinonimo_de_sacado(cabecalho):
    csv = f"vencimento,valor,{cabecalho}\n10/03/2026,100,Alfa"
    assert ler_titulos_csv(csv)[0].sacado == "Alfa"


@pytest.mark.parametrize(
    "bruto,esperado",
    [("1500.00", "1500.00"), ("1.500,00", "1500.00"), ("1500,50", "1500.50"), ("R$ 250,00", "250.00")],
)
def test_formatos_de_valor(bruto, esperado):
    csv = f'vencimento,valor,cliente\n2026-03-10,"{bruto}",Alfa'
    assert ler_titulos_csv(csv)[0].valor == Decimal(esperado)


@pytest.mark.parametrize("bruto", ["2026-03-10", "10/03/2026", "10-03-2026", "2026/03/10"])
def test_formatos_de_data(bruto):
    csv = f"vencimento,valor,cliente\n{bruto},100,Alfa"
    assert ler_titulos_csv(csv)[0].vencimento == date(2026, 3, 10)


def test_gera_id_quando_nao_ha_coluna():
    csv = "vencimento,valor,cliente\n2026-03-10,100,Alfa"
    assert ler_titulos_csv(csv)[0].id == "CSV-00000"


def test_coluna_obrigatoria_ausente_diz_qual():
    with pytest.raises(CsvInvalido, match="sacado"):
        ler_titulos_csv("vencimento,valor\n2026-03-10,100")


def test_csv_vazio():
    with pytest.raises(CsvInvalido, match="nenhuma linha"):
        ler_titulos_csv("vencimento,valor,cliente")


def test_data_ilegivel_diz_qual_valor():
    with pytest.raises(CsvInvalido, match="31/31/2026"):
        ler_titulos_csv("vencimento,valor,cliente\n31/31/2026,100,Alfa")
