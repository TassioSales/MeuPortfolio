from datetime import date
from decimal import Decimal

import pytest

from core.ofx import OfxInvalido, ler_ofx

OFX_SGML = """OFXHEADER:100
<OFX><BANKTRANLIST>
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20260305120000[-3:BRT]<TRNAMT>1500,00<FITID>A1<MEMO>PIX PADARIA
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260306<TRNAMT>-45.90<FITID>A2<MEMO>TARIFA</STMTTRN>
</BANKTRANLIST></OFX>"""


def test_le_credito_com_virgula_e_fuso():
    lancamentos = ler_ofx(OFX_SGML.replace("<MEMO>PIX PADARIA\n", "<MEMO>PIX PADARIA</STMTTRN>\n"))
    assert len(lancamentos) == 1
    assert lancamentos[0].data == date(2026, 3, 5)
    assert lancamentos[0].valor == Decimal("1500.00")


def test_descarta_debito():
    conteudo = "<STMTTRN><DTPOSTED>20260301<TRNAMT>100.00<FITID>C</STMTTRN>" \
               "<STMTTRN><DTPOSTED>20260302<TRNAMT>-50.00<FITID>D</STMTTRN>"
    assert [l.id for l in ler_ofx(conteudo)] == ["C"]


def test_junta_memo_e_name():
    conteudo = "<STMTTRN><DTPOSTED>20260301<TRNAMT>10.00<FITID>X<MEMO>TED<NAME>CLIENTE</STMTTRN>"
    assert ler_ofx(conteudo)[0].descricao == "TED CLIENTE"


def test_gera_id_quando_falta_fitid():
    conteudo = "<STMTTRN><DTPOSTED>20260301<TRNAMT>10.00<MEMO>SEM ID</STMTTRN>"
    assert ler_ofx(conteudo)[0].id == "OFX-00000"


def test_arquivo_sem_transacao():
    with pytest.raises(OfxInvalido, match="STMTTRN"):
        ler_ofx("<OFX></OFX>")


def test_arquivo_so_com_debito():
    with pytest.raises(OfxInvalido, match="nenhuma de crédito"):
        ler_ofx("<STMTTRN><DTPOSTED>20260301<TRNAMT>-10.00<FITID>D</STMTTRN>")


def test_data_ilegivel():
    with pytest.raises(OfxInvalido, match="Data OFX"):
        ler_ofx("<STMTTRN><DTPOSTED>2026<TRNAMT>10.00<FITID>X</STMTTRN>")


def test_valor_com_ponto_de_milhar_e_virgula_decimal():
    conteudo = "<STMTTRN><DTPOSTED>20260301<TRNAMT>1.234,56<FITID>X</STMTTRN>"
    assert ler_ofx(conteudo)[0].valor == Decimal("1234.56")
