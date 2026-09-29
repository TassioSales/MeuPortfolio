"""Leitura do contas a receber em CSV, aceitando os nomes de coluna que os ERPs usam."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO

import polars as pl

from core.modelos import Titulo

# Cada ERP batiza a coluna do seu jeito. Mapear aqui evita obrigar o usuário a editar o arquivo
# antes de usar a ferramenta, que é onde a maioria desiste.
SINONIMOS: dict[str, tuple[str, ...]] = {
    "id": ("id", "numero", "num", "titulo", "nosso_numero", "codigo"),
    "vencimento": ("vencimento", "data_vencimento", "dt_vencimento", "data", "vcto"),
    "valor": ("valor", "valor_titulo", "vl_titulo", "total", "valor_documento"),
    "sacado": ("sacado", "cliente", "nome", "razao_social", "pagador", "devedor"),
    "documento": ("documento", "doc", "nota", "nf", "numero_documento", "nosso_numero"),
}

FORMATOS_DATA = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")


class CsvInvalido(ValueError):
    pass


def _achar_coluna(disponiveis: list[str], alvo: str) -> str | None:
    normalizadas = {c.strip().lower().replace(" ", "_"): c for c in disponiveis}
    for sinonimo in SINONIMOS[alvo]:
        if sinonimo in normalizadas:
            return normalizadas[sinonimo]
    return None


def _data(bruto: str) -> date:
    texto = str(bruto).strip()[:10]
    for formato in FORMATOS_DATA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise CsvInvalido(f"Data em formato não reconhecido: {bruto!r}")


def _valor(bruto: str) -> Decimal:
    texto = str(bruto).strip().replace("R$", "").replace(" ", "")
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation as erro:
        raise CsvInvalido(f"Valor em formato não reconhecido: {bruto!r}") from erro


def ler_titulos_csv(conteudo: str) -> list[Titulo]:
    try:
        tabela = pl.read_csv(StringIO(conteudo), infer_schema_length=0)
    except Exception as erro:  # noqa: BLE001 - polars lança tipos variados para CSV malformado
        raise CsvInvalido(f"Não consegui ler o CSV: {erro}") from erro

    if tabela.height == 0:
        raise CsvInvalido("O CSV não tem nenhuma linha")

    colunas = {alvo: _achar_coluna(tabela.columns, alvo) for alvo in SINONIMOS}
    faltando = [alvo for alvo in ("vencimento", "valor", "sacado") if colunas[alvo] is None]
    if faltando:
        raise CsvInvalido(
            f"Faltam colunas obrigatórias: {', '.join(faltando)}. "
            f"Colunas encontradas: {', '.join(tabela.columns)}"
        )

    titulos: list[Titulo] = []
    for indice, linha in enumerate(tabela.iter_rows(named=True)):
        identificador = str(linha[colunas["id"]]).strip() if colunas["id"] else ""
        titulos.append(
            Titulo(
                id=identificador or f"CSV-{indice:05d}",
                vencimento=_data(linha[colunas["vencimento"]]),
                valor=_valor(linha[colunas["valor"]]),
                sacado=str(linha[colunas["sacado"]]).strip(),
                documento=str(linha[colunas["documento"]]).strip() if colunas["documento"] else "",
            )
        )
    return titulos
