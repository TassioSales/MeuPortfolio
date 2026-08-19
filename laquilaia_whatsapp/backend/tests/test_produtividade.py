"""
O que gente fez, e quem fez.

Nos prints do produto concorrente esta tela existe e está vazia: todo card diz
"Sem responsável". Não é defeito de tela — é que lá ninguém registra quem
agiu. Aqui dá para preencher porque a trilha passou a gravar cada ação humana.

O número que importa não é o total: é a razão entre o que a IA resolveu
sozinha e o que precisou de gente. Ela responde se o agente está trabalhando
ou se virou um formulário caro que alguém preenche à mão.
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
    LeadTimeline,
)
from app.main import app
from app.services.kanban_defaults import criar_colunas_padrao
from tests.conftest import criar_acesso

client = TestClient(app)


def _login(sufixo: str, papel: str = "admin") -> tuple[dict, str]:
    email = f"prod-{sufixo}@example.com"
    criar_acesso(client, email, "SenhaSegura123!", f"Pessoa {sufixo}", papel=papel)
    r = client.post("/api/v1/auth/login", json={"email": email, "senha": "SenhaSegura123!"})
    cabecalho = {"Authorization": f"Bearer {r.json()['access_token']}"}
    eu = client.get("/api/v1/auth/me", headers=cabecalho).json()
    return cabecalho, eu["id"]


async def _agente(sufixo: str, dono: str) -> str:
    agent_id = f"ag-{sufixo}"
    async with AsyncSessionLocal() as db:
        db.add(Agent(id=agent_id, user_id=dono, nome="Triagem", system_prompt="p",
                     temperatura=0.4, max_tokens=1024, status="ativo"))
        await db.flush()
        await criar_colunas_padrao(agent_id, db)
        await db.commit()
    return agent_id


async def _lead(agent_id: str, sufixo: str):
    async with AsyncSessionLocal() as db:
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=agent_id,
                            phone_number=f"5561{sufixo}", status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}", nome="X",
                    phone_number=f"5561{sufixo}", status_funil="novo"))
        await db.commit()
    return f"lead-{sufixo}"


async def _acao(lead_id: str, motivo: str, quem: str | None, dias_atras: int = 0):
    async with AsyncSessionLocal() as db:
        db.add(LeadTimeline(lead_id=lead_id, status_anterior="novo",
                            status_novo="qualificado", mudado_por=quem, motivo=motivo,
                            timestamp=datetime.utcnow() - timedelta(days=dias_atras)))
        await db.commit()


def _buscar(agent_id: str, cabecalho: dict, **params):
    return client.get(f"/api/v1/agents/{agent_id}/metrics/produtividade",
                      headers=cabecalho, params=params)


class TestARazaoEntreIAeGente:
    @pytest.mark.asyncio
    async def test_separa_o_que_foi_da_ia(self):
        cabecalho, dono = _login("a1")
        agent_id = await _agente("a1", dono)
        lead = await _lead(agent_id, "a1")
        await _acao(lead, "Qualificação automática", None)
        await _acao(lead, "Qualificação automática", None)
        await _acao(lead, "Movido para Viabilidade no painel", dono)

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["acoes_da_ia"] == 2
        assert dados["acoes_de_gente"] == 1
        assert dados["percentual_humano"] == pytest.approx(33.3)

    @pytest.mark.asyncio
    async def test_periodo_vazio_nao_divide_por_zero(self):
        """Escritório que não abriu é o estado normal, não uma anomalia."""
        cabecalho, dono = _login("a2")
        agent_id = await _agente("a2", dono)

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["percentual_humano"] == 0.0
        assert dados["pessoas"] == []


class TestOQueCadaUmFez:
    @pytest.mark.asyncio
    async def test_separa_por_tipo_de_ação(self):
        cabecalho, dono = _login("b1")
        agent_id = await _agente("b1", dono)
        lead = await _lead(agent_id, "b1")
        await _acao(lead, "Humano assumiu a conversa", dono)
        await _acao(lead, "Conversa devolvida para a IA", dono)
        await _acao(lead, "Movido para Arquivado no painel", dono)

        pessoa = _buscar(agent_id, cabecalho).json()["pessoas"][0]

        assert pessoa["nome"] == "Pessoa b1"
        assert pessoa["acoes"] == 3
        assert pessoa["conversas_assumidas"] == 1
        assert pessoa["conversas_devolvidas"] == 1
        assert pessoa["cards_movidos"] == 1

    @pytest.mark.asyncio
    async def test_conta_leads_distintos_e_nao_so_acoes(self):
        """
        Quinze ações num lead só não é o mesmo trabalho que uma ação em
        quinze leads, e o ranking por ações sozinho confunde os dois.
        """
        cabecalho, dono = _login("b2")
        agent_id = await _agente("b2", dono)
        um = await _lead(agent_id, "b2a")
        outro = await _lead(agent_id, "b2b")
        for _ in range(4):
            await _acao(um, "Movido para Viabilidade no painel", dono)
        await _acao(outro, "Movido para Viabilidade no painel", dono)

        pessoa = _buscar(agent_id, cabecalho).json()["pessoas"][0]

        assert pessoa["acoes"] == 5
        assert pessoa["leads_atendidos"] == 2

    @pytest.mark.asyncio
    async def test_quem_fez_mais_vem_primeiro(self):
        cabecalho, dono = _login("b3")
        outro_cabecalho, outro = _login("b3b", papel="operador")
        agent_id = await _agente("b3", dono)
        lead = await _lead(agent_id, "b3")
        await _acao(lead, "Movido para Viabilidade no painel", dono)
        for _ in range(3):
            await _acao(lead, "Movido para Entrevista no painel", outro)

        pessoas = _buscar(agent_id, cabecalho).json()["pessoas"]

        assert [p["nome"] for p in pessoas] == ["Pessoa b3b", "Pessoa b3"]

    @pytest.mark.asyncio
    async def test_apagar_o_usuario_nao_leva_o_agente_junto(self):
        """
        O alçapão que este teste achou.

        `agents.user_id` significava "dono" e passou a significar "quem criou"
        quando o agente virou do escritório — mas o `ondelete=CASCADE` ficou.
        Remover a conta de quem saiu levaria junto o agente e, em cascata, as
        conversas, os leads, os casos e o histórico. Tudo, em silêncio.

        O segundo assert documenta o que **se perde de fato**: `mudado_por` é
        `SET NULL`, então as ações da pessoa apagada passam a contar como da
        IA. O painel não apaga usuário — desativa —, então isto só acontece
        por `DELETE` manual.
        """
        cabecalho, dono = _login("b4")
        # O segundo acesso nasce antes: o cadastro público fecha no primeiro
        # usuário, e apagá-lo primeiro deixaria a suíte sem quem criar outro.
        sobrevivente, _ = _login("b4b")
        agent_id = await _agente("b4", dono)
        lead = await _lead(agent_id, "b4")
        await _acao(lead, "Movido para Viabilidade no painel", dono)

        async with AsyncSessionLocal() as db:
            from app.db.models import User
            usuario = (await db.execute(select(User).where(User.id == dono))).scalars().first()
            await db.delete(usuario)
            await db.commit()

        resposta = _buscar(agent_id, sobrevivente)

        # O agente — e tudo pendurado nele — continua de pé.
        assert resposta.status_code == 200, resposta.text
        dados = resposta.json()
        assert dados["pessoas"] == []
        assert dados["acoes_da_ia"] == 1

    @pytest.mark.asyncio
    async def test_o_recorte_de_dias_vale(self):
        cabecalho, dono = _login("b5")
        agent_id = await _agente("b5", dono)
        lead = await _lead(agent_id, "b5")
        await _acao(lead, "Movido para Viabilidade no painel", dono, dias_atras=2)
        await _acao(lead, "Movido para Entrevista no painel", dono, dias_atras=200)

        assert _buscar(agent_id, cabecalho).json()["acoes_de_gente"] == 1
        assert _buscar(agent_id, cabecalho, dias=365).json()["acoes_de_gente"] == 2


class TestAcesso:
    @pytest.mark.asyncio
    async def test_operador_ve(self):
        cabecalho, dono = _login("c1")
        agent_id = await _agente("c1", dono)
        operador, _ = _login("c1op", papel="operador")

        assert _buscar(agent_id, operador).status_code == 200

    def test_sem_token_e_401(self, client):
        assert client.get("/api/v1/agents/x/metrics/produtividade").status_code == 401

    @pytest.mark.asyncio
    async def test_agente_inexistente_e_404(self):
        cabecalho, _ = _login("c3")

        assert _buscar("nao-existe", cabecalho).status_code == 404
