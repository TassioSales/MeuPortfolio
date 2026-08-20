"""Follow-up de conversa abandonada

Quem some no meio da triagem ficava para sempre na primeira coluna, e ninguém
sabia se tinha desistido ou se só não tinha visto a mensagem — as duas coisas
tinham a mesma aparência no painel.

`followups_enviados` conta silêncio **seguido**: zera assim que o cliente
escreve. Por isso `server_default="0"` e não nulo — conversa antiga entra na
contagem como quem nunca foi cutucado, que é a verdade.

Revision ID: 1a6649a34d5e
Revises: e0ee1f31a89c
Create Date: 2026-08-20 23:02:49.012665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a6649a34d5e'
down_revision: Union[str, None] = 'e0ee1f31a89c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("followups_enviados", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "conversations", sa.Column("ultimo_followup_em", sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("conversations", "ultimo_followup_em")
    op.drop_column("conversations", "followups_enviados")
