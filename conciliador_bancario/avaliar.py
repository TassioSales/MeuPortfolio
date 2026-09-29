"""Mede o motor contra o gabarito do cenário sintético.

Precisão importa mais que cobertura aqui: um casamento errado entra na contabilidade e alguém
descobre meses depois. Uma linha deixada para revisão custa minutos de uma pessoa. O motor é
calibrado para preferir o segundo erro.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.matching import conciliar
from dados_exemplo.gerar import gerar


def avaliar(quantidade: int = 200, semente: int = 42) -> dict[str, float | int]:
    cenario = gerar(quantidade, semente)
    resultado = conciliar(cenario.lancamentos, cenario.titulos)

    gabarito = {(l, t) for l, t in cenario.gabarito}
    obtido = {(frozenset(c.lancamentos), frozenset(c.titulos)) for c in resultado.conciliacoes}

    corretos = len(obtido & gabarito)
    errados = len(obtido - gabarito)

    return {
        "titulos": len(cenario.titulos),
        "lancamentos": len(cenario.lancamentos),
        "pagamentos_reais": len(gabarito),
        "casamentos_propostos": len(obtido),
        "corretos": corretos,
        "errados": errados,
        "precisao": corretos / len(obtido) if obtido else 0.0,
        "cobertura": corretos / len(gabarito) if gabarito else 0.0,
        "para_revisao": len(resultado.lancamentos_sem_par),
    }


if __name__ == "__main__":
    for semente in (42, 7, 2026):
        m = avaliar(semente=semente)
        print(
            f"semente {semente:>4} | {m['pagamentos_reais']:>3} pagamentos | "
            f"precisão {m['precisao']:6.1%} | cobertura {m['cobertura']:6.1%} | "
            f"errados {m['errados']:>2} | revisão {m['para_revisao']:>3}"
        )
