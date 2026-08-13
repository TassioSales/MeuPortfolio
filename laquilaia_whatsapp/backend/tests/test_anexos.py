"""
Anexos: imagem, PDF e áudio que o cliente manda.

A foto da carta de demissão e o PDF do contrato são o que a triagem mais
precisa ver — e eram descartados no webhook, antes de qualquer decisão.

O que estes casos travam: quem decide se o anexo é lido (o agente, não o
webhook), o que acontece quando ele não pode ser lido, e o roteamento de áudio
— que só um dos dois provedores sabe ouvir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.webhook_models import DataModel
from app.services.llm_service import _bloco_de_anexo_claude, claude_le
from app.services.message_orchestrator import MessageOrchestrator


def _agente(anexos: bool):
    a = MagicMock()
    a.id = "ag-1"
    a.anexos_habilitados = anexos
    return a


IMAGEM = {"base64": "iVBORw0KGgo=", "mimetype": "image/jpeg", "nome": "foto.jpg", "tamanho": 1}
PDF = {"base64": "JVBERi0=", "mimetype": "application/pdf", "nome": "contrato.pdf", "tamanho": 2}
AUDIO = {"base64": "T2dnUw==", "mimetype": "audio/ogg", "nome": None, "tamanho": 3}


class TestReconhecimentoNoWebhook:
    def test_reconhece_os_tipos_que_importam_na_triagem(self):
        for tipo, esperado in [
            ("imageMessage", "imagem"),
            ("documentMessage", "documento"),
            ("documentWithCaptionMessage", "documento"),
            ("audioMessage", "audio"),
            ("pttMessage", "audio"),
        ]:
            assert DataModel(messageType=tipo).tipo_de_anexo == esperado

    def test_figurinha_nao_e_anexo(self):
        """Figurinha, localização e contato não são documento de triagem."""
        assert DataModel(messageType="stickerMessage").tipo_de_anexo is None

    def test_a_legenda_e_lida(self):
        """
        Quase sempre é onde está a pergunta: o anexo é o contrato, a legenda é
        "olha a cláusula 8, isso pode?". Ignorá-la joga fora o que a pessoa
        quer.
        """
        dados = DataModel(
            messageType="documentMessage",
            message={"caption": "olha a cláusula 8"},
        )

        assert dados.legenda == "olha a cláusula 8"


class TestDecisaoDoAgente:
    orquestrador = MessageOrchestrator()

    async def test_agente_sem_anexos_nao_baixa_e_pede_texto(self):
        """
        Ignorar em silêncio deixaria a pessoa esperando resposta sobre uma foto
        que ninguém abriu.
        """
        with patch(
            "app.services.whatsapp_service.whatsapp_service.baixar_midia",
            new_callable=AsyncMock,
        ) as baixar:
            anexo, texto = await self.orquestrador._preparar_anexo(
                _agente(anexos=False), "imagem", {"id": "M1"}, ""
            )

        baixar.assert_not_awaited()
        assert anexo is None
        assert "enviou uma imagem" in texto
        assert "por escrito" in texto

    async def test_agente_com_anexos_baixa_e_devolve_a_midia(self):
        with patch(
            "app.services.whatsapp_service.whatsapp_service.baixar_midia",
            new_callable=AsyncMock,
            return_value=PDF,
        ):
            anexo, texto = await self.orquestrador._preparar_anexo(
                _agente(anexos=True), "documento", {"id": "M1"}, "olha a cláusula 8"
            )

        assert anexo == PDF
        # A legenda continua na mensagem: é a pergunta de verdade.
        assert "olha a cláusula 8" in texto

    async def test_download_que_falha_nao_derruba_o_atendimento(self):
        """
        Perder a foto é ruim; perder o atendimento por causa da foto é pior.
        """
        with patch(
            "app.services.whatsapp_service.whatsapp_service.baixar_midia",
            new_callable=AsyncMock,
            return_value=None,
        ):
            anexo, texto = await self.orquestrador._preparar_anexo(
                _agente(anexos=True), "imagem", {"id": "M1"}, ""
            )

        assert anexo is None
        assert "enviou uma imagem" in texto

    async def test_sem_anexo_o_texto_passa_intacto(self):
        anexo, texto = await self.orquestrador._preparar_anexo(
            _agente(anexos=True), None, None, "bom dia"
        )

        assert (anexo, texto) == (None, "bom dia")

    async def test_a_mensagem_nunca_chega_vazia_ao_modelo(self):
        """
        Anexo sem legenda deixaria `user_message` vazio, e o modelo
        responderia no vácuo — sem saber sequer que houve um arquivo.
        """
        with patch(
            "app.services.whatsapp_service.whatsapp_service.baixar_midia",
            new_callable=AsyncMock,
            return_value=AUDIO,
        ):
            _, texto = await self.orquestrador._preparar_anexo(
                _agente(anexos=True), "audio", {"id": "M1"}, ""
            )

        assert texto.strip() != ""


class TestQuemLeOQue:
    def test_claude_le_imagem_e_pdf(self):
        assert claude_le("image/jpeg")
        assert claude_le("application/pdf")

    def test_claude_nao_le_audio(self):
        """
        A API da Anthropic não aceita áudio de entrada. Mandar assim mesmo é
        400 na cara de quem gravou dois minutos contando o caso.
        """
        assert not claude_le("audio/ogg")

    def test_imagem_e_pdf_usam_blocos_diferentes(self):
        """Trocar um pelo outro é 400 — são tipos distintos na mesma API."""
        assert _bloco_de_anexo_claude(IMAGEM)["type"] == "image"
        assert _bloco_de_anexo_claude(PDF)["type"] == "document"

    def test_o_bloco_leva_o_base64_e_o_mimetype(self):
        bloco = _bloco_de_anexo_claude(IMAGEM)

        assert bloco["source"]["media_type"] == "image/jpeg"
        assert bloco["source"]["data"] == IMAGEM["base64"]


class TestMontagemDaMensagem:
    def test_o_anexo_vem_antes_do_texto(self):
        """
        A legenda ("olha a cláusula 8") só faz sentido depois de o modelo ter
        visto o documento. Na ordem inversa ele lê a pergunta sem ter o que
        responder.
        """
        from app.services.llm_service import llm_service

        mensagens = llm_service._build_messages(None, "olha a cláusula 8", PDF)

        blocos = mensagens[-1]["content"]
        assert blocos[0]["type"] == "document"
        assert blocos[1]["type"] == "text"

    def test_sem_anexo_o_conteudo_continua_string(self):
        """
        O formato antigo não pode mudar: toda conversa sem anexo passa por
        aqui, e trocar string por lista de blocos sem necessidade é mexer no
        que funciona.
        """
        from app.services.llm_service import llm_service

        mensagens = llm_service._build_messages(None, "bom dia")

        assert mensagens[-1]["content"] == "bom dia"

    def test_o_gemini_recebe_inlineData_antes_do_texto(self):
        from app.services.gemini_client import GeminiClient

        contents = GeminiClient._montar_contents(None, "olha a cláusula 8", PDF)

        partes = contents[-1]["parts"]
        # `inlineData` em camelCase, e o base64 cru — sem o prefixo `data:`,
        # que aqui é erro, não enfeite.
        assert partes[0]["inlineData"]["mimeType"] == "application/pdf"
        assert partes[0]["inlineData"]["data"] == PDF["base64"]
        assert partes[1]["text"] == "olha a cláusula 8"
