"""
O dossiê que o card do funil abre.

O card mostrava nome, telefone e um número de 0 a 100 — e o número sozinho não
diz nada. Estes casos cobrem o que a tela precisa e, principalmente, o que ela
não pode entregar: dossiê de contato de outro escritório.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.db.database import AsyncSessionLocal
from app.db.models import Agent, Caso, Conversation, Lead, LeadDetails, User
from app.main import app
from app.services.auth_service import AuthService
from tests.conftest import criar_acesso

client = TestClient(app)


def _login(sufixo: str) -> tuple[dict, str]:
    """Cabeçalho de autorização e o id do usuário, que o seed precisa."""
    email = f"dossie-{sufixo}@example.com"
    criar_acesso(client, email, "SenhaSegura123!", "Dono")
    r = client.post("/api/v1/auth/login", json={"email": email, "senha": "SenhaSegura123!"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    eu = client.get("/api/v1/auth/me", headers=headers).json()
    return headers, eu["id"]


async def _semear(
    sufixo: str,
    *,
    dono: str | None = None,
    com_caso: bool = True,
    com_detalhes: bool = True,
):
    """
    Um agente com um lead, opcionalmente com caso e dados coletados.

    `dono` é o id do usuário logado. Sem ele o agente nasce de outro dono — que
    é justamente o cenário dos testes de acesso.
    """
    async with AsyncSessionLocal() as db:
        if dono is None:
            outro = User(
                id=f"u-{sufixo}",
                email=f"seed-{sufixo}@example.com",
                nome="Outro escritório",
                senha_hash=AuthService.hash_password("x"),
                status="ativo",
            )
            db.add(outro)
            await db.flush()
            dono = outro.id

        agente = Agent(
            id=f"ag-{sufixo}",
            user_id=dono,
            nome="Triagem",
            system_prompt="p",
            temperatura=0.4,
            max_tokens=1024,
            status="ativo",
        )
        db.add(agente)
        await db.flush()

        conversa = Conversation(
            id=f"conv-{sufixo}", agent_id=agente.id, phone_number=f"55619{sufixo}", status="ativa"
        )
        db.add(conversa)
        await db.flush()

        lead = Lead(
            id=f"lead-{sufixo}",
            conversation_id=conversa.id,
            nome="Jonas Ferreira",
            email="jonas@example.com",
            phone_number=f"55619{sufixo}",
            status_funil="qualificado",
        )
        db.add(lead)
        await db.flush()

        if com_detalhes:
            db.add(
                LeadDetails(
                    lead_id=lead.id,
                    score_qualificacao=85,
                    inconsistencias="Não disse o salário",
                    problemas_detectados="Prazo apertado",
                    dados_json=json.dumps(
                        {
                            "dados_economicos": "salário R$ 2.100, 4 anos de casa",
                            "documentos_em_maos": "atestado e prints do RH",
                            "recomendacoes": "pedir a carta de justa causa",
                        }
                    ),
                )
            )

        if com_caso:
            db.add(
                Caso(
                    id=f"caso-{sufixo}",
                    lead_id=lead.id,
                    area="trabalhista",
                    resumo="Justa causa por abandono, com atestado enviado ao RH.",
                    score_qualificacao=85,
                    valor_estimado_min=18000,
                    valor_estimado_max=75000,
                    viabilidade="acima_do_piso",
                    analise_preliminar="## Resumo\nCliente relata demissão.",
                )
            )

        await db.commit()
    return f"ag-{sufixo}", f"lead-{sufixo}"


async def _cenario(sufixo: str, **kwargs):
    """
    Login **antes** da semeadura, e não depois.

    O cadastro público fecha no primeiro usuário. Semeando um `User` direto
    pelo SQLAlchemy antes de chamar `criar_acesso`, o cadastro já está fechado
    e não existe administrador conhecido para abrir sessão — o helper recusa,
    com razão.
    """
    headers, user_id = _login(sufixo)
    agent_id, lead_id = await _semear(sufixo, dono=user_id, **kwargs)
    return agent_id, lead_id, headers


def _buscar(agent_id: str, lead_id: str, headers: dict):
    return client.get(
        f"/api/v1/agents/{agent_id}/kanban/leads/{lead_id}", headers=headers
    )


class TestDossie:
    @pytest.mark.asyncio
    async def test_traz_o_caso_com_a_faixa_e_o_veredito(self):
        agent_id, lead_id, headers = await _cenario("a1")

        r = _buscar(agent_id, lead_id, headers)

        assert r.status_code == 200
        dados = r.json()
        assert dados["nome"] == "Jonas Ferreira"
        assert dados["score_qualificacao"] == 85
        caso = dados["casos"][0]
        assert caso["area"] == "trabalhista"
        assert (caso["valor_estimado_min"], caso["valor_estimado_max"]) == (18000, 75000)
        assert caso["viabilidade"] == "acima_do_piso"

    @pytest.mark.asyncio
    async def test_abre_os_campos_que_a_triagem_coletou(self):
        """
        Eles moram dentro do `dados_json` e nunca tinham saído de lá.

        Sem coluna própria de propósito: o bloco de qualificação muda com o
        prompt, e criar coluna a cada campo novo transformaria uma edição de
        texto em migração.
        """
        agent_id, lead_id, headers = await _cenario("a2")

        dados = _buscar(agent_id, lead_id, headers).json()

        assert "R$ 2.100" in dados["dados_economicos"]
        assert "atestado" in dados["documentos_em_maos"]
        assert "carta de justa causa" in dados["recomendacoes"]
        assert dados["inconsistencias"] == "Não disse o salário"

    @pytest.mark.asyncio
    async def test_leva_para_a_conversa(self):
        """Sem o id, o botão "ver o atendimento" não teria para onde ir."""
        agent_id, lead_id, headers = await _cenario("a3")

        r = _buscar(agent_id, lead_id, headers)
        assert r.status_code == 200, r.json()
        assert r.json()["conversation_id"] == "conv-a3"

    @pytest.mark.asyncio
    async def test_contato_sem_caso_nem_detalhes_ainda_abre(self):
        """
        Lead que entrou no funil e nunca foi qualificado é o estado normal da
        primeira coluna. Se o dossiê quebrasse aqui, a coluna mais cheia do
        board seria a que não abre.
        """
        agent_id, lead_id, headers = await _cenario(
            "a4", com_caso=False, com_detalhes=False
        )

        dados = _buscar(agent_id, lead_id, headers).json()

        assert dados["casos"] == []
        assert dados["score_qualificacao"] == 0
        assert dados["dados_economicos"] is None

    @pytest.mark.asyncio
    async def test_dados_json_quebrado_nao_derruba_o_dossie(self):
        """
        `dados_json` guarda o que o modelo devolveu. JSON inválido ali é motivo
        para o dossiê vir sem esses campos, não para a tela falhar.
        """
        agent_id, lead_id, headers = await _cenario("a5")
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select

            detalhes = (
                await db.execute(select(LeadDetails).where(LeadDetails.lead_id == lead_id))
            ).scalars().first()
            detalhes.dados_json = "{isso não é json"
            await db.commit()

        r = _buscar(agent_id, lead_id, headers)

        assert r.status_code == 200
        assert r.json()["dados_economicos"] is None


class TestAcesso:
    @pytest.mark.asyncio
    async def test_lead_de_outro_agente_e_404(self):
        """
        Conhecer o id de um lead não pode bastar para ler o dossiê dele.

        404 e não 403: dizer "existe, mas não é seu" já entrega que o contato
        existe naquele escritório.
        """
        agent_id, _, headers = await _cenario("b1")
        _, lead_alheio = await _semear("b2")

        assert _buscar(agent_id, lead_alheio, headers).status_code == 404

    @pytest.mark.asyncio
    async def test_agente_de_outro_dono_e_404(self):
        headers, _ = _login("b4")
        agent_alheio, lead_alheio = await _semear("b3")

        assert _buscar(agent_alheio, lead_alheio, headers).status_code == 404

    @pytest.mark.asyncio
    async def test_sem_token_e_401(self):
        agent_id, lead_id = await _semear("b5")

        assert client.get(
            f"/api/v1/agents/{agent_id}/kanban/leads/{lead_id}"
        ).status_code in (401, 403)
