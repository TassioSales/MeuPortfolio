"""Limpeza do histórico bancário antes de qualquer comparação.

O histórico que o banco manda é ruidoso e cada banco ruído do seu jeito: "TED 033 RECEBIDA
CLIENTE X LTDA", "PIX QRS CLIENTE X", "CRED TEF 0001 CLIENTE X ME". Comparar essas strings cruas
com o nome do sacado no contas a receber não casa quase nada, e é o motivo pelo qual conciliação
feita com LIKE simples devolve resultado ruim.
"""

from __future__ import annotations

import re
import unicodedata

# Termos que todo banco injeta e que não identificam ninguém. Remover antes de comparar nomes
# evita que "TED" em duas descrições diferentes conte como similaridade.
RUIDO_BANCARIO = frozenset(
    {
        "TED", "DOC", "PIX", "TEF", "CRED", "CREDITO", "DEPOSITO", "DEP", "TRANSF",
        "TRANSFERENCIA", "RECEBIDA", "RECEBIDO", "ENVIADO", "LIQUIDACAO", "COBRANCA",
        "BOLETO", "TITULO", "PAGTO", "PAGAMENTO", "REF", "QRS", "QR", "AVULSO", "ONLINE",
        "BCO", "BANCO", "AG", "CC", "CONTA", "DA", "DE", "DO", "DAS", "DOS", "E",
    }
)

# Sufixos societários: "CLIENTE X LTDA" e "CLIENTE X" são a mesma empresa para fins de casamento.
SUFIXOS_SOCIETARIOS = frozenset({"LTDA", "ME", "EPP", "EIRELI", "SA", "S/A", "MEI", "EI"})

_NAO_ALFANUMERICO = re.compile(r"[^A-Z0-9 ]+")
_ESPACOS = re.compile(r"\s+")


def sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


def normalizar(texto: str | None) -> str:
    """Caixa alta, sem acento, sem pontuação, espaço único."""
    if not texto:
        return ""
    limpo = _NAO_ALFANUMERICO.sub(" ", sem_acento(texto).upper())
    return _ESPACOS.sub(" ", limpo).strip()


def tokens_significativos(texto: str | None) -> frozenset[str]:
    """Os tokens que sobram depois de tirar ruído bancário, sufixo societário e número solto.

    Número é descartado aqui de propósito: agência, conta e código de banco aparecem no histórico
    e casariam por acaso entre clientes diferentes. Documento tem extração própria.
    """
    palavras = normalizar(texto).split()
    return frozenset(
        p
        for p in palavras
        if p not in RUIDO_BANCARIO and p not in SUFIXOS_SOCIETARIOS and not p.isdigit() and len(p) > 2
    )


def similaridade_nome(descricao: str | None, sacado: str | None) -> float:
    """Fração dos tokens do sacado presentes no histórico, de 0 a 1.

    Índice de contenção, não Jaccard: o histórico bancário carrega palavras que o nome do sacado
    nunca terá, e penalizar por isso derrubaria casamento correto. O que importa é quanto do nome
    do cliente aparece no extrato.
    """
    tokens_sacado = tokens_significativos(sacado)
    if not tokens_sacado:
        return 0.0
    tokens_descricao = tokens_significativos(descricao)
    return len(tokens_sacado & tokens_descricao) / len(tokens_sacado)


def extrair_documentos(texto: str | None) -> frozenset[str]:
    """Sequências numéricas longas do histórico, candidatas a número de documento ou boleto.

    Corte em 5 dígitos: abaixo disso entra agência, parcela e ano, que geram casamento falso.
    O zero à esquerda cai porque o extrato e o contas a receber raramente concordam sobre ele.
    """
    return frozenset(
        achado.lstrip("0") or "0" for achado in re.findall(r"\d{5,}", normalizar(texto))
    )
