"""
Quem está esperando resposta agora.

O painel mostrava conversas e leads; não mostrava **omissão**. Um cliente que
escreveu às 2h da manhã e não recebeu resposta não aparecia em lugar nenhum:
a conversa continuava lá, com o mesmo aspecto das outras, e o escritório
descobria pelo próprio cliente reclamando — ou não descobria.

São dois donos possíveis para o mesmo silêncio, e a tela precisa separá-los
porque a ação é diferente:

- **`ia_sem_resposta`** — a conversa está no automático e o agente não
  respondeu. É defeito: modelo fora do ar, cota estourada, mensagem que o
  webhook perdeu. Quem resolve é quem cuida do sistema.
- **`humano_sem_resposta`** — alguém assumiu a conversa e não voltou. Não é
  defeito de software; é gente ocupada. Quem resolve é o escritório.

Misturar os dois num alerta só transformaria "a IA caiu" e "o Paulo foi
almoçar" no mesmo aviso, e o primeiro é urgente de um jeito que o segundo
não é.
"""

from datetime import datetime, timedelta
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.models import Agent, Conversation, Lead, Message
from app.utils.auth_middleware import get_current_user
from app.utils.exceptions import NotFoundException
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["alertas"])

# Meia hora é o mesmo limite que o produto concorrente usa, e é defensável:
# num atendimento de WhatsApp, quinze minutos ainda é "a pessoa está
# digitando"; meia hora já é abandono.
MINUTOS_PADRAO = 30

TipoDeAlerta = Literal["ia_sem_resposta", "humano_sem_resposta"]


class ClienteEsperando(BaseModel):
    """Uma conversa em que o cliente falou por último e ninguém respondeu."""

    tipo: TipoDeAlerta
    conversation_id: str
    phone_number: str
    lead_nome: Optional[str] = None
    # O que ele disse, para dar para triar sem abrir a conversa.
    ultima_mensagem: str
    desde: datetime
    minutos_esperando: int


class AlertasResponse(BaseModel):
    agent_id: str
    minutos: int
    # Contagens à parte da lista: a lista é truncada, o número não pode ser.
    total_ia: int
    total_humano: int
    conversas: List[ClienteEsperando]


@router.get("/agents/{agent_id}/alertas", response_model=AlertasResponse)
async def clientes_esperando(
    agent_id: str,
    minutos: int = Query(MINUTOS_PADRAO, ge=1, le=10080),
    limite: int = Query(50, ge=1, le=200),
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    As conversas paradas com a bola do lado de cá.

    O critério é um só, e é o que o cliente sente: **a última mensagem da
    conversa é dele**, e faz mais de `minutos` que ela chegou. Não importa
    quantas mensagens vieram antes nem se o agente respondeu ontem — importa
    que agora tem gente esperando.

    Conversa encerrada não entra: ela acabou, e a última palavra ser do
    cliente ("obrigado") é o desfecho normal, não uma pendência.
    """
    existe = await db.execute(select(Agent.id).where(Agent.id == agent_id))
    if existe.scalars().first() is None:
        raise NotFoundException("Agent")

    limite_de_tempo = datetime.utcnow() - timedelta(minutes=minutos)

    # A última mensagem de cada conversa, em uma passada.
    #
    # O caminho ingênuo seria carregar as conversas e consultar as mensagens
    # de cada uma — uma consulta por conversa, e a fila do escritório tem
    # centenas. Esta subconsulta resolve tudo no banco.
    ultima = (
        select(
            Message.conversation_id.label("conversation_id"),
            func.max(Message.timestamp).label("quando"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    consulta = (
        select(
            Conversation.id,
            Conversation.phone_number,
            Conversation.status,
            Lead.nome,
            Message.conteudo,
            ultima.c.quando,
        )
        .join(ultima, ultima.c.conversation_id == Conversation.id)
        .join(
            Message,
            (Message.conversation_id == Conversation.id)
            & (Message.timestamp == ultima.c.quando),
        )
        .outerjoin(Lead, Lead.conversation_id == Conversation.id)
        .where(Conversation.agent_id == agent_id)
        .where(Conversation.status.in_(("ativa", "pausada")))
        .where(Message.remetente == "user")
        .where(ultima.c.quando < limite_de_tempo)
        .order_by(ultima.c.quando)
    )

    agora = datetime.utcnow()
    esperando: List[ClienteEsperando] = []
    vistas: set = set()

    for id_, telefone, status_, nome, conteudo, quando in await db.execute(consulta):
        # Duas mensagens com o mesmo timestamp duplicariam a linha. Raro, e o
        # efeito seria o mesmo cliente aparecendo duas vezes na tela.
        if id_ in vistas:
            continue
        vistas.add(id_)

        esperando.append(
            ClienteEsperando(
                tipo="humano_sem_resposta" if status_ == "pausada" else "ia_sem_resposta",
                conversation_id=id_,
                phone_number=telefone,
                lead_nome=nome,
                ultima_mensagem=conteudo,
                desde=quando,
                minutos_esperando=int((agora - quando).total_seconds() // 60),
            )
        )

    total_ia = sum(1 for c in esperando if c.tipo == "ia_sem_resposta")
    total_humano = len(esperando) - total_ia

    if esperando:
        logger.info(
            f"⏳ {len(esperando)} cliente(s) esperando no agente {agent_id} "
            f"({total_ia} pela IA, {total_humano} por gente)"
        )

    return AlertasResponse(
        agent_id=agent_id,
        minutos=minutos,
        total_ia=total_ia,
        total_humano=total_humano,
        # O corte vem depois da contagem: a tela mostra 50, o número diz 300.
        conversas=esperando[:limite],
    )
