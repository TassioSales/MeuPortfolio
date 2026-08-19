"""
Todo mundo que já chegou, em lista.

O Kanban é bom para trabalhar o funil e péssimo para **achar uma pessoa**.
A primeira coluna do escritório tem 155 cards; procurar o Sr. Alexandre ali é
rolar uma coluna até o olho cansar. Quem atende no telefone precisa do
contrário: digitar "Alexandre" ou os quatro últimos dígitos e chegar nele.

Por isso esta tela existe ao lado do board e não no lugar dele. São duas
perguntas diferentes: "o que está travado?" (board) e "cadê o fulano?"
(lista).
"""

import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.models import (
    Agent,
    Conversation,
    KanbanCard,
    KanbanColumn,
    Lead,
    LeadDetails,
)
from app.utils.auth_middleware import get_current_user
from app.utils.exceptions import NotFoundException
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["clientes"])

POR_PAGINA = 50

# Abaixo disto a busca não filtra nada útil e faz o banco varrer tudo — uma
# letra só casa com metade da base.
BUSCA_MINIMA = 2


class ClienteNaLista(BaseModel):
    lead_id: str
    nome: Optional[str] = None
    phone_number: str
    email: Optional[str] = None
    empresa: Optional[str] = None
    cargo: Optional[str] = None
    score_qualificacao: int = 0
    # A coluna do board. `None` quando o lead ainda não tem card — acontece
    # com lead criado antes de o funil existir.
    etapa: Optional[str] = None
    dias_parado: Optional[int] = None
    data_criacao: Optional[datetime] = None
    # Para o botão "ver o atendimento".
    conversation_id: Optional[str] = None


class ClientesResponse(BaseModel):
    agent_id: str
    # O total da **busca**, não da base: é o que a paginação precisa e é o que
    # responde "achei quantos?".
    total: int
    pagina: int
    por_pagina: int
    clientes: List[ClienteNaLista]


def _dias(movido_em: Optional[datetime], agora: datetime) -> Optional[int]:
    if movido_em is None:
        return None
    return max(0, (agora - movido_em).days)


def _do_bloco(detalhes: Optional[LeadDetails], campo: str) -> Optional[str]:
    """Empresa e cargo vivem dentro do `dados_json`, sem coluna própria."""
    if detalhes is None or not detalhes.dados_json:
        return None
    try:
        return (json.loads(detalhes.dados_json) or {}).get(campo) or None
    except (json.JSONDecodeError, AttributeError):
        # JSON quebrado é motivo para o campo vir vazio, não para a lista
        # inteira falhar.
        return None


@router.get("/agents/{agent_id}/clientes", response_model=ClientesResponse)
async def listar_clientes(
    agent_id: str,
    busca: str = Query("", max_length=120),
    etapa: str = Query("", max_length=120),
    pagina: int = Query(1, ge=1),
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Os contatos do agente, do mais recente para o mais antigo.

    `busca` casa com nome, telefone e e-mail ao mesmo tempo, porque quem
    procura não sabe de antemão por qual dos três vai lembrar. É `ILIKE
    %termo%` — sem índice, e assumidamente: são milhares de linhas, não
    milhões, e um índice trigram para uma tabela desse tamanho é preço sem
    benefício.

    `etapa` filtra pelo nome da coluna do board.
    """
    existe = await db.execute(select(Agent.id).where(Agent.id == agent_id))
    if existe.scalars().first() is None:
        raise NotFoundException("Agent")

    base = (
        select(Lead, LeadDetails, KanbanCard, KanbanColumn.nome, Conversation.id)
        .join(Conversation, Lead.conversation_id == Conversation.id)
        .outerjoin(LeadDetails, LeadDetails.lead_id == Lead.id)
        .outerjoin(KanbanCard, KanbanCard.lead_id == Lead.id)
        .outerjoin(KanbanColumn, KanbanColumn.id == KanbanCard.column_id)
        .where(Conversation.agent_id == agent_id)
    )

    termo = busca.strip()
    if len(termo) >= BUSCA_MINIMA:
        # O telefone é guardado só com dígitos; quem digita "(61) 99999" não
        # acharia nada sem esta limpeza.
        so_digitos = "".join(c for c in termo if c.isdigit())
        condicoes = [
            Lead.nome.ilike(f"%{termo}%"),
            Lead.email.ilike(f"%{termo}%"),
        ]
        if so_digitos:
            condicoes.append(Lead.phone_number.ilike(f"%{so_digitos}%"))
        base = base.where(or_(*condicoes))

    if etapa.strip():
        base = base.where(KanbanColumn.nome == etapa.strip())

    # A contagem vem da mesma consulta, sem as colunas: contar o resultado
    # paginado devolveria "50 de 50" para uma base de trezentos.
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar() or 0

    pagina_de = (
        base.order_by(Lead.data_criacao.desc())
        .offset((pagina - 1) * POR_PAGINA)
        .limit(POR_PAGINA)
    )

    agora = datetime.utcnow()
    clientes = [
        ClienteNaLista(
            lead_id=lead.id,
            nome=lead.nome,
            phone_number=lead.phone_number,
            email=lead.email,
            empresa=_do_bloco(detalhes, "empresa"),
            cargo=_do_bloco(detalhes, "cargo"),
            score_qualificacao=detalhes.score_qualificacao if detalhes else 0,
            etapa=coluna,
            dias_parado=_dias(card.data_movimentacao if card else None, agora),
            data_criacao=lead.data_criacao,
            conversation_id=conversation_id,
        )
        for lead, detalhes, card, coluna, conversation_id in await db.execute(pagina_de)
    ]

    logger.info(
        f"👥 {total} contato(s) no agente {agent_id}"
        + (f" para a busca {termo!r}" if termo else "")
    )

    return ClientesResponse(
        agent_id=agent_id,
        total=total,
        pagina=pagina,
        por_pagina=POR_PAGINA,
        clientes=clientes,
    )
