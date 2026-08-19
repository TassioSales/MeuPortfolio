"""
Quem fez o quê, e quando.

A trilha (`lead_timeline`) existia desde o começo e ninguém nunca a leu. Pior:
só a IA escrevia nela. Card arrastado por gente e conversa assumida por gente
não deixavam rastro — num escritório com mais de uma pessoa no board, "quem
mandou esse caso para o arquivo?" não tinha resposta.

Esta rota é a leitura dessa trilha, e ela ficou útil no mesmo commit em que o
Kanban e a pausa passaram a escrever nela.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.models import Agent, Conversation, Lead, LeadTimeline, User
from app.utils.auth_middleware import get_current_user
from app.utils.exceptions import NotFoundException
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["historico"])

POR_PAGINA = 50


class Movimento(BaseModel):
    id: str
    lead_id: str
    lead_nome: Optional[str] = None
    phone_number: str
    status_anterior: Optional[str] = None
    status_novo: str
    motivo: Optional[str] = None
    # Nulo quando foi a IA. É a distinção que o histórico existe para mostrar.
    responsavel: Optional[str] = None
    quando: datetime


class HistoricoResponse(BaseModel):
    agent_id: str
    total: int
    pagina: int
    por_pagina: int
    movimentos: List[Movimento]


@router.get("/agents/{agent_id}/historico", response_model=HistoricoResponse)
async def historico(
    agent_id: str,
    dias: int = Query(30, ge=1, le=365),
    apenas_humanos: bool = Query(False),
    pagina: int = Query(1, ge=1),
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    O que aconteceu com os leads, do mais recente para o mais antigo.

    `apenas_humanos` é o filtro que faz esta tela valer: a IA move dezenas de
    cards por dia e afoga as poucas ações de gente, que são justamente as que
    alguém precisa auditar.
    """
    existe = await db.execute(select(Agent.id).where(Agent.id == agent_id))
    if existe.scalars().first() is None:
        raise NotFoundException("Agent")

    base = (
        select(LeadTimeline, Lead, User.nome)
        .join(Lead, Lead.id == LeadTimeline.lead_id)
        .join(Conversation, Conversation.id == Lead.conversation_id)
        .outerjoin(User, User.id == LeadTimeline.mudado_por)
        .where(Conversation.agent_id == agent_id)
        .where(LeadTimeline.timestamp >= datetime.utcnow() - timedelta(days=dias))
    )

    if apenas_humanos:
        base = base.where(LeadTimeline.mudado_por.isnot(None))

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar() or 0

    linhas = await db.execute(
        base.order_by(LeadTimeline.timestamp.desc())
        .offset((pagina - 1) * POR_PAGINA)
        .limit(POR_PAGINA)
    )

    movimentos = [
        Movimento(
            id=evento.id,
            lead_id=lead.id,
            lead_nome=lead.nome,
            phone_number=lead.phone_number,
            status_anterior=evento.status_anterior,
            status_novo=evento.status_novo,
            motivo=evento.motivo,
            responsavel=responsavel,
            quando=evento.timestamp,
        )
        for evento, lead, responsavel in linhas
    ]

    logger.info(f"🕓 {total} movimento(s) no agente {agent_id} nos últimos {dias} dias")

    return HistoricoResponse(
        agent_id=agent_id,
        total=total,
        pagina=pagina,
        por_pagina=POR_PAGINA,
        movimentos=movimentos,
    )
