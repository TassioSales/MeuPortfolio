"""
Quanto vale o que entrou, e de onde veio.

As métricas contavam gente: atendimentos, leads, taxa de qualificação. Um
escritório não vive de quantidade de conversa — vive do tamanho das causas que
consegue. Dois meses com o mesmo número de leads podem valer dez vezes um ao
outro, e o painel dizia que eram iguais.

Três leituras, todas em cima do que o parecer já estima:

- **por dia** — o valor entrando ao longo do tempo, para ver se a curva sobe;
- **por porte** — quantos casos grandes contra quantos pequenos, porque a
  média esconde: dez causas de mil e uma de cem mil dão a mesma média que
  onze de dez mil, e não são o mesmo escritório;
- **por UF** — de onde vem o dinheiro, para decidir onde anunciar.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db_session
from app.db.models import Agent, Caso, Conversation, Lead
from app.utils.auth_middleware import get_current_user
from app.utils.ddd import uf_do_telefone
from app.utils.exceptions import NotFoundException
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["valor"])

# Onde ficam as fronteiras de porte.
#
# Saem do piso comercial que o escritório já configurou (`CASO_VALOR_MINIMO`),
# e não de números redondos inventados aqui: abaixo do piso é o caso que não
# paga o trabalho, e "grande" é cinco vezes isso. Assim as faixas acompanham a
# decisão do escritório em vez de contradizê-la.
MULTIPLO_DO_GRANDE = 5


class ValorPorDia(BaseModel):
    data: str
    casos: int
    # A faixa somada. Duas colunas e não uma média: o parecer estima faixa
    # porque não tem documento, e achatar isso numa média inventa precisão.
    total_min: int
    total_max: int


class PortePorFaixa(BaseModel):
    porte: str
    rotulo: str
    casos: int
    total_min: int
    total_max: int


class ValorPorUF(BaseModel):
    uf: str
    leads: int
    casos_dimensionados: int
    total_max: int


class ValorResponse(BaseModel):
    agent_id: str
    dias: int
    casos_dimensionados: int
    # Casos sem faixa: o parecer não conseguiu, ou ainda não rodou. Aparecem
    # no número para a soma não parecer o total quando não é.
    casos_sem_valor: int
    total_min: int
    total_max: int
    por_dia: List[ValorPorDia]
    por_porte: List[PortePorFaixa]
    por_uf: List[ValorPorUF]


def _porte(valor_max: Optional[int], piso: int) -> str:
    if valor_max is None:
        return "indeterminado"
    if valor_max < piso:
        return "baixo"
    if valor_max < piso * MULTIPLO_DO_GRANDE:
        return "medio"
    return "alto"


@router.get("/agents/{agent_id}/metrics/valor", response_model=ValorResponse)
async def valor(
    agent_id: str,
    dias: int = Query(30, ge=1, le=365),
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    O valor estimado que entrou no período.

    É estimativa de parecer preliminar, sem documento na mão — serve para
    comparar períodos e campanhas, não para prometer nada a ninguém.
    """
    existe = await db.execute(select(Agent.id).where(Agent.id == agent_id))
    if existe.scalars().first() is None:
        raise NotFoundException("Agent")

    corte = datetime.utcnow() - timedelta(days=dias)
    piso = settings.caso_valor_minimo

    linhas = (
        await db.execute(
            select(Caso, Lead.phone_number)
            .join(Lead, Lead.id == Caso.lead_id)
            .join(Conversation, Conversation.id == Lead.conversation_id)
            .where(Conversation.agent_id == agent_id)
            .where(Caso.data_abertura >= corte)
        )
    ).all()

    por_dia: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"casos": 0, "min": 0, "max": 0}
    )
    por_porte: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"casos": 0, "min": 0, "max": 0}
    )
    por_uf: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"leads": 0, "dimensionados": 0, "max": 0}
    )

    total_min = total_max = 0
    dimensionados = sem_valor = 0

    for caso, telefone in linhas:
        minimo = caso.valor_estimado_min or 0
        maximo = caso.valor_estimado_max or 0
        tem_valor = caso.valor_estimado_max is not None

        if tem_valor:
            dimensionados += 1
            total_min += minimo
            total_max += maximo
        else:
            sem_valor += 1

        dia = (caso.data_abertura or datetime.utcnow()).strftime("%Y-%m-%d")
        por_dia[dia]["casos"] += 1
        por_dia[dia]["min"] += minimo
        por_dia[dia]["max"] += maximo

        faixa = _porte(caso.valor_estimado_max, piso)
        por_porte[faixa]["casos"] += 1
        por_porte[faixa]["min"] += minimo
        por_porte[faixa]["max"] += maximo

        # Telefone de fora do Brasil, ou DDD que não existe, entra em
        # "desconhecido" — melhor do que sumir da soma e fazer as partes não
        # baterem com o total.
        uf = uf_do_telefone(telefone) or "??"
        por_uf[uf]["leads"] += 1
        if tem_valor:
            por_uf[uf]["dimensionados"] += 1
            por_uf[uf]["max"] += maximo

    ROTULOS = {
        "alto": f"Acima de R$ {piso * MULTIPLO_DO_GRANDE:,}".replace(",", "."),
        "medio": f"R$ {piso:,} a R$ {piso * MULTIPLO_DO_GRANDE:,}".replace(",", "."),
        "baixo": f"Abaixo de R$ {piso:,}".replace(",", "."),
        "indeterminado": "Sem estimativa",
    }

    logger.info(
        f"💵 Valor do agente {agent_id}: {dimensionados} caso(s) dimensionado(s), "
        f"até R$ {total_max}"
    )

    return ValorResponse(
        agent_id=agent_id,
        dias=dias,
        casos_dimensionados=dimensionados,
        casos_sem_valor=sem_valor,
        total_min=total_min,
        total_max=total_max,
        por_dia=[
            ValorPorDia(data=d, casos=v["casos"], total_min=v["min"], total_max=v["max"])
            for d, v in sorted(por_dia.items())
        ],
        # Ordem fixa do maior para o menor, e não por contagem: o board precisa
        # ser lido sempre na mesma sequência para comparar meses de relance.
        por_porte=[
            PortePorFaixa(
                porte=p,
                rotulo=ROTULOS[p],
                casos=por_porte[p]["casos"],
                total_min=por_porte[p]["min"],
                total_max=por_porte[p]["max"],
            )
            for p in ("alto", "medio", "baixo", "indeterminado")
        ],
        por_uf=sorted(
            (
                ValorPorUF(
                    uf=uf,
                    leads=v["leads"],
                    casos_dimensionados=v["dimensionados"],
                    total_max=v["max"],
                )
                for uf, v in por_uf.items()
            ),
            key=lambda x: (-x.total_max, -x.leads, x.uf),
        ),
    )
