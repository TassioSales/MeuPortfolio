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
#
# As colunas são o fluxo do escritório, não estados genéricos de CRM.
# "Lead Qualificado" dizia o que o software achava; "Viabilidade" diz o que
# alguém precisa fazer com o caso. A diferença aparece no uso: um board de
# estados é lido, um board de tarefas é trabalhado.
#
# Só as três primeiras são automáticas — é até onde a IA vai. Da quarta em
# diante quem arrasta é gente, e é por isso que elas existem: sem uma coluna
# para "coletando documento" o caso ficava parado em "Qualificado" por duas
# semanas parecendo que ninguém tinha feito nada.
#
# As cores: as cinco primeiras vêm do conjunto que já estava validado; as
# duas novas (#86b6ef e #104281) saem de `FUNNEL_RAMP` em
# `frontend/components/charts/theme.ts`, validadas contra a mesma superfície.
COLUNAS_PADRAO: List[Tuple[str, str, str]] = [
    ("Closer", "novo", "#3164ff"),
    ("Entrevista", "em_qualificacao", "#5598e7"),
    ("Viabilidade", "qualificado", "#16a34a"),
    ("Coleta de documentos", "agendado", "#eda100"),
    ("Saneamento", "saneamento", "#86b6ef"),
    ("Revisão", "revisao", "#104281"),
    ("Arquivado", "arquivado", "#52514e"),
]

# Como as colunas se chamavam antes, para a migração e para quem for ler o
# histórico do banco e não entender por que os nomes mudaram.
NOMES_ANTIGOS: List[Tuple[str, str]] = [
    ("Novo Lead", "Closer"),
    ("Em Qualificação", "Entrevista"),
    ("Lead Qualificado", "Viabilidade"),
    ("Agendado", "Coleta de documentos"),
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
