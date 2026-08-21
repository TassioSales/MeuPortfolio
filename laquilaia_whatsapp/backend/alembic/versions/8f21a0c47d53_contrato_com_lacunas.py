"""Contrato com lacunas

Três tabelas fecham o ciclo do escritório: o modelo que o advogado escreve no
painel, os dados de qualificação civil do cliente (que a triagem não pergunta)
e o contrato emitido — com o texto **já preenchido**, para que um contrato de
janeiro continue dizendo o que dizia em janeiro depois de o modelo mudar.

Revision ID: 8f21a0c47d53
Revises: 1a6649a34d5e
Create Date: 2026-08-20 23:41:12.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f21a0c47d53"
down_revision: Union[str, None] = "1a6649a34d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "modelos_contrato",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("corpo", sa.Text(), nullable=False),
        # `server_default` porque a coluna é NOT NULL: sem ele, uma linha
        # inserida por fora do ORM (seed, psql) falharia sem explicação.
        sa.Column(
            "ativo", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("data_criacao", sa.DateTime(), nullable=True),
        sa.Column("data_atualizacao", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("nome", name="uix_modelo_contrato_nome"),
    )

    op.create_table(
        "dados_do_contrato",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("lead_id", sa.String(length=36), nullable=False),
        sa.Column("cpf", sa.String(length=14), nullable=True),
        sa.Column("rg", sa.String(length=30), nullable=True),
        sa.Column("nacionalidade", sa.String(length=60), nullable=True),
        sa.Column("estado_civil", sa.String(length=40), nullable=True),
        sa.Column("profissao", sa.String(length=120), nullable=True),
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("cep", sa.String(length=9), nullable=True),
        sa.Column("cidade", sa.String(length=120), nullable=True),
        sa.Column("uf", sa.String(length=2), nullable=True),
        sa.Column("data_atualizacao", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("lead_id", name="uix_dados_do_contrato_lead"),
    )

    op.create_table(
        "contratos",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("lead_id", sa.String(length=36), nullable=False),
        sa.Column("modelo_id", sa.String(length=36), nullable=True),
        sa.Column("corpo", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="gerado"
        ),
        sa.Column("link_assinatura", sa.String(length=500), nullable=True),
        sa.Column("data_assinatura", sa.DateTime(), nullable=True),
        sa.Column("gerado_por", sa.String(length=36), nullable=True),
        sa.Column("data_criacao", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        # Apagar o modelo não pode apagar contrato emitido.
        sa.ForeignKeyConstraint(
            ["modelo_id"], ["modelos_contrato.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["gerado_por"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_contrato_lead", "contratos", ["lead_id"])

    # A cidade do escritório entra junto porque o contrato precisa dela
    # isolada: a cláusula de foro e a linha de assinatura. Está dentro de
    # `endereco`, que é texto livre — extrair de lá é adivinhar.
    op.add_column(
        "configuracao_escritorio",
        sa.Column("cidade", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("configuracao_escritorio", "cidade")
    # Ordem inversa da criação: `contratos` referencia `modelos_contrato`, e o
    # Postgres recusa derrubar a tabela apontada enquanto a FK existir.
    op.drop_index("idx_contrato_lead", table_name="contratos")
    op.drop_table("contratos")
    op.drop_table("dados_do_contrato")
    op.drop_table("modelos_contrato")
