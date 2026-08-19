"""
O funil de venda.

As métricas que já existiam contam volume. Nenhuma responde a pergunta que o
dono do escritório faz: de cada cem que escrevem, quantos viram caso — e
entre quais duas etapas eles somem.

A conta é cumulativa e sai da posição atual do card: as colunas são
ordenadas, então quem está em "Revisão" necessariamente passou por "Closer".
O que estes casos travam é essa aritmética e, principalmente, o lugar do
arquivado — que fora da cadeia é descarte e dentro dela seria sucesso.
"""

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
    Message,
)
from app.main import app
from app.services.kanban_defaults import criar_colunas_padrao
from tests.conftest import criar_acesso

client = TestClient(app)


def _login(sufixo: str) -> tuple[dict, str]:
    email = f"funil-{sufixo}@example.com"
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


async def _lead(
    agent_id: str,
    sufixo: str,
    coluna: str,
    *,
    dias_atras: int = 0,
    com_operador: bool = False,
):
    async with AsyncSessionLocal() as db:
        nascimento = datetime.utcnow() - timedelta(days=dias_atras)
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=agent_id,
                            phone_number=f"5561{sufixo}", status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}",
                    nome=f"Lead {sufixo}", phone_number=f"5561{sufixo}",
                    status_funil="novo", data_criacao=nascimento))
        await db.flush()

        alvo = (
            await db.execute(
                select(KanbanColumn).where(
                    (KanbanColumn.agent_id == agent_id) & (KanbanColumn.nome == coluna)
                )
            )
        ).scalars().first()
        db.add(KanbanCard(column_id=alvo.id, lead_id=f"lead-{sufixo}", ordem=1))

        # Duas mensagens do operador de propósito: o contador é de **leads**
        # com intervenção, não de mensagens.
        if com_operador:
            for i in range(2):
                db.add(Message(conversation_id=f"cv-{sufixo}", remetente="operador",
                               conteudo=f"oi {i}", timestamp=datetime.utcnow()))

        await db.commit()


def _buscar(agent_id: str, cabecalho: dict, **params):
    return client.get(
        f"/api/v1/agents/{agent_id}/metrics/funil", headers=cabecalho, params=params
    )


def _por_nome(dados: dict) -> dict:
    return {e["nome"]: e for e in dados["etapas"]}


class TestAAritmetica:
    @pytest.mark.asyncio
    async def test_quem_esta_adiante_conta_nas_etapas_anteriores(self):
        """
        O coração do funil. Um lead em "Revisão" passou por Closer,
        Entrevista, Viabilidade e Coleta — contá-lo só na última faria o topo
        parecer menor que a base.
        """
        cabecalho, dono = _login("a1")
        agent_id = await _agente("a1", dono)
        await _lead(agent_id, "a1x", "Revisão")

        etapas = _por_nome(_buscar(agent_id, cabecalho).json())

        assert etapas["Closer"]["chegaram"] == 1
        assert etapas["Revisão"]["chegaram"] == 1
        assert etapas["Closer"]["parados_aqui"] == 0
        assert etapas["Revisão"]["parados_aqui"] == 1

    @pytest.mark.asyncio
    async def test_o_percentual_do_topo_da_a_forma_do_funil(self):
        cabecalho, dono = _login("a2")
        agent_id = await _agente("a2", dono)
        for i in range(8):
            await _lead(agent_id, f"a2c{i}", "Closer")
        await _lead(agent_id, "a2v", "Viabilidade")
        await _lead(agent_id, "a2r", "Revisão")

        etapas = _por_nome(_buscar(agent_id, cabecalho).json())

        assert etapas["Closer"]["chegaram"] == 10
        assert etapas["Closer"]["percentual_do_topo"] == 100.0
        assert etapas["Viabilidade"]["chegaram"] == 2
        assert etapas["Viabilidade"]["percentual_do_topo"] == 20.0
        assert etapas["Revisão"]["percentual_do_topo"] == 10.0

    @pytest.mark.asyncio
    async def test_a_conversao_da_etapa_diz_onde_o_funil_aperta(self):
        """
        É o número acionável. "20% do topo" na Viabilidade não diz se a perda
        foi na Entrevista ou na Coleta; a conversão etapa a etapa diz.
        """
        cabecalho, dono = _login("a3")
        agent_id = await _agente("a3", dono)
        for i in range(10):
            await _lead(agent_id, f"a3c{i}", "Closer")
        for i in range(5):
            await _lead(agent_id, f"a3e{i}", "Entrevista")

        etapas = _por_nome(_buscar(agent_id, cabecalho).json())

        assert etapas["Closer"]["conversao_da_etapa"] == 100.0
        # 5 de 15 chegaram à Entrevista.
        assert etapas["Entrevista"]["chegaram"] == 5
        assert etapas["Entrevista"]["conversao_da_etapa"] == pytest.approx(33.3)

    @pytest.mark.asyncio
    async def test_funil_vazio_abre_sem_dividir_por_zero(self):
        """Agente novo tem topo zero; a tela precisa abrir mesmo assim."""
        cabecalho, dono = _login("a4")
        agent_id = await _agente("a4", dono)

        resposta = _buscar(agent_id, cabecalho)

        assert resposta.status_code == 200
        dados = resposta.json()
        assert dados["total_de_leads"] == 0
        assert all(e["percentual_do_topo"] == 0.0 for e in dados["etapas"])


class TestOArquivado:
    @pytest.mark.asyncio
    async def test_arquivado_fica_fora_da_cadeia(self):
        """
        O que mais importa aqui. Um lead arquivado direto do primeiro contato
        não passou por etapa nenhuma. Dentro da cadeia cumulativa ele contaria
        como "chegou até o fim", e o escritório leria descarte como sucesso —
        o sinal do funil invertido.
        """
        cabecalho, dono = _login("b1")
        agent_id = await _agente("b1", dono)
        await _lead(agent_id, "b1c", "Closer")
        await _lead(agent_id, "b1a", "Arquivado")

        dados = _buscar(agent_id, cabecalho).json()
        etapas = _por_nome(dados)

        assert dados["arquivados"] == 1
        assert dados["total_de_leads"] == 2
        assert etapas["Closer"]["chegaram"] == 1
        assert "Arquivado" not in etapas

    @pytest.mark.asyncio
    async def test_arquivado_nao_infla_a_conversao_da_revisao(self):
        cabecalho, dono = _login("b2")
        agent_id = await _agente("b2", dono)
        for i in range(4):
            await _lead(agent_id, f"b2a{i}", "Arquivado")
        await _lead(agent_id, "b2c", "Closer")

        etapas = _por_nome(_buscar(agent_id, cabecalho).json())

        assert etapas["Revisão"]["chegaram"] == 0
        assert etapas["Revisão"]["conversao_da_etapa"] == 0.0


class TestIntervencaoHumana:
    @pytest.mark.asyncio
    async def test_conta_leads_e_nao_mensagens(self):
        cabecalho, dono = _login("c1")
        agent_id = await _agente("c1", dono)
        await _lead(agent_id, "c1a", "Viabilidade", com_operador=True)
        await _lead(agent_id, "c1b", "Viabilidade")

        etapas = _por_nome(_buscar(agent_id, cabecalho).json())

        # Duas mensagens do operador num lead só.
        assert etapas["Viabilidade"]["com_intervencao_humana"] == 1

    @pytest.mark.asyncio
    async def test_a_intervencao_tambem_acumula_para_tras(self):
        """
        Se alguém falou com o cliente na Revisão, esse cliente teve
        intervenção humana no caminho todo — e é isso que a etapa anterior
        precisa mostrar.
        """
        cabecalho, dono = _login("c2")
        agent_id = await _agente("c2", dono)
        await _lead(agent_id, "c2r", "Revisão", com_operador=True)

        etapas = _por_nome(_buscar(agent_id, cabecalho).json())

        assert etapas["Closer"]["com_intervencao_humana"] == 1
        assert etapas["Revisão"]["com_intervencao_humana"] == 1

    @pytest.mark.asyncio
    async def test_mensagem_da_ia_nao_e_intervencao(self):
        cabecalho, dono = _login("c3")
        agent_id = await _agente("c3", dono)
        await _lead(agent_id, "c3", "Viabilidade")
        async with AsyncSessionLocal() as db:
            db.add(Message(conversation_id="cv-c3", remetente="assistant",
                           conteudo="oi", timestamp=datetime.utcnow()))
            await db.commit()

        etapas = _por_nome(_buscar(agent_id, cabecalho).json())

        assert etapas["Viabilidade"]["com_intervencao_humana"] == 0


class TestPeriodoEAcesso:
    @pytest.mark.asyncio
    async def test_o_filtro_de_dias_corta_pela_data_de_entrada(self):
        cabecalho, dono = _login("d1")
        agent_id = await _agente("d1", dono)
        await _lead(agent_id, "d1novo", "Closer", dias_atras=2)
        await _lead(agent_id, "d1velho", "Closer", dias_atras=90)

        assert _buscar(agent_id, cabecalho).json()["total_de_leads"] == 2
        assert _buscar(agent_id, cabecalho, dias=30).json()["total_de_leads"] == 1

    @pytest.mark.asyncio
    async def test_sem_filtro_e_desde_sempre(self):
        """
        Um escritório com poucos leads por semana não tem funil nenhum em
        sete dias, e uma tela que abre em "0 de 0" parece quebrada.
        """
        cabecalho, dono = _login("d2")
        agent_id = await _agente("d2", dono)
        await _lead(agent_id, "d2", "Closer", dias_atras=300)

        assert _buscar(agent_id, cabecalho).json()["total_de_leads"] == 1

    @pytest.mark.asyncio
    async def test_operador_ve_o_funil(self):
        cabecalho, dono = _login("d3")
        agent_id = await _agente("d3", dono)
        criar_acesso(client, "operador-funil@example.com", "SenhaDoOperador123",
                     "Operador", papel="operador")
        login = client.post("/api/v1/auth/login", json={
            "email": "operador-funil@example.com", "senha": "SenhaDoOperador123"})
        operador = {"Authorization": f"Bearer {login.json()['access_token']}"}

        assert _buscar(agent_id, operador).status_code == 200

    def test_sem_token_e_401(self):
        assert client.get("/api/v1/agents/x/metrics/funil").status_code == 401

    @pytest.mark.asyncio
    async def test_agente_inexistente_e_404(self):
        cabecalho, _ = _login("d5")

        assert _buscar("nao-existe", cabecalho).status_code == 404
