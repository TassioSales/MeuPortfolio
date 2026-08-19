"""O agente sobrevive a quem o criou

`agents.user_id` significava "dono" e passou a significar "quem criou" quando
o agente virou do escritório. O `ondelete=CASCADE` ficou para trás, e com ele
um alçapão: remover a conta de quem saiu do escritório levaria junto o agente
— e, em cascata, as conversas, os leads, os casos e o histórico. Tudo, em
silêncio, por uma linha de SQL que ninguém associaria a isso.

Revision ID: e0ee1f31a89c
Revises: 2c3cec3081b9
Create Date: 2026-08-19 13:39:50.812464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0ee1f31a89c'
down_revision: Union[str, None] = '2c3cec3081b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A coluna vira anulável antes de a chave mudar: `SET NULL` numa coluna
    # NOT NULL é uma violação esperando o primeiro DELETE.
    op.alter_column("agents", "user_id", existing_type=sa.String(length=36), nullable=True)

    op.drop_constraint("agents_user_id_fkey", "agents", type_="foreignkey")
    op.create_foreign_key(
        "agents_user_id_fkey", "agents", "users", ["user_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    """
    Volta ao CASCADE.

    Agente cujo criador já foi apagado tem `user_id` nulo, e a coluna volta a
    ser NOT NULL — esses ficariam órfãos e impediriam a alteração. Eles são
    adotados pelo administrador mais antigo antes, que é o desfecho menos
    ruim: perder o agente do escritório para satisfazer uma constraint seria
    trocar dado por arrumação.
    """
    conexao = op.get_bind()
    conexao.execute(
        sa.text(
            """
            UPDATE agents SET user_id = (
                SELECT id FROM users WHERE papel = 'admin'
                ORDER BY data_criacao LIMIT 1
            )
            WHERE user_id IS NULL
            """
        )
    )

    op.drop_constraint("agents_user_id_fkey", "agents", type_="foreignkey")
    op.create_foreign_key(
        "agents_user_id_fkey", "agents", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.alter_column("agents", "user_id", existing_type=sa.String(length=36), nullable=False)
