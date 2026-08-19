"""
Os retornos combinados com o cliente.

"Te ligo amanhã às 15h" era dito na conversa e morria ali. Virava um
compromisso que só existia na cabeça de quem prometeu — e o cliente ficava
esperando a ligação que ninguém marcou em lugar nenhum.

A tela separa por urgência, e o grupo que existe por causa disso é
**atrasado**: retorno cuja hora passou e ninguém fechou. É o mesmo defeito
que a faixa de pendências trata nas conversas — omissão que não aparece em
lugar nenhum até o cliente reclamar.
"""

from datetime import datetime, timedelta
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.models import Agendamento, Agent, Conversation, Lead, User
from app.utils.auth_middleware import get_current_user
from app.utils.exceptions import NotFoundException
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["agendamentos"])

Situacao = Literal["pendente", "realizado", "cancelado"]

# Janela em que dois agendamentos para o mesmo lead são o mesmo compromisso.
#
# Vem de um defeito observado no produto concorrente: três retornos para a
# mesma cliente, criados às 15:00, 15:03 e 15:06, todos marcados "realizado".
# Não eram três combinações — era o mesmo clique repetido. Uma agenda com
# duplicata deixa de ser agenda.
JANELA_DE_DUPLICATA = timedelta(minutes=10)


class NovoAgendamento(BaseModel):
    lead_id: str
    quando: datetime
    motivo: Optional[str] = Field(default=None, max_length=500)


class AgendamentoResponse(BaseModel):
    id: str
    lead_id: str
    lead_nome: Optional[str] = None
    phone_number: str
    quando: datetime
    motivo: Optional[str] = None
    status: Situacao
    # Nulo quando quem agendou foi a triagem.
    criado_por: Optional[str] = None
    # Positivo quando a hora já passou e o retorno continua pendente.
    minutos_de_atraso: int = 0


class MudarSituacao(BaseModel):
    status: Situacao


async def _agente_existe(agent_id: str, db: AsyncSession) -> None:
    resultado = await db.execute(select(Agent.id).where(Agent.id == agent_id))
    if resultado.scalars().first() is None:
        raise NotFoundException("Agent")


def _montar(agendamento: Agendamento, lead: Lead, quem: Optional[str], agora: datetime):
    atraso = 0
    if agendamento.status == "pendente" and agendamento.quando < agora:
        atraso = int((agora - agendamento.quando).total_seconds() // 60)

    return AgendamentoResponse(
        id=agendamento.id,
        lead_id=lead.id,
        lead_nome=lead.nome,
        phone_number=lead.phone_number,
        quando=agendamento.quando,
        motivo=agendamento.motivo,
        status=agendamento.status,
        criado_por=quem,
        minutos_de_atraso=atraso,
    )


@router.get("/agents/{agent_id}/agendamentos", response_model=List[AgendamentoResponse])
async def listar(
    agent_id: str,
    incluir_fechados: bool = Query(False),
    dias: int = Query(30, ge=1, le=365),
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Os retornos do agente, do mais atrasado para o mais distante.

    Fechados ficam de fora por padrão: o que a agenda precisa mostrar é o que
    ainda deve ser feito. Compromisso cumprido vira histórico, e histórico no
    meio da lista de tarefas esconde a tarefa.
    """
    await _agente_existe(agent_id, db)

    consulta = (
        select(Agendamento, Lead, User.nome)
        .join(Lead, Lead.id == Agendamento.lead_id)
        .join(Conversation, Conversation.id == Lead.conversation_id)
        .outerjoin(User, User.id == Agendamento.criado_por)
        .where(Conversation.agent_id == agent_id)
        .where(Agendamento.quando >= datetime.utcnow() - timedelta(days=dias))
        .order_by(Agendamento.quando)
    )

    if not incluir_fechados:
        consulta = consulta.where(Agendamento.status == "pendente")

    agora = datetime.utcnow()
    return [
        _montar(agendamento, lead, quem, agora)
        for agendamento, lead, quem in await db.execute(consulta)
    ]


@router.post(
    "/agents/{agent_id}/agendamentos",
    response_model=AgendamentoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar(
    agent_id: str,
    dados: NovoAgendamento,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Marca um retorno. Qualquer pessoa do escritório — quem combina é quem
    atende.

    Agendamento repetido para o mesmo lead na mesma janela de dez minutos é
    recusado: não são duas combinações, é o mesmo clique repetido, e uma
    agenda com duplicata deixa de ser agenda.
    """
    await _agente_existe(agent_id, db)

    lead = (
        await db.execute(
            select(Lead)
            .join(Conversation, Conversation.id == Lead.conversation_id)
            .where(Lead.id == dados.lead_id)
            .where(Conversation.agent_id == agent_id)
        )
    ).scalars().first()

    if lead is None:
        raise NotFoundException("Lead")

    repetido = (
        await db.execute(
            select(Agendamento.id)
            .where(Agendamento.lead_id == lead.id)
            .where(Agendamento.status == "pendente")
            .where(Agendamento.quando >= dados.quando - JANELA_DE_DUPLICATA)
            .where(Agendamento.quando <= dados.quando + JANELA_DE_DUPLICATA)
        )
    ).scalars().first()

    if repetido:
        # 409 e não 422: o corpo da requisição está correto: o problema é o
        # estado do servidor. A tela precisa dessa diferença para dizer "já
        # está marcado" em vez de "dado inválido", que mandaria a pessoa
        # conferir o que ela digitou certo.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um retorno marcado para este contato nesse horário.",
        )

    agendamento = Agendamento(
        lead_id=lead.id,
        quando=dados.quando,
        motivo=(dados.motivo or "").strip() or None,
        criado_por=user_id,
        status="pendente",
    )
    db.add(agendamento)
    await db.commit()
    await db.refresh(agendamento)

    quem = (await db.execute(select(User.nome).where(User.id == user_id))).scalars().first()
    logger.info(f"📅 Retorno marcado para {lead.phone_number} em {dados.quando}")
    return _montar(agendamento, lead, quem, datetime.utcnow())


@router.patch("/agendamentos/{agendamento_id}", response_model=AgendamentoResponse)
async def mudar_situacao(
    agendamento_id: str,
    dados: MudarSituacao,
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Marca como realizado ou cancelado — ou devolve para pendente."""
    linha = (
        await db.execute(
            select(Agendamento, Lead, User.nome)
            .join(Lead, Lead.id == Agendamento.lead_id)
            .outerjoin(User, User.id == Agendamento.criado_por)
            .where(Agendamento.id == agendamento_id)
        )
    ).first()

    if linha is None:
        raise NotFoundException("Agendamento")

    agendamento, lead, quem = linha
    agendamento.status = dados.status
    await db.commit()
    await db.refresh(agendamento)

    return _montar(agendamento, lead, quem, datetime.utcnow())
