"""Pytest configuration and fixtures."""

import asyncio
import pytest
import sys
import os
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# As duas variáveis abaixo precisam existir ANTES de importar `app`: o
# `Settings` lê o ambiente na importação e o engine é criado junto.
#
# - DATABASE_URL aponta para um banco separado, para os testes não
#   destruírem dados de desenvolvimento (o schema é recriado a cada sessão).
# - DEBUG=true faz o engine usar NullPool. Com pool, as conexões asyncpg
#   ficam presas ao event loop que as abriu, e o TestClient cria um loop
#   novo a cada request — reusar a conexão estoura "attached to a
#   different loop".
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://laquilaia:laquilaia_dev_pwd@localhost:5432/laquilaia_test_db",
)
os.environ["DEBUG"] = "true"

from sqlalchemy import text
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import engine


# Credenciais do primeiro acesso criado no teste corrente. O cadastro público
# fecha depois dele, então é por ele que os demais entram.
_PRIMEIRO_ACESSO: dict = {}
from app.db.models import Base


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    """
    Cria o schema uma vez por sessão de testes.

    Os testes de integração usam o TestClient sem disparar o lifespan do app,
    então `init_db()` não roda e as tabelas não existiriam.
    """

    async def create_all():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_all())
    yield


@pytest.fixture(autouse=True)
def clean_tables(database_schema):
    """
    Esvazia as tabelas ao fim de cada teste.

    Sem isso os testes compartilham o mesmo banco e um e-mail cadastrado por
    um teste faz o cadastro de outro devolver 400 — falhas que só aparecem na
    suíte completa, nunca quando o teste roda sozinho.

    A limpeza é no teardown (e não no setup) porque o `setup_method` das
    classes de teste roda antes das fixtures de função.
    """
    yield

    _PRIMEIRO_ACESSO.clear()

    async def truncate():
        async with engine.begin() as conn:
            tables = ", ".join(
                f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables)
            )
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))

    asyncio.run(truncate())


@pytest.fixture
def client():
    """Provide a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_user_data():
    """Provide sample user data for tests."""
    return {
        "email": "test@example.com",
        "nome": "Test User",
        "senha": "TestPassword123!",
    }


@pytest.fixture
def sample_agent_data():
    """Provide sample agent data for tests."""
    return {
        "nome": "Agent de Vendas",
        "descricao": "Agente especializado em vendas",
        "system_prompt": "Você é um agente de vendas assistente.",
        "temperatura": 0.7,
        "max_tokens": 1024,
    }


@pytest.fixture
def sample_conversation_data():
    """Provide sample conversation data for tests."""
    return {
        "phone_number": "+5561999887234",
        "status": "ativa",
    }



def criar_acesso(client, email: str, senha: str, nome: str = "Teste", papel: str = "admin"):
    """
    Garante um acesso utilizável no teste.

    O `POST /auth/register` fecha no primeiro usuário — é a porta de entrada
    única do produto, e os testes de autorização precisam de dois donos
    diferentes. Este helper segue o caminho real: o primeiro se cadastra e
    vira administrador; os demais são criados por ele, em `POST /auth/users`.

    O papel padrão é `admin` porque quem cria agente nos testes é o dono do
    sistema; para exercitar o operador, passe `papel="operador"`.
    """
    corpo = {"email": email, "nome": nome, "senha": senha}

    resposta = client.post("/api/v1/auth/register", json=corpo)
    if resposta.status_code == 201:
        _PRIMEIRO_ACESSO.setdefault("email", email)
        _PRIMEIRO_ACESSO.setdefault("senha", senha)
        return

    if not _PRIMEIRO_ACESSO:
        raise AssertionError(
            "Cadastro fechado e nenhum acesso conhecido neste teste — "
            "chame criar_acesso() para o administrador antes dos demais."
        )

    admin = client.post("/api/v1/auth/login", json=_PRIMEIRO_ACESSO)
    token = admin.json()["access_token"]
    client.post(
        "/api/v1/auth/users",
        json={**corpo, "papel": papel},
        headers={"Authorization": f"Bearer {token}"},
    )
