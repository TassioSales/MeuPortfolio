"""porte economico do caso

Revision ID: 126ed7e48b1b
Revises: 2b7ce3cb554d
Create Date: 2026-08-13 00:34:07.205757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '126ed7e48b1b'
down_revision: Union[str, None] = '2b7ce3cb554d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('casos', sa.Column('valor_estimado_min', sa.Integer(), nullable=True))
    op.add_column('casos', sa.Column('valor_estimado_max', sa.Integer(), nullable=True))
    op.add_column('casos', sa.Column('viabilidade', sa.String(length=30), nullable=True))

    # O default do modelo é do lado do Python: só vale para linha nova. Sem
    # este UPDATE, todo caso já existente fica com `viabilidade = NULL`, e o
    # painel teria dois jeitos de dizer a mesma coisa — NULL e
    # 'indeterminado' — que é exatamente como nasce um `if` errado.
    op.execute("UPDATE casos SET viabilidade = 'indeterminado' WHERE viabilidade IS NULL")


def downgrade() -> None:
    op.drop_column('casos', 'viabilidade')
    op.drop_column('casos', 'valor_estimado_max')
    op.drop_column('casos', 'valor_estimado_min')
