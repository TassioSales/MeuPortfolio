"""Fase da conversa

Em que ponto do ciclo a conversa está: `triagem`, `coleta`, `contratado`.

Separada de `status` de propósito. `status` diz **quem responde** — ativa (a
IA), pausada (um humano assumiu), encerrada. `fase` diz **o que está sendo
perguntado**, e as duas variam juntas sem se implicar: uma conversa pausada
pode estar em coleta, e uma ativa pode já ter contrato assinado.

Revision ID: d5a17c093e2b
Revises: c9e2b83f41d7
Create Date: 2026-08-24 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d5a17c093e2b"
down_revision: Union[str, None] = "c9e2b83f41d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `server_default` porque a coluna é NOT NULL numa tabela com linhas: sem
    # ele o Postgres não sabe o que escrever nas conversas que já existem, e o
    # ALTER falha. O `default=` do SQLAlchemy só vale para linha nova —
    # armadilha já anotada no CLAUDE.md.
    #
    # E `triagem` é o valor certo para o histórico: toda conversa anterior a
    # esta migração aconteceu quando só havia triagem.
    op.add_column(
        "conversations",
        sa.Column(
            "fase", sa.String(length=20), nullable=False, server_default="triagem"
        ),
    )


def downgrade() -> None:
    op.drop_column("conversations", "fase")
