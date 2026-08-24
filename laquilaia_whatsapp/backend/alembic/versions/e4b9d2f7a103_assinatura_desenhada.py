"""Assinatura desenhada

O rabisco que a pessoa faz com o dedo na tela, em PNG.

Juridicamente ele não acrescenta nada — o que prova a assinatura é a trilha:
token individual, hora, IP, aparelho e hash do texto. Mas um contrato sem nada
escrito na linha da assinatura **não parece assinado**, e o cliente que recebe
esse PDF fica sem saber se aquilo valeu.

Revision ID: e4b9d2f7a103
Revises: d5a17c093e2b
Create Date: 2026-08-24 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4b9d2f7a103"
down_revision: Union[str, None] = "d5a17c093e2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contratos", sa.Column("assinatura_imagem", sa.LargeBinary(), nullable=True)
    )


def downgrade() -> None:
    # Os contratos já assinados perdem o rabisco; o PDF absorvido continua
    # inteiro, porque a imagem foi desenhada dentro dele no ato.
    op.drop_column("contratos", "assinatura_imagem")
