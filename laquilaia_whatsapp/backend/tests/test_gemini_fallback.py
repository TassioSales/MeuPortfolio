"""
Testes do provedor de reserva (Gemini).

O corpo da requisição é conferido de verdade, com `httpx.MockTransport`, e não
pelos kwargs de um mock: o que quebra numa integração REST é o formato do JSON
que sai, e um mock só provaria que o código chama o que o próprio teste espera.
"""

import httpx
import pytest
from unittest.mock import MagicMock, patch

from anthropic import APIConnectionError, APIError, RateLimitError

from app.config import settings
from app.db.models import Agent
from app.services.gemini_client import (
    FOLGA_DE_RACIOCINIO,
    GeminiClient,
    GeminiIndisponivel,
)
from app.services.llm_service import LLMService
from app.utils.exceptions import ValidationException


RESPOSTA_OK = {
    "candidates": [
        {
            "content": {"parts": [{"text": "Olá! Como posso ajudar?"}], "role": "model"},
            "finishReason": "STOP",
        }
    ],
    "usageMetadata": {
        "promptTokenCount": 12,
        "candidatesTokenCount": 7,
        "totalTokenCount": 19,
    },
}


def _agente(temperatura=0.5, max_tokens=256):
    agent = MagicMock(spec=Agent)
    agent.id = "agent-1"
    agent.user_id = "user-1"
    agent.system_prompt = "Você é um atendente."
    agent.temperatura = temperatura
    agent.max_tokens = max_tokens
    return agent


def _captura(resposta=None, status=200):
    """MockTransport que guarda o corpo enviado e devolve `resposta`."""
    registrado = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        registrado["url"] = str(request.url)
        registrado["headers"] = dict(request.headers)
        registrado["body"] = json.loads(request.content)
        return httpx.Response(status, json=resposta if resposta is not None else {})

    return httpx.MockTransport(handler), registrado


class TestFormatoDaRequisicao:
    """O JSON que sai tem que ser o do Gemini, não o do Claude."""

    async def test_historico_usa_papel_model_e_parts(self):
        transporte, registrado = _captura(RESPOSTA_OK)
        cliente = GeminiClient(api_key="k", model="gemini-flash-latest", transport=transporte)

        await cliente.generate(
            system_prompt="prompt do sistema",
            user_message="Oi",
            conversation_history=[
                {"role": "user", "content": "Primeira"},
                {"role": "assistant", "content": "Resposta"},
            ],
        )

        contents = registrado["body"]["contents"]
        assert [c["role"] for c in contents] == ["user", "model", "user"]
        # `parts`, não `content` — mandar no formato do Claude não dá erro,
        # o Gemini só ignora o turno e responde sem contexto.
        assert contents[1]["parts"][0]["text"] == "Resposta"
        assert contents[-1]["parts"][0]["text"] == "Oi"

    async def test_system_prompt_vai_em_systemInstruction(self):
        transporte, registrado = _captura(RESPOSTA_OK)
        cliente = GeminiClient(api_key="k", transport=transporte)

        await cliente.generate(system_prompt="seja formal", user_message="Oi")

        assert registrado["body"]["systemInstruction"] == {
            "parts": [{"text": "seja formal"}]
        }

    async def test_temperatura_e_max_tokens_vao_em_generationConfig(self):
        transporte, registrado = _captura(RESPOSTA_OK)
        cliente = GeminiClient(api_key="k", transport=transporte)

        await cliente.generate(
            system_prompt=None, user_message="Oi", max_tokens=512, temperature=0.9
        )

        config = registrado["body"]["generationConfig"]
        # O orçamento é compartilhado com o raciocínio, então vai com folga —
        # ver FOLGA_DE_RACIOCINIO.
        assert config["maxOutputTokens"] == 512 + FOLGA_DE_RACIOCINIO
        # Diferente do Claude novo, aqui a temperatura vale.
        assert config["temperature"] == 0.9

    async def test_chave_vai_no_header_e_modelo_na_url(self):
        transporte, registrado = _captura(RESPOSTA_OK)
        cliente = GeminiClient(api_key="segredo", model="gemini-3-pro", transport=transporte)

        await cliente.generate(system_prompt=None, user_message="Oi")

        assert registrado["headers"]["x-goog-api-key"] == "segredo"
        assert registrado["url"].endswith("/models/gemini-3-pro:generateContent")


class TestLeituraDaResposta:
    async def test_extrai_texto_e_tokens(self):
        transporte, _ = _captura(RESPOSTA_OK)
        cliente = GeminiClient(api_key="k", transport=transporte)

        texto, uso = await cliente.generate(system_prompt=None, user_message="Oi")

        assert texto == "Olá! Como posso ajudar?"
        assert uso == {"input_tokens": 12, "output_tokens": 7, "total_tokens": 19}

    async def test_resposta_cortada_pelo_filtro_vira_erro(self):
        # Candidato sem `parts` é o que volta quando a segurança corta.
        transporte, _ = _captura(
            {"candidates": [{"finishReason": "SAFETY", "content": {}}]}
        )
        cliente = GeminiClient(api_key="k", transport=transporte)

        with pytest.raises(GeminiIndisponivel) as exc:
            await cliente.generate(system_prompt=None, user_message="Oi")
        assert "SAFETY" in str(exc.value)

    async def test_erro_http_carrega_o_corpo(self):
        transporte, _ = _captura({"error": {"message": "API key not valid"}}, status=400)
        cliente = GeminiClient(api_key="k", transport=transporte)

        with pytest.raises(GeminiIndisponivel) as exc:
            await cliente.generate(system_prompt=None, user_message="Oi")
        assert "400" in str(exc.value)
        assert "API key not valid" in str(exc.value)

    async def test_raciocinio_entra_na_conta_de_tokens(self):
        """
        Os números são de uma resposta real do gemini-3.6-flash.

        `candidatesTokenCount` conta só o texto; o raciocínio vem à parte e é
        cobrado. Ignorá-lo faria o limitador contar 5 tokens onde a API cobrou
        174, e o painel mostraria três números que não somam.
        """
        transporte, _ = _captura(
            {
                "candidates": [
                    {
                        "content": {"parts": [{"text": "A integração funcionou."}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 23,
                    "candidatesTokenCount": 5,
                    "thoughtsTokenCount": 146,
                    "totalTokenCount": 174,
                },
            }
        )
        cliente = GeminiClient(api_key="k", transport=transporte)

        _, uso = await cliente.generate(system_prompt=None, user_message="Oi")

        assert uso["input_tokens"] + uso["output_tokens"] == uso["total_tokens"]
        assert uso["total_tokens"] == 174

    async def test_orcamento_consumido_pelo_raciocinio_diz_o_que_fazer(self):
        """Candidato sem texto e com MAX_TOKENS: o raciocínio comeu tudo."""
        transporte, _ = _captura(
            {
                "candidates": [{"finishReason": "MAX_TOKENS", "content": {}}],
                "usageMetadata": {
                    "promptTokenCount": 23,
                    "candidatesTokenCount": 0,
                    "thoughtsTokenCount": 44,
                    "totalTokenCount": 67,
                },
            }
        )
        cliente = GeminiClient(api_key="k", transport=transporte)

        with pytest.raises(GeminiIndisponivel) as exc:
            await cliente.generate(system_prompt=None, user_message="Oi")
        assert "raciocínio" in str(exc.value)
        assert "max_tokens" in str(exc.value)

    async def test_texto_truncado_ainda_e_devolvido(self):
        """
        Meia resposta é melhor que nenhuma — mas com aviso.

        Este corpo é o da primeira chamada real que fizemos: a frase saiu
        cortada em "A integração funcion".
        """
        transporte, _ = _captura(
            {
                "candidates": [
                    {
                        "content": {"parts": [{"text": "A integração funcion"}]},
                        "finishReason": "MAX_TOKENS",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 23,
                    "candidatesTokenCount": 3,
                    "thoughtsTokenCount": 93,
                    "totalTokenCount": 119,
                },
            }
        )
        cliente = GeminiClient(api_key="k", transport=transporte)

        texto, uso = await cliente.generate(system_prompt=None, user_message="Oi")

        assert texto == "A integração funcion"
        assert uso["total_tokens"] == 119

    async def test_parte_so_com_assinatura_nao_quebra(self):
        """A série 3 manda `thoughtSignature` junto; parte sem `text` é normal."""
        transporte, _ = _captura(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"thoughtSignature": "EtYDCtMD..."},
                                {"text": "Resposta."},
                            ]
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 2},
            }
        )
        cliente = GeminiClient(api_key="k", transport=transporte)

        texto, _ = await cliente.generate(system_prompt=None, user_message="Oi")
        assert texto == "Resposta."

    async def test_sem_chave_nao_faz_requisicao(self):
        cliente = GeminiClient(api_key="")

        assert cliente.configured is False
        with pytest.raises(GeminiIndisponivel):
            await cliente.generate(system_prompt=None, user_message="Oi")


class TestEscolhaDoProvedor:
    """Quando o Claude cede a vez, e quando não cede."""

    def _servico(self, gemini_key, transporte=None):
        servico = LLMService()
        servico.rate_limiter.max_calls_per_minute = 1000
        servico.rate_limiter.max_tokens_per_minute = 10**6
        servico.gemini = GeminiClient(
            api_key=gemini_key, model="gemini-flash-latest", transport=transporte
        )
        return servico

    @staticmethod
    def _com_chave_anthropic():
        """
        Finge que a ANTHROPIC_API_KEY existe.

        Sem ela — e havendo reserva — o serviço pula o Claude de propósito,
        então os testes que exercitam a queda precisam de uma chave para que
        exista um Claude a cair.
        """
        return patch.object(settings, "anthropic_api_key", "sk-ant-teste")

    async def test_claude_falhando_cai_para_o_gemini(self):
        transporte, _ = _captura(RESPOSTA_OK)
        servico = self._servico("k", transporte)

        cliente_claude = MagicMock()
        cliente_claude.messages.create.side_effect = APIConnectionError(
            message="sem rede",
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
        )
        servico.client = cliente_claude

        with self._com_chave_anthropic():
            texto, uso = await servico.generate_response(_agente(), "Oi")

        assert texto == "Olá! Como posso ajudar?"
        # Quem responde precisa aparecer no uso: o painel mostra esse valor.
        assert uso["model"] == "gemini-flash-latest"
        cliente_claude.messages.create.assert_called_once()

    async def test_rate_limit_do_claude_tambem_cai_para_o_gemini(self):
        transporte, _ = _captura(RESPOSTA_OK)
        servico = self._servico("k", transporte)

        cliente_claude = MagicMock()
        cliente_claude.messages.create.side_effect = RateLimitError(
            message="limite",
            response=httpx.Response(
                429, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            ),
            body={},
        )
        servico.client = cliente_claude

        with self._com_chave_anthropic():
            texto, _ = await servico.generate_response(_agente(), "Oi")
        assert texto == "Olá! Como posso ajudar?"

    async def test_sem_reserva_o_erro_original_sobe(self):
        """Sem GEMINI_API_KEY o comportamento antigo tem que ficar intacto."""
        servico = self._servico("")

        cliente_claude = MagicMock()
        cliente_claude.messages.create.side_effect = APIConnectionError(
            message="sem rede",
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
        )
        servico.client = cliente_claude

        with self._com_chave_anthropic(), pytest.raises(ValidationException) as exc:
            await servico.generate_response(_agente(), "Oi")
        assert "Connection error" in str(exc.value)

    async def test_reserva_falhando_relanca_o_erro_do_claude(self):
        """
        O erro que sobe é o do provedor principal, não o da reserva.

        Ver "GEMINI_API_KEY inválida" quando o problema é um 529 da Anthropic
        manda investigar o lado errado.
        """
        transporte, _ = _captura({"error": {"message": "quota"}}, status=429)
        servico = self._servico("k", transporte)

        cliente_claude = MagicMock()
        cliente_claude.messages.create.side_effect = APIError(
            "anthropic caiu",
            httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
            body={},
        )
        servico.client = cliente_claude

        with self._com_chave_anthropic(), pytest.raises(ValidationException) as exc:
            await servico.generate_response(_agente(), "Oi")
        assert "anthropic caiu" in str(exc.value)

    async def test_claude_ok_nao_chama_a_reserva(self):
        def explode(request):
            raise AssertionError("a reserva não devia ter sido chamada")

        servico = self._servico("k", httpx.MockTransport(explode))

        mensagem = MagicMock()
        mensagem.content = [MagicMock(text="resposta do claude")]
        mensagem.usage = MagicMock(input_tokens=3, output_tokens=4)
        cliente_claude = MagicMock()
        cliente_claude.messages.create.return_value = mensagem
        servico.client = cliente_claude

        with self._com_chave_anthropic():
            texto, uso = await servico.generate_response(_agente(), "Oi")

        assert texto == "resposta do claude"
        assert uso["model"] == servico.model
        assert uso["total_tokens"] == 7

    async def test_sem_chave_da_anthropic_vai_direto_ao_gemini(self):
        """
        A situação de hoje: só o Gemini configurado.

        Chamar o Claude sem chave seria um 401 garantido por mensagem — o
        serviço pula, e o mock do Claude prova que ele nem foi tocado.
        """
        transporte, _ = _captura(RESPOSTA_OK)
        servico = self._servico("k", transporte)

        cliente_claude = MagicMock()
        servico.client = cliente_claude

        with patch.object(settings, "anthropic_api_key", ""):
            texto, uso = await servico.generate_response(_agente(), "Oi")

        assert texto == "Olá! Como posso ajudar?"
        assert uso["model"] == "gemini-flash-latest"
        cliente_claude.messages.create.assert_not_called()

    async def test_sem_nenhum_provedor_a_mensagem_diz_o_que_falta(self):
        servico = self._servico("")
        servico.client = MagicMock()

        with patch.object(settings, "anthropic_api_key", ""), patch.object(
            servico, "_tentar_claude_primeiro", return_value=False
        ), pytest.raises(ValidationException) as exc:
            await servico.generate_response(_agente(), "Oi")

        assert "ANTHROPIC_API_KEY" in str(exc.value)
        assert "GEMINI_API_KEY" in str(exc.value)
