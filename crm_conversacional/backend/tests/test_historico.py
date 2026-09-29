"""
Quem fez o quê, e quando.

A trilha existia desde o começo e ninguém nunca a leu — e só a IA escrevia
nela. Card arrastado por gente e conversa assumida por gente não deixavam
rastro; num escritório com mais de uma pessoa no board, "quem mandou esse
caso para o arquivo?" não tinha resposta.

Metade destes casos cobre a **escrita** que faltava, e é a metade que
importa: uma tela de histórico lendo uma trilha vazia seria pior que
nenhuma tela.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from unittest.mock import AsyncMock, patch

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Agent,
    Conversation,
    KanbanCard,
    KanbanColumn,
    Lead,
    LeadTimeline,
)
from app.main import app
from app.services.kanban_defaults import criar_colunas_padrao
from tests.conftest import criar_acesso

client = TestClient(app)


def _login(sufixo: str, papel: str = "admin") -> tuple[dict, str]:
    email = f"hist-{sufixo}@example.com"
    criar_acesso(client, email, "SenhaSegura123!", f"Pessoa {sufixo}", papel=papel)
    r = client.post("/api/v1/auth/login", json={"email": email, "senha": "SenhaSegura123!"})
    cabecalho = {"Authorization": f"Bearer {r.json()['access_token']}"}
    eu = client.get("/api/v1/auth/me", headers=cabecalho).json()
    return cabecalho, eu["id"]


async def _cenario(sufixo: str, dono: str) -> tuple[str, str]:
    """Um agente com funil, um lead e o card na primeira coluna."""
    agent_id = f"ag-{sufixo}"
    async with AsyncSessionLocal() as db:
        db.add(Agent(id=agent_id, user_id=dono, nome="Triagem", system_prompt="p",
                     temperatura=0.4, max_tokens=1024, status="ativo"))
        await db.flush()
        await criar_colunas_padrao(agent_id, db)

        db.add(Conversation(id=f"cv-{sufixo}", agent_id=agent_id,
                            phone_number=f"5561{sufixo}", status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}", nome="Marina",
                    phone_number=f"5561{sufixo}", status_funil="novo"))
        await db.flush()

        primeira = (
            await db.execute(
                select(KanbanColumn)
                .where(KanbanColumn.agent_id == agent_id)
                .order_by(KanbanColumn.ordem)
            )
        ).scalars().first()
        db.add(KanbanCard(column_id=primeira.id, lead_id=f"lead-{sufixo}", ordem=1))
        await db.commit()
    return agent_id, f"lead-{sufixo}"


async def _coluna(agent_id: str, nome: str) -> str:
    async with AsyncSessionLocal() as db:
        col = (
            await db.execute(
                select(KanbanColumn).where(
                    (KanbanColumn.agent_id == agent_id) & (KanbanColumn.nome == nome)
                )
            )
        ).scalars().first()
        return col.id


class TestOArrastoDeixaRastro:
    @pytest.mark.asyncio
    async def test_mover_o_card_registra_quem_moveu(self):
        cabecalho, dono = _login("a1")
        agent_id, lead_id = await _cenario("a1", dono)
        destino = await _coluna(agent_id, "Viabilidade")

        r = client.post(
            f"/api/v1/agents/{agent_id}/kanban/move",
            json={"lead_id": lead_id, "target_column_id": destino, "new_order": 0},
            headers=cabecalho,
        )
        assert r.status_code == 200, r.text

        dados = client.get(f"/api/v1/agents/{agent_id}/historico", headers=cabecalho).json()

        assert dados["total"] == 1
        movimento = dados["movimentos"][0]
        assert movimento["responsavel"] == "Pessoa a1"
        assert movimento["status_novo"] == "qualificado"
        assert "Viabilidade" in movimento["motivo"]

    @pytest.mark.asyncio
    async def test_o_status_do_lead_acompanha_a_coluna(self):
        """
        Aqui havia um mapa duplicado com os nomes antigos das colunas. Depois
        da renomeação ele não casava com nenhuma, e o `.get(..., atual)`
        engolia isso: o card andava na tela e o `status_funil` ficava para
        trás, então board e métricas contavam coisas diferentes sobre o mesmo
        lead.
        """
        cabecalho, dono = _login("a2")
        agent_id, lead_id = await _cenario("a2", dono)
        destino = await _coluna(agent_id, "Arquivado")

        client.post(
            f"/api/v1/agents/{agent_id}/kanban/move",
            json={"lead_id": lead_id, "target_column_id": destino, "new_order": 0},
            headers=cabecalho,
        )

        async with AsyncSessionLocal() as db:
            lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalars().first()

        assert lead.status_funil == "arquivado"

    @pytest.mark.asyncio
    async def test_cada_movimento_e_uma_linha(self):
        cabecalho, dono = _login("a3")
        agent_id, lead_id = await _cenario("a3", dono)

        for nome in ("Entrevista", "Viabilidade", "Arquivado"):
            client.post(
                f"/api/v1/agents/{agent_id}/kanban/move",
                json={"lead_id": lead_id, "target_column_id": await _coluna(agent_id, nome),
                      "new_order": 0},
                headers=cabecalho,
            )

        dados = client.get(f"/api/v1/agents/{agent_id}/historico", headers=cabecalho).json()

        assert dados["total"] == 3
        # Do mais recente para o mais antigo.
        assert dados["movimentos"][0]["status_novo"] == "arquivado"


class TestATomadaDeConversa:
    @pytest.mark.asyncio
    async def test_assumir_e_devolver_ficam_registrados(self):
        """
        O buraco maior do histórico. Quem lia a transcrição via a IA parar de
        responder no meio e não tinha como saber quem tinha assumido nem
        quando — num escritório com plantão é a primeira pergunta que se faz.
        """
        cabecalho, dono = _login("b1")
        agent_id, _ = await _cenario("b1", dono)

        client.post("/api/v1/conversations/cv-b1/pause", headers=cabecalho)
        client.post("/api/v1/conversations/cv-b1/resume", headers=cabecalho)

        dados = client.get(f"/api/v1/agents/{agent_id}/historico", headers=cabecalho).json()

        motivos = [m["motivo"] for m in dados["movimentos"]]
        assert "Humano assumiu a conversa" in motivos
        assert "Conversa devolvida para a IA" in motivos
        assert all(m["responsavel"] == "Pessoa b1" for m in dados["movimentos"])

    @pytest.mark.asyncio
    async def test_pausar_o_que_ja_esta_pausado_nao_duplica(self):
        """
        O botão pode ser clicado duas vezes, e o painel também repausa quando
        recarrega. Uma linha por clique encheria o histórico de ruído.
        """
        cabecalho, dono = _login("b2")
        agent_id, _ = await _cenario("b2", dono)

        client.post("/api/v1/conversations/cv-b2/pause", headers=cabecalho)
        client.post("/api/v1/conversations/cv-b2/pause", headers=cabecalho)

        dados = client.get(f"/api/v1/agents/{agent_id}/historico", headers=cabecalho).json()

        assert dados["total"] == 1


class TestALeitura:
    @pytest.mark.asyncio
    async def test_separa_o_que_foi_gente_do_que_foi_a_ia(self):
        """
        O filtro que faz a tela valer: a IA move dezenas de cards por dia e
        afoga as poucas ações humanas, que são as que alguém precisa auditar.
        """
        cabecalho, dono = _login("c1")
        agent_id, lead_id = await _cenario("c1", dono)

        client.post(
            f"/api/v1/agents/{agent_id}/kanban/move",
            json={"lead_id": lead_id,
                  "target_column_id": await _coluna(agent_id, "Viabilidade"),
                  "new_order": 0},
            headers=cabecalho,
        )
        async with AsyncSessionLocal() as db:
            db.add(LeadTimeline(lead_id=lead_id, status_anterior="novo",
                                status_novo="em_qualificacao", mudado_por=None,
                                motivo="Qualificação automática", timestamp=datetime.utcnow()))
            await db.commit()

        tudo = client.get(f"/api/v1/agents/{agent_id}/historico", headers=cabecalho).json()
        so_gente = client.get(
            f"/api/v1/agents/{agent_id}/historico?apenas_humanos=true", headers=cabecalho
        ).json()

        assert tudo["total"] == 2
        assert so_gente["total"] == 1
        assert so_gente["movimentos"][0]["responsavel"] == "Pessoa c1"

    @pytest.mark.asyncio
    async def test_movimento_da_ia_vem_sem_responsavel(self):
        cabecalho, dono = _login("c2")
        agent_id, lead_id = await _cenario("c2", dono)
        async with AsyncSessionLocal() as db:
            db.add(LeadTimeline(lead_id=lead_id, status_anterior="novo",
                                status_novo="qualificado", mudado_por=None,
                                motivo="Qualificação automática", timestamp=datetime.utcnow()))
            await db.commit()

        dados = client.get(f"/api/v1/agents/{agent_id}/historico", headers=cabecalho).json()

        assert dados["movimentos"][0]["responsavel"] is None

    @pytest.mark.asyncio
    async def test_o_recorte_de_dias_corta_o_antigo(self):
        cabecalho, dono = _login("c3")
        agent_id, lead_id = await _cenario("c3", dono)
        async with AsyncSessionLocal() as db:
            db.add(LeadTimeline(lead_id=lead_id, status_anterior="novo",
                                status_novo="qualificado", motivo="antigo",
                                timestamp=datetime.utcnow() - timedelta(days=90)))
            db.add(LeadTimeline(lead_id=lead_id, status_anterior="novo",
                                status_novo="qualificado", motivo="recente",
                                timestamp=datetime.utcnow()))
            await db.commit()

        recente = client.get(f"/api/v1/agents/{agent_id}/historico", headers=cabecalho).json()
        tudo = client.get(f"/api/v1/agents/{agent_id}/historico?dias=365", headers=cabecalho).json()

        assert recente["total"] == 1
        assert tudo["total"] == 2

    @pytest.mark.asyncio
    async def test_nao_mistura_agente(self):
        cabecalho, dono = _login("c4")
        a, lead_a = await _cenario("c4a", dono)
        b, lead_b = await _cenario("c4b", dono)
        async with AsyncSessionLocal() as db:
            db.add(LeadTimeline(lead_id=lead_a, status_novo="x", motivo="do A",
                                timestamp=datetime.utcnow()))
            db.add(LeadTimeline(lead_id=lead_b, status_novo="x", motivo="do B",
                                timestamp=datetime.utcnow()))
            await db.commit()

        dados = client.get(f"/api/v1/agents/{a}/historico", headers=cabecalho).json()

        assert [m["motivo"] for m in dados["movimentos"]] == ["do A"]

    @pytest.mark.asyncio
    async def test_operador_ve_o_historico(self):
        cabecalho, dono = _login("c5")
        agent_id, _ = await _cenario("c5", dono)
        operador, _ = _login("c5op", papel="operador")

        assert client.get(
            f"/api/v1/agents/{agent_id}/historico", headers=operador
        ).status_code == 200

    def test_sem_token_e_401(self):
        assert client.get("/api/v1/agents/x/historico").status_code == 401

    @pytest.mark.asyncio
    async def test_agente_inexistente_e_404(self):
        cabecalho, _ = _login("c7")

        assert client.get(
            "/api/v1/agents/nao-existe/historico", headers=cabecalho
        ).status_code == 404
