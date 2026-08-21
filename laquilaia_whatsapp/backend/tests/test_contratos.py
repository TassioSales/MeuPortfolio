"""
O contrato: o modelo com lacunas, o preenchimento e o PDF.

Três coisas aqui não são hipótese, são o motivo de o código ter a forma que
tem:

1. **O contrato guarda o texto preenchido, não uma referência ao modelo.** Se
   guardasse a referência, corrigir uma cláusula em março mudaria o que o
   cliente assinou em janeiro.
2. **Dado que falta vira `____________`, não string vazia.** "portador do CPF
   nº " seguido de nada é o que faz alguém assinar sem reparar.
3. **`&` e `<` no nome de uma empresa quebrariam o parser do reportlab.**
   "Silva & Filhos" derrubaria a geração inteira no meio de um contrato.
"""

import pytest
from fastapi.testclient import TestClient

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Agent,
    Caso,
    ConfiguracaoEscritorio,
    Conversation,
    Lead,
    LeadDetails,
)
from app.main import app
from app.services import contrato_service
from tests.conftest import criar_acesso

client = TestClient(app)

CORPO = (
    "# CONTRATO\n"
    "{{cliente.nome}}, CPF {{cliente.cpf}}, de {{cliente.cidade}}/{{cliente.uf}}.\n"
    "Causa: {{caso.area}} contra {{caso.empresa}}.\n"
    "{{escritorio.nome}} — OAB {{escritorio.oab}}.\n"
    "{{data.cidade_e_data}}\n"
)


def _login(sufixo: str, papel: str = "admin") -> tuple[dict, str]:
    email = f"ctr-{sufixo}@example.com"
    criar_acesso(client, email, "SenhaSegura123!", f"Pessoa {sufixo}", papel=papel)
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "senha": "SenhaSegura123!"}
    )
    cabecalho = {"Authorization": f"Bearer {r.json()['access_token']}"}
    eu = client.get("/api/v1/auth/me", headers=cabecalho).json()
    return cabecalho, eu["id"]


async def _cenario(sufixo: str, dono: str, com_escritorio: bool = True) -> str:
    """Um lead com caso e detalhes, pronto para virar contrato."""
    async with AsyncSessionLocal() as db:
        db.add(Agent(id=f"ag-{sufixo}", user_id=dono, nome="Triagem",
                     system_prompt="p", temperatura=0.4, max_tokens=1024,
                     status="ativo"))
        await db.flush()
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=f"ag-{sufixo}",
                            phone_number=f"5561{sufixo}", status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}",
                    nome="Tássio Sales", phone_number=f"5561{sufixo}",
                    status_funil="qualificado"))
        await db.flush()
        db.add(Caso(id=f"caso-{sufixo}", lead_id=f"lead-{sufixo}",
                    area="trabalhista", resumo="Verbas rescisórias"))
        db.add(LeadDetails(id=f"det-{sufixo}", lead_id=f"lead-{sufixo}",
                           dados_json='{"empresa": "Silva & Filhos", "cargo": "Analista"}'))
        if com_escritorio:
            db.add(ConfiguracaoEscritorio(id="unica", nome="Escritório X",
                                          oab_responsavel="DF 12345",
                                          cidade="Brasília"))
        await db.commit()
    return f"lead-{sufixo}"


def _criar_modelo(cabecalho: dict, nome="Padrão", corpo=CORPO, ativo=True):
    return client.post("/api/v1/contratos/modelos", headers=cabecalho,
                       json={"nome": nome, "corpo": corpo, "ativo": ativo})


# ------------------------------------------------------------ o preenchimento

class TestPreenchimento:
    def test_cpf_sai_formatado(self):
        assert contrato_service.formatar_cpf("12345678901") == "123.456.789-01"

    def test_cpf_de_tamanho_errado_sai_como_veio(self):
        """
        Formatar um CPF inválido esconderia o erro atrás de uma máscara
        bonita — e alguém assinaria um número que não existe.
        """
        assert contrato_service.formatar_cpf("123") == "123"

    def test_variavel_inexistente_e_apontada(self):
        assert contrato_service.variaveis_desconhecidas(
            "Eu, {{cliente.nome}}, {{cliente.cpj}}."
        ) == ["cliente.cpj"]

    def test_variavel_inexistente_vira_lacuna_e_nao_some(self):
        """Buraco invisível no texto é pior que lacuna visível."""
        saida = contrato_service.preencher("A {{cliente.cpj}} B", {})
        assert contrato_service.LACUNA in saida

    def test_dado_ausente_vira_lacuna(self):
        contexto = contrato_service.montar_contexto(
            lead=None, dados=None, caso=None, detalhes_json={}, escritorio=None
        )
        assert contexto["cliente.cpf"] == contrato_service.LACUNA
        assert contexto["cliente.nome"] == contrato_service.LACUNA


class TestRascunhoBase:
    def test_o_rascunho_so_usa_lacunas_que_existem(self):
        """
        O rascunho semeado é texto escrito à mão. Uma lacuna digitada errada
        nele viraria espaço em branco no contrato de todo cliente que usasse
        o modelo sem reparar.
        """
        from app.prompts.modelo_contrato_base import MODELO_BASE

        assert contrato_service.variaveis_desconhecidas(MODELO_BASE) == []

    def test_o_rascunho_nao_crava_percentual_de_honorarios(self):
        """
        O número é compromisso comercial do escritório. Um default de software
        viraria obrigação assumida por quem nunca a escolheu — por isso o
        percentual é lacuna, e o rascunho nasce inativo.
        """
        from app.prompts.modelo_contrato_base import MODELO_BASE

        import re
        assert re.search(r"percentual de ____", MODELO_BASE)
        assert not re.search(r"\d+\s*%", MODELO_BASE)


class TestPdf:
    def test_sai_um_pdf(self):
        pdf = contrato_service.em_pdf("# Título\nUm parágrafo.")
        assert pdf.startswith(b"%PDF-")

    def test_e_comercial_no_nome_da_empresa_nao_derruba(self):
        """
        `&` e `<` são marcação para o reportlab. Sem escape, "Silva & Filhos"
        estoura o parser no meio da geração.
        """
        pdf = contrato_service.em_pdf("Contra **Silva & Filhos** <Ltda>.")
        assert pdf.startswith(b"%PDF-")


# ------------------------------------------------------------------- modelos

class TestModelos:
    def test_admin_cria_e_lista(self):
        cabecalho, _ = _login("m1")
        r = _criar_modelo(cabecalho)
        assert r.status_code == 201
        assert r.json()["ativo"] is True

        lista = client.get("/api/v1/contratos/modelos", headers=cabecalho)
        assert [m["nome"] for m in lista.json()] == ["Padrão"]

    def test_operador_nao_cria(self):
        """Cláusula e honorários são compromisso do escritório, não do plantão."""
        _login("m2")
        op, _ = _login("m2op", papel="operador")
        assert _criar_modelo(op).status_code == 404

    def test_operador_le(self):
        """Quem gera o contrato precisa ver o texto antes de enviá-lo."""
        cabecalho, _ = _login("m3")
        _criar_modelo(cabecalho)
        op, _ = _login("m3op", papel="operador")
        assert client.get("/api/v1/contratos/modelos", headers=op).status_code == 200

    def test_variavel_inexistente_recusa_o_modelo(self):
        """
        O erro aparece ao salvar, não na hora de gerar o contrato do cliente —
        quando alguém já prometeu o documento.
        """
        cabecalho, _ = _login("m4")
        r = _criar_modelo(cabecalho, corpo="Eu, {{cliente.cpj}}.")
        assert r.status_code == 422
        assert "cliente.cpj" in r.json()["detail"]

    def test_so_um_ativo_por_vez(self):
        cabecalho, _ = _login("m5")
        primeiro = _criar_modelo(cabecalho, nome="Primeiro").json()
        _criar_modelo(cabecalho, nome="Segundo")

        modelos = {m["id"]: m["ativo"] for m in
                   client.get("/api/v1/contratos/modelos", headers=cabecalho).json()}
        assert modelos[primeiro["id"]] is False
        assert sum(1 for ativo in modelos.values() if ativo) == 1

    def test_nome_repetido_e_recusado(self):
        cabecalho, _ = _login("m6")
        _criar_modelo(cabecalho, nome="Igual")
        assert _criar_modelo(cabecalho, nome="Igual").status_code == 422

    def test_anonimo_nao_le(self):
        assert client.get("/api/v1/contratos/modelos").status_code == 401

    def test_variaveis_vem_do_backend(self):
        """Duas listas — a do editor e a do preenchimento — divergiriam."""
        cabecalho, _ = _login("m7")
        r = client.get("/api/v1/contratos/variaveis", headers=cabecalho)
        nomes = {v["nome"] for v in r.json()}
        assert nomes == set(contrato_service.VARIAVEIS)


# ---------------------------------------------------------- dados do cliente

class TestDados:
    @pytest.mark.asyncio
    async def test_abre_vazio_e_nao_404(self):
        """Cliente sem qualificação civil é o estado normal."""
        cabecalho, dono = _login("d1")
        lead = await _cenario("d1", dono)
        r = client.get(f"/api/v1/contratos/leads/{lead}/dados", headers=cabecalho)
        assert r.status_code == 200
        assert r.json()["cpf"] is None

    @pytest.mark.asyncio
    async def test_grava_e_le_de_volta(self):
        cabecalho, dono = _login("d2")
        lead = await _cenario("d2", dono)
        client.put(f"/api/v1/contratos/leads/{lead}/dados", headers=cabecalho,
                   json={"cpf": "123.456.789-01", "uf": "df", "estado_civil": "casado"})

        r = client.get(f"/api/v1/contratos/leads/{lead}/dados", headers=cabecalho)
        # Guardado só com dígitos: assim "123.456.789-01" e "12345678901" são
        # o mesmo CPF no banco.
        assert r.json()["cpf"] == "12345678901"
        assert r.json()["uf"] == "DF"

    @pytest.mark.asyncio
    async def test_operador_grava(self):
        """Quem atende preenche isto na hora de fechar."""
        _, dono = _login("d3")
        op, _ = _login("d3op", papel="operador")
        lead = await _cenario("d3", dono)
        r = client.put(f"/api/v1/contratos/leads/{lead}/dados", headers=op,
                       json={"cpf": "12345678901"})
        assert r.status_code == 200

    def test_lead_inexistente_da_404(self):
        cabecalho, _ = _login("d4")
        r = client.get("/api/v1/contratos/leads/nao-existe/dados", headers=cabecalho)
        assert r.status_code == 404


# ------------------------------------------------------------------ gerar

class TestGerar:
    @pytest.mark.asyncio
    async def test_gera_com_tudo_preenchido(self):
        cabecalho, dono = _login("g1")
        lead = await _cenario("g1", dono)
        _criar_modelo(cabecalho)
        client.put(f"/api/v1/contratos/leads/{lead}/dados", headers=cabecalho,
                   json={"cpf": "12345678901", "cidade": "Taguatinga", "uf": "DF"})

        r = client.post(f"/api/v1/contratos/leads/{lead}", headers=cabecalho, json={})
        assert r.status_code == 201
        corpo = r.json()["corpo"]
        assert "Tássio Sales" in corpo
        assert "123.456.789-01" in corpo
        assert "Taguatinga/DF" in corpo
        assert "trabalhista contra Silva & Filhos" in corpo
        assert "Escritório X — OAB DF 12345" in corpo
        assert "Brasília," in corpo
        assert "{{" not in corpo

    @pytest.mark.asyncio
    async def test_dado_que_falta_vira_lacuna_visivel(self):
        """
        Contrato com linha para preencher se vê. Contrato com o campo apagado
        é o que alguém assina sem reparar.
        """
        cabecalho, dono = _login("g2")
        lead = await _cenario("g2", dono)
        _criar_modelo(cabecalho)

        r = client.post(f"/api/v1/contratos/leads/{lead}", headers=cabecalho, json={})
        assert contrato_service.LACUNA in r.json()["corpo"]

    @pytest.mark.asyncio
    async def test_texto_congela_quando_o_modelo_muda(self):
        """
        O motivo de `corpo` existir. Corrigir uma cláusula em março não pode
        mudar o que o cliente assinou em janeiro.
        """
        cabecalho, dono = _login("g3")
        lead = await _cenario("g3", dono)
        modelo = _criar_modelo(cabecalho).json()
        gerado = client.post(f"/api/v1/contratos/leads/{lead}",
                             headers=cabecalho, json={}).json()

        client.put(f"/api/v1/contratos/modelos/{modelo['id']}", headers=cabecalho,
                   json={"nome": "Padrão", "corpo": "# OUTRO TEXTO\n", "ativo": True})

        de_volta = client.get(f"/api/v1/contratos/leads/{lead}",
                              headers=cabecalho).json()[0]
        assert de_volta["corpo"] == gerado["corpo"]
        assert "OUTRO TEXTO" not in de_volta["corpo"]

    @pytest.mark.asyncio
    async def test_modelo_apagado_nao_apaga_o_contrato(self):
        """A FK é `SET NULL`. Documento emitido não desaparece."""
        cabecalho, dono = _login("g4")
        lead = await _cenario("g4", dono)
        modelo = _criar_modelo(cabecalho).json()
        client.post(f"/api/v1/contratos/leads/{lead}", headers=cabecalho, json={})

        assert client.delete(f"/api/v1/contratos/modelos/{modelo['id']}",
                             headers=cabecalho).status_code == 204

        lista = client.get(f"/api/v1/contratos/leads/{lead}", headers=cabecalho).json()
        assert len(lista) == 1
        assert lista[0]["modelo_id"] is None
        assert "Tássio Sales" in lista[0]["corpo"]

    @pytest.mark.asyncio
    async def test_sem_modelo_ativo_da_404(self):
        cabecalho, dono = _login("g5")
        lead = await _cenario("g5", dono)
        _criar_modelo(cabecalho, ativo=False)
        r = client.post(f"/api/v1/contratos/leads/{lead}", headers=cabecalho, json={})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_operador_gera(self):
        """
        Quem fecha o atendimento emite o contrato; quem **escreve** o texto é
        o admin. São permissões diferentes de propósito.
        """
        admin, dono = _login("g6")
        lead = await _cenario("g6", dono)
        _criar_modelo(admin)
        op, _ = _login("g6op", papel="operador")

        r = client.post(f"/api/v1/contratos/leads/{lead}", headers=op, json={})
        assert r.status_code == 201
        assert "Tássio Sales" in r.json()["corpo"]

    @pytest.mark.asyncio
    async def test_json_quebrado_nao_derruba_a_geracao(self):
        """Perde empresa e cargo, não o contrato."""
        cabecalho, dono = _login("g7")
        lead = await _cenario("g7", dono)
        async with AsyncSessionLocal() as db:
            from sqlalchemy import update as sa_update
            await db.execute(
                sa_update(LeadDetails)
                .where(LeadDetails.lead_id == lead)
                .values(dados_json="{isso não é json")
            )
            await db.commit()
        _criar_modelo(cabecalho)

        r = client.post(f"/api/v1/contratos/leads/{lead}", headers=cabecalho, json={})
        assert r.status_code == 201
        assert "Tássio Sales" in r.json()["corpo"]

    def test_anonimo_nao_gera(self):
        assert client.post("/api/v1/contratos/leads/x", json={}).status_code == 401


class TestPdfBaixado:
    @pytest.mark.asyncio
    async def test_baixa_o_pdf(self):
        cabecalho, dono = _login("p1")
        lead = await _cenario("p1", dono)
        _criar_modelo(cabecalho)
        contrato = client.post(f"/api/v1/contratos/leads/{lead}",
                               headers=cabecalho, json={}).json()

        r = client.get(f"/api/v1/contratos/{contrato['id']}/pdf", headers=cabecalho)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF-")

    def test_contrato_inexistente_da_404(self):
        cabecalho, _ = _login("p2")
        assert client.get("/api/v1/contratos/nao-existe/pdf",
                          headers=cabecalho).status_code == 404

    def test_anonimo_nao_baixa(self):
        assert client.get("/api/v1/contratos/x/pdf").status_code == 401
