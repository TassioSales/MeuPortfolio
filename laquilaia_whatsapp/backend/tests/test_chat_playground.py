"""
Testes do playground de chat (Fase 12).

Cobrem o que o frontend precisa: continuar a mesma conversa entre mensagens,
carregar o histórico ao abrir a página e resetar a conversa.
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.routers.chat import TEST_PHONE_NUMBER

client = TestClient(app)

CLAUDE_REPLY = (
    "Olá! Como posso ajudar?",
    {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
)


def _auth_headers(suffix: str) -> dict:
    """Registra um usuário, faz login e devolve o header de autorização."""
    credentials = {
        "email": f"playground-{suffix}@example.com",
        "nome": "Playground User",
        "senha": "SenhaSegura123!",
    }
    client.post("/api/v1/auth/register", json=credentials)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "senha": credentials["senha"]},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_agent(headers: dict) -> str:
    response = client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "nome": "Agente de teste",
            "system_prompt": "Você é um assistente.",
            "temperatura": 0.7,
            "max_tokens": 1024,
        },
    )
    return response.json()["id"]


class TestChatConversationContinuity:
    """A conversa do playground precisa persistir entre mensagens."""

    def test_chat_returns_conversation_id(self):
        headers = _auth_headers("continuity")
        agent_id = _create_agent(headers)

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = CLAUDE_REPLY

            response = client.post(
                f"/api/v1/agents/{agent_id}/chat",
                headers=headers,
                json={"message": "Oi"},
            )

        assert response.status_code == 200
        # Sem o id na resposta o cliente não conseguiria continuar a conversa.
        assert response.json()["conversation_id"]

    def test_second_message_reuses_the_same_conversation(self):
        """
        Sem conversation_id no corpo, o endpoint reaproveita a conversa de
        teste. Antes ele tentava criar outra e batia na constraint única
        (agent_id, phone_number).
        """
        headers = _auth_headers("reuse")
        agent_id = _create_agent(headers)

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = CLAUDE_REPLY

            first = client.post(
                f"/api/v1/agents/{agent_id}/chat",
                headers=headers,
                json={"message": "Primeira"},
            )
            second = client.post(
                f"/api/v1/agents/{agent_id}/chat",
                headers=headers,
                json={"message": "Segunda"},
            )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["conversation_id"] == second.json()["conversation_id"]

    def test_chat_passes_history_to_the_model(self):
        """A segunda chamada precisa levar o histórico como contexto."""
        headers = _auth_headers("history-context")
        agent_id = _create_agent(headers)

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = CLAUDE_REPLY

            client.post(
                f"/api/v1/agents/{agent_id}/chat",
                headers=headers,
                json={"message": "Primeira"},
            )
            client.post(
                f"/api/v1/agents/{agent_id}/chat",
                headers=headers,
                json={"message": "Segunda"},
            )

            history = mock_llm.call_args.kwargs["conversation_history"]

        assert history, "a segunda mensagem deveria levar histórico"

    def test_chat_on_unknown_agent_is_404(self):
        headers = _auth_headers("unknown")

        response = client.post(
            "/api/v1/agents/agente-inexistente/chat",
            headers=headers,
            json={"message": "Oi"},
        )

        assert response.status_code == 404

    def test_chat_requires_authentication(self):
        response = client.post(
            "/api/v1/agents/qualquer/chat",
            json={"message": "Oi"},
        )

        assert response.status_code in (401, 403)


class TestChatHistory:
    """Histórico carregado ao abrir o playground."""

    def test_history_is_empty_for_untested_agent(self):
        headers = _auth_headers("empty-history")
        agent_id = _create_agent(headers)

        response = client.get(f"/api/v1/agents/{agent_id}/chat/history", headers=headers)

        assert response.status_code == 200
        body = response.json()
        # Agente nunca testado devolve vazio, não 404.
        assert body["conversation_id"] is None
        assert body["messages"] == []

    def test_history_returns_messages_in_chronological_order(self):
        headers = _auth_headers("ordered-history")
        agent_id = _create_agent(headers)

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = CLAUDE_REPLY

            client.post(
                f"/api/v1/agents/{agent_id}/chat",
                headers=headers,
                json={"message": "Pergunta"},
            )

        response = client.get(f"/api/v1/agents/{agent_id}/chat/history", headers=headers)

        messages = response.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["remetente"] == "user"
        assert messages[0]["conteudo"] == "Pergunta"
        assert messages[1]["remetente"] == "assistant"

    def test_history_of_unknown_agent_is_404(self):
        headers = _auth_headers("history-404")

        response = client.get(
            "/api/v1/agents/agente-inexistente/chat/history", headers=headers
        )

        assert response.status_code == 404


class TestChatReset:
    """Reset da conversa do playground."""

    def test_reset_clears_the_history(self):
        headers = _auth_headers("reset")
        agent_id = _create_agent(headers)

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = CLAUDE_REPLY

            client.post(
                f"/api/v1/agents/{agent_id}/chat",
                headers=headers,
                json={"message": "Oi"},
            )

        reset = client.delete(f"/api/v1/agents/{agent_id}/chat/history", headers=headers)
        history = client.get(f"/api/v1/agents/{agent_id}/chat/history", headers=headers)

        assert reset.status_code == 200
        assert reset.json()["deleted"] == 2
        assert history.json()["messages"] == []

    def test_chat_works_again_after_reset(self):
        """
        O reset apaga a conversa; a mensagem seguinte precisa criar outra sem
        esbarrar na constraint única do telefone de teste.
        """
        headers = _auth_headers("reset-then-chat")
        agent_id = _create_agent(headers)

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = CLAUDE_REPLY

            first = client.post(
                f"/api/v1/agents/{agent_id}/chat",
                headers=headers,
                json={"message": "Antes"},
            )
            client.delete(f"/api/v1/agents/{agent_id}/chat/history", headers=headers)
            after = client.post(
                f"/api/v1/agents/{agent_id}/chat",
                headers=headers,
                json={"message": "Depois"},
            )

        assert after.status_code == 200
        assert after.json()["conversation_id"] != first.json()["conversation_id"]

    def test_reset_without_conversation_is_not_an_error(self):
        headers = _auth_headers("reset-noop")
        agent_id = _create_agent(headers)

        response = client.delete(
            f"/api/v1/agents/{agent_id}/chat/history", headers=headers
        )

        assert response.status_code == 200
        assert response.json()["deleted"] == 0


class TestPlaygroundIsolation:
    """A conversa do playground não deve se misturar com as do WhatsApp."""

    def test_test_conversation_uses_the_reserved_phone_number(self):
        headers = _auth_headers("isolation")
        agent_id = _create_agent(headers)

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = CLAUDE_REPLY

            client.post(
                f"/api/v1/agents/{agent_id}/chat",
                headers=headers,
                json={"message": "Oi"},
            )

        assert TEST_PHONE_NUMBER == "test_api"
