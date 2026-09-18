"""Cobrança da assinatura

Contrato enviado e não assinado precisa de alguém atrás dele. As duas colunas
ficam no **contrato**, e não na conversa, porque são coisas diferentes: o
follow-up de conversa cutuca quem parou de responder; esta cobra quem recebeu
um documento e não voltou. Dá para estar em dia com a conversa e devendo
assinatura.

Revision ID: c9e2b83f41d7
Revises: b7d4e91c25a8
Create Date: 2026-08-21 02:20:15.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9e2b83f41d7"
down_revision: Union[str, None] = "b7d4e91c25a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `server_default="0"` porque a coluna é NOT NULL e a tabela já tem
    # linhas: sem ele o Postgres não sabe o que escrever nos contratos que já
    # existem, e o ALTER falha. O `default=` do SQLAlchemy só vale para linha
    # nova — armadilha que já mordeu neste projeto.
    op.add_column(
        "contratos",
        sa.Column(
            "cobrancas_enviadas", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "contratos", sa.Column("ultima_cobranca_em", sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("contratos", "ultima_cobranca_em")
    op.drop_column("contratos", "cobrancas_enviadas")
