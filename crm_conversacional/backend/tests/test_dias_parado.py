"""
Há quantos dias o card não sai do lugar.

É o único contador que sobrevive ao uso real. Num board de escritório de
verdade, "ligações 0/5" e "mensagens 0/5" ficam zerados para sempre porque
ninguém para de atender para registrar ligação — mas o tempo passa sozinho.
Um caso parado há catorze dias em "Coleta de documentos" é a informação que
faz alguém agir, e ela não existia no painel.

O relógio sai de `KanbanCard.data_movimentacao`, que o SQLAlchemy renova a
cada UPDATE da linha. Daí o segundo grupo de casos: qualquer coisa que
reescreva o card sem ele ter mudado de coluna zera esse relógio, e um caso
esquecido volta a parecer recém-chegado.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Agent,
    Conversation,
    KanbanCard,
    KanbanColumn,
    Lead,
)
from app.main import app
from app.routers.kanban import _dias_parado
from app.services.lead_processor import lead_processor
from tests.conftest import criar_acesso

client = TestClient(app)


def _login(sufixo: str) -> tuple[dict, str]:
    email = f"parado-{sufixo}@example.com"
    criar_acesso(client, email, "SenhaSegura123!", "Dono")
    r = client.post("/api/v1/auth/login", json={"email": email, "senha": "SenhaSegura123!"})
    cabecalho = {"Authorization": f"Bearer {r.json()['access_token']}"}
    eu = client.get("/api/v1/auth/me", headers=cabecalho).json()
    return cabecalho, eu["id"]


async def _board(sufixo: str, dono: str, *, dias: int) -> str:
    """Um agente com o funil montado e um lead parado há `dias` numa coluna."""
    agent_id = f"ag-{sufixo}"
    async with AsyncSessionLocal() as db:
        db.add(
            Agent(id=agent_id, user_id=dono, nome="Triagem", system_prompt="p",
                  temperatura=0.4, max_tokens=1024, status="ativo")
        )
        await db.flush()

        from app.services.kanban_defaults import criar_colunas_padrao

        await criar_colunas_padrao(agent_id, db)

        coluna = (
            await db.execute(
                select(KanbanColumn).where(
                    (KanbanColumn.agent_id == agent_id) & (KanbanColumn.nome == "Viabilidade")
                )
            )
        ).scalars().first()

        db.add(Conversation(id=f"cv-{sufixo}", agent_id=agent_id,
                            phone_number=f"5561{sufixo}", status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}",
                    nome="Marina", phone_number=f"5561{sufixo}", status_funil="qualificado"))
        await db.flush()
        db.add(
            KanbanCard(
                id=f"card-{sufixo}",
                column_id=coluna.id,
                lead_id=f"lead-{sufixo}",
                ordem=1,
                data_movimentacao=datetime.utcnow() - timedelta(days=dias),
            )
        )
        await db.commit()
    return agent_id


class TestAContagem:
    def test_conta_dias_inteiros(self):
        agora = datetime(2026, 8, 19, 12, 0)
        assert _dias_parado(agora - timedelta(days=14), agora) == 14

    def test_movido_hoje_e_zero(self):
        agora = datetime(2026, 8, 19, 12, 0)
        assert _dias_parado(agora - timedelta(hours=3), agora) == 0

    def test_sem_data_e_zero_e_nao_um_chute(self):
        """
        Card antigo pode não ter data — a coluna nasceu depois de alguns
        deles. Zero aqui quer dizer "não sei", e ninguém age errado por causa
        disso; um chute alto mandaria o escritório correr atrás de um caso que
        talvez tenha se movido ontem.
        """
        assert _dias_parado(None, datetime.utcnow()) == 0

    def test_data_no_futuro_nao_vira_negativo(self):
        """
        Relógio do banco adiantado, ou linha semeada com data futura. "Parado
        há -2 dias" na tela é pior que impreciso: é visivelmente quebrado.
        """
        agora = datetime(2026, 8, 19, 12, 0)
        assert _dias_parado(agora + timedelta(days=2), agora) == 0


class TestNoBoard:
    @pytest.mark.asyncio
    async def test_o_card_chega_com_a_idade(self):
        cabecalho, dono = _login("b1")
        agent_id = await _board("b1", dono, dias=14)

        board = client.get(f"/api/v1/agents/{agent_id}/kanban", headers=cabecalho).json()

        cards = [c for col in board["columns"] for c in col["cards"]]
        assert len(cards) == 1
        assert cards[0]["dias_parado"] == 14


class TestORelogioNaoZeraSozinho:
    @pytest.mark.asyncio
    async def test_requalificar_na_mesma_coluna_preserva_a_idade(self):
        """
        O caso que motivou a correção.

        `_move_in_kanban` apagava e recriava o card mesmo quando a coluna era
        a mesma. Cada requalificação — e há várias por lead — zerava o
        relógio. Um caso esquecido há duas semanas voltava a parecer
        recém-chegado, que é exatamente o contrário do que a coluna serve
        para mostrar.
        """
        _, dono = _login("c1")
        agent_id = await _board("c1", dono, dias=20)

        async with AsyncSessionLocal() as db:
            lead = (
                await db.execute(select(Lead).where(Lead.id == "lead-c1"))
            ).scalars().first()

            await lead_processor._move_in_kanban(lead, agent_id, "qualificado", db)
            await db.commit()

        async with AsyncSessionLocal() as db:
            card = (
                await db.execute(select(KanbanCard).where(KanbanCard.lead_id == "lead-c1"))
            ).scalars().first()
            idade = (datetime.utcnow() - card.data_movimentacao).days

        assert idade == 20, "a requalificação zerou o relógio do card"

    @pytest.mark.asyncio
    async def test_mudar_de_coluna_zera_a_idade_mesmo(self):
        """
        O outro lado: quando o card **anda**, a contagem tem de recomeçar. Um
        caso que acabou de entrar em "Saneamento" não está parado há 20 dias
        nessa etapa.
        """
        _, dono = _login("c2")
        agent_id = await _board("c2", dono, dias=20)

        async with AsyncSessionLocal() as db:
            lead = (
                await db.execute(select(Lead).where(Lead.id == "lead-c2"))
            ).scalars().first()

            await lead_processor._move_in_kanban(lead, agent_id, "arquivado", db)
            await db.commit()

        async with AsyncSessionLocal() as db:
            card = (
                await db.execute(select(KanbanCard).where(KanbanCard.lead_id == "lead-c2"))
            ).scalars().first()
            coluna = (
                await db.execute(
                    select(KanbanColumn).where(KanbanColumn.id == card.column_id)
                )
            ).scalars().first()

        assert coluna.nome == "Arquivado"
        assert (datetime.utcnow() - card.data_movimentacao).days == 0
