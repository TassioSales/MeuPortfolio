"""Tipos do domínio da conciliação.

Tudo aqui é imutável de propósito: o resultado de uma conciliação precisa ser reproduzível a
partir das mesmas entradas, e estrutura mutável passando por seis estratégias de casamento é o
caminho mais curto para um bug que só aparece no fechamento do mês.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum


class Estrategia(str, Enum):
    """Como o casamento foi encontrado, da mais confiável para a menos."""

    DOCUMENTO = "documento"
    APELIDO = "apelido"
    VALOR_DATA = "valor_e_data"
    VALOR_NOME = "valor_e_nome"
    UM_PARA_MUITOS = "um_para_muitos"
    MUITOS_PARA_UM = "muitos_para_um"
    TOLERANCIA = "dentro_da_tolerancia"


class Situacao(str, Enum):
    CONCILIADO = "conciliado"
    DIVERGENTE = "divergente"
    REVISAR = "revisar"


@dataclass(frozen=True, slots=True)
class Lancamento:
    """Uma linha de crédito do extrato bancário."""

    id: str
    data: date
    valor: Decimal
    descricao: str

    def __post_init__(self) -> None:
        if self.valor <= 0:
            raise ValueError(f"Lançamento {self.id}: conciliação trata de crédito, valor foi {self.valor}")


@dataclass(frozen=True, slots=True)
class Titulo:
    """Um título a receber, do contas a receber."""

    id: str
    vencimento: date
    valor: Decimal
    sacado: str
    documento: str = ""

    def __post_init__(self) -> None:
        if self.valor <= 0:
            raise ValueError(f"Título {self.id}: valor precisa ser positivo, foi {self.valor}")


@dataclass(frozen=True, slots=True)
class Conciliacao:
    """Um casamento entre lançamentos e títulos, com o porquê registrado.

    O campo `motivo` não é enfeite: quem confere o fechamento precisa saber por que o sistema
    juntou essas linhas, e uma conciliação que ninguém consegue auditar não é usada duas vezes.
    """

    lancamentos: tuple[str, ...]
    titulos: tuple[str, ...]
    estrategia: Estrategia
    confianca: float
    situacao: Situacao
    diferenca: Decimal
    motivo: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.confianca <= 1.0:
            raise ValueError(f"Confiança fora de 0..1: {self.confianca}")
        if not self.lancamentos or not self.titulos:
            raise ValueError("Conciliação precisa de ao menos um lançamento e um título")


@dataclass(frozen=True, slots=True)
class Candidato:
    """Um título que combina parcialmente com um lançamento sem casar, oferecido para revisão."""

    titulo: str
    confianca: float
    motivo: str


@dataclass(frozen=True, slots=True)
class Resultado:
    conciliacoes: tuple[Conciliacao, ...]
    lancamentos_sem_par: tuple[str, ...]
    titulos_sem_par: tuple[str, ...]
    candidatos: dict[str, tuple[Candidato, ...]] = field(default_factory=dict)

    @property
    def total_conciliado(self) -> int:
        return sum(1 for c in self.conciliacoes if c.situacao is Situacao.CONCILIADO)

    @property
    def total_divergente(self) -> int:
        return sum(1 for c in self.conciliacoes if c.situacao is Situacao.DIVERGENTE)
