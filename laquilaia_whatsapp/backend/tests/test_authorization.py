"""
Testes de autorização dos endpoints de Kanban e métricas.

Esses dois routers foram escritos sem nenhuma dependência de autenticação:
qualquer requisição anônima lia (e movia) os leads de qualquer agente, o que
inclui nome, e-mail e telefone dos clientes. Os testes abaixo fixam o
comportamento correto para a regressão não passar despercebida.
"""
from tests.conftest import criar_acesso

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
    criar_acesso(client, credentials["email"], credentials["senha"], credentials.get("nome", "Teste"))
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

    @pytest.mark.parametrize("method,path,body", ALL_ENDPOINTS)
    def test_sem_cabecalho_e_401_e_nao_403(self, method, path, body):
        """
        Sem cabeçalho `Authorization` a resposta é **401**, nunca 403.

        403 quer dizer "sei quem você é e você não pode"; quem chega sem
        cabeçalho nenhum ainda não é ninguém. A distinção parece formalidade e
        não é: o `HTTPBearer` do FastAPI recusava com 403 por padrão, e o
        cliente HTTP do painel só renova a sessão quando vê 401. Como o cookie
        do access token expira em 30 minutos e o browser o apaga, a partir daí
        as chamadas saíam sem cabeçalho — e o usuário era deslogado com um
        refresh token válido por sete dias no bolso, que ninguém usou.

        Os endpoints administrativos respondem 404 de propósito (não revelam
        que existem), e por isso ficam de fora.
        """
        url = path.format(agent_id="qualquer-agente")

        response = client.request(method, url, json=body)

        if response.status_code == 404:
            pytest.skip("rota que esconde a própria existência de quem não é admin")

        assert response.status_code == 401, (
            f"{method} {url} respondeu {response.status_code}; em 403 o painel "
            "não tenta renovar a sessão e desloga o usuário"
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


class TestTimeseriesEndpoint:
    """A série temporal alimenta o gráfico de linha do dashboard."""

    def test_requires_authentication(self):
        response = client.get("/api/v1/agents/qualquer/metrics/timeseries")

        assert response.status_code in (401, 403)

    def test_cannot_reach_another_users_agent(self):
        owner = _register_and_login("ts-owner")
        agent_id = _create_agent(owner)
        intruder = _register_and_login("ts-intruder")

        response = client.get(
            f"/api/v1/agents/{agent_id}/metrics/timeseries", headers=intruder
        )

        assert response.status_code == 404

    def test_returns_one_point_per_day_including_empty_days(self):
        headers = _register_and_login("ts-shape")
        agent_id = _create_agent(headers)

        response = client.get(
            f"/api/v1/agents/{agent_id}/metrics/timeseries?dias=7", headers=headers
        )

        assert response.status_code == 200
        body = response.json()
        # Dias sem movimento entram zerados, para a linha não pular datas.
        assert len(body["pontos"]) == 7
        assert all(p["atendimentos"] == 0 for p in body["pontos"])

    def test_rejects_range_over_90_days(self):
        headers = _register_and_login("ts-range")
        agent_id = _create_agent(headers)

        response = client.get(
            f"/api/v1/agents/{agent_id}/metrics/timeseries?dias=200", headers=headers
        )

        assert response.status_code == 422


class TestPapeis:
    """
    O operador atende; quem configura é o administrador.

    Sem isto, qualquer conta criada no sistema podia reescrever o prompt do
    agente — que é onde mora o comportamento inteiro do atendimento.
    """

    def setup_method(self, method):
        self.admin = {
            "email": f"papel-admin-{method.__name__}@example.com",
            "nome": "Dono",
            "senha": "SenhaSegura123!",
        }
        criar_acesso(client, self.admin["email"], self.admin["senha"], self.admin["nome"])
        self.operador = {
            "email": f"papel-op-{method.__name__}@example.com",
            "nome": "Operador",
            "senha": "SenhaSegura123!",
        }
        criar_acesso(
            client,
            self.operador["email"],
            self.operador["senha"],
            self.operador["nome"],
            papel="operador",
        )

    def _headers(self, credenciais):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": credenciais["email"], "senha": credenciais["senha"]},
        )
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_operador_nao_cria_agente(self):
        resposta = client.post(
            "/api/v1/agents",
            json={
                "nome": "Agente do operador",
                "system_prompt": "teste",
                "temperatura": 0.5,
                "max_tokens": 512,
            },
            headers=self._headers(self.operador),
        )

        # 404, e não 403: dizer "existe, mas você não pode" entrega a rota a
        # quem não deveria enxergá-la. É a mesma regra dos agentes alheios.
        assert resposta.status_code == 404

    def test_operador_nao_usa_o_chat_de_teste(self):
        """O chat de teste calibra prompt e gasta LLM: é configuração."""
        resposta = client.post(
            "/api/v1/agents/qualquer-id/chat",
            json={"message": "oi"},
            headers=self._headers(self.operador),
        )

        assert resposta.status_code == 404

    def test_o_papel_chega_em_auth_me(self):
        """
        O painel decide o menu por este campo — e ele não vinha.

        `UserResponse` tem default "operador", então `/auth/me` respondia
        "operador" para todo mundo, inclusive para o administrador. O menu
        esconderia dele justamente as telas que só ele pode abrir, e o sintoma
        seria "sumiu a tela de agentes", não "o papel veio errado".
        """
        admin = client.get("/api/v1/auth/me", headers=self._headers(self.admin))
        operador = client.get("/api/v1/auth/me", headers=self._headers(self.operador))

        assert admin.json()["papel"] == "admin"
        assert operador.json()["papel"] == "operador"

    def test_operador_lista_agentes(self):
        """
        Listar continua liberado: a tela de atendimentos tem uma aba por
        agente, e sem a lista o operador não escolhe qual fila abrir.
        """
        resposta = client.get("/api/v1/agents", headers=self._headers(self.operador))

        assert resposta.status_code == 200

    def test_admin_cria_agente(self):
        resposta = client.post(
            "/api/v1/agents",
            json={
                "nome": "Agente do dono",
                "system_prompt": "teste",
                "temperatura": 0.5,
                "max_tokens": 512,
            },
            headers=self._headers(self.admin),
        )

        assert resposta.status_code == 201

    def test_operador_nao_cria_outros_acessos(self):
        resposta = client.post(
            "/api/v1/auth/users",
            json={
                "email": "novo@example.com",
                "nome": "Novo",
                "senha": "SenhaSegura123!",
                "papel": "admin",
            },
            headers=self._headers(self.operador),
        )

        assert resposta.status_code == 404

    def test_cadastro_publico_fecha_no_primeiro(self):
        """
        A porta de entrada é única.

        Sem isso, qualquer um que alcançasse a URL criava conta e entrava no
        sistema do escritório.
        """
        resposta = client.post(
            "/api/v1/auth/register",
            json={
                "email": "intruso@example.com",
                "nome": "Intruso",
                "senha": "SenhaSegura123!",
            },
        )

        assert resposta.status_code == 403
        assert "administrador" in resposta.json()["detail"]
