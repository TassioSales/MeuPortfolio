"""Tests for webhook and message orchestration."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app
from app.models.webhook_models import WebhookPayload
from app.db.models import Conversation, Message

client = TestClient(app)


class TestWebhookIntegration:
    """Test webhook message processing."""

    def setup_method(self, method):
        """Setup test user, login, and create test agent."""
        self.user_data = {
            "email": f"test-{method.__name__}@example.com",
            "nome": "Test User",
            "senha": "TestPassword123!",
        }
        client.post("/api/v1/auth/register", json=self.user_data)

        login_response = client.post("/api/v1/auth/login", json={
            "email": self.user_data["email"],
            "senha": self.user_data["senha"],
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Create test agent
        agent_data = {
            "nome": "Test Webhook Agent",
            "descricao": "Agent for webhook testing",
            "system_prompt": "Você é um assistente de atendimento.",
            "temperatura": 0.7,
            "max_tokens": 1024,
        }
        create_response = client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=self.headers,
        )
        self.agent_id = create_response.json()["id"]

    @patch("app.services.whatsapp_service.whatsapp_service.send_message")
    @patch("app.services.llm_service.llm_service.generate_response")
    def test_webhook_message_processing(self, mock_llm, mock_whatsapp):
        """Test webhook receives and processes message."""
        # Mock Claude response
        mock_llm.return_value = (
            "Olá! Como posso ajudá-lo?",
            {"input_tokens": 50, "output_tokens": 10, "total_tokens": 60}
        )

        # Mock WhatsApp send
        mock_whatsapp.return_value = {
            "success": True,
            "message_id": "msg-123",
            "phone": "5561999887234",
        }

        # Create webhook payload
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {
                    "remoteJid": "5561999887234@s.whatsapp.net",
                    "fromMe": False,
                    "agentId": self.agent_id,
                },
                "message": {
                    "messageTimestamp": 1691688000,
                    "messageType": "textMessage",
                    "messageBody": "Olá, tudo bem?",
                },
                "owner": "5561999887234",
            },
        }

        # Send webhook
        response = client.post("/api/v1/webhook/messages", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "conversation_id" in data
        assert data["message_id"] == "msg-123"

    @patch("app.services.llm_service.llm_service.generate_response")
    def test_webhook_non_text_message_ignored(self, mock_llm):
        """Test that non-text messages are ignored."""
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {
                    "remoteJid": "5561999887234@s.whatsapp.net",
                    "fromMe": False,
                    "agentId": self.agent_id,
                },
                "message": {
                    "messageTimestamp": 1691688000,
                    "messageType": "imageMessage",
                    "caption": "Image caption",
                    "mimetype": "image/jpeg",
                },
                "owner": "5561999887234",
            },
        }

        response = client.post("/api/v1/webhook/messages", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert "non-text message" in data.get("reason", "")
        assert not mock_llm.called

    def test_webhook_outgoing_message_ignored(self):
        """Test that outgoing messages are ignored."""
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {
                    "remoteJid": "5561999887234@s.whatsapp.net",
                    "fromMe": True,  # Outgoing message
                    "agentId": self.agent_id,
                },
                "message": {
                    "messageTimestamp": 1691688000,
                    "messageType": "textMessage",
                    "messageBody": "This is outgoing",
                },
                "owner": "5561999887234",
            },
        }

        response = client.post("/api/v1/webhook/messages", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert "outgoing message" in data.get("reason", "")

    def test_webhook_non_message_event_ignored(self):
        """Test that non-message events are ignored."""
        payload = {
            "event": "connection.update",  # Not messages.upsert
            "data": {
                "key": {},
                "message": {},
                "owner": "test",
            },
        }

        response = client.post("/api/v1/webhook/messages", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["event"] == "connection.update"

    def test_webhook_empty_message_ignored(self):
        """Test that empty messages are ignored."""
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {
                    "remoteJid": "5561999887234@s.whatsapp.net",
                    "fromMe": False,
                    "agentId": self.agent_id,
                },
                "message": {
                    "messageTimestamp": 1691688000,
                    "messageType": "textMessage",
                    "messageBody": "   ",  # Only whitespace
                },
                "owner": "5561999887234",
            },
        }

        response = client.post("/api/v1/webhook/messages", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    @patch("app.services.whatsapp_service.whatsapp_service.send_message")
    @patch("app.services.llm_service.llm_service.generate_response")
    def test_webhook_missing_agent_id(self, mock_llm, mock_whatsapp):
        """Test webhook with missing agent_id."""
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {
                    "remoteJid": "5561999887234@s.whatsapp.net",
                    "fromMe": False,
                    # Missing agentId
                },
                "message": {
                    "messageTimestamp": 1691688000,
                    "messageType": "textMessage",
                    "messageBody": "Hello",
                },
                "owner": "5561999887234",
            },
        }

        response = client.post("/api/v1/webhook/messages", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "agent_id" in data.get("detail", "").lower()


class TestWebhookHealth:
    """Test webhook health endpoint."""

    def test_webhook_health_check(self):
        """Test health check endpoint."""
        response = client.get("/api/v1/webhook/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["ok", "degraded", "error"]
        assert "timestamp" in data

    def test_legacy_webhook_endpoint(self):
        """Test legacy webhook endpoint still works."""
        payload = {"event": "test", "data": "test"}
        response = client.post("/api/v1/webhook/whatsapp", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestConversationCreation:
    """Test conversation creation in webhook flow."""

    def setup_method(self, method):
        """Setup."""
        self.user_data = {
            "email": f"test-{method.__name__}@example.com",
            "nome": "Test User",
            "senha": "TestPassword123!",
        }
        client.post("/api/v1/auth/register", json=self.user_data)

        login_response = client.post("/api/v1/auth/login", json={
            "email": self.user_data["email"],
            "senha": self.user_data["senha"],
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

        agent_data = {
            "nome": "Conversation Test Agent",
            "system_prompt": "You are helpful.",
            "temperatura": 0.7,
            "max_tokens": 1024,
        }
        create_response = client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=self.headers,
        )
        self.agent_id = create_response.json()["id"]

    @patch("app.services.whatsapp_service.whatsapp_service.send_message")
    @patch("app.services.llm_service.llm_service.generate_response")
    def test_creates_new_conversation(self, mock_llm, mock_whatsapp):
        """Test that webhook creates new conversation."""
        mock_llm.return_value = (
            "Response",
            {"input_tokens": 50, "output_tokens": 10, "total_tokens": 60}
        )
        mock_whatsapp.return_value = {
            "success": True,
            "message_id": "msg-1",
        }

        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {
                    "remoteJid": "5561999887234@s.whatsapp.net",
                    "fromMe": False,
                    "agentId": self.agent_id,
                },
                "message": {
                    "messageTimestamp": 1691688000,
                    "messageType": "textMessage",
                    "messageBody": "Test message",
                },
                "owner": "5561999887234",
            },
        }

        response = client.post("/api/v1/webhook/messages", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @patch("app.services.whatsapp_service.whatsapp_service.send_message")
    @patch("app.services.llm_service.llm_service.generate_response")
    def test_reuses_existing_conversation(self, mock_llm, mock_whatsapp):
        """Test that webhook reuses existing conversation."""
        mock_llm.return_value = (
            "Response",
            {"input_tokens": 50, "output_tokens": 10, "total_tokens": 60}
        )
        mock_whatsapp.return_value = {
            "success": True,
            "message_id": "msg-1",
        }

        phone = "5561999887234"
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {
                    "remoteJid": f"{phone}@s.whatsapp.net",
                    "fromMe": False,
                    "agentId": self.agent_id,
                },
                "message": {
                    "messageTimestamp": 1691688000,
                    "messageType": "textMessage",
                    "messageBody": "Message 1",
                },
                "owner": phone,
            },
        }

        # First message
        response1 = client.post("/api/v1/webhook/messages", json=payload)
        conv_id_1 = response1.json()["conversation_id"]

        # Second message from same phone
        payload["data"]["message"]["messageBody"] = "Message 2"
        response2 = client.post("/api/v1/webhook/messages", json=payload)
        conv_id_2 = response2.json()["conversation_id"]

        # Should use same conversation
        assert conv_id_1 == conv_id_2


class TestMessageOrchestration:
    """Test message orchestration logic."""

    @pytest.mark.asyncio
    async def test_orchestrator_saves_messages(self):
        """Test that orchestrator saves both user and agent messages."""
        from app.services.message_orchestrator import orchestrator
        from app.db.database import AsyncSessionLocal
        from app.db.models import Agent

        async with AsyncSessionLocal() as db:
            # Create test agent
            agent = Agent(
                id="test-orch-agent",
                user_id="test-orch-user",
                nome="Orchestrator Test",
                system_prompt="Test prompt",
                temperatura=0.7,
                max_tokens=1024,
                status="ativo",
            )
            db.add(agent)
            await db.commit()

            # Mock LLM
            with patch("app.services.llm_service.llm_service.generate_response") as mock_llm:
                with patch("app.services.whatsapp_service.whatsapp_service.send_message") as mock_wa:
                    mock_llm.return_value = (
                        "Test response",
                        {"input_tokens": 50, "output_tokens": 20, "total_tokens": 70}
                    )
                    mock_wa.return_value = {"success": True, "message_id": "msg-1"}

                    result = await orchestrator.process_incoming_message(
                        agent_id=agent.id,
                        phone_number="5561999887234",
                        message_text="Test input",
                        db=db,
                    )

            assert result["success"]
            assert "conversation_id" in result
            assert result["tokens_used"] == 70
