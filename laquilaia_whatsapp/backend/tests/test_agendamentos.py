"""
Os retornos combinados com o cliente.

"Te ligo amanhã às 15h" era dito na conversa e morria ali — compromisso que
só existia na cabeça de quem prometeu, enquanto o cliente esperava a ligação
que ninguém marcou.

Dois casos aqui vieram de defeito observado, não de hipótese: a duplicata
(três retornos para a mesma cliente em seis minutos, no produto concorrente) e
o atraso, que é a única informação pela qual a tela existe.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db.database import AsyncSessionLocal
from app.db.models import Agent, Conversation, Lead
from app.main import app
from tests.conftest import criar_acesso

client = TestClient(app)


def _login(sufixo: str, papel: str = "admin") -> tuple[dict, str]:
    email = f"agd-{sufixo}@example.com"
    criar_acesso(client, email, "SenhaSegura123!", f"Pessoa {sufixo}", papel=papel)
    r = client.post("/api/v1/auth/login", json={"email": email, "senha": "SenhaSegura123!"})
    cabecalho = {"Authorization": f"Bearer {r.json()['access_token']}"}
    eu = client.get("/api/v1/auth/me", headers=cabecalho).json()
    return cabecalho, eu["id"]


async def _cenario(sufixo: str, dono: str) -> tuple[str, str]:
    agent_id = f"ag-{sufixo}"
    async with AsyncSessionLocal() as db:
        db.add(Agent(id=agent_id, user_id=dono, nome="Triagem", system_prompt="p",
                     temperatura=0.4, max_tokens=1024, status="ativo"))
        await db.flush()
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=agent_id,
                            phone_number=f"5561{sufixo}", status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}", nome="Andreia",
                    phone_number=f"5561{sufixo}", status_funil="novo"))
        await db.commit()
    return agent_id, f"lead-{sufixo}"


def _marcar(agent_id: str, cabecalho: dict, lead_id: str, quando: datetime, motivo="Retorno"):
    return client.post(
        f"/api/v1/agents/{agent_id}/agendamentos",
        json={"lead_id": lead_id, "quando": quando.isoformat(), "motivo": motivo},
        headers=cabecalho,
    )


def _listar(agent_id: str, cabecalho: dict, **params):
    return client.get(f"/api/v1/agents/{agent_id}/agendamentos",
                      headers=cabecalho, params=params)


class TestMarcar:
    @pytest.mark.asyncio
    async def test_marca_e_aparece_na_lista(self):
        cabecalho, dono = _login("a1")
        agent_id, lead_id = await _cenario("a1", dono)
        quando = datetime.utcnow() + timedelta(hours=3)

        r = _marcar(agent_id, cabecalho, lead_id, quando, "Coletar documentos")

        assert r.status_code == 201, r.text
        assert r.json()["criado_por"] == "Pessoa a1"
        lista = _listar(agent_id, cabecalho).json()
        assert [a["motivo"] for a in lista] == ["Coletar documentos"]

    @pytest.mark.asyncio
    async def test_o_operador_marca_porque_e_ele_quem_combina(self):
        cabecalho, dono = _login("a2")
        agent_id, lead_id = await _cenario("a2", dono)
        operador, _ = _login("a2op", papel="operador")

        r = _marcar(agent_id, operador, lead_id, datetime.utcnow() + timedelta(days=1))

        assert r.status_code == 201

    @pytest.mark.asyncio
    async def test_repetir_o_mesmo_horario_e_recusado(self):
        """
        Veio de defeito observado: três retornos para a mesma cliente às
        15:00, 15:03 e 15:06, todos "realizado". Não eram três combinações,
        era o mesmo clique repetido — e agenda com duplicata deixa de ser
        agenda.
        """
        cabecalho, dono = _login("a3")
        agent_id, lead_id = await _cenario("a3", dono)
        quando = datetime.utcnow() + timedelta(hours=5)

        assert _marcar(agent_id, cabecalho, lead_id, quando).status_code == 201
        repetido = _marcar(agent_id, cabecalho, lead_id, quando + timedelta(minutes=3))

        # 409 e não 422: o que a pessoa digitou está correto — o problema é
        # que o compromisso já existe.
        assert repetido.status_code == 409
        assert len(_listar(agent_id, cabecalho).json()) == 1

    @pytest.mark.asyncio
    async def test_outro_horario_no_mesmo_dia_e_legitimo(self):
        """Ligar de manhã e de tarde é combinação diferente, não duplicata."""
        cabecalho, dono = _login("a4")
        agent_id, lead_id = await _cenario("a4", dono)
        quando = datetime.utcnow() + timedelta(hours=5)

        _marcar(agent_id, cabecalho, lead_id, quando)
        r = _marcar(agent_id, cabecalho, lead_id, quando + timedelta(hours=4))

        assert r.status_code == 201
        assert len(_listar(agent_id, cabecalho).json()) == 2

    @pytest.mark.asyncio
    async def test_lead_de_outro_agente_e_404(self):
        cabecalho, dono = _login("a5")
        a, _ = await _cenario("a5a", dono)
        _b, lead_de_b = await _cenario("a5b", dono)

        assert _marcar(a, cabecalho, lead_de_b, datetime.utcnow()).status_code == 404


class TestOAtraso:
    @pytest.mark.asyncio
    async def test_retorno_vencido_vem_com_o_atraso(self):
        """A única informação pela qual esta tela existe."""
        cabecalho, dono = _login("b1")
        agent_id, lead_id = await _cenario("b1", dono)
        _marcar(agent_id, cabecalho, lead_id, datetime.utcnow() - timedelta(hours=2))

        agendamento = _listar(agent_id, cabecalho).json()[0]

        assert agendamento["minutos_de_atraso"] >= 119

    @pytest.mark.asyncio
    async def test_retorno_futuro_nao_esta_atrasado(self):
        cabecalho, dono = _login("b2")
        agent_id, lead_id = await _cenario("b2", dono)
        _marcar(agent_id, cabecalho, lead_id, datetime.utcnow() + timedelta(hours=2))

        assert _listar(agent_id, cabecalho).json()[0]["minutos_de_atraso"] == 0

    @pytest.mark.asyncio
    async def test_realizado_nao_conta_atraso(self):
        """
        Cumprido às 15h05 um retorno marcado para 15h não é uma dívida de
        cinco minutos — é um retorno cumprido.
        """
        cabecalho, dono = _login("b3")
        agent_id, lead_id = await _cenario("b3", dono)
        criado = _marcar(agent_id, cabecalho, lead_id,
                         datetime.utcnow() - timedelta(hours=3)).json()

        r = client.patch(f"/api/v1/agendamentos/{criado['id']}",
                         json={"status": "realizado"}, headers=cabecalho)

        assert r.status_code == 200
        assert r.json()["minutos_de_atraso"] == 0

    @pytest.mark.asyncio
    async def test_do_mais_atrasado_para_o_mais_distante(self):
        cabecalho, dono = _login("b4")
        agent_id, lead_id = await _cenario("b4", dono)
        _marcar(agent_id, cabecalho, lead_id, datetime.utcnow() + timedelta(days=2), "amanhã")
        _marcar(agent_id, cabecalho, lead_id, datetime.utcnow() - timedelta(days=1), "ontem")

        assert [a["motivo"] for a in _listar(agent_id, cabecalho).json()] == ["ontem", "amanhã"]


class TestFechar:
    @pytest.mark.asyncio
    async def test_realizado_sai_da_lista_de_pendencias(self):
        """
        Compromisso cumprido vira histórico, e histórico no meio da lista de
        tarefas esconde a tarefa.
        """
        cabecalho, dono = _login("c1")
        agent_id, lead_id = await _cenario("c1", dono)
        criado = _marcar(agent_id, cabecalho, lead_id,
                         datetime.utcnow() + timedelta(hours=1)).json()

        client.patch(f"/api/v1/agendamentos/{criado['id']}",
                     json={"status": "realizado"}, headers=cabecalho)

        assert _listar(agent_id, cabecalho).json() == []
        assert len(_listar(agent_id, cabecalho, incluir_fechados=True).json()) == 1

    @pytest.mark.asyncio
    async def test_cancelar_tambem_fecha(self):
        cabecalho, dono = _login("c2")
        agent_id, lead_id = await _cenario("c2", dono)
        criado = _marcar(agent_id, cabecalho, lead_id,
                         datetime.utcnow() + timedelta(hours=1)).json()

        client.patch(f"/api/v1/agendamentos/{criado['id']}",
                     json={"status": "cancelado"}, headers=cabecalho)

        assert _listar(agent_id, cabecalho).json() == []

    @pytest.mark.asyncio
    async def test_fechado_libera_o_horario_para_remarcar(self):
        """
        Remarcar depois de cancelar é o caminho normal; a trava de duplicata
        não pode impedir isso.
        """
        cabecalho, dono = _login("c3")
        agent_id, lead_id = await _cenario("c3", dono)
        quando = datetime.utcnow() + timedelta(hours=6)
        criado = _marcar(agent_id, cabecalho, lead_id, quando).json()
        client.patch(f"/api/v1/agendamentos/{criado['id']}",
                     json={"status": "cancelado"}, headers=cabecalho)

        assert _marcar(agent_id, cabecalho, lead_id, quando).status_code == 201

    @pytest.mark.asyncio
    async def test_situacao_invalida_e_recusada(self):
        cabecalho, dono = _login("c4")
        agent_id, lead_id = await _cenario("c4", dono)
        criado = _marcar(agent_id, cabecalho, lead_id,
                         datetime.utcnow() + timedelta(hours=1)).json()

        r = client.patch(f"/api/v1/agendamentos/{criado['id']}",
                         json={"status": "esquecido"}, headers=cabecalho)

        assert r.status_code == 422

    def test_agendamento_inexistente_e_404(self, client):
        cabecalho, _ = _login("c5")

        assert client.patch("/api/v1/agendamentos/nao-existe",
                            json={"status": "realizado"},
                            headers=cabecalho).status_code == 404


class TestAcesso:
    def test_sem_token_e_401(self, client):
        assert client.get("/api/v1/agents/x/agendamentos").status_code == 401

    @pytest.mark.asyncio
    async def test_agente_inexistente_e_404(self):
        cabecalho, _ = _login("d2")

        assert _listar("nao-existe", cabecalho).status_code == 404

    @pytest.mark.asyncio
    async def test_nao_mistura_agente(self):
        cabecalho, dono = _login("d3")
        a, lead_a = await _cenario("d3a", dono)
        b, lead_b = await _cenario("d3b", dono)
        _marcar(a, cabecalho, lead_a, datetime.utcnow() + timedelta(hours=1), "do A")
        _marcar(b, cabecalho, lead_b, datetime.utcnow() + timedelta(hours=1), "do B")

        assert [x["motivo"] for x in _listar(a, cabecalho).json()] == ["do A"]
