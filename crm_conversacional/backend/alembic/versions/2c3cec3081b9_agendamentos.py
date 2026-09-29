"""Agendamentos

O retorno combinado com o cliente. "Te ligo amanhã às 15h" era dito na conversa
e morria ali — virava compromisso que só existia na cabeça de quem prometeu.

Revision ID: 2c3cec3081b9
Revises: 5d6752e27f46
Create Date: 2026-08-19 05:58:50.580908

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c3cec3081b9'
down_revision: Union[str, None] = '5d6752e27f46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agendamentos",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("lead_id", sa.String(length=36), nullable=False),
        sa.Column("quando", sa.DateTime(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pendente"),
        sa.Column("criado_por", sa.String(length=36), nullable=True),
        sa.Column("data_criacao", sa.DateTime(), nullable=True),
        sa.Column("data_atualizacao", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["criado_por"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_agendamento_quando", "agendamentos", ["quando"])
    op.create_index("idx_agendamento_lead", "agendamentos", ["lead_id"])


def downgrade() -> None:
    op.drop_index("idx_agendamento_lead", table_name="agendamentos")
    op.drop_index("idx_agendamento_quando", table_name="agendamentos")
    op.drop_table("agendamentos")
