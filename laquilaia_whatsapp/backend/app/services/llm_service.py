"""LLM service for Claude integration."""

from typing import AsyncIterator, Dict, List, Optional, Tuple
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError
from app.config import settings
from app.utils.logger import logger
from app.utils.exceptions import ValidationException
from app.services.rate_limiter import RateLimiter
from app.services.gemini_client import GeminiClient, GeminiIndisponivel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Agent, Message, Conversation
import asyncio


# Famílias de modelo que ainda aceitam parâmetros de amostragem.
#
# A lista é de quem **aceita**, e não de quem recusa, de propósito: omitir
# `temperature` é aceito por todos os modelos, enquanto enviá-lo devolve 400
# nos mais novos (Opus 4.7 em diante, Sonnet 5, Opus 5, Fable 5). Assim um
# modelo lançado depois deste código cai sozinho no caminho seguro, em vez de
# quebrar até alguém lembrar de atualizar uma lista de bloqueio.
MODELOS_QUE_ACEITAM_TEMPERATURA = (
    "claude-3",
    "claude-sonnet-4-0",
    "claude-sonnet-4-5",
    "claude-sonnet-4-6",
    "claude-opus-4-0",
    "claude-opus-4-1",
    "claude-opus-4-5",
    "claude-opus-4-6",
    "claude-haiku-4-5",
)


def aceita_temperatura(modelo: str) -> bool:
    """Se este modelo aceita `temperature` na requisição."""
    return modelo.startswith(MODELOS_QUE_ACEITAM_TEMPERATURA)


# O que cada provedor consegue ler.
#
# Imagem e PDF os dois leem. Áudio, só o Gemini: a API da Anthropic não aceita
# áudio como entrada, e mandar assim mesmo é 400 na cara do cliente que gravou
# um áudio de dois minutos contando o caso dele.
FORMATOS_DO_CLAUDE = ("image/", "application/pdf")


def _bloco_de_anexo_claude(anexo: dict) -> dict:
    """
    O anexo no formato de bloco de conteúdo da Anthropic.

    Imagem e PDF usam blocos diferentes (`image` e `document`) com a mesma
    fonte base64 — trocar um pelo outro é 400.
    """
    mimetype = anexo["mimetype"]
    tipo = "document" if mimetype == "application/pdf" else "image"
    return {
        "type": tipo,
        "source": {
            "type": "base64",
            "media_type": mimetype,
            "data": anexo["base64"],
        },
    }


def claude_le(mimetype: str) -> bool:
    """Se o Claude consegue receber este tipo de arquivo."""
    return mimetype.startswith(FORMATOS_DO_CLAUDE)


def texto_da_resposta(response) -> str:
    """
    O texto da resposta, ignorando os blocos que não são texto.

    `content[0].text` funcionou enquanto todo modelo devolvia texto e mais
    nada. O Opus 5 raciocina por padrão: o primeiro bloco é um `ThinkingBlock`,
    que não tem `.text`, e a chamada morria com `AttributeError` antes de
    qualquer resposta chegar ao cliente. Foi o que aconteceu na primeira
    chamada real com a chave da Anthropic.

    Filtrar por `type == "text"` e juntar o que sobra vale para qualquer
    modelo, com ou sem raciocínio, hoje e quando aparecer um bloco novo.
    """
    partes = [
        bloco.text
        for bloco in response.content
        if getattr(bloco, "type", None) == "text"
    ]
    return "".join(partes)


def sistema_do_agente(agent: Agent) -> str:
    """
    O system prompt como o modelo o recebe.

    O nome do atendente entra aqui, e não no texto do prompt, porque o prompt é
    do dono do agente: ele pode reescrevê-lo inteiro pelo painel, e um nome
    escondido no meio do texto se perderia na primeira edição. Anexado ao fim,
    ele sobrevive a qualquer prompt.

    Sem nome configurado, nada é anexado — e o prompt manda não inventar um.
    Atendente que inventa nome próprio é atendente que mente sobre quem é.
    """
    nome = (getattr(agent, "nome_atendente", None) or "").strip()
    if not nome:
        return agent.system_prompt

    return (
        f"{agent.system_prompt}\n\n"
        f"Você atende com o nome {nome}. É assim que você se apresenta e "
        f"assina, se precisar assinar."
    )


class LLMService:
    """Service for managing Claude LLM interactions."""

    def __init__(self):
        """Initialize LLM service with Anthropic client."""
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        # Reserva. Sem GEMINI_API_KEY ele fica inerte e o erro do Claude sobe
        # como sempre subiu.
        self.gemini = GeminiClient()
        # Um balde por conta, guardado no Redis para valer entre réplicas.
        # Ver `rate_limiter.py` para a janela e o comportamento sem Redis.
        self.rate_limiter = RateLimiter(
            max_calls_per_minute=settings.llm_max_calls_per_minute,
            max_tokens_per_minute=settings.llm_max_tokens_per_minute,
        )

    # Chave usada quando não há usuário no contexto (testes, chamadas internas).
    SHARED_BUCKET = "__shared__"

    @property
    def max_calls_per_minute(self) -> int:
        return self.rate_limiter.max_calls_per_minute

    @max_calls_per_minute.setter
    def max_calls_per_minute(self, value: int) -> None:
        self.rate_limiter.max_calls_per_minute = value

    @property
    def max_tokens_per_minute(self) -> int:
        return self.rate_limiter.max_tokens_per_minute

    @max_tokens_per_minute.setter
    def max_tokens_per_minute(self, value: int) -> None:
        self.rate_limiter.max_tokens_per_minute = value

    def _parametros_do_modelo(self, agent: Agent, model: Optional[str] = None) -> dict:
        """
        Parâmetros da requisição que dependem do modelo configurado.

        `temperature` só entra quando o modelo aceita. Nos modelos novos ele
        é recusado com 400 — e o agente guarda o valor porque o formulário
        deixa escolher, então mandar sempre derrubaria toda chamada com o
        default `claude-sonnet-5`.

        O modelo é parâmetro e não `self.model` porque o parecer jurídico roda
        num modelo próprio: a decisão sobre temperatura tem que seguir o modelo
        da chamada, não o do atendimento.
        """
        modelo = model or self.model
        params = {"max_tokens": agent.max_tokens or settings.max_tokens}

        if aceita_temperatura(modelo):
            params["temperature"] = agent.temperatura or settings.temperature
        elif agent.temperatura is not None:
            logger.debug(
                f"🌡️ temperatura {agent.temperatura} ignorada: {modelo} "
                "não aceita o parâmetro"
            )

        return params

    def _tentar_claude_primeiro(self) -> bool:
        """
        Se vale a pena chamar o Claude antes da reserva.

        Sem chave da Anthropic, chamar mesmo assim é um 401 garantido por
        mensagem — latência e log de erro em troca de nada. Só pulamos o
        Claude quando há reserva configurada para assumir; sem ela, a chamada
        segue e o erro de autenticação sobe, que é o diagnóstico correto.
        """
        if settings.anthropic_api_key:
            return True
        return not self.gemini.configured

    async def _chamar_claude(
        self, agent: Agent, messages: List[dict], model: Optional[str] = None
    ) -> Tuple[str, dict]:
        """
        Uma resposta do Claude, **fora** do event loop.

        O cliente da Anthropic aqui é o síncrono, e ele estava sendo chamado
        direto de dentro de função `async`. Uma chamada bloqueante no event
        loop não atrasa só quem espera por ela: **para o processo inteiro**.
        Durante os cinco segundos de uma resposta de atendimento, nenhum outro
        webhook era lido e nenhuma tela do painel carregava; durante os dois
        minutos de um parecer, o backend ficava parado — e a segunda mensagem
        do cliente esperava o parecer da primeira terminar antes de sequer ser
        lida. Era a demora "de minutos" que aparecia no WhatsApp com o
        servidor aparentemente ocioso.

        `to_thread` em vez de trocar para o `AsyncAnthropic`: a mudança fica
        contida numa linha por ponto de chamada, e o cliente síncrono é o que
        os testes usam.
        """
        return await asyncio.to_thread(self._chamar_claude_sincrono, agent, messages, model)

    def _chamar_claude_sincrono(
        self, agent: Agent, messages: List[dict], model: Optional[str] = None
    ) -> Tuple[str, dict]:
        modelo = model or self.model
        response = self.client.messages.create(
            model=modelo,
            system=sistema_do_agente(agent),
            messages=messages,
            **self._parametros_do_modelo(agent, modelo),
        )

        entrada = response.usage.input_tokens
        saida = response.usage.output_tokens

        texto = texto_da_resposta(response)
        if not texto:
            # Acontece quando o orçamento acaba durante o raciocínio: vem um
            # bloco de pensamento, nenhum de texto, e `stop_reason` é
            # "max_tokens". Sem este aviso o sintoma é o atendente mudo.
            raise ValidationException(
                f"{modelo} não devolveu texto (stop_reason={response.stop_reason}); "
                "o max_tokens provavelmente acabou durante o raciocínio"
            )

        return texto, {
            "input_tokens": entrada,
            "output_tokens": saida,
            "total_tokens": entrada + saida,
            "model": modelo,
            # Vai junto porque `max_tokens` é o único motivo de parada que não
            # se parece com erro: a resposta chega, bem escrita, terminando no
            # meio de uma frase. Quem chama precisa poder perceber — foi assim
            # que três pareceres seguidos perderam a conclusão sem que nada
            # aparecesse no log.
            "stop_reason": response.stop_reason,
        }

    async def _chamar_reserva(
        self,
        agent: Agent,
        user_message: str,
        conversation_history: Optional[List[dict]],
        causa: Optional[Exception],
        model: Optional[str] = None,
        anexo: Optional[dict] = None,
    ) -> Tuple[str, dict]:
        """
        Tenta o provedor de reserva.

        Se a reserva não estiver configurada ou também falhar, relança a falha
        original do Claude — nunca a da reserva. Quem lê o log precisa saber
        que o provedor principal caiu; "GEMINI_API_KEY não configurada" no
        lugar de um 529 da Anthropic manda investigar o problema errado.
        """
        if not self.gemini.configured:
            if causa is not None:
                raise causa
            raise ValidationException(
                "Nenhum provedor de LLM configurado: defina ANTHROPIC_API_KEY "
                "ou GEMINI_API_KEY."
            )

        if causa is not None:
            logger.warning(f"⚠️ Claude falhou ({causa}); tentando o Gemini")

        try:
            texto, uso = await self.gemini.generate(
                system_prompt=sistema_do_agente(agent),
                user_message=user_message,
                conversation_history=conversation_history,
                max_tokens=agent.max_tokens or settings.max_tokens,
                temperature=agent.temperatura or settings.temperature,
                model=model,
                anexo=anexo,
            )
        except GeminiIndisponivel as e:
            logger.error(f"❌ A reserva também falhou: {e}")
            if causa is not None:
                raise causa
            raise ValidationException(f"Erro no provedor de reserva: {e}")

        uso["model"] = model or self.gemini.model
        return texto, uso

    async def generate_response(
        self,
        agent: Agent,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
        anexo: Optional[dict] = None,
    ) -> Tuple[str, dict]:
        """
        Generate response using Claude with context.

        Args:
            agent: Agent model instance
            user_message: Current user message
            conversation_history: Previous messages for context

        Returns:
            Tuple of (response_text, token_usage_dict)

        Raises:
            ValidationException: Rate limit or validation errors
        """
        try:
            # Check rate limits
            await self._check_rate_limits(agent.user_id)

            # Build messages array
            messages = self._build_messages(conversation_history, user_message, anexo)

            # Áudio é o caso em que a reserva não é reserva: é o único
            # provedor que sabe ler. Tentar o Claude antes seria gastar uma
            # chamada para receber 400.
            so_o_gemini_le = anexo is not None and not claude_le(anexo["mimetype"])

            if so_o_gemini_le:
                response_text, token_usage = await self._chamar_reserva(
                    agent, user_message, conversation_history, causa=None, anexo=anexo
                )
            elif self._tentar_claude_primeiro():
                try:
                    response_text, token_usage = await self._chamar_claude(agent, messages)
                except (RateLimitError, APIConnectionError, APIError) as e:
                    # A reserva devolve a falha original se não puder assumir,
                    # para o tratamento lá embaixo continuar valendo.
                    response_text, token_usage = await self._chamar_reserva(
                        agent, user_message, conversation_history, causa=e, anexo=anexo
                    )
            else:
                response_text, token_usage = await self._chamar_reserva(
                    agent, user_message, conversation_history, causa=None, anexo=anexo
                )

            # Track usage
            await self._track_usage(token_usage["total_tokens"], agent.user_id)

            logger.info(
                f"✅ Resposta gerada para o agente {agent.id} por "
                f"{token_usage['model']} (tokens: {token_usage['total_tokens']})"
            )

            return response_text, token_usage

        except RateLimitError as e:
            logger.warning(f"⚠️ Rate limit exceeded: {e}")
            raise ValidationException("Rate limit exceeded. Please try again in a moment.")
        except APIConnectionError as e:
            logger.error(f"❌ API connection error: {e}")
            raise ValidationException("Connection error. Please try again.")
        except APIError as e:
            logger.error(f"❌ API error: {e}")
            raise ValidationException(f"API error: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            raise

    async def stream_response(
        self,
        agent: Agent,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream response from Claude (generator).

        Assíncrono porque a contagem de uso passou a viver no Redis: um
        gerador `def` não tem como esperar o `await` do limitador.

        Args:
            agent: Agent model instance
            user_message: Current user message
            conversation_history: Previous messages for context

        Yields:
            Text chunks from Claude response
        """
        try:
            # Check rate limits
            await self._check_rate_limits(agent.user_id)

            # Build messages array
            messages = self._build_messages(conversation_history, user_message)

            # Stream from Claude API
            with self.client.messages.stream(
                model=self.model,
                system=sistema_do_agente(agent),
                messages=messages,
                **self._parametros_do_modelo(agent),
            ) as stream:
                total_tokens = 0
                for text in stream.text_stream:
                    yield text

                # Track usage from final message
                if hasattr(stream, "get_final_message"):
                    final = stream.get_final_message()
                    total_tokens = (
                        final.usage.input_tokens + final.usage.output_tokens
                    )
                    await self._track_usage(total_tokens, agent.user_id)
                    logger.info(
                        f"✅ Claude stream completed for agent {agent.id} "
                        f"(tokens: {total_tokens})"
                    )

        except RateLimitError as e:
            logger.warning(f"⚠️ Rate limit exceeded: {e}")
            raise ValidationException("Rate limit exceeded.")
        except Exception as e:
            logger.error(f"❌ Error streaming response: {e}")
            raise

    async def analisar_com_prompt(
        self,
        system_prompt: str,
        user_message: str,
        user_id: Optional[str] = None,
        max_tokens: int = 1500,
        modelo_claude: Optional[str] = None,
        modelo_gemini: Optional[str] = None,
    ) -> Tuple[str, dict]:
        """
        Uma chamada avulsa ao modelo, sem agente e sem histórico.

        Serve para trabalho interno — o parecer do `legal_analyst` — em que o
        prompt não é o do atendimento e não existe conversa a continuar. Passa
        pelo mesmo limitador e pela mesma reserva: é a mesma cota, e a análise
        não pode furar a fila do atendimento.

        O modelo vem separado por provedor porque a queda para a reserva
        continua valendo aqui: um id de modelo da Anthropic não existe no
        Gemini, e vice-versa. Qualquer um dos dois vazio cai no modelo do
        atendimento.
        """
        # Um agente sintético reaproveita `_chamar_claude` e `_chamar_reserva`
        # sem duplicar a lógica de queda entre provedores.
        class _AgenteAvulso:
            id = "interno"
            system_prompt = None
            temperatura = None
            max_tokens = None
            user_id = None

        agente = _AgenteAvulso()
        agente.system_prompt = system_prompt
        agente.max_tokens = max_tokens
        agente.user_id = user_id

        await self._check_rate_limits(user_id)
        messages = self._build_messages(None, user_message)

        if self._tentar_claude_primeiro():
            try:
                texto, uso = await self._chamar_claude(agente, messages, model=modelo_claude)
            except (RateLimitError, APIConnectionError, APIError) as e:
                texto, uso = await self._chamar_reserva(
                    agente, user_message, None, causa=e, model=modelo_gemini
                )
        else:
            texto, uso = await self._chamar_reserva(
                agente, user_message, None, causa=None, model=modelo_gemini
            )

        await self._track_usage(uso["total_tokens"], user_id)
        return texto, uso

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using Claude's tokenizer.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        try:
            # Rough approximation: ~4 chars per token
            # For accurate counting, we'd need beta_messages_2024_12_19 with token counting
            # But for MVP, this approximation works
            token_count = len(text) // 4
            return max(1, token_count)
        except Exception as e:
            logger.error(f"❌ Error counting tokens: {e}")
            return len(text) // 4

    async def get_conversation_history(
        self,
        conversation_id: str,
        db: AsyncSession,
        limit: int = 10,
    ) -> List[dict]:
        """
        As últimas mensagens da conversa, para irem como contexto.

        Lê sempre do banco. Houve aqui um cache de uma hora que devolvia o
        histórico congelado no início da conversa — ver `memory_service`.

        Args:
            conversation_id: Conversation ID
            db: Database session
            limit: Maximum number of messages to retrieve

        Returns:
            List of conversation messages
        """
        try:
            from app.services.memory_service import memory_service

            return await memory_service.get_conversation_history(
                conversation_id, db, limit=limit
            )
        except Exception as e:
            logger.error(f"❌ Error retrieving conversation history: {e}")
            return []

    def _build_messages(
        self,
        conversation_history: Optional[List[dict]],
        user_message: str,
        anexo: Optional[dict] = None,
    ) -> List[dict]:
        """
        Build messages array for Claude API.

        Args:
            conversation_history: Previous messages
            user_message: Current user message

        Returns:
            Formatted messages for Claude
        """
        messages = []

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        if anexo:
            # O anexo vai **antes** do texto: a legenda ("olha a cláusula 8")
            # só faz sentido depois de o modelo ter visto o documento. Na ordem
            # inversa ele lê a pergunta sem ter o que responder.
            messages.append(
                {
                    "role": "user",
                    "content": [
                        _bloco_de_anexo_claude(anexo),
                        {"type": "text", "text": user_message},
                    ],
                }
            )
        else:
            messages.append({"role": "user", "content": user_message})

        return messages

    async def _check_rate_limits(self, user_id: Optional[str] = None) -> None:
        """
        Check if rate limits are exceeded.

        Raises:
            ValidationException: If rate limit exceeded
        """
        await self.rate_limiter.check(user_id or self.SHARED_BUCKET)

    async def _track_usage(
        self, total_tokens: int, user_id: Optional[str] = None
    ) -> None:
        """
        Track API usage for rate limiting.

        Args:
            total_tokens: Total tokens used in this request
        """
        bucket = user_id or self.SHARED_BUCKET
        await self.rate_limiter.track(bucket, total_tokens)
        logger.debug(f"📊 Uso registrado ({bucket}): +1 chamada, {total_tokens} tokens")

    async def get_rate_limit_status(self, user_id: Optional[str] = None) -> dict:
        """
        Get current rate limit status.

        Returns:
            Dict with usage statistics
        """
        return await self.rate_limiter.status(user_id or self.SHARED_BUCKET)


# Global instance
llm_service = LLMService()
