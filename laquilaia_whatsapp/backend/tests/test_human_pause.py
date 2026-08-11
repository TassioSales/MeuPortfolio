"""
Testes da pausa humana (Fase 16).

O ponto crítico é o orquestrador: com a conversa pausada a mensagem do cliente
ainda é registrada, mas a IA não responde — senão operador e agente falariam
ao mesmo tempo com o cliente.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.db.database import AsyncSessionLocal
from app.db.models import Agent, Conversation, Message, User
from app.services.message_orchestrator import orchestrator

client = TestClient(app)


def _login(suffix: str) -> dict:
    creds = {
        "email": f"pause-{suffix}@example.com",
        "nome": "Pause User",
        "senha": "SenhaSegura123!",
    }
    client.post("/api/v1/auth/register", json=creds)
    r = client.post(
        "/api/v1/auth/login", json={"email": creds["email"], "senha": creds["senha"]}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _seed(agent_id: str, user_id: str, conv_id: str) -> None:
    async with AsyncSessionLocal() as db:
        db.add(
            User(id=user_id, email=f"{user_id}@x.com", nome="Dono",
                 senha_hash="x", status="ativo")
        )
        await db.flush()
        db.add(
            Agent(id=agent_id, user_id=user_id, nome="Agente",
                  system_prompt="p", temperatura=0.7, max_tokens=1024, status="ativo")
        )
        await db.flush()
        db.add(
            Conversation(id=conv_id, agent_id=agent_id,
                         phone_number="5561900001111", status="ativa")
        )
        await db.commit()


class TestOrchestratorRespectsPause:
    @pytest.mark.asyncio
    async def test_paused_conversation_does_not_call_the_model(self):
        await _seed("ag-pause", "user-pause", "conv-pause")

        async with AsyncSessionLocal() as db:
            conv = (await db.execute(
                select(Conversation).where(Conversation.id == "conv-pause")
            )).scalars().first()
            conv.status = "pausada"
            await db.commit()

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm:
            async with AsyncSessionLocal() as db:
                result = await orchestrator.process_incoming_message(
                    "ag-pause", "5561900001111", "Oi", db
                )

        assert result["paused"] is True
        assert result["response"] is None
        # O que realmente importa: nada de chamada paga ao Claude.
        mock_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_paused_conversation_still_records_the_message(self):
        await _seed("ag-rec", "user-rec", "conv-rec")

        async with AsyncSessionLocal() as db:
            conv = (await db.execute(
                select(Conversation).where(Conversation.id == "conv-rec")
            )).scalars().first()
            conv.status = "pausada"
            await db.commit()

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ):
            async with AsyncSessionLocal() as db:
                await orchestrator.process_incoming_message(
                    "ag-rec", "5561900001111", "Preciso de ajuda", db
                )

        async with AsyncSessionLocal() as db:
            msgs = (await db.execute(
                select(Message).where(Message.conversation_id == "conv-rec")
            )).scalars().all()

        # A mensagem do cliente não pode se perder: o operador precisa vê-la.
        assert len(msgs) == 1
        assert msgs[0].remetente == "user"
        assert msgs[0].conteudo == "Preciso de ajuda"

    @pytest.mark.asyncio
    async def test_active_conversation_still_answers(self):
        await _seed("ag-act", "user-act", "conv-act")

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm, patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new_callable=AsyncMock,
        ) as mock_wa:
            mock_llm.return_value = ("Claro!", {"input_tokens": 1, "output_tokens": 1,
                                                "total_tokens": 2})
            mock_wa.return_value = {"success": True, "message_id": "m1"}

            async with AsyncSessionLocal() as db:
                result = await orchestrator.process_incoming_message(
                    "ag-act", "5561900001111", "Oi", db
                )

        assert result.get("paused") is None
        mock_llm.assert_awaited_once()


class TestPauseEndpoints:
    def _agent_and_conversation(self, headers: dict) -> str:
        agent_id = client.post(
            "/api/v1/agents", headers=headers,
            json={"nome": "A", "system_prompt": "p", "temperatura": 0.7,
                  "max_tokens": 1024},
        ).json()["id"]

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = ("oi", {"input_tokens": 1, "output_tokens": 1,
                                            "total_tokens": 2})
            r = client.post(
                f"/api/v1/agents/{agent_id}/chat", headers=headers,
                json={"message": "Oi"},
            )
        return r.json()["conversation_id"]

    def test_pause_then_resume(self):
        headers = _login("endpoints")
        conv_id = self._agent_and_conversation(headers)

        pausa = client.post(f"/api/v1/conversations/{conv_id}/pause", headers=headers)
        assert pausa.status_code == 200
        assert pausa.json()["ia_ativa"] is False

        retoma = client.post(f"/api/v1/conversations/{conv_id}/resume", headers=headers)
        assert retoma.status_code == 200
        assert retoma.json()["ia_ativa"] is True

    def test_status_reflects_the_pause(self):
        headers = _login("status")
        conv_id = self._agent_and_conversation(headers)

        client.post(f"/api/v1/conversations/{conv_id}/pause", headers=headers)
        body = client.get(
            f"/api/v1/conversations/{conv_id}/status", headers=headers
        ).json()

        assert body["status"] == "pausada"
        assert body["ia_ativa"] is False

    def test_requires_authentication(self):
        r = client.post("/api/v1/conversations/qualquer/pause")

        assert r.status_code in (401, 403)

    def test_cannot_pause_another_users_conversation(self):
        dono = _login("dono")
        conv_id = self._agent_and_conversation(dono)
        intruso = _login("intruso")

        r = client.post(f"/api/v1/conversations/{conv_id}/pause", headers=intruso)

        assert r.status_code == 404

    def test_unknown_conversation_is_404(self):
        headers = _login("desconhecida")

        r = client.post("/api/v1/conversations/nao-existe/pause", headers=headers)

        assert r.status_code == 404
