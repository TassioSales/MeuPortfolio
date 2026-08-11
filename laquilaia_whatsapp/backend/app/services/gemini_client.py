"""
Cliente da API do Gemini, usado como provedor de reserva do Claude.

Fala HTTP direto com `generativelanguage.googleapis.com` em vez de usar o
SDK `google-generativeai`. O motivo é dependência: o backend já carrega
`httpx` (o SDK da Anthropic o usa) e o pino é 0.25.0; trazer outro SDK
significaria mais um pacote com faixa própria de httpx para conciliar, em
troca de um POST e um parse de JSON.

O contrato aqui é o mesmo de `LLMService.generate_response`: devolve
`(texto, uso_de_tokens)` com as mesmas chaves, para que quem chama não
precise saber qual provedor respondeu.
"""

from typing import List, Optional, Tuple

import httpx

from app.config import settings
from app.utils.logger import logger


BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiIndisponivel(RuntimeError):
    """Gemini não está configurado, ou não devolveu uma resposta usável."""


class GeminiClient:
    """Chamada única ao `generateContent`, sem estado entre requisições."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        # `None` significa "pergunte às settings"; string vazia significa
        # "não configurado" e é resposta legítima, então os dois casos
        # precisam ser distinguidos.
        self.api_key = settings.gemini_api_key if api_key is None else api_key
        self.model = model or settings.gemini_model
        self.timeout = timeout
        # Ponto de injeção dos testes: com um MockTransport dá para conferir
        # o corpo que sai, que é onde os erros de formato aparecem.
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        system_prompt: Optional[str],
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Tuple[str, dict]:
        """
        Gera uma resposta.

        Raises:
            GeminiIndisponivel: sem chave, erro HTTP, ou resposta sem texto
                (o que acontece quando o filtro de segurança corta o candidato).
        """
        if not self.configured:
            raise GeminiIndisponivel("GEMINI_API_KEY não configurada")

        payload = self._montar_payload(
            system_prompt, user_message, conversation_history, max_tokens, temperature
        )

        url = f"{BASE_URL}/models/{self.model}:generateContent"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, transport=self._transport
            ) as client:
                resposta = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-goog-api-key": self.api_key,
                    },
                )
        except httpx.HTTPError as e:
            raise GeminiIndisponivel(f"falha de rede: {e}") from e

        if resposta.status_code >= 400:
            # O corpo do erro do Google traz a razão; sem ele o diagnóstico
            # vira adivinhação entre chave inválida, cota e modelo errado.
            raise GeminiIndisponivel(
                f"HTTP {resposta.status_code}: {resposta.text[:300]}"
            )

        return self._ler_resposta(resposta.json())

    def _montar_payload(
        self,
        system_prompt: Optional[str],
        user_message: str,
        conversation_history: Optional[List[dict]],
        max_tokens: Optional[int],
        temperature: Optional[float],
    ) -> dict:
        payload = {
            "contents": self._montar_contents(conversation_history, user_message),
        }

        if system_prompt:
            # `systemInstruction`, em camelCase, e com `parts` — não é uma
            # string solta como no Claude.
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        config = {}
        if max_tokens is not None:
            config["maxOutputTokens"] = max_tokens
        if temperature is not None:
            # Ao contrário dos modelos novos do Claude, o Gemini aceita
            # `temperature` — quando ele responde, o valor do agente vale.
            config["temperature"] = temperature
        if config:
            payload["generationConfig"] = config

        return payload

    @staticmethod
    def _montar_contents(
        conversation_history: Optional[List[dict]], user_message: str
    ) -> List[dict]:
        """
        Converte o histórico do formato do Claude para o do Gemini.

        São dois nomes diferentes para a mesma coisa: o papel do assistente é
        `model`, não `assistant`, e o texto vai em `parts`, não em `content`.
        Mandar no formato do Claude não dá erro — o Gemini ignora o turno e
        responde sem o contexto, que é pior do que falhar.
        """
        contents: List[dict] = []

        for mensagem in conversation_history or []:
            papel = "model" if mensagem.get("role") == "assistant" else "user"
            contents.append(
                {"role": papel, "parts": [{"text": mensagem.get("content", "")}]}
            )

        contents.append({"role": "user", "parts": [{"text": user_message}]})
        return contents

    @staticmethod
    def _ler_resposta(dados: dict) -> Tuple[str, dict]:
        candidatos = dados.get("candidates") or []
        if not candidatos:
            raise GeminiIndisponivel(
                f"resposta sem candidatos: {dados.get('promptFeedback', dados)}"
            )

        primeiro = candidatos[0]
        partes = (primeiro.get("content") or {}).get("parts") or []
        texto = "".join(parte.get("text", "") for parte in partes)

        if not texto:
            # Acontece quando o filtro de segurança corta a resposta: vem um
            # candidato com finishReason e sem parts.
            raise GeminiIndisponivel(
                f"resposta sem texto (finishReason={primeiro.get('finishReason')})"
            )

        uso = dados.get("usageMetadata") or {}
        entrada = uso.get("promptTokenCount", 0)
        saida = uso.get("candidatesTokenCount", 0)

        return texto, {
            "input_tokens": entrada,
            "output_tokens": saida,
            "total_tokens": uso.get("totalTokenCount", entrada + saida),
        }
