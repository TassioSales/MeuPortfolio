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

from app.db.models import Caso, KanbanCard, KanbanColumn, Lead, LeadDetails, Message


# Quantas mensagens da conversa vão como contexto.
#
# Eram 5, e uma triagem passa disso no terceiro par de perguntas — o relato do
# caso caía fora da janela antes de a conversa terminar. Foram para 20, o que
# pareceu suficiente até a primeira triagem real: ela levou quase cinquenta
# mensagens, porque no WhatsApp o cliente responde "mandaod", "1", "analista"
# — uma ideia por mensagem, não um parágrafo. Com 20, o agente perdia a data
# de admissão que ele mesmo tinha perguntado dez mensagens antes, e
# reperguntava.
#
# Sessenta cobre a triagem inteira desse tamanho. São mensagens curtas: o
# histórico completo dá umas poucas centenas de tokens, contra os 6,4 mil
# caracteres do system prompt que vão em toda chamada de qualquer jeito.
# Repetir pergunta custa mais — em mensagem trocada e em cliente que desiste —
# do que os tokens que isto economizava.
MENSAGENS_DE_CONTEXTO = 60


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

    # O card do funil, e em que coluna ele está.
    #
    # Isto é um `SELECT` por chave indexada, não uma pergunta ao modelo: saber
    # se o contato já está no funil é fato registrado, e gastar chamada de LLM
    # para descobrir o que o banco responde em milissegundos seria pagar caro
    # por uma resposta pior.
    card = (
        await db.execute(
            select(KanbanCard, KanbanColumn.nome)
            .join(KanbanColumn, KanbanColumn.id == KanbanCard.column_id)
            .where(KanbanCard.lead_id == lead.id)
        )
    ).first()
    if card is not None:
        partes.append(
            f"Já existe card no funil, na coluna '{card[1]}' — o escritório já "
            "está com este contato."
        )

    # Os assuntos já registrados. O contato pode voltar com **outro** caso, e
    # aí não é retomada: é caso novo, do mesmo cliente.
    casos = (
        (
            await db.execute(
                select(Caso)
                .where(Caso.lead_id == lead.id)
                .order_by(Caso.data_abertura.desc())
            )
        )
        .scalars()
        .all()
    )
    if casos:
        descricao = ", ".join(
            f"{c.area or 'sem área'}"
            + (f" (aberto em {c.data_abertura.strftime('%d/%m/%Y')})" if c.data_abertura else "")
            for c in casos
        )
        partes.append(f"Casos já registrados deste contato: {descricao}.")
        partes.append(
            "Se o que a pessoa traz agora for um destes assuntos, retome sem "
            "reperguntar. Se for assunto diferente, é caso novo: faça a "
            "triagem dele do começo, sem misturar com o anterior."
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
