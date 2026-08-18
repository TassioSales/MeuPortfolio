"""Tests for LLM service."""

import time

import httpx
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from app.config import settings
from app.services.llm_service import llm_service, LLMService
from app.services.rate_limiter import MemoryRateLimitBackend, RateLimiter
from app.db.models import Agent
from app.utils.exceptions import ValidationException


class _SemRedis:
    """Backend que falha sempre, para o limitador contar em memória."""

    async def add(self, *args):
        raise ConnectionError("sem Redis")

    async def counts(self, *args):
        raise ConnectionError("sem Redis")


class TestTokenCounting:
    """Test token counting functionality."""

    def test_count_tokens_short_text(self):
        """Test counting tokens in short text."""
        text = "Hello"
        tokens = llm_service.count_tokens(text)
        assert tokens >= 1
        assert isinstance(tokens, int)

    def test_count_tokens_long_text(self):
        """Test counting tokens in long text."""
        text = "This is a much longer text " * 100
        tokens = llm_service.count_tokens(text)
        assert tokens > 100
        assert isinstance(tokens, int)

    def test_count_tokens_empty_string(self):
        """Test counting tokens in empty string."""
        tokens = llm_service.count_tokens("")
        assert tokens >= 1  # Minimum of 1 token

    def test_count_tokens_special_characters(self):
        """Test counting tokens with special characters."""
        text = "Hello! @#$%^&*() 你好 🎉"
        tokens = llm_service.count_tokens(text)
        assert tokens >= 1
        assert isinstance(tokens, int)


class TestRateLimiting:
    """Test rate limiting functionality."""

    def setup_method(self):
        """
        Reset LLM service before each test.

        O limitador é trocado por um só de memória: estes casos verificam a
        contagem, não a ida ao Redis (que tem cobertura própria em
        `test_rate_limit_por_conta.py`), e assim não dependem do serviço estar
        no ar nem sujam o banco de teste.
        """
        self.service = LLMService()
        self.service.rate_limiter = RateLimiter(
            max_calls_per_minute=60,
            max_tokens_per_minute=40000,
            redis_backend=_SemRedis(),
        )

    async def test_rate_limit_initial_status(self):
        """Test initial rate limit status."""
        status = await self.service.get_rate_limit_status()
        assert status["calls_used"] == 0
        assert status["tokens_used"] == 0
        assert status["calls_remaining"] == self.service.max_calls_per_minute
        assert status["tokens_remaining"] == self.service.max_tokens_per_minute

    async def test_rate_limit_after_usage(self):
        """Test rate limit status after tracking usage."""
        await self.service._track_usage(100)
        status = await self.service.get_rate_limit_status()
        assert status["calls_used"] == 1
        assert status["tokens_used"] == 100
        assert status["calls_remaining"] == self.service.max_calls_per_minute - 1
        assert status["tokens_remaining"] == self.service.max_tokens_per_minute - 100

    async def test_rate_limit_multiple_calls(self):
        """Test rate limit with multiple calls."""
        for _ in range(5):
            await self.service._track_usage(500)
        status = await self.service.get_rate_limit_status()
        assert status["calls_used"] == 5
        assert status["tokens_used"] == 2500

    async def test_rate_limit_exceeded_calls(self):
        """Test that rate limit exception is raised for too many calls."""
        self.service.max_calls_per_minute = 3
        await self.service._track_usage(100)
        await self.service._track_usage(100)
        await self.service._track_usage(100)

        with pytest.raises(ValidationException) as exc_info:
            await self.service._check_rate_limits()
        assert "Rate limit exceeded" in str(exc_info.value)

    async def test_rate_limit_exceeded_tokens(self):
        """Test that rate limit exception is raised for too many tokens."""
        self.service.max_tokens_per_minute = 1000
        await self.service._track_usage(600)
        await self.service._track_usage(500)

        with pytest.raises(ValidationException) as exc_info:
            await self.service._check_rate_limits()
        assert "Rate limit exceeded" in str(exc_info.value)

    async def test_rate_limit_ignora_uso_fora_da_janela(self):
        """
        Uso antigo não conta.

        A entrada velha é plantada direto no backend porque a janela é de um
        minuto e o teste não vai esperar sessenta segundos.
        """
        backend = MemoryRateLimitBackend()
        self.service.rate_limiter = RateLimiter(
            max_calls_per_minute=60,
            max_tokens_per_minute=40000,
            redis_backend=_SemRedis(),
            memory_backend=backend,
        )

        antigo = time.time() - 180  # três minutos atrás
        backend._entries[LLMService.SHARED_BUCKET].append((antigo, 999))

        await self.service._track_usage(100)

        status = await self.service.get_rate_limit_status()
        assert status["calls_used"] == 1
        assert status["tokens_used"] == 100


class TestGenerateResponse:
    """Test response generation with Claude."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = LLMService()
        self.agent = Agent(
            id="test-agent",
            user_id="test-user",
            nome="Test Agent",
            descricao="A test agent",
            system_prompt="You are a helpful assistant.",
            temperatura=0.7,
            max_tokens=1024,
            status="ativo",
        )

    @patch("app.services.llm_service.Anthropic")
    async def test_generate_response_success(self, mock_anthropic):
        """Test successful response generation."""
        # Mock Claude response
        mock_message = MagicMock()
        mock_message.content = [MagicMock(type="text", text="Hello! How can I help?")]
        mock_message.usage = MagicMock(
            input_tokens=10, output_tokens=5
        )

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        self.service.client = mock_client

        response, tokens = await self.service.generate_response(
            self.agent, "Hello"
        )

        assert response == "Hello! How can I help?"
        assert tokens["input_tokens"] == 10
        assert tokens["output_tokens"] == 5
        assert tokens["total_tokens"] == 15

    @patch("app.services.llm_service.Anthropic")
    async def test_uma_chamada_nao_congela_o_processo(self, mock_anthropic):
        """
        Duas respostas em paralelo não esperam uma pela outra.

        O cliente da Anthropic usado aqui é o síncrono, e ele estava sendo
        chamado direto de dentro de função `async`. Chamada bloqueante no event
        loop não atrasa só quem espera por ela: para o processo inteiro. Nos
        cinco segundos de uma resposta, nenhum outro webhook era lido e nenhuma
        tela do painel carregava; nos dois minutos de um parecer, o backend
        ficava parado, e a segunda mensagem do cliente esperava o parecer da
        primeira terminar antes de ser lida.

        O teste usa `time.sleep` de propósito — é justamente o bloqueio que
        precisa ser tolerado. Com a chamada fora do loop, as duas caminham
        juntas; presas nele, somam.
        """
        import asyncio
        import time

        DEMORA = 0.4

        def resposta_lenta(*_args, **_kwargs):
            time.sleep(DEMORA)
            mensagem = MagicMock()
            mensagem.content = [MagicMock(type="text", text="pronto")]
            mensagem.usage = MagicMock(input_tokens=1, output_tokens=1)
            return mensagem

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = resposta_lenta
        self.service.client = mock_client

        inicio = time.monotonic()
        await asyncio.gather(
            self.service.generate_response(self.agent, "primeira"),
            self.service.generate_response(self.agent, "segunda"),
        )
        decorrido = time.monotonic() - inicio

        assert decorrido < DEMORA * 1.8, (
            f"as duas chamadas levaram {decorrido:.2f}s, perto da soma "
            f"({DEMORA * 2:.2f}s): a chamada está bloqueando o event loop"
        )

    @patch("app.services.llm_service.Anthropic")
    async def test_generate_response_with_history(self, mock_anthropic):
        """Test response generation with conversation history."""
        mock_message = MagicMock()
        mock_message.content = [MagicMock(type="text", text="Response with history")]
        mock_message.usage = MagicMock(
            input_tokens=20, output_tokens=8
        )

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        self.service.client = mock_client

        history = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"},
        ]

        response, tokens = await self.service.generate_response(
            self.agent, "New message", history
        )

        assert response == "Response with history"
        assert tokens["total_tokens"] == 28
        # Verify history was included
        call_args = mock_client.messages.create.call_args
        assert len(call_args[1]["messages"]) == 3

    @patch("app.services.llm_service.Anthropic")
    async def test_generate_response_rate_limit_error(self, mock_anthropic):
        """Test rate limit error handling."""
        from anthropic import RateLimitError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429),
            body={}
        )
        self.service.client = mock_client

        with pytest.raises(ValidationException) as exc_info:
            await self.service.generate_response(self.agent, "Hello")
        assert "Rate limit exceeded" in str(exc_info.value)

    @patch("app.services.llm_service.Anthropic")
    async def test_generate_response_connection_error(self, mock_anthropic):
        """Test connection error handling."""
        from anthropic import APIConnectionError

        mock_client = MagicMock()
        # O SDK exige o `request` que originou a falha.
        mock_client.messages.create.side_effect = APIConnectionError(
            message="Connection failed",
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
        )
        self.service.client = mock_client

        with pytest.raises(ValidationException) as exc_info:
            await self.service.generate_response(self.agent, "Hello")
        assert "Connection error" in str(exc_info.value)

    @patch("app.services.llm_service.Anthropic")
    async def test_generate_response_api_error(self, mock_anthropic):
        """Test API error handling."""
        from anthropic import APIError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = APIError(
            "API error",
            httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
            body={},
        )
        self.service.client = mock_client

        with pytest.raises(ValidationException) as exc_info:
            await self.service.generate_response(self.agent, "Hello")
        assert "API error" in str(exc_info.value)

    @patch("app.services.llm_service.Anthropic")
    async def test_generate_response_uses_agent_temperature(self, mock_anthropic):
        """A temperatura do agente chega à API — nos modelos que a aceitam.

        O modelo é fixado aqui porque o default (`claude-sonnet-5`) recusa o
        parâmetro; quem cobre esse recorte é `TestParametrosDeAmostragem`.
        """
        mock_message = MagicMock()
        mock_message.content = [MagicMock(type="text", text="Response")]
        mock_message.usage = MagicMock(input_tokens=5, output_tokens=3)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        self.service.client = mock_client
        self.service.model = "claude-sonnet-4-6"

        self.agent.temperatura = 1.5

        await self.service.generate_response(self.agent, "Hello")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["temperature"] == 1.5

    @patch("app.services.llm_service.Anthropic")
    async def test_generate_response_uses_agent_max_tokens(self, mock_anthropic):
        """Test that agent max_tokens is used in API call."""
        mock_message = MagicMock()
        mock_message.content = [MagicMock(type="text", text="Response")]
        mock_message.usage = MagicMock(input_tokens=5, output_tokens=3)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        self.service.client = mock_client

        self.agent.max_tokens = 2048

        await self.service.generate_response(self.agent, "Hello")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 2048


class TestStreamResponse:
    """Test streaming response functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = LLMService()
        self.agent = Agent(
            id="test-agent",
            user_id="test-user",
            nome="Test Agent",
            system_prompt="You are helpful.",
            temperatura=0.7,
            max_tokens=1024,
            status="ativo",
        )

    @patch("app.services.llm_service.Anthropic")
    async def test_stream_response_yields_text(self, mock_anthropic):
        """Test that stream response yields text chunks."""
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=None)
        mock_stream.text_stream = ["Hello", " ", "world", "!"]
        mock_stream.get_final_message.return_value = MagicMock(
            usage=MagicMock(input_tokens=10, output_tokens=4)
        )

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream
        self.service.client = mock_client

        chunks = [chunk async for chunk in self.service.stream_response(self.agent, "Hi")]
        assert chunks == ["Hello", " ", "world", "!"]

    @patch("app.services.llm_service.Anthropic")
    async def test_stream_response_error_handling(self, mock_anthropic):
        """Test error handling in stream response."""
        from anthropic import RateLimitError

        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = RateLimitError(
            message="Rate limit",
            response=MagicMock(status_code=429),
            body={}
        )
        self.service.client = mock_client

        with pytest.raises(ValidationException):
            [chunk async for chunk in self.service.stream_response(self.agent, "Hi")]


class TestBuildMessages:
    """Test message building functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = LLMService()

    def test_build_messages_no_history(self):
        """Test building messages without history."""
        messages = self.service._build_messages(None, "Hello")
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

    def test_build_messages_with_history(self):
        """Test building messages with history."""
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]
        messages = self.service._build_messages(history, "How are you?")
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2] == {"role": "user", "content": "How are you?"}

    def test_build_messages_empty_history(self):
        """Test building messages with empty history list."""
        messages = self.service._build_messages([], "Hello")
        assert len(messages) == 1
        assert messages[0]["content"] == "Hello"


class TestRateLimitTracking:
    """Test rate limit tracking functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = LLMService()
        self.backend = MemoryRateLimitBackend()
        self.service.rate_limiter = RateLimiter(
            max_calls_per_minute=60,
            max_tokens_per_minute=40000,
            redis_backend=_SemRedis(),
            memory_backend=self.backend,
        )

    async def test_track_usage_adds_timestamp(self):
        """Test that tracking usage adds timestamp."""
        await self.service._track_usage(100)
        assert (await self.service.get_rate_limit_status())["calls_used"] == 1

    async def test_track_usage_records_tokens(self):
        """Test that tracking usage records tokens."""
        await self.service._track_usage(500)
        assert (await self.service.get_rate_limit_status())["tokens_used"] == 500

    async def test_track_usage_multiple_calls(self):
        """Test tracking multiple calls."""
        for i in range(3):
            await self.service._track_usage(i * 100)

        status = await self.service.get_rate_limit_status()
        assert status["calls_used"] == 3
        assert status["tokens_used"] == 300

    async def test_track_usage_old_entries_removed(self):
        """Entradas fora do período de retenção saem do balde."""
        bucket = LLMService.SHARED_BUCKET
        # Além dos 120s de retenção, para o registro seguinte varrer a entrada.
        self.backend._entries[bucket].append((time.time() - 300, 999))

        await self.service._track_usage(100)

        assert len(self.backend._entries[bucket]) == 1
        assert (await self.service.get_rate_limit_status())["calls_used"] == 1


class TestLeituraDaResposta:
    """
    `content[0].text` quebrou na primeira chamada real com chave da Anthropic.

    O Opus 5 raciocina por padrão e o primeiro bloco é um `ThinkingBlock`, que
    não tem `.text`: a chamada morria com `AttributeError` antes de qualquer
    resposta chegar ao cliente. Filtrar por tipo vale para qualquer modelo, com
    ou sem raciocínio.
    """

    @staticmethod
    def _bloco(tipo, **campos):
        b = MagicMock()
        b.type = tipo
        for k, v in campos.items():
            setattr(b, k, v)
        return b

    def test_ignora_bloco_de_raciocinio_e_devolve_o_texto(self):
        from app.services.llm_service import texto_da_resposta

        resposta = MagicMock()
        resposta.content = [
            self._bloco("thinking", thinking="deixa eu pensar"),
            self._bloco("text", text="## Resumo\nCliente relata demissão."),
        ]

        assert texto_da_resposta(resposta) == "## Resumo\nCliente relata demissão."

    def test_junta_varios_blocos_de_texto(self):
        from app.services.llm_service import texto_da_resposta

        resposta = MagicMock()
        resposta.content = [
            self._bloco("text", text="parte um "),
            self._bloco("thinking", thinking="..."),
            self._bloco("text", text="parte dois"),
        ]

        assert texto_da_resposta(resposta) == "parte um parte dois"

    def test_so_raciocinio_e_nenhum_texto_da_zero(self):
        """
        Acontece quando o orçamento acaba no meio do raciocínio.

        Devolver string vazia daqui mandaria uma mensagem em branco ao cliente;
        quem chama transforma isso em erro com o `stop_reason` junto.
        """
        from app.services.llm_service import texto_da_resposta

        resposta = MagicMock()
        resposta.content = [self._bloco("thinking", thinking="pensei e acabou o teto")]

        assert texto_da_resposta(resposta) == ""


class TestParametrosDeAmostragem:
    """
    `temperature` só vai para os modelos que o aceitam.

    Os modelos novos (Opus 4.7 em diante, Sonnet 5, Opus 5, Fable 5) recusam
    parâmetros de amostragem com 400. O default do projeto é
    `claude-sonnet-5`, então mandar sempre — como o código fazia — derrubaria
    toda chamada ao Claude. Os testes olham o corpo HTTP de verdade, e não um
    mock do cliente: o ponto é o que sai na requisição.
    """

    def _corpo_enviado(self, modelo: str, temperatura: float | None = 0.7) -> dict:
        import json

        import anthropic
        import httpx

        capturado: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            capturado.update(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "id": "msg_1", "type": "message", "role": "assistant",
                    "model": modelo, "content": [{"type": "text", "text": "ok"}],
                    "stop_reason": "end_turn", "stop_sequence": None,
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                },
            )

        service = LLMService()
        service.model = modelo
        service.rate_limiter = RateLimiter(
            max_calls_per_minute=60, max_tokens_per_minute=40000,
            redis_backend=_SemRedis(),
        )
        service.client = anthropic.Anthropic(
            api_key="sk-ant-teste",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

        agent = Agent(
            id="ag", user_id="u", nome="A", system_prompt="p",
            temperatura=temperatura, max_tokens=512, status="ativo",
        )
        import asyncio

        asyncio.run(service.generate_response(agent, "oi"))
        return capturado

    def test_modelo_novo_nao_recebe_temperatura(self):
        for modelo in ("claude-sonnet-5", "claude-opus-5", "claude-opus-4-7"):
            assert "temperature" not in self._corpo_enviado(modelo), modelo

    def test_modelo_antigo_ainda_recebe_temperatura(self):
        corpo = self._corpo_enviado("claude-sonnet-4-6")

        assert corpo["temperature"] == 0.7

    def test_modelo_desconhecido_cai_no_caminho_seguro(self):
        """
        A lista é de quem aceita, não de quem recusa.

        Omitir `temperature` é aceito por todos os modelos; enviá-lo quebra nos
        novos. Um modelo lançado depois deste código precisa, portanto, cair no
        lado que não quebra.
        """
        assert "temperature" not in self._corpo_enviado("claude-modelo-do-futuro-9")

    def test_max_tokens_do_agente_sempre_vai(self):
        assert self._corpo_enviado("claude-sonnet-5")["max_tokens"] == 512


class TestExcecoesDoSDK:
    """
    As exceções tratadas existem e mantêm a hierarquia que o `except` assume.

    O `llm_service` captura RateLimitError antes de APIError; se a herança
    mudasse numa atualização do SDK, o primeiro `except` deixaria de pegar e o
    erro cairia no genérico — sem quebrar teste nenhum.
    """

    def test_hierarquia_das_excecoes(self):
        import anthropic

        assert issubclass(anthropic.RateLimitError, anthropic.APIError)
        assert issubclass(anthropic.APIConnectionError, anthropic.APIError)

    def test_ordem_do_except_pega_o_mais_especifico(self):
        import anthropic

        # RateLimitError precisa ser mais específico que APIError, senão o
        # `except APIError` de llm_service.py o engoliria primeiro.
        assert anthropic.RateLimitError is not anthropic.APIError
        assert issubclass(anthropic.RateLimitError, anthropic.APIStatusError)


class TestServiceInitialization:
    """Test LLM service initialization."""

    def test_service_initialization(self):
        """Test that service initializes correctly."""
        service = LLMService()
        assert service.client is not None
        # Compara com a config em vez de fixar a versão do modelo: trocar o
        # default não deve quebrar o teste de inicialização.
        assert service.model == settings.claude_model
        assert service.max_calls_per_minute > 0
        assert service.max_tokens_per_minute > 0

    def test_service_singleton(self):
        """Test that global service instance exists."""
        from app.services.llm_service import llm_service as global_service
        assert global_service is not None
        assert isinstance(global_service, LLMService)


class TestConversationHistoryRetrieval:
    """Test conversation history retrieval."""

    @pytest.mark.asyncio
    async def test_get_conversation_history_empty(self):
        """Test retrieving history from empty conversation."""
        service = LLMService()
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = []

        history = await service.get_conversation_history(
            "nonexistent-convo", mock_db
        )
        assert history == []

    @pytest.mark.asyncio
    async def test_get_conversation_history_with_messages(self):
        """Test retrieving history with messages."""
        service = LLMService()

        mock_message1 = MagicMock()
        mock_message1.remetente = "user"
        mock_message1.conteudo = "Hello"

        mock_message2 = MagicMock()
        mock_message2.remetente = "assistant"
        mock_message2.conteudo = "Hi there!"

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        # Delega ao memory_service, cuja query é ORDER BY timestamp DESC:
        # o banco devolveria a mais recente primeiro.
        mock_result.scalars.return_value.all.return_value = [mock_message2, mock_message1]
        mock_db.execute.return_value = mock_result

        history = await service.get_conversation_history(
            "test-convo", mock_db
        )
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"


class TestSistemaDoAgente:
    """
    O nome do atendente entra no system prompt, e não no texto do prompt.

    O prompt é do dono do agente: ele pode reescrevê-lo inteiro pelo painel, e
    um nome escondido no meio do texto se perderia na primeira edição.
    """

    def _agente(self, nome_atendente=None, prompt="Você é o atendimento."):
        a = MagicMock()
        a.system_prompt = prompt
        a.nome_atendente = nome_atendente
        return a

    def test_com_nome_o_modelo_recebe_o_nome(self):
        from app.services.llm_service import sistema_do_agente

        sistema = sistema_do_agente(self._agente("Fernanda"))

        assert "Você é o atendimento." in sistema
        assert "Fernanda" in sistema

    def test_sem_nome_o_prompt_passa_intacto(self):
        """
        Nada anexado: o prompt manda não inventar nome, e uma frase vazia
        ("Você atende com o nome .") seria pior que silêncio.
        """
        from app.services.llm_service import sistema_do_agente

        assert sistema_do_agente(self._agente()) == "Você é o atendimento."

    def test_nome_só_com_espaços_conta_como_sem_nome(self):
        from app.services.llm_service import sistema_do_agente

        assert sistema_do_agente(self._agente("   ")) == "Você é o atendimento."

    def test_agente_antigo_sem_o_campo_nao_quebra(self):
        """
        Objeto sem `nome_atendente` — agente carregado antes da migração, ou
        mock de teste antigo. Deve seguir como se não tivesse nome.
        """
        from app.services.llm_service import sistema_do_agente

        class AgenteVelho:
            system_prompt = "Você é o atendimento."

        assert sistema_do_agente(AgenteVelho()) == "Você é o atendimento."
