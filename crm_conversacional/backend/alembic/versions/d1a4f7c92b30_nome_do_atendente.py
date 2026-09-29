"""nome do atendente por agente

Revision ID: d1a4f7c92b30
Revises: ce6f2f281ee4
Create Date: 2026-08-18 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1a4f7c92b30'
down_revision: Union[str, None] = 'ce6f2f281ee4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nulo de propósito, e sem `server_default`.
    #
    # Ao contrário de `anexos_habilitados`, aqui não há valor certo para os
    # agentes que já existem: inventar um nome para todos eles faria o
    # atendimento se apresentar com nome que o escritório nunca escolheu.
    # Vazio é estado válido — o agente se apresenta como o escritório.
    op.add_column(
        'agents',
        sa.Column('nome_atendente', sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('agents', 'nome_atendente')
