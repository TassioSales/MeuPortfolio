"""
O que o agente precisa saber antes de responder de novo ao mesmo número.

Sem isto, quem já foi atendido e volta uma semana depois ouve "seu caso é
sobre o quê?" outra vez: o agente enxerga só as últimas mensagens da conversa,
e o que ficou para trás — inclusive a triagem inteira — não existe para ele.
Para o cliente parece que o escritório esqueceu; para o escritório, o mesmo
caso chega duas vezes.
"""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Lead, LeadDetails, Message


# Quantas mensagens da conversa vão como contexto.
#
# Eram 5, e uma triagem passa disso no terceiro par de perguntas — o relato do
# caso caía fora da janela antes de a conversa terminar. Vinte cobre uma
# triagem inteira sem inflar demais o custo por mensagem; conversas mais
# longas que isso perdem o começo, e é aí que a nota de atendimento abaixo
# passa a carregar o resumo.
MENSAGENS_DE_CONTEXTO = 20


async def nota_de_atendimento_anterior(
    phone_number: str,
    conversation_id: str,
    db: AsyncSession,
) -> Optional[str]:
    """
    Um lembrete do que já se sabe deste número, ou `None` se for a primeira vez.

    Vai como primeira mensagem do contexto, no papel de usuário — é o único
    canal que o serviço tem para falar com o modelo sem alterar o system
    prompt, que é do dono do agente.
    """
    resultado = await db.execute(
        select(Lead).where(Lead.phone_number == phone_number)
    )
    lead = resultado.scalars().first()
    if lead is None:
        return None

    partes = ["[Nota do sistema, não é mensagem do cliente]"]
    nome = lead.nome or "sem nome registrado"
    partes.append(f"Este número já tem atendimento registrado: {nome}.")

    if lead.status_funil:
        partes.append(f"Situação no funil: {lead.status_funil}.")

    if lead.data_criacao:
        partes.append(
            f"Primeiro contato em {lead.data_criacao.strftime('%d/%m/%Y')}."
        )

    detalhes = await db.execute(
        select(LeadDetails).where(LeadDetails.lead_id == lead.id)
    )
    detalhe = detalhes.scalars().first()
    if detalhe is not None and detalhe.analise_preliminar:
        # Só o resumo. O parecer inteiro é do advogado, e o agente não deve
        # repetir teses nem prazos para o cliente.
        resumo = _primeira_secao(detalhe.analise_preliminar)
        if resumo:
            partes.append(f"Resumo do caso já levantado: {resumo}")

    total = await db.execute(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
    )
    partes.append(f"Mensagens trocadas até aqui: {total.scalar() or 0}.")

    partes.append(
        "Não recomece a triagem do zero. Cumprimente pelo nome, retome de onde "
        "parou e pergunte o que a pessoa precisa agora. Só refaça as perguntas "
        "cujas respostas você não tem."
    )

    return " ".join(partes)


def _primeira_secao(markdown: str, limite: int = 400) -> str:
    """O texto da primeira seção do parecer, cortado."""
    linhas = []
    dentro = False
    for linha in markdown.split("\n"):
        if linha.startswith("#"):
            if dentro:
                break
            dentro = True
            continue
        if dentro and linha.strip():
            linhas.append(linha.strip())

    texto = " ".join(linhas)
    return texto[:limite].rstrip()


def com_nota(historico: List[dict], nota: Optional[str]) -> List[dict]:
    """Põe a nota na frente do histórico, quando houver."""
    if not nota:
        return historico
    return [{"role": "user", "content": nota}] + historico
