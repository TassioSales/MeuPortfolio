"""papel do usuario

Revision ID: 2b7ce3cb554d
Revises: 1d8272fae6bb
Create Date: 2026-08-12 19:20:50.212077

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b7ce3cb554d'
down_revision: Union[str, None] = '1d8272fae6bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A coluna nasce com server_default para as linhas que já existem: sem
    # ele, um NOT NULL numa tabela populada falha na hora de aplicar.
    op.add_column(
        "users",
        sa.Column(
            "papel",
            sa.String(length=20),
            nullable=False,
            server_default="operador",
        ),
    )

    # Quem já estava no sistema é dono dele — foi quem criou os agentes antes
    # de existir papel. Deixá-los como operador tiraria do administrador o
    # acesso à própria configuração.
    op.execute("UPDATE users SET papel = 'admin'")

    # O default fica só na migração. Na aplicação quem decide o papel é o
    # código de criação, e um default no banco esconderia o esquecimento.
    op.alter_column("users", "papel", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "papel")
