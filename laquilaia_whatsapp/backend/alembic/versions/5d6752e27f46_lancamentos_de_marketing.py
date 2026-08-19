"""Lançamentos de marketing

O gasto em anúncio, que só o escritório sabe. O consumo de IA fica de fora
desta tabela de propósito: ele já está em `messages.tokens_usados` e é somado
na hora de calcular, em vez de ser digitado.

Dinheiro em centavos inteiros — ponto flutuante acumula erro na soma, e um
relatório de custo que não fecha com o extrato ninguém usa duas vezes.

Revision ID: 5d6752e27f46
Revises: 4cb4514806b4
Create Date: 2026-08-19 05:46:55.426870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d6752e27f46'
down_revision: Union[str, None] = '4cb4514806b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lancamentos_marketing",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("investimento_ads_centavos", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("criado_por", sa.String(length=36), nullable=True),
        sa.Column("data_criacao", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["criado_por"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_lancamento_data", "lancamentos_marketing", ["data"])


def downgrade() -> None:
    op.drop_index("idx_lancamento_data", table_name="lancamentos_marketing")
    op.drop_table("lancamentos_marketing")
