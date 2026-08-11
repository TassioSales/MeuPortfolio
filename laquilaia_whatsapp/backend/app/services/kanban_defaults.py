"""
As colunas padrão do funil, em um lugar só.

Havia duas definições divergentes: o seed usava a paleta validada e começava
a ordem em zero; o `POST /kanban/columns/init` usava hexes crus do Tailwind e
começava em um. Quem criasse agente pela tela ficava com um board de cores que
nunca passaram pelo validador de contraste e daltonismo, diferente do de quem
rodou o seed.

As cores são as de `frontend/components/charts/theme.ts` — não troque um hex
sem revalidar o conjunto.
"""

from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KanbanColumn
from app.utils.logger import logger


# (nome exibido, status do funil, cor). O nome é o que `lead_processor`
# procura ao mover o card, via COLUMN_MAPPING — mudar aqui exige mudar lá.
COLUNAS_PADRAO: List[Tuple[str, str, str]] = [
    ("Novo Lead", "novo", "#3164ff"),
    ("Em Qualificação", "em_qualificacao", "#5598e7"),
    ("Lead Qualificado", "qualificado", "#16a34a"),
    ("Agendado", "agendado", "#eda100"),
    ("Arquivado", "arquivado", "#52514e"),
]


async def criar_colunas_padrao(agent_id: str, db: AsyncSession) -> int:
    """
    Cria as colunas do funil para um agente, se ele ainda não tiver nenhuma.

    Não faz commit: quem chama decide o momento, porque na criação do agente
    isto entra na mesma transação.

    Returns:
        Quantas colunas foram criadas (zero se já existiam).
    """
    resultado = await db.execute(
        select(func.count(KanbanColumn.id)).where(KanbanColumn.agent_id == agent_id)
    )
    if resultado.scalar():
        logger.debug(f"⏭️ Agente {agent_id} já tem colunas de Kanban")
        return 0

    for ordem, (nome, _status, cor) in enumerate(COLUNAS_PADRAO):
        db.add(
            KanbanColumn(agent_id=agent_id, nome=nome, ordem=ordem, cor_hex=cor)
        )

    await db.flush()
    return len(COLUNAS_PADRAO)
