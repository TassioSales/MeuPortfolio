"""Colunas do Kanban viram o fluxo do escritório

Revision ID: f3c81b0d9a24
Revises: d1a4f7c92b30
Create Date: 2026-08-19

O board tinha estados genéricos de CRM — "Novo Lead", "Em Qualificação",
"Lead Qualificado", "Agendado". Eles diziam o que o software achava do lead.
As colunas novas dizem o que alguém precisa **fazer** com o caso, e é isso que
um board serve para mostrar.

Esta migração tem de conviver com dados de verdade: o escritório já tem
centenas de cards distribuídos pelas colunas antigas. Por isso ela **renomeia**
em vez de recriar — apagar e criar colunas levaria os cards junto pelo
`ondelete=CASCADE`, e o funil inteiro do escritório iria embora sem aviso.

Os dois nomes novos (Saneamento, Revisão) são inseridos, e "Arquivado" é
empurrado para o fim. `agendado` continua existindo como status: ele agora
aponta para "Coleta de documentos", que é o que o escritório faz depois de
marcar a conversa.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3c81b0d9a24"
down_revision: Union[str, None] = "d1a4f7c92b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (nome antigo, nome novo, ordem nova, cor). A cor é reafirmada porque o board
# antigo podia ter sido criado pelo `/columns/init` de antes da unificação,
# com hexes crus do Tailwind.
RENOMEACOES = [
    ("Novo Lead", "Closer", 0, "#3164ff"),
    ("Em Qualificação", "Entrevista", 1, "#5598e7"),
    ("Lead Qualificado", "Viabilidade", 2, "#16a34a"),
    ("Agendado", "Coleta de documentos", 3, "#eda100"),
]

# As que não existiam. Entram só onde já há board — agente sem coluna nenhuma
# é agente que nunca foi usado, e ele ganha o conjunto novo pelo
# `criar_colunas_padrao` quando for.
NOVAS = [
    ("Saneamento", 4, "#86b6ef"),
    ("Revisão", 5, "#104281"),
]

ARQUIVADO_ORDEM = 6


def upgrade() -> None:
    conexao = op.get_bind()

    for antigo, novo, ordem, cor in RENOMEACOES:
        conexao.execute(
            sa.text(
                "UPDATE kanban_columns SET nome = :novo, ordem = :ordem, "
                "cor_hex = :cor WHERE nome = :antigo"
            ),
            {"novo": novo, "ordem": ordem, "cor": cor, "antigo": antigo},
        )

    conexao.execute(
        sa.text(
            "UPDATE kanban_columns SET ordem = :ordem, cor_hex = :cor "
            "WHERE nome = 'Arquivado'"
        ),
        {"ordem": ARQUIVADO_ORDEM, "cor": "#52514e"},
    )

    # Um INSERT ... SELECT por coluna nova, para cada agente que já tem board.
    #
    # O `NOT EXISTS` é o que torna isto repetível: a tabela tem unicidade por
    # (agente, nome), e sem ele uma segunda execução — ou um banco onde
    # alguém já criou "Revisão" à mão — estouraria a migração inteira.
    #
    # Os `CAST` não são enfeite. Sem eles o asyncpg vê o mesmo `:nome` como
    # valor inserido e como comparação contra uma coluna, não consegue deduzir
    # um tipo só, e a migração morre com `AmbiguousParameterError` — ou seja,
    # o backend não sobe. E é `CAST(...)` e não `::text` porque o `::` colide
    # com a sintaxe de parâmetro do `text()` do SQLAlchemy.
    for nome, ordem, cor in NOVAS:
        conexao.execute(
            sa.text(
                """
                INSERT INTO kanban_columns (id, agent_id, nome, ordem, cor_hex, data_criacao)
                SELECT gen_random_uuid()::text, a.id, CAST(:nome AS text),
                       CAST(:ordem AS integer), CAST(:cor AS text), NOW()
                FROM agents a
                WHERE EXISTS (
                    SELECT 1 FROM kanban_columns c WHERE c.agent_id = a.id
                )
                AND NOT EXISTS (
                    SELECT 1 FROM kanban_columns c
                    WHERE c.agent_id = a.id AND c.nome = CAST(:nome AS text)
                )
                """
            ),
            {"nome": nome, "ordem": ordem, "cor": cor},
        )


def downgrade() -> None:
    """
    Devolve os nomes antigos e remove as duas colunas novas.

    Os cards que estiverem em Saneamento ou Revisão **voltam para
    Viabilidade** antes da remoção. Deixar o CASCADE agir apagaria o card — e
    com ele o lugar do lead no funil, que é trabalho de gente, não dado
    derivado.

    A ordem aqui importa e já mordeu uma vez: o resgate procura a coluna de
    destino pelo nome que ela tem **agora** ("Viabilidade"), não pelo nome
    para o qual ela ainda vai ser renomeada. Escrito na ordem errada, o
    `UPDATE` não casava com nada, o `DELETE` seguinte levava as colunas, e o
    `ondelete=CASCADE` levava os cards — perda silenciosa de dado num caminho
    que ninguém costuma exercitar.
    """
    conexao = op.get_bind()

    conexao.execute(
        sa.text(
            """
            UPDATE kanban_cards
            SET column_id = (
                SELECT destino.id FROM kanban_columns destino
                WHERE destino.agent_id = origem.agent_id
                  AND destino.nome = 'Viabilidade'
                LIMIT 1
            )
            FROM kanban_columns origem
            WHERE kanban_cards.column_id = origem.id
              AND origem.nome IN ('Saneamento', 'Revisão')
              AND EXISTS (
                  SELECT 1 FROM kanban_columns d
                  WHERE d.agent_id = origem.agent_id AND d.nome = 'Viabilidade'
              )
            """
        )
    )

    for antigo, novo, _ordem, _cor in RENOMEACOES:
        conexao.execute(
            sa.text("UPDATE kanban_columns SET nome = :antigo WHERE nome = :novo"),
            {"antigo": antigo, "novo": novo},
        )

    conexao.execute(
        sa.text("DELETE FROM kanban_columns WHERE nome IN ('Saneamento', 'Revisão')")
    )

    # A ordem antiga: Novo Lead 0 … Arquivado 4.
    for ordem, nome in enumerate(
        ["Novo Lead", "Em Qualificação", "Lead Qualificado", "Agendado", "Arquivado"]
    ):
        conexao.execute(
            sa.text("UPDATE kanban_columns SET ordem = :ordem WHERE nome = :nome"),
            {"ordem": ordem, "nome": nome},
        )
