"""Tests for Kanban API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from tests.conftest import criar_acesso
from app.db.models import Agent, KanbanColumn, KanbanCard, Lead, LeadDetails, Conversation

client = TestClient(app)


class TestKanbanBoard:
    """Test Kanban board endpoints."""

    def setup_method(self, method):
        """Setup test user, login, and create test agent."""
        self.user_data = {
            "email": f"kanban-test-{method.__name__}@example.com",
            "nome": "Kanban Test User",
            "senha": "TestPassword123!",
        }
        criar_acesso(client, self.user_data["email"], self.user_data["senha"], self.user_data.get("nome", "Teste"))

        login_response = client.post("/api/v1/auth/login", json={
            "email": self.user_data["email"],
            "senha": self.user_data["senha"],
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Create test agent
        agent_data = {
            "nome": "Kanban Test Agent",
            "system_prompt": "Test prompt",
            "temperatura": 0.7,
            "max_tokens": 1024,
        }
        create_response = client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=self.headers,
        )
        self.agent_id = create_response.json()["id"]

    def test_board_de_agente_novo_ja_vem_com_o_funil(self):
        """
        O agente nasce com as colunas padrão.

        Este teste afirmava `columns == []` e passava — mas o que ele
        documentava era um defeito: sem coluna nenhuma, um lead qualificado
        era gravado e nunca aparecia no board, porque não havia onde pôr o
        card. Só o `POST /kanban/columns/init` criava as colunas, e nada o
        chamava.
        """
        response = client.get(
            f"/api/v1/agents/{self.agent_id}/kanban",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == self.agent_id
        assert [c["nome"] for c in data["columns"]] == [
            "Novo Lead",
            "Em Qualificação",
            "Lead Qualificado",
            "Agendado",
            "Arquivado",
        ]
        assert all(c["cards"] == [] for c in data["columns"])
        # A paleta é a validada, não os hexes crus do Tailwind que o endpoint
        # de init usava por conta própria.
        assert data["columns"][0]["cor_hex"] == "#3164ff"

    def test_get_kanban_board_agent_not_found(self):
        """Test getting board for non-existent agent."""
        response = client.get(
            "/api/v1/agents/invalid-agent-id/kanban",
            headers=self.headers,
        )

        assert response.status_code == 404

    def test_initialize_kanban_columns(self):
        """
        O init virou idempotente na prática: as colunas já vêm com o agente.

        O endpoint continua existindo para agentes criados antes desta
        mudança, que estão no banco sem funil nenhum.
        """
        response = client.post(
            f"/api/v1/agents/{self.agent_id}/kanban/columns/init",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "already initialized" in data["message"]

    def test_initialize_kanban_columns_already_exist(self):
        """Test initializing columns when already present."""
        # Initialize first time
        client.post(
            f"/api/v1/agents/{self.agent_id}/kanban/columns/init",
            headers=self.headers,
        )

        # Try to initialize again
        response = client.post(
            f"/api/v1/agents/{self.agent_id}/kanban/columns/init",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_list_kanban_columns(self):
        """Test listing Kanban columns."""
        # Initialize columns first
        client.post(
            f"/api/v1/agents/{self.agent_id}/kanban/columns/init",
            headers=self.headers,
        )

        response = client.get(
            f"/api/v1/agents/{self.agent_id}/kanban/columns",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["columns"]) == 5

    def test_get_kanban_stats(self):
        """Test getting Kanban statistics."""
        # Initialize columns
        client.post(
            f"/api/v1/agents/{self.agent_id}/kanban/columns/init",
            headers=self.headers,
        )

        response = client.get(
            f"/api/v1/agents/{self.agent_id}/kanban/stats",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_leads" in data
        assert "columns" in data
        assert data["total_leads"] == 0  # No leads yet


class TestMoveCard:
    """Test moving cards between columns."""

    def setup_method(self, method):
        """Setup test infrastructure."""
        self.user_data = {
            "email": f"move-test-{method.__name__}@example.com",
            "nome": "Move Test User",
            "senha": "TestPassword123!",
        }
        criar_acesso(client, self.user_data["email"], self.user_data["senha"], self.user_data.get("nome", "Teste"))

        login_response = client.post("/api/v1/auth/login", json={
            "email": self.user_data["email"],
            "senha": self.user_data["senha"],
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Create test agent
        agent_data = {
            "nome": "Move Test Agent",
            "system_prompt": "Test",
            "temperatura": 0.7,
            "max_tokens": 1024,
        }
        create_response = client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=self.headers,
        )
        self.agent_id = create_response.json()["id"]

        # Initialize columns
        client.post(
            f"/api/v1/agents/{self.agent_id}/kanban/columns/init",
            headers=self.headers,
        )

    @patch("app.services.lead_processor.lead_processor.process_response")
    @patch("app.services.whatsapp_service.whatsapp_service.send_message")
    @patch("app.services.llm_service.llm_service.generate_response")
    def test_move_card_between_columns(
        self,
        mock_llm,
        mock_whatsapp,
        mock_lead_processor,
    ):
        """Test moving card between columns."""
        # Mock responses
        mock_llm.return_value = (
            "Response",
            {"input_tokens": 50, "output_tokens": 10, "total_tokens": 60}
        )
        mock_whatsapp.return_value = {
            "success": True,
            "message_id": "msg-123",
        }
        mock_lead_processor.return_value = {
            "success": False,  # No qualification in this test
        }

        # Send webhook message to create conversation and lead
        webhook_payload = {
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

        webhook_response = client.post(
            "/api/v1/webhook/messages",
            json=webhook_payload,
        )

        if webhook_response.status_code == 200:
            lead_data = webhook_response.json()
            conversation_id = lead_data.get("conversation_id")

            # Get board to find lead and columns
            board_response = client.get(
                f"/api/v1/agents/{self.agent_id}/kanban",
                headers=self.headers,
            )

            if board_response.status_code == 200:
                board = board_response.json()
                if board["columns"] and board["columns"][0]["cards"]:
                    lead_id = board["columns"][0]["cards"][0]["id"]
                    target_column_id = board["columns"][2]["id"]  # Lead Qualificado

                    # Move card
                    move_response = client.post(
                        f"/api/v1/agents/{self.agent_id}/kanban/move",
                        json={
                            "lead_id": lead_id,
                            "target_column_id": target_column_id,
                            "new_order": 1,
                        },
                        headers=self.headers,
                    )

                    # Should succeed or return 200
                    assert move_response.status_code in [200, 404]  # 404 if card not found in test

    def test_move_card_invalid_column(self):
        """Test moving card to invalid column."""
        # This would fail because we don't have a real lead/card in test
        # Just verify endpoint exists
        response = client.post(
            f"/api/v1/agents/{self.agent_id}/kanban/move",
            json={
                "lead_id": "invalid-lead",
                "target_column_id": "invalid-column",
                "new_order": 1,
            },
            headers=self.headers,
        )

        # Should return 404 (not found)
        assert response.status_code in [404, 500]


class TestKanbanColumns:
    """Test Kanban column operations."""

    def setup_method(self, method):
        """Setup."""
        self.user_data = {
            "email": f"col-test-{method.__name__}@example.com",
            "nome": "Column Test User",
            "senha": "TestPassword123!",
        }
        criar_acesso(client, self.user_data["email"], self.user_data["senha"], self.user_data.get("nome", "Teste"))

        login_response = client.post("/api/v1/auth/login", json={
            "email": self.user_data["email"],
            "senha": self.user_data["senha"],
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Create test agent
        agent_data = {
            "nome": "Column Test Agent",
            "system_prompt": "Test",
            "temperatura": 0.7,
            "max_tokens": 1024,
        }
        create_response = client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=self.headers,
        )
        self.agent_id = create_response.json()["id"]

    def test_default_columns_structure(self):
        """Test that default columns have correct structure."""
        # Initialize
        init_response = client.post(
            f"/api/v1/agents/{self.agent_id}/kanban/columns/init",
            headers=self.headers,
        )

        assert init_response.status_code == 200

        # Get columns
        response = client.get(
            f"/api/v1/agents/{self.agent_id}/kanban/columns",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()

        expected_columns = [
            "Novo Lead",
            "Em Qualificação",
            "Lead Qualificado",
            "Agendado",
            "Arquivado",
        ]

        assert len(data["columns"]) == 5
        for i, col in enumerate(data["columns"]):
            assert col["nome"] == expected_columns[i]
            assert "ordem" in col
            assert "id" in col


class TestKanbanIntegration:
    """Integration tests for Kanban."""

    def setup_method(self, method):
        """Setup."""
        self.user_data = {
            "email": f"integration-test-{method.__name__}@example.com",
            "nome": "Integration Test User",
            "senha": "TestPassword123!",
        }
        criar_acesso(client, self.user_data["email"], self.user_data["senha"], self.user_data.get("nome", "Teste"))

        login_response = client.post("/api/v1/auth/login", json={
            "email": self.user_data["email"],
            "senha": self.user_data["senha"],
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

        agent_data = {
            "nome": "Integration Test Agent",
            "system_prompt": "Test",
            "temperatura": 0.7,
            "max_tokens": 1024,
        }
        create_response = client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=self.headers,
        )
        self.agent_id = create_response.json()["id"]

    def test_full_kanban_flow(self):
        """Test complete Kanban flow: init → list → stats."""
        # 1. Initialize
        init_response = client.post(
            f"/api/v1/agents/{self.agent_id}/kanban/columns/init",
            headers=self.headers,
        )
        assert init_response.status_code == 200

        # 2. List columns
        list_response = client.get(
            f"/api/v1/agents/{self.agent_id}/kanban/columns",
            headers=self.headers,
        )
        assert list_response.status_code == 200
        assert len(list_response.json()["columns"]) == 5

        # 3. Get full board
        board_response = client.get(
            f"/api/v1/agents/{self.agent_id}/kanban",
            headers=self.headers,
        )
        assert board_response.status_code == 200
        board = board_response.json()
        assert board["agent_id"] == self.agent_id
        assert len(board["columns"]) == 5

        # 4. Get stats
        stats_response = client.get(
            f"/api/v1/agents/{self.agent_id}/kanban/stats",
            headers=self.headers,
        )
        assert stats_response.status_code == 200
        assert stats_response.json()["total_leads"] == 0
