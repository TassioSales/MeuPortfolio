"""
Quanto custa cada lead, e cada lead qualificado.

É o único número que diz se o sistema se paga, e era o que faltava: o painel
tinha volume e conversão, e nenhum custo — então "vale a pena?" só tinha
resposta no chute.

O gasto com anúncio entra à mão porque só o escritório sabe. O consumo de IA
não: sai de `messages.tokens_usados`. Metade destes casos cobre a aritmética
do dinheiro, que é onde erro passa despercebido por meses.
"""

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Agent,
    Conversation,
    LancamentoMarketing,
    Lead,
    LeadDetails,
    Message,
)
from app.main import app
from tests.conftest import criar_acesso

client = TestClient(app)

LANCAMENTOS = "/api/v1/marketing/lancamentos"


def _login(sufixo: str, papel: str = "admin") -> tuple[dict, str]:
    email = f"mkt-{sufixo}@example.com"
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
        await db.commit()
    return agent_id


async def _lead(agent_id: str, sufixo: str, *, score: int = 0, tokens: int = 0,
                dias_atras: int = 1):
    quando = datetime.utcnow() - timedelta(days=dias_atras)
    async with AsyncSessionLocal() as db:
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=agent_id,
                            phone_number=f"5561{sufixo}", status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}", nome="X",
                    phone_number=f"5561{sufixo}", status_funil="novo",
                    data_criacao=quando))
        await db.flush()
        if score:
            db.add(LeadDetails(lead_id=f"lead-{sufixo}", score_qualificacao=score))
        if tokens:
            db.add(Message(conversation_id=f"cv-{sufixo}", remetente="assistant",
                           conteudo="oi", tokens_usados=tokens, timestamp=quando))
        await db.commit()


def _resumo(agent_id: str, cabecalho: dict, **params):
    return client.get(f"/api/v1/agents/{agent_id}/marketing/resumo",
                      headers=cabecalho, params=params)


class TestOLancamento:
    def test_lanca_e_lista(self, client):
        cabecalho, _ = _login("a1")

        r = client.post(LANCAMENTOS, json={"data": str(date.today()),
                                           "investimento_ads": 250.50,
                                           "observacao": "Meta Ads"},
                        headers=cabecalho)

        assert r.status_code == 201
        assert r.json()["investimento_ads"] == 250.50
        assert client.get(LANCAMENTOS, headers=cabecalho).json()[0]["observacao"] == "Meta Ads"

    def test_o_centavo_nao_se_perde_no_ponto_flutuante(self, client):
        """
        `int(19.99 * 100)` é 1998, não 1999. Um centavo por lançamento vira
        conta que não fecha com o extrato no fim do mês — e um relatório que
        não fecha ninguém usa duas vezes.
        """
        cabecalho, _ = _login("a2")
        client.post(LANCAMENTOS, json={"data": str(date.today()),
                                       "investimento_ads": 19.99}, headers=cabecalho)

        assert client.get(LANCAMENTOS, headers=cabecalho).json()[0]["investimento_ads"] == 19.99

    def test_registra_quem_lancou(self, client):
        cabecalho, _ = _login("a4")

        client.post(LANCAMENTOS, json={"data": str(date.today()),
                                       "investimento_ads": 10}, headers=cabecalho)

        assert client.get(LANCAMENTOS, headers=cabecalho).json()[0]["criado_por"] == "Pessoa a4"

    def test_apagar_conserta_o_dedo_gordo(self, client):
        """Digitar 1900 no lugar de 190 tem de ter conserto."""
        cabecalho, _ = _login("a5")
        criado = client.post(LANCAMENTOS, json={"data": str(date.today()),
                                                "investimento_ads": 1900},
                             headers=cabecalho).json()

        r = client.delete(f"{LANCAMENTOS}/{criado['id']}", headers=cabecalho)

        assert r.status_code == 204
        assert client.get(LANCAMENTOS, headers=cabecalho).json() == []

    def test_valor_negativo_e_recusado(self, client):
        cabecalho, _ = _login("a6")

        r = client.post(LANCAMENTOS, json={"data": str(date.today()),
                                           "investimento_ads": -50}, headers=cabecalho)

        assert r.status_code == 422

    def test_operador_nao_lanca_dinheiro(self, client):
        cabecalho, _ = _login("a7")
        operador, _ = _login("a7op", papel="operador")

        r = client.post(LANCAMENTOS, json={"data": str(date.today()),
                                           "investimento_ads": 100}, headers=operador)

        assert r.status_code == 404
        assert client.get(LANCAMENTOS, headers=cabecalho).json() == []

    def test_operador_le_os_lancamentos(self, client):
        cabecalho, _ = _login("a8")
        client.post(LANCAMENTOS, json={"data": str(date.today()),
                                       "investimento_ads": 100}, headers=cabecalho)
        operador, _ = _login("a8op", papel="operador")

        assert len(client.get(LANCAMENTOS, headers=operador).json()) == 1


class TestOResumo:
    @pytest.mark.asyncio
    async def test_custo_por_lead_e_por_qualificado(self):
        """
        O segundo é o que decide: um anúncio pode trazer cem pessoas baratas e
        nenhuma da área, e ainda assim parecer excelente no custo por lead.
        """
        cabecalho, dono = _login("b1")
        agent_id = await _agente("b1", dono)
        client.post(LANCAMENTOS, json={"data": str(date.today()),
                                       "investimento_ads": 300}, headers=cabecalho)
        await _lead(agent_id, "b1a", score=85)
        await _lead(agent_id, "b1b", score=20)
        await _lead(agent_id, "b1c", score=0)

        dados = _resumo(agent_id, cabecalho).json()

        assert dados["leads"] == 3
        assert dados["leads_qualificados"] == 1
        assert dados["custo_por_lead"] == 100.0
        assert dados["custo_por_lead_qualificado"] == 300.0

    @pytest.mark.asyncio
    async def test_sem_lead_nenhum_o_custo_e_nulo_e_nao_infinito(self):
        """Um painel que mostra ∞ como custo é um painel que ninguém acredita."""
        cabecalho, dono = _login("b2")
        agent_id = await _agente("b2", dono)
        client.post(LANCAMENTOS, json={"data": str(date.today()),
                                       "investimento_ads": 500}, headers=cabecalho)

        dados = _resumo(agent_id, cabecalho).json()

        assert dados["custo_por_lead"] is None
        assert dados["custo_por_lead_qualificado"] is None

    @pytest.mark.asyncio
    async def test_o_consumo_de_ia_vem_do_banco_e_nao_da_digitacao(self):
        cabecalho, dono = _login("b3")
        agent_id = await _agente("b3", dono)
        await _lead(agent_id, "b3a", tokens=1200)
        await _lead(agent_id, "b3b", tokens=800)

        assert _resumo(agent_id, cabecalho).json()["tokens_consumidos"] == 2000

    @pytest.mark.asyncio
    async def test_o_recorte_de_dias_vale_para_tudo(self):
        cabecalho, dono = _login("b4")
        agent_id = await _agente("b4", dono)
        await _lead(agent_id, "b4a", tokens=100, dias_atras=2)
        await _lead(agent_id, "b4b", tokens=900, dias_atras=200)

        dados = _resumo(agent_id, cabecalho).json()

        assert dados["leads"] == 1
        assert dados["tokens_consumidos"] == 100

    @pytest.mark.asyncio
    async def test_nao_mistura_o_consumo_de_outro_agente(self):
        cabecalho, dono = _login("b5")
        a = await _agente("b5a", dono)
        b = await _agente("b5b", dono)
        await _lead(a, "b5a", tokens=100)
        await _lead(b, "b5b", tokens=900)

        assert _resumo(a, cabecalho).json()["tokens_consumidos"] == 100

    @pytest.mark.asyncio
    async def test_operador_ve_o_resumo(self):
        cabecalho, dono = _login("b6")
        agent_id = await _agente("b6", dono)
        operador, _ = _login("b6op", papel="operador")

        assert _resumo(agent_id, operador).status_code == 200

    def test_sem_token_e_401(self, client):
        assert client.get("/api/v1/agents/x/marketing/resumo").status_code == 401

    @pytest.mark.asyncio
    async def test_agente_inexistente_e_404(self):
        cabecalho, _ = _login("b8")

        assert _resumo("nao-existe", cabecalho).status_code == 404
