"""Assinatura do contrato

O que faltava para o ciclo fechar sem sair do produto: um link único que só
existe no WhatsApp do cliente, a assinatura registrada com a trilha de prova
(hora, IP, aparelho, hash do texto) e o PDF **absorvido** — guardado aqui
dentro, para o documento não depender de link, de nuvem nem de a pessoa
continuar por perto.

**Atenção ao downgrade.** Ele derruba as colunas, e com elas os PDFs
assinados e a trilha de prova — dado que não existe em nenhum outro lugar,
justamente porque a ideia era não existir em nenhum outro lugar. Descer esta
revisão num banco com contrato assinado destrói o contrato assinado. Faça
cópia antes.

Revision ID: b7d4e91c25a8
Revises: 8f21a0c47d53
Create Date: 2026-08-21 01:12:40.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7d4e91c25a8"
down_revision: Union[str, None] = "8f21a0c47d53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# As colunas nascem todas nulas: contrato gerado e não enviado não tem link,
# não tem prazo e não tem assinatura. Nulo aqui quer dizer "ainda não
# aconteceu", que é diferente de vazio — por isso nenhuma delas ganha default.
COLUNAS = [
    ("token_assinatura", sa.String(length=64)),
    ("token_expira_em", sa.DateTime()),
    ("data_envio", sa.DateTime()),
    ("assinado_nome", sa.String(length=255)),
    ("assinado_ip", sa.String(length=45)),
    ("assinado_user_agent", sa.String(length=500)),
    ("hash_documento", sa.String(length=64)),
    ("pdf_assinado", sa.LargeBinary()),
]


def upgrade() -> None:
    for nome, tipo in COLUNAS:
        op.add_column("contratos", sa.Column(nome, tipo, nullable=True))

    # Um índice **único**, e não uma constraint mais um índice: é o que
    # `unique=True, index=True` no model produz, e divergir daqui faria todo
    # `--autogenerate` futuro acusar deriva que não existe.
    #
    # Único porque dois contratos com o mesmo token seria o pior defeito
    # possível neste recurso — a página pública entregaria o contrato de um
    # cliente a outro. Indexado porque a página busca por ele em toda visita.
    op.create_index(
        "ix_contratos_token_assinatura",
        "contratos",
        ["token_assinatura"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_contratos_token_assinatura", table_name="contratos")
    for nome, _tipo in reversed(COLUNAS):
        op.drop_column("contratos", nome)
