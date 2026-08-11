"""
Testes de autorização dos endpoints de Kanban e métricas.

Esses dois routers foram escritos sem nenhuma dependência de autenticação:
qualquer requisição anônima lia (e movia) os leads de qualquer agente, o que
inclui nome, e-mail e telefone dos clientes. Os testes abaixo fixam o
comportamento correto para a regressão não passar despercebida.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register_and_login(suffix: str) -> dict:
    credentials = {
        "email": f"authz-{suffix}@example.com",
        "nome": "Authz User",
        "senha": "SenhaSegura123!",
    }
    client.post("/api/v1/auth/register", json=credentials)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "senha": credentials["senha"]},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_agent(headers: dict, nome: str = "Agente") -> str:
    response = client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "nome": nome,
            "system_prompt": "prompt",
            "temperatura": 0.7,
            "max_tokens": 1024,
        },
    )
    return response.json()["id"]


KANBAN_ENDPOINTS = [
    ("GET", "/api/v1/agents/{agent_id}/kanban", None),
    ("GET", "/api/v1/agents/{agent_id}/kanban/columns", None),
    ("GET", "/api/v1/agents/{agent_id}/kanban/stats", None),
    ("POST", "/api/v1/agents/{agent_id}/kanban/columns/init", {}),
    (
        "POST",
        "/api/v1/agents/{agent_id}/kanban/move",
        {"lead_id": "lead-1", "target_column_id": "col-1", "new_order": 0},
    ),
]

METRICS_ENDPOINTS = [
    ("GET", "/api/v1/agents/{agent_id}/metrics", None),
    ("GET", "/api/v1/agents/{agent_id}/metrics/period", None),
    ("GET", "/api/v1/agents/{agent_id}/metrics/qualification-rate", None),
    ("GET", "/api/v1/agents/{agent_id}/metrics/response-time", None),
    ("GET", "/api/v1/agents/{agent_id}/metrics/lead-distribution", None),
    ("GET", "/api/v1/agents/{agent_id}/metrics/kpis", None),
]

ALL_ENDPOINTS = KANBAN_ENDPOINTS + METRICS_ENDPOINTS


class TestAnonymousAccessIsRejected:
    """Sem token, nenhum dos endpoints deve responder dados."""

    @pytest.mark.parametrize("method,path,body", ALL_ENDPOINTS)
    def test_requires_authentication(self, method, path, body):
        url = path.format(agent_id="qualquer-agente")

        response = client.request(method, url, json=body)

        assert response.status_code in (401, 403), (
            f"{method} {url} respondeu {response.status_code} sem autenticação"
        )


class TestCrossUserAccessIsRejected:
    """Um usuário autenticado não pode ler os dados de agente alheio."""

    @pytest.mark.parametrize("method,path,body", ALL_ENDPOINTS)
    def test_cannot_reach_another_users_agent(self, method, path, body):
        owner_headers = _register_and_login(f"owner-{path.count('/')}-{method}")
        agent_id = _create_agent(owner_headers, "Agente do dono")

        intruder_headers = _register_and_login(f"intruder-{path.count('/')}-{method}")

        response = client.request(
            method, path.format(agent_id=agent_id), headers=intruder_headers, json=body
        )

        # 404 em vez de 403: não confirma sequer que o agente existe.
        assert response.status_code == 404, (
            f"{method} {path} vazou o agente de outro usuário "
            f"(status {response.status_code})"
        )


class TestOwnerAccessStillWorks:
    """A proteção não pode quebrar o acesso legítimo."""

    def test_owner_reads_own_kanban(self):
        headers = _register_and_login("owner-kanban")
        agent_id = _create_agent(headers)

        client.post(f"/api/v1/agents/{agent_id}/kanban/columns/init", headers=headers)
        response = client.get(f"/api/v1/agents/{agent_id}/kanban", headers=headers)

        assert response.status_code == 200
        assert response.json()["agent_id"] == agent_id

    def test_owner_reads_own_metrics(self):
        headers = _register_and_login("owner-metrics")
        agent_id = _create_agent(headers)

        response = client.get(
            f"/api/v1/agents/{agent_id}/metrics/lead-distribution", headers=headers
        )

        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_owner_gets_404_for_unknown_agent(self):
        headers = _register_and_login("owner-unknown")

        response = client.get("/api/v1/agents/nao-existe/kanban", headers=headers)

        assert response.status_code == 404
