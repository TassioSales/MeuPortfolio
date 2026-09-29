"""
A lista de contatos, com busca.

O Kanban é bom para trabalhar o funil e péssimo para achar uma pessoa: a
primeira coluna do escritório tem 155 cards. Quem atende no telefone precisa
do contrário — digitar "Alexandre" ou os últimos dígitos e chegar nele.

O que estes casos travam é a busca (que precisa casar com as três formas de
lembrar de alguém), a contagem (que é do resultado, não da página) e o que a
lista mostra sem obrigar a abrir o contato.
"""

import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Agent,
    Conversation,
    KanbanCard,
    KanbanColumn,
    Lead,
    LeadDetails,
)
from app.main import app
from app.services.kanban_defaults import criar_colunas_padrao
from tests.conftest import criar_acesso

client = TestClient(app)


def _login(sufixo: str) -> tuple[dict, str]:
    email = f"clientes-{sufixo}@example.com"
    criar_acesso(client, email, "SenhaSegura123!", "Dono")
    r = client.post("/api/v1/auth/login", json={"email": email, "senha": "SenhaSegura123!"})
    cabecalho = {"Authorization": f"Bearer {r.json()['access_token']}"}
    eu = client.get("/api/v1/auth/me", headers=cabecalho).json()
    return cabecalho, eu["id"]


async def _agente(sufixo: str, dono: str) -> str:
    agent_id = f"ag-{sufixo}"
    async with AsyncSessionLocal() as db:
        db.add(
            Agent(id=agent_id, user_id=dono, nome="Triagem", system_prompt="p",
                  temperatura=0.4, max_tokens=1024, status="ativo")
        )
        await db.flush()
        await criar_colunas_padrao(agent_id, db)
        await db.commit()
    return agent_id


async def _contato(
    agent_id: str,
    sufixo: str,
    *,
    nome: str | None = "Marina da Silva",
    telefone: str = "5561999887766",
    email: str | None = None,
    empresa: str | None = None,
    cargo: str | None = None,
    score: int = 0,
    coluna: str | None = None,
    dias_parado: int = 0,
    dados_json_quebrado: bool = False,
):
    async with AsyncSessionLocal() as db:
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=agent_id,
                            phone_number=telefone, status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}", nome=nome,
                    email=email, phone_number=telefone, status_funil="novo"))
        await db.flush()

        if empresa or cargo or score or dados_json_quebrado:
            db.add(
                LeadDetails(
                    lead_id=f"lead-{sufixo}",
                    score_qualificacao=score,
                    dados_json=(
                        "{isto não é json"
                        if dados_json_quebrado
                        else json.dumps({"empresa": empresa, "cargo": cargo})
                    ),
                )
            )

        if coluna:
            alvo = (
                await db.execute(
                    select(KanbanColumn).where(
                        (KanbanColumn.agent_id == agent_id) & (KanbanColumn.nome == coluna)
                    )
                )
            ).scalars().first()
            db.add(
                KanbanCard(
                    column_id=alvo.id,
                    lead_id=f"lead-{sufixo}",
                    ordem=1,
                    data_movimentacao=datetime.utcnow() - timedelta(days=dias_parado),
                )
            )

        await db.commit()


def _buscar(agent_id: str, cabecalho: dict, **params):
    return client.get(f"/api/v1/agents/{agent_id}/clientes", headers=cabecalho, params=params)


class TestOQueALinhaMostra:
    @pytest.mark.asyncio
    async def test_traz_o_que_identifica_o_caso_sem_abrir(self):
        cabecalho, dono = _login("a1")
        agent_id = await _agente("a1", dono)
        await _contato(agent_id, "a1", empresa="Supermercado Tático", cargo="Repositor",
                       score=85, coluna="Viabilidade", dias_parado=6)

        linha = _buscar(agent_id, cabecalho).json()["clientes"][0]

        assert linha["nome"] == "Marina da Silva"
        assert (linha["empresa"], linha["cargo"]) == ("Supermercado Tático", "Repositor")
        assert linha["score_qualificacao"] == 85
        assert linha["etapa"] == "Viabilidade"
        assert linha["dias_parado"] == 6
        assert linha["conversation_id"] == "cv-a1"

    @pytest.mark.asyncio
    async def test_lead_sem_card_ainda_aparece(self):
        """
        Contato criado antes de existir funil não tem card. Sumir da lista
        seria o pior desfecho: some justamente quem ninguém está acompanhando.
        """
        cabecalho, dono = _login("a2")
        agent_id = await _agente("a2", dono)
        await _contato(agent_id, "a2", coluna=None)

        linha = _buscar(agent_id, cabecalho).json()["clientes"][0]

        assert linha["etapa"] is None
        assert linha["dias_parado"] is None

    @pytest.mark.asyncio
    async def test_dados_json_quebrado_nao_derruba_a_lista(self):
        cabecalho, dono = _login("a3")
        agent_id = await _agente("a3", dono)
        await _contato(agent_id, "a3", dados_json_quebrado=True)

        resposta = _buscar(agent_id, cabecalho)

        assert resposta.status_code == 200
        assert resposta.json()["clientes"][0]["empresa"] is None


class TestABusca:
    @pytest.mark.asyncio
    async def test_acha_por_pedaco_do_nome(self):
        cabecalho, dono = _login("b1")
        agent_id = await _agente("b1", dono)
        await _contato(agent_id, "b1a", nome="Alexandre Santos", telefone="5564931207")
        await _contato(agent_id, "b1b", nome="Marina Silva", telefone="5511984479")

        dados = _buscar(agent_id, cabecalho, busca="alexan").json()

        assert [c["nome"] for c in dados["clientes"]] == ["Alexandre Santos"]

    @pytest.mark.asyncio
    async def test_acha_pelo_final_do_telefone(self):
        """Ninguém lembra o número inteiro; lembra os quatro últimos."""
        cabecalho, dono = _login("b2")
        agent_id = await _agente("b2", dono)
        await _contato(agent_id, "b2a", nome="Alexandre", telefone="5564931207")
        await _contato(agent_id, "b2b", nome="Marina", telefone="5511984479")

        dados = _buscar(agent_id, cabecalho, busca="4479").json()

        assert [c["nome"] for c in dados["clientes"]] == ["Marina"]

    @pytest.mark.asyncio
    async def test_telefone_digitado_com_formatacao_ainda_acha(self):
        """
        Quem copia do WhatsApp cola "(61) 99988-7766". Sem limpar a
        pontuação, a busca não casaria com nada e a tela diria "nenhum
        contato" para alguém que está no banco.
        """
        cabecalho, dono = _login("b3")
        agent_id = await _agente("b3", dono)
        await _contato(agent_id, "b3", telefone="5561999887766")

        dados = _buscar(agent_id, cabecalho, busca="(61) 99988-7766").json()

        assert dados["total"] == 1

    @pytest.mark.asyncio
    async def test_acha_pelo_email(self):
        cabecalho, dono = _login("b4")
        agent_id = await _agente("b4", dono)
        await _contato(agent_id, "b4a", nome="Alexandre", email="alex@empresa.com",
                       telefone="5564931207")
        await _contato(agent_id, "b4b", nome="Marina", telefone="5511984479")

        dados = _buscar(agent_id, cabecalho, busca="empresa.com").json()

        assert [c["nome"] for c in dados["clientes"]] == ["Alexandre"]

    @pytest.mark.asyncio
    async def test_uma_letra_nao_filtra(self):
        """
        Uma letra casa com metade da base e faz o banco varrer tudo para não
        filtrar nada. A tela digita a cada tecla; o primeiro caractere não
        pode virar consulta.
        """
        cabecalho, dono = _login("b5")
        agent_id = await _agente("b5", dono)
        await _contato(agent_id, "b5a", nome="Alexandre", telefone="5564931207")
        await _contato(agent_id, "b5b", nome="Marina", telefone="5511984479")

        assert _buscar(agent_id, cabecalho, busca="a").json()["total"] == 2

    @pytest.mark.asyncio
    async def test_busca_sem_resultado_devolve_lista_vazia_e_nao_erro(self):
        cabecalho, dono = _login("b6")
        agent_id = await _agente("b6", dono)
        await _contato(agent_id, "b6")

        dados = _buscar(agent_id, cabecalho, busca="zzzzz").json()

        assert (dados["total"], dados["clientes"]) == (0, [])

    @pytest.mark.asyncio
    async def test_contato_sem_nome_nao_quebra_a_busca(self):
        """Lead que só mandou "oi" não tem nome; `ILIKE` sobre NULL é NULL."""
        cabecalho, dono = _login("b7")
        agent_id = await _agente("b7", dono)
        await _contato(agent_id, "b7a", nome=None, telefone="5564931207")
        await _contato(agent_id, "b7b", nome="Marina", telefone="5511984479")

        dados = _buscar(agent_id, cabecalho, busca="marina").json()

        assert dados["total"] == 1


class TestFiltroEPaginacao:
    @pytest.mark.asyncio
    async def test_filtra_por_etapa(self):
        cabecalho, dono = _login("c1")
        agent_id = await _agente("c1", dono)
        await _contato(agent_id, "c1a", nome="Em viabilidade", telefone="5564931207",
                       coluna="Viabilidade")
        await _contato(agent_id, "c1b", nome="No arquivo", telefone="5511984479",
                       coluna="Arquivado")

        dados = _buscar(agent_id, cabecalho, etapa="Arquivado").json()

        assert [c["nome"] for c in dados["clientes"]] == ["No arquivo"]

    @pytest.mark.asyncio
    async def test_o_total_e_do_resultado_e_nao_da_pagina(self):
        """
        Contar as linhas devolvidas diria "50 de 50" para uma base de
        trezentos, e a paginação nunca ofereceria a página 2.
        """
        cabecalho, dono = _login("c2")
        agent_id = await _agente("c2", dono)
        for i in range(55):
            await _contato(agent_id, f"c2-{i}", nome=f"Contato {i}",
                           telefone=f"55619{i:08d}")

        dados = _buscar(agent_id, cabecalho).json()

        assert dados["total"] == 55
        assert len(dados["clientes"]) == 50

    @pytest.mark.asyncio
    async def test_a_segunda_pagina_traz_o_resto(self):
        cabecalho, dono = _login("c3")
        agent_id = await _agente("c3", dono)
        for i in range(55):
            await _contato(agent_id, f"c3-{i}", nome=f"Contato {i}",
                           telefone=f"55619{i:08d}")

        dados = _buscar(agent_id, cabecalho, pagina=2).json()

        assert len(dados["clientes"]) == 5


class TestAcesso:
    @pytest.mark.asyncio
    async def test_operador_ve_a_lista(self):
        cabecalho, dono = _login("d1")
        agent_id = await _agente("d1", dono)
        await _contato(agent_id, "d1")

        criar_acesso(client, "operador-clientes@example.com", "SenhaDoOperador123",
                     "Operador", papel="operador")
        login = client.post("/api/v1/auth/login", json={
            "email": "operador-clientes@example.com", "senha": "SenhaDoOperador123"})
        operador = {"Authorization": f"Bearer {login.json()['access_token']}"}

        assert _buscar(agent_id, operador).status_code == 200

    def test_sem_token_e_401(self):
        assert client.get("/api/v1/agents/qualquer/clientes").status_code == 401

    @pytest.mark.asyncio
    async def test_agente_inexistente_e_404(self):
        cabecalho, _ = _login("d2")

        assert _buscar("nao-existe", cabecalho).status_code == 404

    @pytest.mark.asyncio
    async def test_nao_mistura_contato_de_outro_agente(self):
        cabecalho, dono = _login("d3")
        a = await _agente("d3a", dono)
        b = await _agente("d3b", dono)
        await _contato(a, "d3a", nome="Do agente A", telefone="5564931207")
        await _contato(b, "d3b", nome="Do agente B", telefone="5511984479")

        dados = _buscar(a, cabecalho).json()

        assert [c["nome"] for c in dados["clientes"]] == ["Do agente A"]
