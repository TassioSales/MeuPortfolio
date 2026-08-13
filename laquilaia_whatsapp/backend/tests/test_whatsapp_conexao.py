"""
Estado da conexão e QR, vindos da Evolution.

O transporte é mockado com `httpx.MockTransport` — é o que dá para conferir
sem uma Evolution no ar, e é onde os erros de formato aparecem. O que **não**
está coberto aqui é a Evolution de verdade: há um histórico de versões
devolvendo `{"count": 0}` sem QR (issues #2380 e #2385), e isso só se descobre
sondando a instância. Ver `scripts/sondar_evolution.py`.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.whatsapp_service import WhatsAppService, _com_prefixo_de_imagem
from tests.conftest import criar_acesso

client = TestClient(app)


def _servico(resposta: httpx.Response) -> WhatsAppService:
    """Um serviço cujo httpx devolve sempre a resposta dada."""
    servico = WhatsAppService()
    servico.api_url = "http://evolution:8080"
    servico.api_key = "chave"
    servico.instance_name = "laquilaia"

    transporte = httpx.MockTransport(lambda _: resposta)
    original = httpx.AsyncClient

    class ClienteFixo(original):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transporte
            super().__init__(*args, **kwargs)

    httpx.AsyncClient = ClienteFixo
    servico._restaurar = lambda: setattr(httpx, "AsyncClient", original)
    return servico


class TestEstadoDaConexao:
    async def test_open_vira_conectado(self):
        """
        O painel não fala "open".

        Traduzir aqui também protege o front do dia em que a Evolution mudar o
        vocabulário: muda um dicionário, não uma tela.
        """
        servico = _servico(httpx.Response(200, json={"instance": {"state": "open"}}))
        try:
            assert (await servico.estado_da_conexao())["estado"] == "conectado"
        finally:
            servico._restaurar()

    async def test_close_vira_desconectado(self):
        servico = _servico(httpx.Response(200, json={"instance": {"state": "close"}}))
        try:
            assert (await servico.estado_da_conexao())["estado"] == "desconectado"
        finally:
            servico._restaurar()

    async def test_estado_desconhecido_nao_vira_desconectado(self):
        """
        Palavra nova da Evolution não pode virar "desconectado" em silêncio:
        seria o painel mandando reconectar um número que está no ar.
        """
        servico = _servico(httpx.Response(200, json={"instance": {"state": "banana"}}))
        try:
            resultado = await servico.estado_da_conexao()
        finally:
            servico._restaurar()

        assert resultado["estado"] == "desconhecido"
        assert "banana" in resultado["detalhe"]

    async def test_evolution_fora_do_ar_nao_levanta(self):
        """
        A tela de conexão precisa dizer alguma coisa quando a Evolution some —
        e "a Evolution está fora" é diagnóstico diferente de "o número caiu".
        """
        servico = _servico(httpx.Response(502, text="bad gateway"))
        try:
            resultado = await servico.estado_da_conexao()
        finally:
            servico._restaurar()

        assert resultado["estado"] == "indisponivel"
        assert "502" in resultado["detalhe"]


class TestQrCode:
    async def test_base64_na_raiz(self):
        servico = _servico(httpx.Response(200, json={"base64": "iVBORw0KGgo="}))
        try:
            resultado = await servico.qrcode()
        finally:
            servico._restaurar()

        assert resultado["qrcode"] == "data:image/png;base64,iVBORw0KGgo="

    async def test_base64_dentro_de_qrcode(self):
        """A Evolution já devolveu das duas formas. Aceitar as duas é uma linha."""
        servico = _servico(
            httpx.Response(200, json={"qrcode": {"base64": "iVBORw0KGgo="}})
        )
        try:
            resultado = await servico.qrcode()
        finally:
            servico._restaurar()

        assert resultado["qrcode"].endswith("iVBORw0KGgo=")

    async def test_resposta_sem_qr_e_dita_com_todas_as_letras(self):
        """
        `{"count": 0}` é a resposta que as issues #2380 e #2385 relatam: sem
        QR, sem código e sem erro. A tela precisa distinguir isso de "já está
        conectado" e de "falhou" — são três telas diferentes.
        """
        servico = _servico(httpx.Response(200, json={"count": 0}))
        try:
            resultado = await servico.qrcode()
        finally:
            servico._restaurar()

        assert resultado["qrcode"] is None
        assert resultado["codigo"] is None
        assert "sem QR" in resultado["detalhe"]

    async def test_codigo_de_pareamento_tambem_serve(self):
        """Quem não consegue ler o QR pode digitar o código no aparelho."""
        servico = _servico(httpx.Response(200, json={"pairingCode": "ABCD-1234"}))
        try:
            resultado = await servico.qrcode()
        finally:
            servico._restaurar()

        assert resultado["codigo"] == "ABCD-1234"
        assert resultado["detalhe"] is None


class TestPrefixoDaImagem:
    def test_poe_o_prefixo_que_a_tag_img_exige(self):
        # Sem ele a imagem não aparece, e não há erro nenhum no console.
        assert _com_prefixo_de_imagem("abc").startswith("data:image/png;base64,")

    def test_nao_duplica_prefixo_existente(self):
        pronto = "data:image/png;base64,abc"
        assert _com_prefixo_de_imagem(pronto) == pronto

    def test_vazio_continua_vazio(self):
        assert _com_prefixo_de_imagem(None) is None
        assert _com_prefixo_de_imagem("") is None


class TestAcesso:
    """Conectar o número é configuração: só o administrador."""

    def _headers(self, email: str, papel: str) -> dict:
        criar_acesso(client, email, "SenhaSegura123!", "Fulano", papel=papel)
        r = client.post(
            "/api/v1/auth/login", json={"email": email, "senha": "SenhaSegura123!"}
        )
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_operador_nao_ve_o_qr(self):
        """
        404 e não 403: o QR pareia o número do escritório inteiro. Dizer
        "existe, mas não é para você" já entrega que a tela existe.
        """
        admin = self._headers("wa-admin@example.com", "admin")
        operador = self._headers("wa-operador@example.com", "operador")

        assert client.get("/api/v1/whatsapp/qrcode", headers=operador).status_code == 404
        assert client.get("/api/v1/whatsapp/status", headers=operador).status_code == 404
        # E o admin passa — senão o teste acima passaria com a rota quebrada.
        assert client.get("/api/v1/whatsapp/status", headers=admin).status_code == 200

    def test_sem_token_nao_passa(self):
        assert client.get("/api/v1/whatsapp/qrcode").status_code in (401, 403)
