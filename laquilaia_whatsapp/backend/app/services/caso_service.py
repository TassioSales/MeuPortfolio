"""
Abertura e reaproveitamento de casos de um contato.

Um `Lead` é a pessoa que manda mensagem; um `Caso` é o assunto que ela traz. A
mesma pessoa pode voltar com outro assunto, e o assunto pode ser de terceiro —
o irmão perguntando pelo divórcio da irmã. Sem a separação, os dois casos
dividem o mesmo cadastro e o parecer de um sobrescreve o do outro.
"""

import re
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Caso, Lead
from app.utils.logger import logger


AREAS = {
    "trabalhista",
    "familia",
    "consumidor",
    "previdenciario",
    "civel",
    "criminal",
    "outro",
}

# Como o titular vem quando é a própria pessoa que escreve.
TITULAR_O_PROPRIO = {"o próprio contato", "o proprio contato", "próprio contato"}


def ler_ficha(parecer: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrai `Área` e `Titular` da seção Ficha do parecer.

    Devolve `(None, None)` quando o modelo não seguiu o formato — e isso não é
    erro: um parecer sem ficha continua sendo um parecer útil, só não classifica
    o caso sozinho.
    """
    if not parecer:
        return None, None

    area = None
    titular = None

    m = re.search(r"^\s*[Áa]rea:\s*(.+)$", parecer, re.MULTILINE)
    if m:
        # O modelo às vezes devolve "Área: trabalhista (reversão de justa
        # causa)" — o que interessa é a primeira palavra da lista conhecida.
        bruto = m.group(1).strip().lower()
        bruto = _sem_acento(bruto)
        for candidata in AREAS:
            if _sem_acento(candidata) in bruto:
                area = candidata
                break

    m = re.search(r"^\s*Titular:\s*(.+)$", parecer, re.MULTILINE)
    if m:
        bruto = m.group(1).strip()
        if bruto.lower() not in TITULAR_O_PROPRIO:
            titular = bruto[:255]

    return area, titular


# Como o parecer escreve a viabilidade → como o sistema guarda.
#
# Guardar o texto do modelo direto seria pedir para o painel comparar strings
# com acento e maiúscula variando a cada parecer. O `indeterminado` é o default
# de propósito: parecer que não fala de porte não é caso viável nem inviável, é
# caso que ninguém dimensionou ainda.
VIABILIDADES = {
    "acima do piso": "acima_do_piso",
    "abaixo do piso": "abaixo_do_piso",
    "nao da para dimensionar": "indeterminado",
    "nao se aplica": "nao_se_aplica",
}


def ler_porte(parecer: str) -> Tuple[Optional[int], Optional[int], str]:
    """
    Extrai a faixa de valor e a viabilidade da seção de Porte econômico.

    Devolve `(piso, provavel, viabilidade)` em reais inteiros. Faixa ausente ou
    ilegível devolve `(None, None, ...)` sem estragar o resto: o parecer segue
    valendo, só não classifica o porte sozinho.
    """
    if not parecer:
        return None, None, "indeterminado"

    piso = provavel = None
    m = re.search(
        r"^\s*Valor estimado:\s*R\$\s*([\d.,]+)\s*a\s*R\$\s*([\d.,]+)",
        parecer,
        re.MULTILINE | re.IGNORECASE,
    )
    if m:
        piso, provavel = _em_reais(m.group(1)), _em_reais(m.group(2))
        # O modelo às vezes inverte a ordem da faixa. Ordenar é mais útil que
        # descartar: os dois números estão certos, só trocados de lugar.
        if piso is not None and provavel is not None and piso > provavel:
            piso, provavel = provavel, piso

    viabilidade = "indeterminado"
    m = re.search(r"^\s*Viabilidade:\s*(.+)$", parecer, re.MULTILINE | re.IGNORECASE)
    if m:
        bruto = _sem_acento(m.group(1).strip().lower())
        for texto, chave in VIABILIDADES.items():
            if _sem_acento(texto) in bruto:
                viabilidade = chave
                break

    return piso, provavel, viabilidade


def _em_reais(bruto: str) -> Optional[int]:
    """
    "35.000" e "35.000,00" viram 35000.

    Só o inteiro interessa: centavo em estimativa preliminar é precisão que o
    número não tem.
    """
    limpo = bruto.strip().rstrip(".,")
    if "," in limpo:  # formato brasileiro: ponto é milhar, vírgula é decimal
        limpo = limpo.split(",")[0]
    limpo = limpo.replace(".", "")
    return int(limpo) if limpo.isdigit() else None


def _sem_acento(texto: str) -> str:
    trocas = str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc")
    return texto.translate(trocas)


def _e_o_proprio(titular: Optional[str], nome_do_lead: Optional[str]) -> bool:
    """
    Se o titular do caso é a própria pessoa que escreve.

    O prompt pede "o próprio contato" nesse caso, mas o modelo tende a repetir
    o nome — foi o que aconteceu no primeiro parecer gerado com o prompt novo.
    Aceitar isso põe uma tarja "de Jonas Ferreira" na tela de um caso que é do
    próprio Jonas, e a tarja existe justamente para avisar que a parte é outra
    pessoa. Um aviso que aparece sempre deixa de ser aviso.
    """
    if not titular or not nome_do_lead:
        return False
    return _sem_acento(titular.strip().lower()) == _sem_acento(
        nome_do_lead.strip().lower()
    )


def _resumo_do_parecer(parecer: str, limite: int = 600) -> Optional[str]:
    """O texto da primeira seção — o resumo do caso."""
    linhas = []
    dentro = False
    for linha in parecer.split("\n"):
        if linha.startswith("#"):
            if dentro:
                break
            dentro = True
            continue
        if dentro and linha.strip():
            linhas.append(linha.strip())
    texto = " ".join(linhas).strip()
    return texto[:limite] or None


async def registrar_caso(
    lead: Lead,
    parecer: Optional[str],
    score: int,
    db: AsyncSession,
) -> Optional[Caso]:
    """
    Abre um caso para o contato, ou atualiza o que já existe na mesma área.

    A área é o critério de identidade porque é o que o sistema consegue
    reconhecer sozinho: dois relatos trabalhistas do mesmo contato quase sempre
    são o mesmo caso, e dois de áreas diferentes nunca são. Quem separar casos
    da mesma área é o advogado, pelo painel — o sistema não tem como saber que
    houve uma segunda demissão.

    Sem parecer não há ficha, e sem ficha não há área: nesse caso o caso não é
    aberto, para não encher o cadastro de registros vazios.
    """
    if not parecer:
        return None

    area, titular = ler_ficha(parecer)
    if _e_o_proprio(titular, lead.nome):
        titular = None
    if not area:
        logger.debug(f"⏭️ Parecer sem área identificada; caso não registrado ({lead.id})")
        return None

    resultado = await db.execute(
        select(Caso).where((Caso.lead_id == lead.id) & (Caso.area == area))
    )
    caso = resultado.scalars().first()

    if caso is None:
        caso = Caso(lead_id=lead.id, area=area)
        db.add(caso)
        logger.info(f"📁 Caso novo ({area}) para o contato {lead.id}")
    else:
        logger.debug(f"📁 Caso de {area} já existia para {lead.id}; atualizando")

    caso.titular = titular
    caso.resumo = _resumo_do_parecer(parecer)
    caso.analise_preliminar = parecer
    caso.score_qualificacao = score
    caso.valor_estimado_min, caso.valor_estimado_max, caso.viabilidade = ler_porte(
        parecer
    )

    await db.flush()
    return caso
