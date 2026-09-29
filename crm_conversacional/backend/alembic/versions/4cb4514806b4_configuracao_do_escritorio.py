"""Configuração do escritório

A tabela que guarda o que o agente precisa saber sobre o escritório que ele
representa: nome, telefone, endereço, horário — e o telefone do suporte, que
é o número dado a quem **já é cliente** e escreveu no comercial por engano.

Uma linha só, com id fixo. Esta instalação atende um escritório, a mesma
premissa que sustenta a autorização por papel.

Revision ID: 4cb4514806b4
Revises: f3c81b0d9a24
Create Date: 2026-08-19 03:03:42.896254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cb4514806b4'
down_revision: Union[str, None] = 'f3c81b0d9a24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "configuracao_escritorio",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("nome", sa.String(length=255), nullable=True),
        sa.Column("cnpj", sa.String(length=32), nullable=True),
        sa.Column("oab_responsavel", sa.String(length=64), nullable=True),
        sa.Column("fundador", sa.String(length=255), nullable=True),
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("telefone", sa.String(length=32), nullable=True),
        sa.Column("telefone_suporte", sa.String(length=32), nullable=True),
        sa.Column("horario_atendimento", sa.String(length=255), nullable=True),
        sa.Column("site", sa.String(length=255), nullable=True),
        sa.Column("instagram", sa.String(length=255), nullable=True),
        sa.Column("data_atualizacao", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("configuracao_escritorio")
