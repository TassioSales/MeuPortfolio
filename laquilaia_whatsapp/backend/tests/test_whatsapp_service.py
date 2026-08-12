"""
Testes do envio pela Evolution API.

Não havia nenhum, e foi por isso que o formato errado sobreviveu até um
WhatsApp de verdade ser pareado: o corpo saía com o nome de campo da v1 e a
Evolution devolvia 400 — depois de a chamada ao LLM já ter sido paga e a
conversa gravada.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.whatsapp_service import whatsapp_service
from app.utils.exceptions import ValidationException


def _cliente_falso(status_code=201, json_body=None):
    """AsyncClient falso que captura o que foi enviado."""
    capturado = {}

    async def post(url, json=None, headers=None):
        capturado["url"] = url
        capturado["json"] = json
        capturado["headers"] = headers
        resposta = MagicMock()
        resposta.status_code = status_code
        resposta.json.return_value = json_body or {"messageId": "MSG-1"}
        resposta.text = str(json_body)
        return resposta

    cliente = MagicMock()
    cliente.post = post
    contexto = MagicMock()
    contexto.__aenter__ = AsyncMock(return_value=cliente)
    contexto.__aexit__ = AsyncMock(return_value=False)
    return contexto, capturado


class TestFormatoDoEnvio:
    async def test_texto_vai_no_campo_text(self):
        """
        `text`, não `textMessage`.

        A Evolution v2 respondeu literalmente
        `instance requires property "text"` — o nome antigo é da v1.
        """
        contexto, capturado = _cliente_falso()
        with patch("httpx.AsyncClient", return_value=contexto):
            await whatsapp_service.send_message("556196298484", "Olá!")

        assert capturado["json"]["text"] == "Olá!"
        assert "textMessage" not in capturado["json"]

    async def test_ddi_e_preservado(self):
        """
        O número vai como a Evolution o entrega.

        O `remoteJid` do webhook chega como `556196298484@s.whatsapp.net`, e é
        esse o identificador do contato: responder para `6196298484` é
        responder para outra pessoa. O código arrancava o `55`.
        """
        contexto, capturado = _cliente_falso()
        with patch("httpx.AsyncClient", return_value=contexto):
            await whatsapp_service.send_message("556196298484", "Oi")

        assert capturado["json"]["number"] == "556196298484"

    async def test_numero_de_ddd_55_nao_e_mutilado(self):
        """DDD 55 é Santa Maria/RS — a regra antiga comia os dois dígitos."""
        contexto, capturado = _cliente_falso()
        with patch("httpx.AsyncClient", return_value=contexto):
            await whatsapp_service.send_message("5599998888", "Oi")

        assert capturado["json"]["number"] == "5599998888"

    async def test_mais_e_espacos_saem(self):
        contexto, capturado = _cliente_falso()
        with patch("httpx.AsyncClient", return_value=contexto):
            await whatsapp_service.send_message("+55 61 96298484", "Oi")

        assert capturado["json"]["number"] == "556196298484"

    async def test_erro_da_api_vira_excecao(self):
        contexto, _ = _cliente_falso(status_code=400, json_body={"error": "Bad Request"})
        with patch("httpx.AsyncClient", return_value=contexto):
            with pytest.raises(ValidationException) as exc:
                await whatsapp_service.send_message("556196298484", "Oi")
        assert "400" in str(exc.value)
