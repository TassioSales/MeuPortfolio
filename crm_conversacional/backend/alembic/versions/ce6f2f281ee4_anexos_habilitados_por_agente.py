"""anexos habilitados por agente

Revision ID: ce6f2f281ee4
Revises: 126ed7e48b1b
Create Date: 2026-08-13 13:44:55.057364

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce6f2f281ee4'
down_revision: Union[str, None] = '126ed7e48b1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `server_default` é obrigatório aqui, e o autogenerate não o põe.
    #
    # `NOT NULL` sem default em tabela que já tem linhas é erro na hora do
    # ALTER: o Postgres não sabe o que escrever nos agentes existentes. Com o
    # default, cada um deles nasce com anexos desligados — que é a escolha
    # certa: ninguém liga leitura de documento sem saber.
    op.add_column(
        'agents',
        sa.Column(
            'anexos_habilitados',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column('agents', 'anexos_habilitados')
