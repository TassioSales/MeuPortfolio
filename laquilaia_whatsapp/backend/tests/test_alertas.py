"""
O alerta de cliente esperando.

O painel mostrava conversas e leads; não mostrava omissão. Alguém que
escreveu de madrugada e não teve resposta ficava com a mesma cara de quem foi
atendido — e o escritório descobria pelo cliente reclamando.

O que estes casos travam é o critério: a última palavra da conversa é do
cliente, e faz tempo. E a separação entre quem deve a resposta, porque "a IA
caiu" e "o operador foi almoçar" não são o mesmo problema.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db.database import AsyncSessionLocal
from app.db.models import Agent, Conversation, Lead, Message, User
from app.main import app
from app.services.auth_service import AuthService
from tests.conftest import criar_acesso

client = TestClient(app)

ROTA = "/api/v1/agents/{}/alertas"


def _login(sufixo: str) -> tuple[dict, str]:
    email = f"alerta-{sufixo}@example.com"
    criar_acesso(client, email, "SenhaSegura123!", "Dono")
    r = client.post("/api/v1/auth/login", json={"email": email, "senha": "SenhaSegura123!"})
    cabecalho = {"Authorization": f"Bearer {r.json()['access_token']}"}
    eu = client.get("/api/v1/auth/me", headers=cabecalho).json()
    return cabecalho, eu["id"]


async def _agente(sufixo: str, dono: str) -> str:
    async with AsyncSessionLocal() as db:
        db.add(
            Agent(
                id=f"ag-{sufixo}",
                user_id=dono,
                nome="Triagem",
                system_prompt="p",
                temperatura=0.4,
                max_tokens=1024,
                status="ativo",
            )
        )
        await db.commit()
    return f"ag-{sufixo}"


async def _conversa(
    agent_id: str,
    conv_id: str,
    *,
    status: str = "ativa",
    minutos_atras: int = 60,
    quem_falou_por_ultimo: str = "user",
    nome_do_lead: str | None = None,
    texto: str = "e aí, tem novidade?",
):
    """
    Uma conversa cuja última mensagem tem a idade pedida.

    A primeira mensagem é sempre do cliente e vem antes; assim a conversa tem
    histórico de verdade e o teste não passa por acidente de só existir uma
    linha.
    """
    quando = datetime.utcnow() - timedelta(minutes=minutos_atras)

    async with AsyncSessionLocal() as db:
        db.add(
            Conversation(
                id=conv_id,
                agent_id=agent_id,
                phone_number=f"5561{abs(hash(conv_id)) % 100000000:08d}",
                status=status,
                data_ultima_msg=quando,
            )
        )
        await db.flush()

        db.add(
            Message(
                conversation_id=conv_id,
                remetente="user",
                conteudo="oi, boa noite",
                timestamp=quando - timedelta(minutes=5),
            )
        )
        db.add(
            Message(
                conversation_id=conv_id,
                remetente=quem_falou_por_ultimo,
                conteudo=texto,
                timestamp=quando,
            )
        )

        if nome_do_lead:
            db.add(
                Lead(
                    conversation_id=conv_id,
                    nome=nome_do_lead,
                    phone_number="5561999990000",
                    status_funil="novo",
                )
            )

        await db.commit()


def _buscar(agent_id: str, cabecalho: dict, **params):
    return client.get(ROTA.format(agent_id), headers=cabecalho, params=params)


class TestQuemEntraNoAlerta:
    @pytest.mark.asyncio
    async def test_cliente_falou_e_ninguem_respondeu(self):
        cabecalho, dono = _login("a1")
        agent_id = await _agente("a1", dono)
        await _conversa(agent_id, "conv-a1", minutos_atras=90, nome_do_lead="Marina")

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["total_ia"] == 1
        alerta = dados["conversas"][0]
        assert alerta["conversation_id"] == "conv-a1"
        assert alerta["lead_nome"] == "Marina"
        assert alerta["minutos_esperando"] >= 89

    @pytest.mark.asyncio
    async def test_conversa_respondida_nao_alerta(self):
        """
        O critério é a **última** palavra ser do cliente. Uma conversa com dez
        mensagens dele e uma resposta no fim está atendida.
        """
        cabecalho, dono = _login("a2")
        agent_id = await _agente("a2", dono)
        await _conversa(
            agent_id, "conv-a2", minutos_atras=300, quem_falou_por_ultimo="assistant"
        )

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["conversas"] == []

    @pytest.mark.asyncio
    async def test_mensagem_recente_ainda_nao_e_abandono(self):
        """
        Cinco minutos é a pessoa digitando; meia hora é abandono. Alertar cedo
        demais treina o escritório a ignorar o alerta.
        """
        cabecalho, dono = _login("a3")
        agent_id = await _agente("a3", dono)
        await _conversa(agent_id, "conv-a3", minutos_atras=5)

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["conversas"] == []

    @pytest.mark.asyncio
    async def test_conversa_encerrada_nao_e_pendencia(self):
        """
        "Obrigado" como última mensagem de uma conversa encerrada é desfecho
        normal, não silêncio do escritório.
        """
        cabecalho, dono = _login("a4")
        agent_id = await _agente("a4", dono)
        await _conversa(agent_id, "conv-a4", status="encerrada", minutos_atras=500)

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["conversas"] == []

    @pytest.mark.asyncio
    async def test_conversa_sem_mensagem_nenhuma_nao_quebra(self):
        cabecalho, dono = _login("a5")
        agent_id = await _agente("a5", dono)
        async with AsyncSessionLocal() as db:
            db.add(
                Conversation(
                    id="conv-a5", agent_id=agent_id, phone_number="5561900000000",
                    status="ativa",
                )
            )
            await db.commit()

        resposta = _buscar(agent_id, cabecalho)

        assert resposta.status_code == 200
        assert resposta.json()["conversas"] == []


class TestDeQuemEADivida:
    @pytest.mark.asyncio
    async def test_conversa_no_automatico_cobra_a_ia(self):
        cabecalho, dono = _login("b1")
        agent_id = await _agente("b1", dono)
        await _conversa(agent_id, "conv-b1", status="ativa", minutos_atras=45)

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["conversas"][0]["tipo"] == "ia_sem_resposta"
        assert (dados["total_ia"], dados["total_humano"]) == (1, 0)

    @pytest.mark.asyncio
    async def test_conversa_assumida_cobra_o_humano(self):
        """
        Alguém pausou a IA e não voltou. Não é defeito de software — e o
        alerta não pode dizer que é, senão o escritório vai procurar bug onde
        o que faltou foi gente.
        """
        cabecalho, dono = _login("b2")
        agent_id = await _agente("b2", dono)
        await _conversa(agent_id, "conv-b2", status="pausada", minutos_atras=45)

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["conversas"][0]["tipo"] == "humano_sem_resposta"
        assert (dados["total_ia"], dados["total_humano"]) == (0, 1)


class TestOrdemELimite:
    @pytest.mark.asyncio
    async def test_quem_espera_ha_mais_tempo_vem_primeiro(self):
        cabecalho, dono = _login("c1")
        agent_id = await _agente("c1", dono)
        await _conversa(agent_id, "conv-novo", minutos_atras=40)
        await _conversa(agent_id, "conv-antigo", minutos_atras=600)

        dados = _buscar(agent_id, cabecalho).json()

        assert [c["conversation_id"] for c in dados["conversas"]] == [
            "conv-antigo",
            "conv-novo",
        ]

    @pytest.mark.asyncio
    async def test_o_total_conta_alem_do_que_a_lista_mostra(self):
        """
        A lista é truncada para a tela não morrer; o número não pode ser.
        Um escritório com 300 pessoas esperando precisa ler 300, não 5.
        """
        cabecalho, dono = _login("c2")
        agent_id = await _agente("c2", dono)
        for i in range(6):
            await _conversa(agent_id, f"conv-c2-{i}", minutos_atras=60 + i)

        dados = _buscar(agent_id, cabecalho, limite=2).json()

        assert len(dados["conversas"]) == 2
        assert dados["total_ia"] == 6

    @pytest.mark.asyncio
    async def test_o_limite_de_minutos_e_configuravel(self):
        cabecalho, dono = _login("c3")
        agent_id = await _agente("c3", dono)
        await _conversa(agent_id, "conv-c3", minutos_atras=10)

        assert _buscar(agent_id, cabecalho).json()["conversas"] == []
        assert len(_buscar(agent_id, cabecalho, minutos=5).json()["conversas"]) == 1


class TestAcesso:
    @pytest.mark.asyncio
    async def test_operador_ve_os_alertas(self):
        """É ele quem vai agir sobre a lista; escondê-la seria o alerta inútil."""
        cabecalho, dono = _login("d1")
        agent_id = await _agente("d1", dono)
        await _conversa(agent_id, "conv-d1", minutos_atras=60)

        criar_acesso(client, "operador-alerta@example.com", "SenhaDoOperador123",
                     "Operador", papel="operador")
        login = client.post("/api/v1/auth/login", json={
            "email": "operador-alerta@example.com", "senha": "SenhaDoOperador123",
        })
        operador = {"Authorization": f"Bearer {login.json()['access_token']}"}

        resposta = _buscar(agent_id, operador)

        assert resposta.status_code == 200
        assert len(resposta.json()["conversas"]) == 1

    def test_sem_token_e_401(self):
        assert client.get(ROTA.format("qualquer")).status_code == 401

    @pytest.mark.asyncio
    async def test_agente_inexistente_e_404(self):
        cabecalho, _ = _login("d2")

        assert _buscar("nao-existe", cabecalho).status_code == 404

    @pytest.mark.asyncio
    async def test_alerta_de_um_agente_nao_traz_conversa_de_outro(self):
        """
        Um escritório pode ter mais de um agente. O alerta é por agente porque
        é assim que a tela é filtrada — misturar faria o operador do agente A
        ver pendência que não é dele.
        """
        cabecalho, dono = _login("d3")
        agente_a = await _agente("d3a", dono)
        agente_b = await _agente("d3b", dono)
        await _conversa(agente_a, "conv-d3a", minutos_atras=60)
        await _conversa(agente_b, "conv-d3b", minutos_atras=60)

        dados = _buscar(agente_a, cabecalho).json()

        assert [c["conversation_id"] for c in dados["conversas"]] == ["conv-d3a"]
