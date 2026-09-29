"""Os parâmetros que decidem o que é casamento e o que é palpite.

Os padrões vieram de como o dinheiro se comporta na prática, não de arredondamento bonito:

- `janela_dias` em 5: boleto liquidado cai na conta em D+1, PIX de sexta aparece na segunda, e
  cliente atrasa. Janela menor perde casamento correto; muito maior faz um pagamento casar com
  o título do mês seguinte.
- `tolerancia_centavos` em 2: arredondamento de centavo entre sistemas é comum e não é
  divergência de verdade.
- `tolerancia_percentual` em 1%: cobre tarifa bancária e desconto de pontualidade, que chegam
  como valor a menos sem aviso.
- `max_titulos_combinados` em 4: cliente que paga vários boletos num depósito só costuma juntar
  poucos. Subir esse número cresce a busca por combinação sem achar caso real.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Regras:
    janela_dias: int = 5
    tolerancia_centavos: int = 2
    tolerancia_percentual: Decimal = Decimal("0.01")
    max_titulos_combinados: int = 4
    min_similaridade_nome: float = 0.5
    # Acima deste tamanho, o conjunto de títulos de um mesmo sacado deixa de ser combinado: a
    # busca por soma cresce rápido demais e nenhum cliente real junta tantos boletos num depósito.
    max_titulos_por_sacado_na_combinacao: int = 12

    def __post_init__(self) -> None:
        if self.janela_dias < 0:
            raise ValueError("janela_dias não pode ser negativa")
        if not 2 <= self.max_titulos_combinados <= 6:
            raise ValueError("max_titulos_combinados sai do útil fora de 2..6")
        if not 0.0 <= self.min_similaridade_nome <= 1.0:
            raise ValueError("min_similaridade_nome precisa estar entre 0 e 1")

    def dentro_da_tolerancia(self, esperado: Decimal, recebido: Decimal) -> bool:
        """Se a diferença cabe em tarifa ou arredondamento, e não em erro de pagamento."""
        diferenca = abs(esperado - recebido)
        return (
            diferenca <= Decimal(self.tolerancia_centavos) / 100
            or diferenca <= esperado * self.tolerancia_percentual
        )
