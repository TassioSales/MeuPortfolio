"""
Quanto vale o que entrou, e de onde veio.

As métricas contavam gente. Um escritório não vive de quantidade de conversa —
vive do tamanho das causas. Dois meses com o mesmo número de leads podem valer
dez vezes um ao outro, e o painel dizia que eram iguais.

O caso que mais importa aqui é o do caso **sem estimativa**: ele não pode
somar zero e sumir, senão o total mente para menos e ninguém percebe.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import Agent, Caso, Conversation, Lead
from app.main import app
from app.routers.valor import MULTIPLO_DO_GRANDE, _porte
from tests.conftest import criar_acesso

client = TestClient(app)

PISO = settings.caso_valor_minimo


def _login(sufixo: str, papel: str = "admin") -> tuple[dict, str]:
    email = f"valor-{sufixo}@example.com"
    criar_acesso(client, email, "SenhaSegura123!", f"Pessoa {sufixo}", papel=papel)
    r = client.post("/api/v1/auth/login", json={"email": email, "senha": "SenhaSegura123!"})
    cabecalho = {"Authorization": f"Bearer {r.json()['access_token']}"}
    eu = client.get("/api/v1/auth/me", headers=cabecalho).json()
    return cabecalho, eu["id"]


async def _agente(sufixo: str, dono: str) -> str:
    agent_id = f"ag-{sufixo}"
    async with AsyncSessionLocal() as db:
        db.add(Agent(id=agent_id, user_id=dono, nome="Triagem", system_prompt="p",
                     temperatura=0.4, max_tokens=1024, status="ativo"))
        await db.commit()
    return agent_id


async def _caso(
    agent_id: str,
    sufixo: str,
    *,
    minimo: int | None,
    maximo: int | None,
    telefone: str = "5561999887766",
    dias_atras: int = 1,
):
    quando = datetime.utcnow() - timedelta(days=dias_atras)
    async with AsyncSessionLocal() as db:
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=agent_id,
                            phone_number=telefone, status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}", nome="X",
                    phone_number=telefone, status_funil="qualificado"))
        await db.flush()
        db.add(Caso(id=f"caso-{sufixo}", lead_id=f"lead-{sufixo}", area="trabalhista",
                    resumo="r", valor_estimado_min=minimo, valor_estimado_max=maximo,
                    viabilidade="acima_do_piso", data_abertura=quando))
        await db.commit()


def _buscar(agent_id: str, cabecalho: dict, **params):
    return client.get(f"/api/v1/agents/{agent_id}/metrics/valor",
                      headers=cabecalho, params=params)


def _porte_de(dados: dict, nome: str) -> dict:
    return next(p for p in dados["por_porte"] if p["porte"] == nome)


class TestAFaixaDePorte:
    def test_abaixo_do_piso_e_baixo(self):
        assert _porte(PISO - 1, PISO) == "baixo"

    def test_no_piso_ja_e_medio(self):
        assert _porte(PISO, PISO) == "medio"

    def test_cinco_vezes_o_piso_e_alto(self):
        assert _porte(PISO * MULTIPLO_DO_GRANDE, PISO) == "alto"

    def test_sem_estimativa_e_indeterminado_e_nao_zero(self):
        """
        Zero seria "caso sem valor" — que é uma afirmação. O que existe é
        ausência de estimativa, e as duas coisas mandam fazer coisas
        diferentes.
        """
        assert _porte(None, PISO) == "indeterminado"


class TestOsTotais:
    @pytest.mark.asyncio
    async def test_soma_a_faixa_inteira_e_nao_uma_media(self):
        """
        O parecer estima faixa porque não tem documento. Achatar isso numa
        média inventa uma precisão que a estimativa não tem.
        """
        cabecalho, dono = _login("a1")
        agent_id = await _agente("a1", dono)
        await _caso(agent_id, "a1a", minimo=10000, maximo=30000)
        await _caso(agent_id, "a1b", minimo=5000, maximo=20000,
                    telefone="5511984470001")

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["total_min"] == 15000
        assert dados["total_max"] == 50000
        assert dados["casos_dimensionados"] == 2

    @pytest.mark.asyncio
    async def test_caso_sem_estimativa_aparece_no_numero(self):
        """
        O caso que mais importa. Somar zero e sumir faz o total mentir para
        menos, e ninguém percebe porque o número continua plausível.
        """
        cabecalho, dono = _login("a2")
        agent_id = await _agente("a2", dono)
        await _caso(agent_id, "a2a", minimo=10000, maximo=30000)
        await _caso(agent_id, "a2b", minimo=None, maximo=None,
                    telefone="5511984470002")

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["casos_dimensionados"] == 1
        assert dados["casos_sem_valor"] == 1
        assert _porte_de(dados, "indeterminado")["casos"] == 1

    @pytest.mark.asyncio
    async def test_sem_caso_nenhum_abre_zerado(self):
        cabecalho, dono = _login("a3")
        agent_id = await _agente("a3", dono)

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["total_max"] == 0
        assert len(dados["por_porte"]) == 4
        assert dados["por_uf"] == []


class TestPorDia:
    @pytest.mark.asyncio
    async def test_agrupa_por_dia_de_abertura(self):
        cabecalho, dono = _login("b1")
        agent_id = await _agente("b1", dono)
        await _caso(agent_id, "b1a", minimo=1000, maximo=2000, dias_atras=1)
        await _caso(agent_id, "b1b", minimo=3000, maximo=4000, dias_atras=1,
                    telefone="5511984470003")
        await _caso(agent_id, "b1c", minimo=5000, maximo=6000, dias_atras=5,
                    telefone="5511984470004")

        por_dia = _buscar(agent_id, cabecalho).json()["por_dia"]

        assert len(por_dia) == 2
        # Do mais antigo para o mais recente, que é como um gráfico se lê.
        assert por_dia[0]["data"] < por_dia[1]["data"]
        assert por_dia[1]["casos"] == 2
        assert por_dia[1]["total_max"] == 6000

    @pytest.mark.asyncio
    async def test_o_recorte_de_dias_corta(self):
        cabecalho, dono = _login("b2")
        agent_id = await _agente("b2", dono)
        await _caso(agent_id, "b2a", minimo=1000, maximo=2000, dias_atras=2)
        await _caso(agent_id, "b2b", minimo=9000, maximo=9000, dias_atras=200,
                    telefone="5511984470005")

        assert _buscar(agent_id, cabecalho).json()["total_max"] == 2000
        assert _buscar(agent_id, cabecalho, dias=365).json()["total_max"] == 11000


class TestPorEstado:
    @pytest.mark.asyncio
    async def test_separa_pelo_ddd_sem_campo_de_endereco(self):
        cabecalho, dono = _login("c1")
        agent_id = await _agente("c1", dono)
        await _caso(agent_id, "c1a", minimo=1000, maximo=90000,
                    telefone="5561999887766")
        await _caso(agent_id, "c1b", minimo=1000, maximo=5000,
                    telefone="5511984470006")

        por_uf = _buscar(agent_id, cabecalho).json()["por_uf"]

        # Ordenado pelo valor, que é o que decide onde anunciar.
        assert [u["uf"] for u in por_uf] == ["DF", "SP"]
        assert por_uf[0]["total_max"] == 90000

    @pytest.mark.asyncio
    async def test_telefone_que_nao_da_para_ler_vira_interrogacao(self):
        """
        Sumir da lista faria as partes não baterem com o total, e alguém iria
        procurar o erro na soma em vez de no número de telefone.
        """
        cabecalho, dono = _login("c2")
        agent_id = await _agente("c2", dono)
        await _caso(agent_id, "c2", minimo=1000, maximo=2000,
                    telefone="351912345678")

        por_uf = _buscar(agent_id, cabecalho).json()["por_uf"]

        assert [u["uf"] for u in por_uf] == ["??"]
        assert por_uf[0]["leads"] == 1


class TestAcesso:
    @pytest.mark.asyncio
    async def test_operador_ve(self):
        cabecalho, dono = _login("d1")
        agent_id = await _agente("d1", dono)
        operador, _ = _login("d1op", papel="operador")

        assert _buscar(agent_id, operador).status_code == 200

    def test_sem_token_e_401(self, client):
        assert client.get("/api/v1/agents/x/metrics/valor").status_code == 401

    @pytest.mark.asyncio
    async def test_agente_inexistente_e_404(self):
        cabecalho, _ = _login("d3")

        assert _buscar("nao-existe", cabecalho).status_code == 404

    @pytest.mark.asyncio
    async def test_nao_mistura_agente(self):
        cabecalho, dono = _login("d4")
        a = await _agente("d4a", dono)
        b = await _agente("d4b", dono)
        await _caso(a, "d4a", minimo=1000, maximo=2000)
        await _caso(b, "d4b", minimo=9000, maximo=9000, telefone="5511984470007")

        assert _buscar(a, cabecalho).json()["total_max"] == 2000
