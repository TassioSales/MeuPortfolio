"""Saída da conciliação: resumo para a tela e tabela para exportar."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import polars as pl

from core.modelos import Lancamento, Resultado, Situacao, Titulo


@dataclass(frozen=True, slots=True)
class Resumo:
    lancamentos: int
    titulos: int
    conciliados: int
    divergentes: int
    lancamentos_sem_par: int
    titulos_sem_par: int
    valor_conciliado: Decimal
    valor_em_aberto: Decimal
    diferenca_total: Decimal

    @property
    def cobertura(self) -> float:
        """Fração dos lançamentos que a ferramenta resolveu sem ajuda."""
        return 0.0 if self.lancamentos == 0 else 1 - self.lancamentos_sem_par / self.lancamentos


def resumir(resultado: Resultado, lancamentos: list[Lancamento], titulos: list[Titulo]) -> Resumo:
    por_lancamento = {l.id: l for l in lancamentos}
    por_titulo = {t.id: t for t in titulos}

    valor_conciliado = sum(
        (por_lancamento[i].valor for c in resultado.conciliacoes for i in c.lancamentos),
        Decimal("0"),
    )
    valor_em_aberto = sum((por_titulo[i].valor for i in resultado.titulos_sem_par), Decimal("0"))
    diferenca_total = sum((c.diferenca for c in resultado.conciliacoes), Decimal("0"))

    return Resumo(
        lancamentos=len(lancamentos),
        titulos=len(titulos),
        conciliados=resultado.total_conciliado,
        divergentes=resultado.total_divergente,
        lancamentos_sem_par=len(resultado.lancamentos_sem_par),
        titulos_sem_par=len(resultado.titulos_sem_par),
        valor_conciliado=valor_conciliado,
        valor_em_aberto=valor_em_aberto,
        diferenca_total=diferenca_total,
    )


def para_tabela(resultado: Resultado, lancamentos: list[Lancamento], titulos: list[Titulo]) -> pl.DataFrame:
    """Uma linha por conciliação, com o motivo junto — é isso que vai para o contador."""
    por_lancamento = {l.id: l for l in lancamentos}
    por_titulo = {t.id: t for t in titulos}

    linhas = [
        {
            "situacao": c.situacao.value,
            "estrategia": c.estrategia.value,
            "confianca": round(c.confianca, 3),
            "lancamentos": ", ".join(c.lancamentos),
            "data": min(por_lancamento[i].data for i in c.lancamentos),
            "valor_recebido": float(sum((por_lancamento[i].valor for i in c.lancamentos), Decimal("0"))),
            "titulos": ", ".join(c.titulos),
            "sacado": por_titulo[c.titulos[0]].sacado,
            "valor_titulo": float(sum((por_titulo[i].valor for i in c.titulos), Decimal("0"))),
            "diferenca": float(c.diferenca),
            "motivo": c.motivo,
        }
        for c in resultado.conciliacoes
    ]

    if not linhas:
        return pl.DataFrame(
            schema={
                "situacao": pl.Utf8, "estrategia": pl.Utf8, "confianca": pl.Float64,
                "lancamentos": pl.Utf8, "data": pl.Date, "valor_recebido": pl.Float64,
                "titulos": pl.Utf8, "sacado": pl.Utf8, "valor_titulo": pl.Float64,
                "diferenca": pl.Float64, "motivo": pl.Utf8,
            }
        )

    ordem = {Situacao.DIVERGENTE.value: 0, Situacao.CONCILIADO.value: 1}
    return (
        pl.DataFrame(linhas)
        .with_columns(pl.col("situacao").replace_strict(ordem, default=2).alias("_ordem"))
        .sort(["_ordem", "confianca"], descending=[False, True])
        .drop("_ordem")
    )


def pendencias(resultado: Resultado, lancamentos: list[Lancamento], titulos: list[Titulo]) -> pl.DataFrame:
    """O que sobrou, com as sugestões — para quem vai resolver na mão saber por onde começar."""
    por_lancamento = {l.id: l for l in lancamentos}
    por_titulo = {t.id: t for t in titulos}

    linhas = []
    for id_lancamento in resultado.lancamentos_sem_par:
        lancamento = por_lancamento[id_lancamento]
        sugestoes = resultado.candidatos.get(id_lancamento, ())
        linhas.append(
            {
                "lancamento": id_lancamento,
                "data": lancamento.data,
                "valor": float(lancamento.valor),
                "historico": lancamento.descricao,
                "sugestoes": ", ".join(
                    f"{s.titulo} ({por_titulo[s.titulo].sacado}, {s.confianca:.0%})" for s in sugestoes
                ) or "nenhuma",
            }
        )

    if not linhas:
        return pl.DataFrame(
            schema={"lancamento": pl.Utf8, "data": pl.Date, "valor": pl.Float64, "historico": pl.Utf8, "sugestoes": pl.Utf8}
        )
    return pl.DataFrame(linhas).sort("valor", descending=True)
