"""Leitor de OFX, o formato que todo banco brasileiro exporta.

OFX 1.x é SGML, não XML: as tags fecham sozinhas, e um parser XML recusa o arquivo. OFX 2.x já é
XML de verdade. Em vez de carregar dependência para as duas variantes, este módulo lê as duas com
expressão regular sobre a estrutura plana de transação, que é estável entre bancos.

O que ele não faz: validar cabeçalho, ler saldo, ler investimento. Conciliação precisa das
transações de crédito, e ler só isso mantém o módulo pequeno o bastante para ser auditado.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from core.modelos import Lancamento

_TRANSACAO = re.compile(r"<STMTTRN>(.*?)</STMTTRN>", re.DOTALL | re.IGNORECASE)
_CAMPO = re.compile(r"<([A-Z]+)>([^<\r\n]*)", re.IGNORECASE)

CREDITOS = frozenset({"CREDIT", "DEP", "DIRECTDEP", "XFER", "OTHER", "POS", "PIX"})


class OfxInvalido(ValueError):
    """O arquivo não tem transação reconhecível."""


def _data_ofx(bruto: str) -> date:
    """Converte YYYYMMDD, com ou sem hora e fuso colados, que é como os bancos variam."""
    digitos = re.sub(r"\D", "", bruto)[:8]
    if len(digitos) != 8:
        raise OfxInvalido(f"Data OFX ilegível: {bruto!r}")
    return datetime.strptime(digitos, "%Y%m%d").date()


def _valor_ofx(bruto: str) -> Decimal:
    """Aceita 1234.56 e 1234,56: o separador decimal varia entre exportadores brasileiros."""
    limpo = bruto.strip().replace(" ", "")
    if "," in limpo and "." in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    else:
        limpo = limpo.replace(",", ".")
    try:
        return Decimal(limpo)
    except InvalidOperation as erro:
        raise OfxInvalido(f"Valor OFX ilegível: {bruto!r}") from erro


def ler_ofx(conteudo: str) -> list[Lancamento]:
    """Extrai apenas os créditos do extrato, que é o lado que a conciliação usa.

    Débito é descartado em silêncio: extrato traz tarifa, transferência enviada e estorno, e
    nenhum deles quita título a receber.
    """
    blocos = _TRANSACAO.findall(conteudo)
    if not blocos:
        raise OfxInvalido("Nenhum bloco <STMTTRN> encontrado; o arquivo é OFX de extrato?")

    lancamentos: list[Lancamento] = []
    for indice, bloco in enumerate(blocos):
        campos = {tag.upper(): valor.strip() for tag, valor in _CAMPO.findall(bloco)}
        if "TRNAMT" not in campos or "DTPOSTED" not in campos:
            continue

        valor = _valor_ofx(campos["TRNAMT"])
        if valor <= 0:
            continue

        descricao = " ".join(
            parte for parte in (campos.get("MEMO", ""), campos.get("NAME", "")) if parte
        )
        lancamentos.append(
            Lancamento(
                id=campos.get("FITID") or f"OFX-{indice:05d}",
                data=_data_ofx(campos["DTPOSTED"]),
                valor=valor,
                descricao=descricao,
            )
        )

    if not lancamentos:
        raise OfxInvalido("O arquivo tem transações, mas nenhuma de crédito")
    return lancamentos
