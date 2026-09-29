"""
Quanto custa cada lead, e cada lead qualificado.

É o único número que diz se o sistema se paga. E é o número que o painel não
tinha: havia volume (quantos atendimentos), conversão (quantos viraram caso) e
nenhum custo — então "vale a pena?" só tinha resposta no chute.

O gasto com anúncio entra à mão, porque só o escritório sabe. O consumo de IA
**não**: ele está em `messages.tokens_usados` e é somado aqui. Pedir os dois
digitados é o que o produto concorrente faz, e o resultado aparece nos prints
dele — o campo fica em branco para sempre.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.models import (
    Agent,
    Conversation,
    LancamentoMarketing,
    Lead,
    LeadDetails,
    Message,
    User,
)
from app.utils.auth_middleware import get_current_user, require_admin
from app.utils.exceptions import NotFoundException
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["marketing"])

# Score a partir do qual a triagem considera o lead qualificado. É o mesmo
# corte que `metrics_service` usa; mudar num lugar sem mudar no outro faria
# duas telas darem números diferentes para a mesma pergunta.
SCORE_QUALIFICADO = 70


class LancamentoBase(BaseModel):
    data: date
    # Em reais na API, centavos no banco. Quem digita pensa em reais; quem
    # soma precisa de inteiro.
    investimento_ads: float = Field(ge=0, le=10_000_000)
    observacao: Optional[str] = Field(default=None, max_length=500)


class LancamentoResponse(LancamentoBase):
    id: str
    criado_por: Optional[str] = None


class ResumoResponse(BaseModel):
    agent_id: str
    dias: int
    investimento_ads: float
    tokens_consumidos: int
    leads: int
    leads_qualificados: int
    # `None` quando não houve lead: dividir por zero daria "infinito", e um
    # painel que mostra ∞ como custo é um painel que ninguém acredita.
    custo_por_lead: Optional[float] = None
    custo_por_lead_qualificado: Optional[float] = None


def _reais(centavos: int) -> float:
    return round(centavos / 100, 2)


@router.get("/marketing/lancamentos", response_model=List[LancamentoResponse])
async def listar_lancamentos(
    dias: int = Query(90, ge=1, le=1095),
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Os gastos lançados, do mais recente para o mais antigo."""
    desde = date.today() - timedelta(days=dias)
    linhas = await db.execute(
        select(LancamentoMarketing, User.nome)
        .outerjoin(User, User.id == LancamentoMarketing.criado_por)
        .where(LancamentoMarketing.data >= desde)
        .order_by(LancamentoMarketing.data.desc())
    )
    return [
        LancamentoResponse(
            id=lancamento.id,
            data=lancamento.data,
            investimento_ads=_reais(lancamento.investimento_ads_centavos),
            observacao=lancamento.observacao,
            criado_por=nome,
        )
        for lancamento, nome in linhas
    ]


@router.post(
    "/marketing/lancamentos",
    response_model=LancamentoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_lancamento(
    dados: LancamentoBase,
    admin_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Lança um gasto. Só administrador — é dinheiro do escritório.

    Os reais viram centavos aqui, com `round` antes do `int`: `int(19.99 *
    100)` é 1998 em ponto flutuante, e um centavo perdido por lançamento vira
    conta que não fecha com o extrato no fim do mês.
    """
    lancamento = LancamentoMarketing(
        data=dados.data,
        investimento_ads_centavos=int(round(dados.investimento_ads * 100)),
        observacao=(dados.observacao or "").strip() or None,
        criado_por=admin_id,
    )
    db.add(lancamento)
    await db.commit()
    await db.refresh(lancamento)

    quem = (
        await db.execute(select(User.nome).where(User.id == admin_id))
    ).scalars().first()

    logger.info(f"💰 Lançamento de marketing: {dados.data} R$ {dados.investimento_ads}")
    return LancamentoResponse(
        id=lancamento.id,
        data=lancamento.data,
        investimento_ads=_reais(lancamento.investimento_ads_centavos),
        observacao=lancamento.observacao,
        criado_por=quem,
    )


@router.delete("/marketing/lancamentos/{lancamento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def apagar_lancamento(
    lancamento_id: str,
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Apaga um lançamento — digitar 1900 no lugar de 190 tem de ter conserto."""
    lancamento = (
        await db.execute(
            select(LancamentoMarketing).where(LancamentoMarketing.id == lancamento_id)
        )
    ).scalars().first()

    if lancamento is None:
        raise NotFoundException("Lançamento")

    await db.delete(lancamento)
    await db.commit()


@router.get("/agents/{agent_id}/marketing/resumo", response_model=ResumoResponse)
async def resumo(
    agent_id: str,
    dias: int = Query(30, ge=1, le=365),
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Quanto custou trazer cada pessoa, e cada pessoa que virou caso.

    O custo por lead **qualificado** é o número que decide: um anúncio pode
    trazer cem pessoas baratas e nenhuma da área, e ainda assim parecer
    excelente no custo por lead.
    """
    existe = await db.execute(select(Agent.id).where(Agent.id == agent_id))
    if existe.scalars().first() is None:
        raise NotFoundException("Agent")

    corte = datetime.utcnow() - timedelta(days=dias)

    centavos = (
        await db.execute(
            select(func.coalesce(func.sum(LancamentoMarketing.investimento_ads_centavos), 0))
            .where(LancamentoMarketing.data >= corte.date())
        )
    ).scalar() or 0

    tokens = (
        await db.execute(
            select(func.coalesce(func.sum(Message.tokens_usados), 0))
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Conversation.agent_id == agent_id)
            .where(Message.timestamp >= corte)
        )
    ).scalar() or 0

    leads = (
        await db.execute(
            select(func.count(Lead.id))
            .join(Conversation, Conversation.id == Lead.conversation_id)
            .where(Conversation.agent_id == agent_id)
            .where(Lead.data_criacao >= corte)
        )
    ).scalar() or 0

    qualificados = (
        await db.execute(
            select(func.count(Lead.id))
            .join(Conversation, Conversation.id == Lead.conversation_id)
            .join(LeadDetails, LeadDetails.lead_id == Lead.id)
            .where(Conversation.agent_id == agent_id)
            .where(Lead.data_criacao >= corte)
            .where(LeadDetails.score_qualificacao >= SCORE_QUALIFICADO)
        )
    ).scalar() or 0

    investido = _reais(centavos)

    logger.info(
        f"💰 Resumo do agente {agent_id}: R$ {investido}, {leads} lead(s), "
        f"{qualificados} qualificado(s)"
    )

    return ResumoResponse(
        agent_id=agent_id,
        dias=dias,
        investimento_ads=investido,
        tokens_consumidos=int(tokens),
        leads=leads,
        leads_qualificados=qualificados,
        custo_por_lead=round(investido / leads, 2) if leads else None,
        custo_por_lead_qualificado=(
            round(investido / qualificados, 2) if qualificados else None
        ),
    )
