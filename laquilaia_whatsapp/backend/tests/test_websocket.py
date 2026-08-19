"""
Testes do canal de tempo real.

A versão anterior do WebSocket não tinha autenticação e retransmitia o que o
cliente enviava — qualquer conexão anônima podia injetar conteúdo falso no
painel de todo mundo no mesmo canal. Os testes abaixo fixam as duas correções.
"""
from tests.conftest import criar_acesso

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.main import app
from app.ws.manager import (
    ConnectionManager,
    EVENT_LEAD_MOVED,
    EVENT_NEW_MESSAGE,
    notify_lead_moved,
    notify_new_message,
)

client = TestClient(app)


def _register_and_login(suffix: str, papel: str = "admin") -> tuple[dict, str]:
    credentials = {
        "email": f"ws-{suffix}@example.com",
        "nome": "WS User",
        "senha": "SenhaSegura123!",
    }
    criar_acesso(client, credentials["email"], credentials["senha"],
                 credentials.get("nome", "Teste"), papel=papel)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "senha": credentials["senha"]},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, token


def _create_agent(headers: dict) -> str:
    response = client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "nome": "Agente WS",
            "system_prompt": "prompt",
            "temperatura": 0.7,
            "max_tokens": 1024,
        },
    )
    return response.json()["id"]


class TestWebSocketAuthorization:
    """A conexão é recusada antes do accept quando não deve existir."""

    def test_rejects_connection_without_token(self):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/agents/qualquer"):
                pass

    def test_rejects_invalid_token(self):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/agents/qualquer?token=token-falso"):
                pass

    def test_aceita_o_operador_no_agente_do_admin(self):
        """
        O socket é o que faz a fila de atendimentos se atualizar sozinha.

        Este caso já esperava recusa, sob o nome de "agente de outro usuário".
        Recusar aqui deixaria o operador com uma tela que só muda se ele
        apertar F5 — justamente a pessoa que fica o dia inteiro nela.
        """
        admin_headers, _ = _register_and_login("owner")
        agent_id = _create_agent(admin_headers)
        _, token_do_operador = _register_and_login("operador", papel="operador")

        with client.websocket_connect(
            f"/ws/agents/{agent_id}?token={token_do_operador}"
        ) as ws:
            assert ws is not None

    def test_recusa_agente_que_nao_existe(self):
        _, token = _register_and_login("sem-agente")

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/agents/nao-existe?token={token}"):
                pass

    def test_recusa_conta_desativada(self):
        """
        A revogação imediata vale para o socket também.

        O REST passou a conferir o status a cada requisição. Um socket já
        aberto — ou aberto depois — com token de conta desativada faria essa
        revogação valer pela metade: quem saiu do escritório continuaria
        vendo lead novo chegar em tempo real.
        """
        admin_headers, _ = _register_and_login("dono-revoga")
        agent_id = _create_agent(admin_headers)
        _, token = _register_and_login("desativado", papel="operador")

        alvo = next(
            u
            for u in client.get("/api/v1/auth/users", headers=admin_headers).json()
            if u["email"] == "ws-desativado@example.com"
        )
        client.patch(
            f"/api/v1/auth/users/{alvo['id']}",
            json={"status": "inativo"},
            headers=admin_headers,
        )

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/agents/{agent_id}?token={token}"):
                pass

    def test_accepts_the_agent_owner(self):
        headers, token = _register_and_login("dono")
        agent_id = _create_agent(headers)

        with client.websocket_connect(f"/ws/agents/{agent_id}?token={token}") as ws:
            assert ws is not None


class TestConnectionManager:
    """Comportamento do gerenciador de canais."""

    @pytest.mark.asyncio
    async def test_broadcast_reaches_every_socket_of_the_channel(self):
        manager = ConnectionManager()
        socket_a, socket_b = AsyncMock(), AsyncMock()
        await manager.connect("agent-1", socket_a)
        await manager.connect("agent-1", socket_b)

        entregues = await manager.broadcast("agent-1", {"type": "teste"})

        assert entregues == 2
        socket_a.send_json.assert_awaited_once_with({"type": "teste"})
        socket_b.send_json.assert_awaited_once_with({"type": "teste"})

    @pytest.mark.asyncio
    async def test_channels_are_isolated_per_agent(self):
        manager = ConnectionManager()
        socket_a, socket_b = AsyncMock(), AsyncMock()
        await manager.connect("agent-1", socket_a)
        await manager.connect("agent-2", socket_b)

        await manager.broadcast("agent-1", {"type": "teste"})

        socket_a.send_json.assert_awaited_once()
        # Quem está em outro agente não pode receber o evento.
        socket_b.send_json.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_channel_is_a_noop(self):
        manager = ConnectionManager()

        assert await manager.broadcast("sem-ninguem", {"type": "teste"}) == 0

    @pytest.mark.asyncio
    async def test_dead_socket_is_removed_instead_of_accumulating(self):
        manager = ConnectionManager()
        vivo, morto = AsyncMock(), AsyncMock()
        morto.send_json.side_effect = RuntimeError("socket fechado")
        await manager.connect("agent-1", vivo)
        await manager.connect("agent-1", morto)

        entregues = await manager.broadcast("agent-1", {"type": "teste"})

        assert entregues == 1
        assert manager.connection_count("agent-1") == 1

    @pytest.mark.asyncio
    async def test_disconnect_drops_the_channel_when_empty(self):
        manager = ConnectionManager()
        socket = AsyncMock()
        await manager.connect("agent-1", socket)

        manager.disconnect("agent-1", socket)

        assert manager.connection_count("agent-1") == 0

    @pytest.mark.asyncio
    async def test_disconnect_of_unknown_socket_does_not_raise(self):
        manager = ConnectionManager()

        manager.disconnect("agent-inexistente", AsyncMock())


class TestEvents:
    """Formato dos eventos — é o contrato com o frontend."""

    @pytest.mark.asyncio
    async def test_lead_moved_event_shape(self, monkeypatch):
        recebidos = []

        async def fake_broadcast(agent_id, event):
            recebidos.append((agent_id, event))
            return 1

        monkeypatch.setattr(
            "app.ws.manager.connection_manager.broadcast", fake_broadcast
        )

        await notify_lead_moved("agent-1", "lead-1", "col-2", "qualificado")

        agent_id, event = recebidos[0]
        assert agent_id == "agent-1"
        assert event == {
            "type": EVENT_LEAD_MOVED,
            "lead_id": "lead-1",
            "column_id": "col-2",
            "status_funil": "qualificado",
        }

    @pytest.mark.asyncio
    async def test_new_message_event_carries_no_content(self, monkeypatch):
        recebidos = []

        async def fake_broadcast(agent_id, event):
            recebidos.append(event)
            return 1

        monkeypatch.setattr(
            "app.ws.manager.connection_manager.broadcast", fake_broadcast
        )

        await notify_new_message("agent-1", "conv-1", "5561999990000")

        event = recebidos[0]
        assert event["type"] == EVENT_NEW_MESSAGE
        assert event["conversation_id"] == "conv-1"
        # O conteúdo da mensagem não trafega pelo socket: quem precisa dele
        # busca pela API, que aplica a checagem de dono.
        assert "conteudo" not in event
        assert "message" not in event
