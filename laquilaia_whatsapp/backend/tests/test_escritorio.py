"""
Os dados do escritório, e o que o agente faz com eles.

O agente não sabia nada sobre o escritório que representa. Perguntado "onde
vocês ficam?" ou "qual o telefone?", não tinha o que responder — e o prompt
manda não inventar, então a conversa travava numa pergunta que qualquer
recepcionista responde.

Pior era o cliente antigo: quem já tem processo no escritório e escreve no
número comercial caía numa triagem do zero, como se fosse gente nova.
"""

import pytest
from fastapi.testclient import TestClient

from app.db.database import AsyncSessionLocal
from app.db.models import Agent, ConfiguracaoEscritorio
from app.main import app
from app.services import escritorio_service
from app.services.llm_service import bloco_do_escritorio, sistema_do_agente
from tests.conftest import criar_acesso

client = TestClient(app)

ROTA = "/api/v1/escritorio"

ADMIN = {"email": "escritorio-admin@example.com", "senha": "SenhaDoDono123"}
OPERADOR = {"email": "escritorio-op@example.com", "senha": "SenhaDoOperador123"}


def _cabecalho(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def dupla(client):
    criar_acesso(client, ADMIN["email"], ADMIN["senha"], "Dono")
    criar_acesso(client, OPERADOR["email"], OPERADOR["senha"], "Atendente", papel="operador")
    admin = client.post("/api/v1/auth/login", json=ADMIN).json()["access_token"]
    operador = client.post("/api/v1/auth/login", json=OPERADOR).json()["access_token"]
    return admin, operador


class TestOFormulario:
    def test_escritorio_vazio_abre_com_tudo_nulo(self, client, dupla):
        """
        Estado inicial, não erro. Um 404 aqui faria a tela de configuração
        abrir quebrada justamente na instalação nova, que é quando ela é
        usada.
        """
        admin, _ = dupla

        resposta = client.get(ROTA, headers=_cabecalho(admin))

        assert resposta.status_code == 200
        assert resposta.json()["nome"] is None

    def test_grava_e_devolve(self, client, dupla):
        admin, _ = dupla

        resposta = client.put(
            ROTA,
            json={"nome": "Borges e Lopes", "telefone": "61 99883-7234",
                  "telefone_suporte": "61 99883-1516"},
            headers=_cabecalho(admin),
        )

        assert resposta.status_code == 200
        assert resposta.json()["nome"] == "Borges e Lopes"
        assert client.get(ROTA, headers=_cabecalho(admin)).json()["telefone_suporte"] == "61 99883-1516"

    def test_campo_apagado_fica_nulo_e_nao_string_vazia(self, client, dupla):
        """
        `""` no banco é lixo: some do prompt (que ignora o que é falsy) mas
        aparece em relatório e exportação como se fosse valor.
        """
        admin, _ = dupla
        client.put(ROTA, json={"telefone": "61 3333-3333"}, headers=_cabecalho(admin))

        client.put(ROTA, json={"telefone": "   "}, headers=_cabecalho(admin))

        assert client.get(ROTA, headers=_cabecalho(admin)).json()["telefone"] is None

    def test_salvar_de_novo_nao_cria_segunda_linha(self, client, dupla):
        """Uma instalação, um escritório. Duas linhas seriam dois telefones."""
        admin, _ = dupla
        client.put(ROTA, json={"nome": "Primeiro"}, headers=_cabecalho(admin))
        client.put(ROTA, json={"nome": "Segundo"}, headers=_cabecalho(admin))

        assert client.get(ROTA, headers=_cabecalho(admin)).json()["nome"] == "Segundo"


class TestQuemPodeMexer:
    def test_operador_le(self, client, dupla):
        """
        Ele precisa do telefone do suporte para repassar quando for ele
        atendendo.
        """
        admin, operador = dupla
        client.put(ROTA, json={"telefone_suporte": "61 99883-1516"},
                   headers=_cabecalho(admin))

        resposta = client.get(ROTA, headers=_cabecalho(operador))

        assert resposta.status_code == 200
        assert resposta.json()["telefone_suporte"] == "61 99883-1516"

    def test_operador_nao_grava(self, client, dupla):
        """
        Mudar o telefone do escritório muda o que a IA diz a **todo** cliente.
        Não é decisão de quem está no plantão.
        """
        admin, operador = dupla
        client.put(ROTA, json={"nome": "Borges e Lopes"}, headers=_cabecalho(admin))

        resposta = client.put(ROTA, json={"nome": "Outro nome"},
                              headers=_cabecalho(operador))

        assert resposta.status_code == 404
        assert client.get(ROTA, headers=_cabecalho(admin)).json()["nome"] == "Borges e Lopes"

    def test_sem_token_e_401(self, client):
        assert client.get(ROTA).status_code == 401


class TestOBlocoQueVaiParaOModelo:
    def test_so_entram_os_campos_preenchidos(self):
        """
        "Telefone: não informado" é pior que a ausência — o modelo lê como
        fato e chega a dizer ao cliente que o escritório não tem telefone.
        """
        config = ConfiguracaoEscritorio(id="unica", nome="Borges e Lopes")

        bloco = bloco_do_escritorio(config)

        assert "Borges e Lopes" in bloco
        assert "Telefone" not in bloco
        assert "Endereço" not in bloco

    def test_sem_configuracao_nenhuma_o_bloco_some(self):
        assert bloco_do_escritorio(None) == ""
        assert bloco_do_escritorio(ConfiguracaoEscritorio(id="unica")) == ""

    def test_o_telefone_do_suporte_vem_com_a_instrucao(self):
        """
        O número sozinho não resolve: o modelo precisa saber **para quem** ele
        é, senão passa o suporte para quem está chegando agora.
        """
        config = ConfiguracaoEscritorio(id="unica", telefone_suporte="61 99883-1516")

        bloco = bloco_do_escritorio(config)

        assert "61 99883-1516" in bloco
        assert "já é cliente" in bloco

    def test_o_bloco_e_anexado_ao_prompt_sem_apagar_nada(self):
        """
        O prompt é do dono do agente e ele pode reescrevê-lo inteiro. Os dados
        entram no fim justamente para sobreviver a isso.
        """
        agente = Agent(
            id="ag", user_id="u", nome="Triagem",
            system_prompt="Você é a triagem.", nome_atendente="Fernanda",
            temperatura=0.4, max_tokens=1024, status="ativo",
        )
        config = ConfiguracaoEscritorio(id="unica", nome="Borges e Lopes")

        montado = sistema_do_agente(agente, config)

        assert montado.startswith("Você é a triagem.")
        assert "Fernanda" in montado
        assert "Borges e Lopes" in montado

    def test_sem_config_o_prompt_e_o_de_antes(self):
        """A tela nova não pode mudar o comportamento de quem não a usou."""
        agente = Agent(
            id="ag", user_id="u", nome="Triagem", system_prompt="Você é a triagem.",
            temperatura=0.4, max_tokens=1024, status="ativo",
        )

        assert sistema_do_agente(agente, None) == "Você é a triagem."


class TestLeituraParaOPrompt:
    @pytest.mark.asyncio
    async def test_le_o_que_foi_gravado(self):
        async with AsyncSessionLocal() as db:
            config = await escritorio_service.obter_ou_criar(db)
            config.nome = "Borges e Lopes"
            await db.commit()

        lido = await escritorio_service.para_o_prompt()

        assert lido is not None and lido.nome == "Borges e Lopes"

    @pytest.mark.asyncio
    async def test_sem_linha_devolve_none_em_vez_de_estourar(self):
        assert await escritorio_service.para_o_prompt() is None
