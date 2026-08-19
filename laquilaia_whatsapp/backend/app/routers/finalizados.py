"""
Os casos que acabaram, separados pelo motivo.

Tudo cai em "Arquivado", e o board não diz por quê. Mas "não era da nossa
área" e "o caso é pequeno demais para compensar" pedem coisas opostas do
escritório: o primeiro é volume de marketing errado — gente chegando pelo
anúncio errado —, o segundo é o piso comercial funcionando como devia. Um
número só some com essa diferença.

Os motivos não são um campo novo: saem do que o parecer já grava. Inventar
uma coluna "motivo do arquivamento" para alguém preencher à mão daria um
campo vazio em 90% das linhas — é o que os contadores zerados do produto
concorrente mostram acontecer.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.models import Agent, Caso, Conversation, Lead, LeadTimeline, User
from app.utils.auth_middleware import get_current_user
from app.utils.exceptions import NotFoundException
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["finalizados"])

Motivo = Literal["abaixo_do_piso", "fora_da_area", "sem_retorno", "outro"]

# A ordem é a de precedência ao classificar, e também a de exibição.
MOTIVOS: Dict[Motivo, str] = {
    "abaixo_do_piso": "Abaixo do piso",
    "fora_da_area": "Fora da área",
    "sem_retorno": "Sem retorno",
    "outro": "Outro",
}

AREA_DO_ESCRITORIO = "trabalhista"


class CasoFinalizado(BaseModel):
    lead_id: str
    nome: Optional[str] = None
    phone_number: str
    empresa_ou_resumo: Optional[str] = None
    valor_estimado_min: Optional[int] = None
    valor_estimado_max: Optional[int] = None
    arquivado_em: Optional[datetime] = None
    # Quem arquivou, quando foi gente. Nulo = foi a triagem.
    arquivado_por: Optional[str] = None


class GrupoFinalizado(BaseModel):
    motivo: Motivo
    rotulo: str
    total: int
    casos: List[CasoFinalizado]


class FinalizadosResponse(BaseModel):
    agent_id: str
    dias: int
    total: int
    grupos: List[GrupoFinalizado]


def _classificar(caso: Optional[Caso]) -> Motivo:
    """
    Por que este caso acabou.

    Sem caso nenhum é `sem_retorno`: o contato foi arquivado antes de a
    triagem conseguir dimensionar qualquer coisa — na prática, a pessoa parou
    de responder. Não é o mesmo que caso inviável, e tratar os dois como um só
    esconderia justamente a métrica que diz se o atendimento está perdendo
    gente no meio da conversa.

    `indeterminado` cai em "outro" de propósito. O parecer não conseguiu
    dimensionar, e chamar isso de "abaixo do piso" seria pôr na conta do valor
    do caso o que foi limitação da análise.
    """
    if caso is None:
        return "sem_retorno"
    if caso.viabilidade == "abaixo_do_piso":
        return "abaixo_do_piso"
    if caso.viabilidade == "nao_se_aplica" or (
        caso.area and caso.area != AREA_DO_ESCRITORIO
    ):
        return "fora_da_area"
    return "outro"


@router.get("/agents/{agent_id}/finalizados", response_model=FinalizadosResponse)
async def finalizados(
    agent_id: str,
    dias: int = Query(90, ge=1, le=365),
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Os leads arquivados no período, agrupados pelo motivo."""
    existe = await db.execute(select(Agent.id).where(Agent.id == agent_id))
    if existe.scalars().first() is None:
        raise NotFoundException("Agent")

    desde = datetime.utcnow() - timedelta(days=dias)

    leads = (
        await db.execute(
            select(Lead)
            .join(Conversation, Conversation.id == Lead.conversation_id)
            .where(Conversation.agent_id == agent_id)
            .where(Lead.status_funil == "arquivado")
            .where(Lead.data_atualizacao >= desde)
            .order_by(Lead.data_atualizacao.desc())
        )
    ).scalars().all()

    if not leads:
        return FinalizadosResponse(
            agent_id=agent_id, dias=dias, total=0,
            grupos=[GrupoFinalizado(motivo=m, rotulo=r, total=0, casos=[])
                    for m, r in MOTIVOS.items()],
        )

    ids = [lead.id for lead in leads]

    # O caso mais recente de cada lead, em uma consulta.
    caso_do_lead: Dict[str, Caso] = {}
    for caso in (
        await db.execute(
            select(Caso).where(Caso.lead_id.in_(ids)).order_by(Caso.data_abertura.desc())
        )
    ).scalars().all():
        caso_do_lead.setdefault(caso.lead_id, caso)

    # E quem arquivou, quando foi gente.
    quem_arquivou: Dict[str, str] = {}
    for lead_id, nome in (
        await db.execute(
            select(LeadTimeline.lead_id, User.nome)
            .join(User, User.id == LeadTimeline.mudado_por)
            .where(LeadTimeline.lead_id.in_(ids))
            .where(LeadTimeline.status_novo == "arquivado")
            .order_by(LeadTimeline.timestamp.desc())
        )
    ).all():
        quem_arquivou.setdefault(lead_id, nome)

    por_motivo: Dict[Motivo, List[CasoFinalizado]] = {m: [] for m in MOTIVOS}
    for lead in leads:
        caso = caso_do_lead.get(lead.id)
        por_motivo[_classificar(caso)].append(
            CasoFinalizado(
                lead_id=lead.id,
                nome=lead.nome,
                phone_number=lead.phone_number,
                empresa_ou_resumo=(caso.resumo if caso else None),
                valor_estimado_min=(caso.valor_estimado_min if caso else None),
                valor_estimado_max=(caso.valor_estimado_max if caso else None),
                arquivado_em=lead.data_atualizacao,
                arquivado_por=quem_arquivou.get(lead.id),
            )
        )

    logger.info(f"🗄️ {len(leads)} caso(s) finalizado(s) no agente {agent_id}")

    return FinalizadosResponse(
        agent_id=agent_id,
        dias=dias,
        total=len(leads),
        grupos=[
            GrupoFinalizado(motivo=m, rotulo=r, total=len(por_motivo[m]), casos=por_motivo[m])
            for m, r in MOTIVOS.items()
        ],
    )
