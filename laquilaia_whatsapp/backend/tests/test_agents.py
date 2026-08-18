"""Tests for agent management endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import criar_acesso

client = TestClient(app)


class TestAgentCreation:
    """Test agent creation endpoints."""

    def setup_method(self, method):
        """Setup test user and login before each test."""
        # Register user
        self.user_data = {
            "email": f"test-{method.__name__}@example.com",
            "nome": "Test User",
            "senha": "TestPassword123!",
        }
        criar_acesso(client, self.user_data["email"], self.user_data["senha"], self.user_data.get("nome", "Teste"))

        # Login to get token
        login_response = client.post("/api/v1/auth/login", json={
            "email": self.user_data["email"],
            "senha": self.user_data["senha"],
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_create_agent_success(self, sample_agent_data):
        """Test successful agent creation."""
        response = client.post(
            "/api/v1/agents",
            json=sample_agent_data,
            headers=self.headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == sample_agent_data["nome"]
        assert data["system_prompt"] == sample_agent_data["system_prompt"]
        assert data["temperatura"] == sample_agent_data["temperatura"]
        assert data["status"] == "ativo"
        assert "id" in data
        self.agent_id = data["id"]

    def test_create_agent_without_auth(self, sample_agent_data):
        """Test agent creation without authentication."""
        response = client.post("/api/v1/agents", json=sample_agent_data)
        assert response.status_code == 401

    def test_create_agent_invalid_temperatura(self, sample_agent_data):
        """Test agent creation with invalid temperatura."""
        sample_agent_data["temperatura"] = 5.0  # Out of range
        response = client.post(
            "/api/v1/agents",
            json=sample_agent_data,
            headers=self.headers,
        )
        assert response.status_code == 422

    def test_create_agent_invalid_max_tokens(self, sample_agent_data):
        """Test agent creation with invalid max_tokens."""
        sample_agent_data["max_tokens"] = 5000  # Out of range
        response = client.post(
            "/api/v1/agents",
            json=sample_agent_data,
            headers=self.headers,
        )
        assert response.status_code == 422

    def test_create_agent_empty_prompt(self, sample_agent_data):
        """Test agent creation with empty system_prompt."""
        sample_agent_data["system_prompt"] = "   "  # Whitespace only
        response = client.post(
            "/api/v1/agents",
            json=sample_agent_data,
            headers=self.headers,
        )
        assert response.status_code == 422

    def test_create_agent_missing_field(self):
        """Test agent creation with missing required field."""
        incomplete_data = {
            "nome": "Test Agent",
            # Missing system_prompt
            "temperatura": 0.7,
        }
        response = client.post(
            "/api/v1/agents",
            json=incomplete_data,
            headers=self.headers,
        )
        assert response.status_code == 422


class TestAgentRetrieval:
    """Test agent retrieval endpoints."""

    def setup_method(self, method):
        """Setup test user, login, and create test agent."""
        # Register and login
        self.user_data = {
            "email": f"test-{method.__name__}@example.com",
            "nome": "Test User",
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
            "nome": "Test Agent",
            "descricao": "A test agent",
            "system_prompt": "You are a helpful assistant.",
            "temperatura": 0.7,
            "max_tokens": 1024,
        }
        create_response = client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=self.headers,
        )
        self.agent_id = create_response.json()["id"]

    def test_get_agent_success(self):
        """Test successful agent retrieval."""
        response = client.get(
            f"/api/v1/agents/{self.agent_id}",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == self.agent_id
        assert data["nome"] == "Test Agent"

    def test_get_agent_not_found(self):
        """Test retrieval of non-existent agent."""
        response = client.get(
            "/api/v1/agents/nonexistent-id",
            headers=self.headers,
        )
        assert response.status_code == 404

    def test_get_agent_without_auth(self):
        """Test agent retrieval without authentication."""
        response = client.get(f"/api/v1/agents/{self.agent_id}")
        assert response.status_code == 401

    def test_list_agents_success(self):
        """Test successful agents listing."""
        response = client.get(
            "/api/v1/agents",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(agent["id"] == self.agent_id for agent in data)

    def test_list_agents_with_pagination(self):
        """Test agents listing with pagination."""
        response = client.get(
            "/api/v1/agents?skip=0&limit=10",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_agents_empty(self):
        """Test listing agents for user with no agents."""
        # Register new user
        new_user_data = {
            "email": "empty-user@example.com",
            "nome": "Empty User",
            "senha": "TestPassword123!",
        }
        criar_acesso(client, new_user_data["email"], new_user_data["senha"], new_user_data.get("nome", "Teste"))

        login_response = client.post("/api/v1/auth/login", json={
            "email": new_user_data["email"],
            "senha": new_user_data["senha"],
        })
        new_token = login_response.json()["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}

        response = client.get(
            "/api/v1/agents",
            headers=new_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestAgentUpdate:
    """Test agent update endpoints."""

    def setup_method(self, method):
        """Setup test user, login, and create test agent."""
        self.user_data = {
            "email": f"test-{method.__name__}@example.com",
            "nome": "Test User",
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
            "nome": "Test Agent",
            "descricao": "A test agent",
            "system_prompt": "You are a helpful assistant.",
            "temperatura": 0.7,
            "max_tokens": 1024,
        }
        create_response = client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=self.headers,
        )
        self.agent_id = create_response.json()["id"]

    def test_update_agent_nome(self):
        """Test updating agent name."""
        update_data = {"nome": "Updated Agent"}
        response = client.put(
            f"/api/v1/agents/{self.agent_id}",
            json=update_data,
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["nome"] == "Updated Agent"

    def test_update_agent_system_prompt(self):
        """Test updating agent system prompt."""
        update_data = {"system_prompt": "New system prompt here."}
        response = client.put(
            f"/api/v1/agents/{self.agent_id}",
            json=update_data,
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["system_prompt"] == "New system prompt here."

    def test_update_agent_temperatura(self):
        """Test updating agent temperatura."""
        update_data = {"temperatura": 1.5}
        response = client.put(
            f"/api/v1/agents/{self.agent_id}",
            json=update_data,
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["temperatura"] == 1.5

    def test_update_agent_invalid_temperatura(self):
        """Test updating agent with invalid temperatura."""
        update_data = {"temperatura": 5.0}
        response = client.put(
            f"/api/v1/agents/{self.agent_id}",
            json=update_data,
            headers=self.headers,
        )

        assert response.status_code == 422

    def test_update_nonexistent_agent(self):
        """Test updating non-existent agent."""
        update_data = {"nome": "Updated Agent"}
        response = client.put(
            "/api/v1/agents/nonexistent-id",
            json=update_data,
            headers=self.headers,
        )

        assert response.status_code == 404

    def test_update_agent_without_auth(self):
        """Test agent update without authentication."""
        update_data = {"nome": "Updated Agent"}
        response = client.put(
            f"/api/v1/agents/{self.agent_id}",
            json=update_data,
        )

        assert response.status_code == 401


class TestAgentDeletion:
    """Test agent deletion endpoints."""

    def setup_method(self, method):
        """Setup test user, login, and create test agent."""
        self.user_data = {
            "email": f"test-{method.__name__}@example.com",
            "nome": "Test User",
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
            "nome": "Test Agent",
            "descricao": "A test agent",
            "system_prompt": "You are a helpful assistant.",
            "temperatura": 0.7,
            "max_tokens": 1024,
        }
        create_response = client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=self.headers,
        )
        self.agent_id = create_response.json()["id"]

    def test_delete_agent_success(self):
        """Test successful agent deletion."""
        response = client.delete(
            f"/api/v1/agents/{self.agent_id}",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert self.agent_id in data["agent_id"]

    def test_delete_agent_not_found(self):
        """Test deletion of non-existent agent."""
        response = client.delete(
            "/api/v1/agents/nonexistent-id",
            headers=self.headers,
        )

        assert response.status_code == 404

    def test_delete_agent_without_auth(self):
        """Test agent deletion without authentication."""
        response = client.delete(f"/api/v1/agents/{self.agent_id}")
        assert response.status_code == 401

    def test_delete_and_verify_removed(self):
        """Test that deleted agent cannot be retrieved."""
        # Delete agent
        delete_response = client.delete(
            f"/api/v1/agents/{self.agent_id}",
            headers=self.headers,
        )
        assert delete_response.status_code == 200

        # Try to retrieve deleted agent
        get_response = client.get(
            f"/api/v1/agents/{self.agent_id}",
            headers=self.headers,
        )
        assert get_response.status_code == 404


class TestAgentVariables:
    """Test agent variables endpoints."""

    def setup_method(self, method):
        """Setup test user, login, and create test agent."""
        self.user_data = {
            "email": f"test-{method.__name__}@example.com",
            "nome": "Test User",
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
            "nome": "Test Agent",
            "descricao": "A test agent",
            "system_prompt": "You are a helpful assistant.",
            "temperatura": 0.7,
            "max_tokens": 1024,
        }
        create_response = client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=self.headers,
        )
        self.agent_id = create_response.json()["id"]

    def test_add_variable_success(self):
        """Test successfully adding a variable to agent."""
        variable_data = {
            "nome_variavel": "nome_cliente",
            "tipo": "texto",
            "descricao": "Nome do cliente",
            "valor_padrao": "Visitante",
        }
        response = client.post(
            f"/api/v1/agents/{self.agent_id}/variables",
            json=variable_data,
            headers=self.headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["nome_variavel"] == "nome_cliente"
        assert data["tipo"] == "texto"

    def test_get_variables_empty(self):
        """Test getting variables for agent with no variables."""
        response = client.get(
            f"/api/v1/agents/{self.agent_id}/variables",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_variables_after_add(self):
        """Test getting variables after adding one."""
        # Add variable
        variable_data = {
            "nome_variavel": "status_lead",
            "tipo": "enum",
            "descricao": "Status do lead",
        }
        client.post(
            f"/api/v1/agents/{self.agent_id}/variables",
            json=variable_data,
            headers=self.headers,
        )

        # Get variables
        response = client.get(
            f"/api/v1/agents/{self.agent_id}/variables",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(v["nome_variavel"] == "status_lead" for v in data)


class TestNomeDoAtendente:
    """
    O nome pelo qual o cliente conhece quem o atende.

    Diferente de `nome`, que é o rótulo interno: ninguém no WhatsApp deve ouvir
    "meu nome é Triagem trabalhista".
    """

    def setup_method(self, method):
        self.email = f"atendente-{method.__name__}@example.com"
        criar_acesso(client, self.email, "TestPassword123!", "Dono")
        r = client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "senha": "TestPassword123!"},
        )
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def _criar(self, **extra):
        corpo = {
            "nome": "Triagem trabalhista",
            "system_prompt": "x",
            "temperatura": 0.7,
            "max_tokens": 1024,
            **extra,
        }
        return client.post("/api/v1/agents", json=corpo, headers=self.headers)

    def test_o_nome_do_atendente_vai_e_volta(self):
        criado = self._criar(nome_atendente="Fernanda")

        assert criado.status_code in (200, 201), criado.text
        assert criado.json()["nome_atendente"] == "Fernanda"

        lido = client.get(
            f"/api/v1/agents/{criado.json()['id']}", headers=self.headers
        )
        assert lido.json()["nome_atendente"] == "Fernanda"

    def test_agente_sem_nome_de_atendente_continua_valendo(self):
        """
        Vazio é estado normal, não pendência: o agente se apresenta como o
        escritório. Exigir o campo quebraria todo agente já criado.
        """
        criado = self._criar()

        assert criado.status_code in (200, 201), criado.text
        assert criado.json()["nome_atendente"] is None

    def test_da_para_batizar_depois(self):
        agente = self._criar().json()

        atualizado = client.put(
            f"/api/v1/agents/{agente['id']}",
            json={"nome_atendente": "Fernanda"},
            headers=self.headers,
        )

        assert atualizado.status_code == 200, atualizado.text
        assert atualizado.json()["nome_atendente"] == "Fernanda"
