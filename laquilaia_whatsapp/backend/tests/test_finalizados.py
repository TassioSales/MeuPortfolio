"""
Os casos que acabaram, e por quê.

Tudo cai em "Arquivado" e o board não diz o motivo. Mas "não era da nossa
área" e "o caso é pequeno demais" pedem coisas opostas: o primeiro é volume
de marketing errado, o segundo é o piso comercial funcionando. Um número só
some com essa diferença.

O que estes casos travam é a classificação — que sai do que o parecer já
grava, sem campo novo para alguém preencher à mão.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db.database import AsyncSessionLocal
from app.db.models import Agent, Caso, Conversation, Lead, LeadTimeline
from app.main import app
from app.routers.finalizados import _classificar
from tests.conftest import criar_acesso

client = TestClient(app)


def _login(sufixo: str, papel: str = "admin") -> tuple[dict, str]:
    email = f"fin-{sufixo}@example.com"
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


async def _arquivado(
    agent_id: str,
    sufixo: str,
    *,
    viabilidade: str | None = None,
    area: str = "trabalhista",
    dias_atras: int = 1,
    status_funil: str = "arquivado",
    arquivado_por: str | None = None,
):
    quando = datetime.utcnow() - timedelta(days=dias_atras)
    async with AsyncSessionLocal() as db:
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=agent_id,
                            phone_number=f"5561{sufixo}", status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}",
                    nome=f"Lead {sufixo}", phone_number=f"5561{sufixo}",
                    status_funil=status_funil, data_atualizacao=quando))
        await db.flush()

        if viabilidade is not None:
            db.add(Caso(id=f"caso-{sufixo}", lead_id=f"lead-{sufixo}", area=area,
                        resumo="Justa causa", viabilidade=viabilidade,
                        valor_estimado_min=2000, valor_estimado_max=9000,
                        data_abertura=quando))

        if arquivado_por:
            db.add(LeadTimeline(lead_id=f"lead-{sufixo}", status_anterior="qualificado",
                                status_novo="arquivado", mudado_por=arquivado_por,
                                motivo="Movido para Arquivado no painel", timestamp=quando))

        await db.commit()


def _buscar(agent_id: str, cabecalho: dict, **params):
    return client.get(f"/api/v1/agents/{agent_id}/finalizados",
                      headers=cabecalho, params=params)


def _grupo(dados: dict, motivo: str) -> dict:
    return next(g for g in dados["grupos"] if g["motivo"] == motivo)


class TestAClassificacao:
    def test_abaixo_do_piso(self):
        assert _classificar(Caso(viabilidade="abaixo_do_piso", area="trabalhista")) == "abaixo_do_piso"

    def test_area_de_fora(self):
        assert _classificar(Caso(viabilidade="acima_do_piso", area="familia")) == "fora_da_area"

    def test_nao_se_aplica_tambem_e_fora_da_area(self):
        assert _classificar(Caso(viabilidade="nao_se_aplica", area=None)) == "fora_da_area"

    def test_sem_caso_nenhum_e_sem_retorno(self):
        """
        A pessoa parou de responder antes de a triagem dimensionar qualquer
        coisa. Não é caso inviável — e juntar os dois esconderia justamente a
        métrica que diz se o atendimento perde gente no meio da conversa.
        """
        assert _classificar(None) == "sem_retorno"

    def test_indeterminado_nao_vira_inviavel(self):
        """
        O parecer não conseguiu dimensionar. Chamar isso de "abaixo do piso"
        seria pôr na conta do valor do caso o que foi limitação da análise.
        """
        assert _classificar(Caso(viabilidade="indeterminado", area="trabalhista")) == "outro"


class TestATela:
    @pytest.mark.asyncio
    async def test_agrupa_pelos_motivos(self):
        cabecalho, dono = _login("b1")
        agent_id = await _agente("b1", dono)
        await _arquivado(agent_id, "b1a", viabilidade="abaixo_do_piso")
        await _arquivado(agent_id, "b1b", viabilidade="acima_do_piso", area="civel")
        await _arquivado(agent_id, "b1c", viabilidade=None)

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["total"] == 3
        assert _grupo(dados, "abaixo_do_piso")["total"] == 1
        assert _grupo(dados, "fora_da_area")["total"] == 1
        assert _grupo(dados, "sem_retorno")["total"] == 1

    @pytest.mark.asyncio
    async def test_o_card_traz_a_faixa_estimada(self):
        cabecalho, dono = _login("b2")
        agent_id = await _agente("b2", dono)
        await _arquivado(agent_id, "b2", viabilidade="abaixo_do_piso")

        caso = _grupo(_buscar(agent_id, cabecalho).json(), "abaixo_do_piso")["casos"][0]

        assert (caso["valor_estimado_min"], caso["valor_estimado_max"]) == (2000, 9000)
        assert caso["empresa_ou_resumo"] == "Justa causa"

    @pytest.mark.asyncio
    async def test_mostra_quem_arquivou_quando_foi_gente(self):
        cabecalho, dono = _login("b3")
        agent_id = await _agente("b3", dono)
        await _arquivado(agent_id, "b3", viabilidade="abaixo_do_piso", arquivado_por=dono)

        caso = _grupo(_buscar(agent_id, cabecalho).json(), "abaixo_do_piso")["casos"][0]

        assert caso["arquivado_por"] == "Pessoa b3"

    @pytest.mark.asyncio
    async def test_arquivado_pela_triagem_vem_sem_responsavel(self):
        cabecalho, dono = _login("b4")
        agent_id = await _agente("b4", dono)
        await _arquivado(agent_id, "b4", viabilidade="abaixo_do_piso")

        caso = _grupo(_buscar(agent_id, cabecalho).json(), "abaixo_do_piso")["casos"][0]

        assert caso["arquivado_por"] is None

    @pytest.mark.asyncio
    async def test_lead_ainda_no_funil_nao_aparece(self):
        """Finalizado é quem acabou. Caso em andamento aqui seria enterro em vida."""
        cabecalho, dono = _login("b5")
        agent_id = await _agente("b5", dono)
        await _arquivado(agent_id, "b5", viabilidade="acima_do_piso",
                         status_funil="qualificado")

        assert _buscar(agent_id, cabecalho).json()["total"] == 0

    @pytest.mark.asyncio
    async def test_o_recorte_de_dias_vale(self):
        cabecalho, dono = _login("b6")
        agent_id = await _agente("b6", dono)
        await _arquivado(agent_id, "b6a", viabilidade=None, dias_atras=5)
        await _arquivado(agent_id, "b6b", viabilidade=None, dias_atras=200)

        assert _buscar(agent_id, cabecalho).json()["total"] == 1
        assert _buscar(agent_id, cabecalho, dias=365).json()["total"] == 2

    @pytest.mark.asyncio
    async def test_sem_nada_arquivado_os_grupos_vem_vazios_e_nao_somem(self):
        """
        A tela precisa mostrar as colunas mesmo vazias: um board sem colunas
        parece defeito, e o escritório precisa ver que "abaixo do piso" existe
        como destino antes de haver um caso lá.
        """
        cabecalho, dono = _login("b7")
        agent_id = await _agente("b7", dono)

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["total"] == 0
        assert len(dados["grupos"]) == 4
        assert all(g["casos"] == [] for g in dados["grupos"])


class TestAcesso:
    @pytest.mark.asyncio
    async def test_operador_ve(self):
        cabecalho, dono = _login("c1")
        agent_id = await _agente("c1", dono)
        operador, _ = _login("c1op", papel="operador")

        assert _buscar(agent_id, operador).status_code == 200

    def test_sem_token_e_401(self):
        assert client.get("/api/v1/agents/x/finalizados").status_code == 401

    @pytest.mark.asyncio
    async def test_agente_inexistente_e_404(self):
        cabecalho, _ = _login("c3")

        assert _buscar("nao-existe", cabecalho).status_code == 404

    @pytest.mark.asyncio
    async def test_nao_mistura_agente(self):
        cabecalho, dono = _login("c4")
        a = await _agente("c4a", dono)
        b = await _agente("c4b", dono)
        await _arquivado(a, "c4a", viabilidade=None)
        await _arquivado(b, "c4b", viabilidade=None)

        assert _buscar(a, cabecalho).json()["total"] == 1
