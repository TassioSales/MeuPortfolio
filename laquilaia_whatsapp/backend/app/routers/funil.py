"""
O funil: quantos chegaram, quantos avançaram, onde param.

As métricas que já existiam contam volume — atendimentos, taxa de
qualificação, tempo de resposta. Nenhuma delas responde a pergunta que o dono
do escritório faz: **de cada cem que escrevem, quantos viram caso?** E,
principalmente: entre quais duas etapas eles somem.

A conta é cumulativa e sai da posição atual do card, sem precisar de
histórico: as colunas são ordenadas, e um lead que está em "Revisão"
necessariamente passou por "Closer". Então "quantos chegaram à etapa N" é
"quantos estão em N ou depois".

Arquivado fica **fora** dessa cadeia, e isso não é detalhe: um lead arquivado
direto do primeiro contato não passou por etapa nenhuma. Contá-lo como
"chegou até o fim" inverteria o sinal do funil — o escritório leria como
sucesso o que é descarte.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.models import (
    Agent,
    Conversation,
    KanbanCard,
    KanbanColumn,
    Lead,
    Message,
)
from app.utils.auth_middleware import get_current_user
from app.utils.exceptions import NotFoundException
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["funil"])

# A coluna terminal. Sai da cadeia cumulativa pelo nome, do mesmo jeito que
# `lead_processor.COLUMN_MAPPING` já depende dos nomes — mudar o nome da
# coluna exige mudar aqui.
COLUNA_TERMINAL = "Arquivado"


class EtapaDoFunil(BaseModel):
    nome: str
    ordem: int
    # Quantos estão **nesta** coluna agora.
    parados_aqui: int
    # Quantos chegaram até aqui: os desta coluna mais os de todas as
    # seguintes. É o número do funil.
    chegaram: int
    # Sobre o topo — dá a forma do funil.
    percentual_do_topo: float
    # Sobre a etapa anterior — diz **onde** o funil aperta, que é a
    # informação acionável. O topo é sempre 100.
    conversao_da_etapa: float
    # Quantos destes tiveram alguém do escritório escrevendo na conversa.
    com_intervencao_humana: int


class FunilResponse(BaseModel):
    agent_id: str
    dias: Optional[int] = None
    total_de_leads: int
    arquivados: int
    etapas: List[EtapaDoFunil]


@router.get("/agents/{agent_id}/metrics/funil", response_model=FunilResponse)
async def funil_de_venda(
    agent_id: str,
    dias: int = Query(0, ge=0, le=365, description="0 = desde sempre"),
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    O funil do agente, etapa a etapa.

    `dias=0` é desde sempre, e é o padrão: um escritório com poucos leads por
    semana não tem funil nenhum em sete dias, e uma tela que mostra "0 de 0"
    por padrão parece quebrada.
    """
    existe = await db.execute(select(Agent.id).where(Agent.id == agent_id))
    if existe.scalars().first() is None:
        raise NotFoundException("Agent")

    colunas = (
        await db.execute(
            select(KanbanColumn)
            .where(KanbanColumn.agent_id == agent_id)
            .order_by(KanbanColumn.ordem)
        )
    ).scalars().all()

    filtros = [Conversation.agent_id == agent_id]
    if dias:
        filtros.append(Lead.data_criacao >= datetime.utcnow() - timedelta(days=dias))

    # Quantos leads em cada coluna, numa consulta.
    por_coluna = dict(
        (
            await db.execute(
                select(KanbanCard.column_id, func.count(distinct(Lead.id)))
                .join(Lead, Lead.id == KanbanCard.lead_id)
                .join(Conversation, Conversation.id == Lead.conversation_id)
                .where(*filtros)
                .group_by(KanbanCard.column_id)
            )
        ).all()
    )

    # E quantos, em cada coluna, tiveram gente do escritório escrevendo.
    #
    # O critério é a mensagem do operador, e não "conversa pausada": pausar é
    # intenção, escrever é o ato. Quem assumiu a conversa e não voltou aparece
    # no alerta de pendência, que é onde essa informação serve.
    com_humano = dict(
        (
            await db.execute(
                select(KanbanCard.column_id, func.count(distinct(Lead.id)))
                .join(Lead, Lead.id == KanbanCard.lead_id)
                .join(Conversation, Conversation.id == Lead.conversation_id)
                .join(Message, Message.conversation_id == Conversation.id)
                .where(*filtros, Message.remetente == "operador")
                .group_by(KanbanCard.column_id)
            )
        ).all()
    )

    pipeline = [c for c in colunas if c.nome != COLUNA_TERMINAL]
    arquivados = sum(
        por_coluna.get(c.id, 0) for c in colunas if c.nome == COLUNA_TERMINAL
    )

    # Cumulativo de trás para a frente: quem está em "Revisão" também chegou
    # a "Closer".
    chegaram: List[int] = []
    humanos: List[int] = []
    acumulado = 0
    acumulado_humano = 0
    for coluna in reversed(pipeline):
        acumulado += por_coluna.get(coluna.id, 0)
        acumulado_humano += com_humano.get(coluna.id, 0)
        chegaram.insert(0, acumulado)
        humanos.insert(0, acumulado_humano)

    topo = chegaram[0] if chegaram else 0

    etapas: List[EtapaDoFunil] = []
    for i, coluna in enumerate(pipeline):
        anterior = chegaram[i - 1] if i > 0 else 0
        etapas.append(
            EtapaDoFunil(
                nome=coluna.nome,
                ordem=coluna.ordem,
                parados_aqui=por_coluna.get(coluna.id, 0),
                chegaram=chegaram[i],
                # Divisão por zero é o caso normal de um funil vazio, não uma
                # anomalia: agente novo tem topo zero e a tela precisa abrir.
                percentual_do_topo=round(chegaram[i] / topo * 100, 1) if topo else 0.0,
                conversao_da_etapa=(
                    100.0 if i == 0 else (round(chegaram[i] / anterior * 100, 1) if anterior else 0.0)
                ),
                com_intervencao_humana=humanos[i],
            )
        )

    total = topo + arquivados
    logger.info(f"📉 Funil do agente {agent_id}: {total} lead(s), {arquivados} arquivado(s)")

    return FunilResponse(
        agent_id=agent_id,
        dias=dias or None,
        total_de_leads=total,
        arquivados=arquivados,
        etapas=etapas,
    )
