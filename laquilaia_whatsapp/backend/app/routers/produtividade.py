"""
O que gente fez, e quem fez.

Nos prints do produto concorrente esta tela existe e está vazia: todo card diz
"Sem responsável", e o ranking mostra uma pessoa com zero concluídas. Não é
defeito de tela — é que lá ninguém registra quem agiu.

Aqui dá para preencher porque a trilha (`lead_timeline`) passou a gravar cada
ação humana: card arrastado, conversa assumida, conversa devolvida. Antes ela
só registrava movimento da IA, e uma tela destas seria igualmente vazia.

O número que importa não é o total de ações — é a **razão entre o que a IA
resolveu sozinha e o que precisou de gente**. Ela responde se o agente está
trabalhando ou se virou um formulário caro que alguém preenche à mão.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.models import Agent, Conversation, Lead, LeadTimeline, User
from app.utils.auth_middleware import get_current_user
from app.utils.exceptions import NotFoundException
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["produtividade"])

# Como os motivos gravados na trilha viram categorias de trabalho. A
# correspondência é por trecho porque o motivo é texto livre — ver
# `kanban.move_lead_card` e `chat._set_conversation_status`.
CATEGORIAS = (
    ("assumiu", "Humano assumiu"),
    ("devolvida", "Conversa devolvida"),
    ("Movido para", "Movido no Kanban"),
)


class PessoaProdutiva(BaseModel):
    nome: str
    acoes: int
    conversas_assumidas: int
    conversas_devolvidas: int
    cards_movidos: int
    # Quantos contatos diferentes ela tocou — quinze ações num lead só não é
    # o mesmo trabalho que uma ação em quinze leads.
    leads_atendidos: int


class ProdutividadeResponse(BaseModel):
    agent_id: str
    dias: int
    acoes_de_gente: int
    acoes_da_ia: int
    # De 0 a 100. Quanto maior, mais o escritório está empurrando o funil à
    # mão — e menos o agente está resolvendo.
    percentual_humano: float
    pessoas: List[PessoaProdutiva]


@router.get("/agents/{agent_id}/metrics/produtividade", response_model=ProdutividadeResponse)
async def produtividade(
    agent_id: str,
    dias: int = Query(30, ge=1, le=365),
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Quem do escritório mexeu em quê, no período.

    Só conta o que ficou registrado na trilha. Ligação feita pelo celular e
    conversa no corredor não entram — e não há como entrarem, então a tela
    não pretende medir esforço, e sim o que passou pelo sistema.

    **Limitação conhecida:** apagar um usuário do banco anula o `mudado_por`
    das ações dele (`ondelete=SET NULL`), e a partir daí elas contam como se
    fossem da IA. O painel não apaga usuário — ele desativa, e conta
    desativada mantém o histórico intacto —, então isso só acontece por
    `DELETE` manual. Preservar o nome exigiria gravá-lo junto de cada linha da
    trilha, e não vale a duplicação por um caminho que o produto não oferece.
    """
    existe = await db.execute(select(Agent.id).where(Agent.id == agent_id))
    if existe.scalars().first() is None:
        raise NotFoundException("Agent")

    corte = datetime.utcnow() - timedelta(days=dias)

    linhas = (
        await db.execute(
            select(LeadTimeline, User.nome)
            .join(Lead, Lead.id == LeadTimeline.lead_id)
            .join(Conversation, Conversation.id == Lead.conversation_id)
            .outerjoin(User, User.id == LeadTimeline.mudado_por)
            .where(Conversation.agent_id == agent_id)
            .where(LeadTimeline.timestamp >= corte)
        )
    ).all()

    por_pessoa: Dict[str, Dict[str, object]] = defaultdict(
        lambda: {
            "acoes": 0,
            "assumidas": 0,
            "devolvidas": 0,
            "movidos": 0,
            "leads": set(),
        }
    )
    da_ia = 0

    for evento, nome in linhas:
        if evento.mudado_por is None:
            da_ia += 1
            continue

        registro = por_pessoa[nome]
        registro["acoes"] += 1
        registro["leads"].add(evento.lead_id)

        motivo = evento.motivo or ""
        if CATEGORIAS[0][0] in motivo:
            registro["assumidas"] += 1
        elif CATEGORIAS[1][0] in motivo:
            registro["devolvidas"] += 1
        elif CATEGORIAS[2][0] in motivo:
            registro["movidos"] += 1

    de_gente = sum(int(r["acoes"]) for r in por_pessoa.values())
    total = de_gente + da_ia

    logger.info(
        f"👷 Produtividade do agente {agent_id}: {de_gente} ação(ões) de gente, "
        f"{da_ia} da IA"
    )

    return ProdutividadeResponse(
        agent_id=agent_id,
        dias=dias,
        acoes_de_gente=de_gente,
        acoes_da_ia=da_ia,
        # Sem ação nenhuma o percentual é zero, e não uma divisão por zero:
        # período vazio é o estado normal de um escritório que não abriu.
        percentual_humano=round(de_gente / total * 100, 1) if total else 0.0,
        pessoas=sorted(
            (
                PessoaProdutiva(
                    nome=nome,
                    acoes=int(r["acoes"]),
                    conversas_assumidas=int(r["assumidas"]),
                    conversas_devolvidas=int(r["devolvidas"]),
                    cards_movidos=int(r["movidos"]),
                    leads_atendidos=len(r["leads"]),  # type: ignore[arg-type]
                )
                for nome, r in por_pessoa.items()
            ),
            key=lambda p: (-p.acoes, p.nome),
        ),
    )
