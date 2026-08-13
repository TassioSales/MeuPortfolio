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

# Folga somada ao `max_tokens` do agente ao falar com o Gemini.
#
# `maxOutputTokens` limita raciocínio **e** resposta no mesmo orçamento, e os
# modelos da série 3 raciocinam sempre — `thinkingBudget: 0` é recusado com
# 400. Medido contra a API real: uma saudação gasta ~120 tokens de raciocínio
# e uma pergunta de qualificação de lead chegou a 565. Sem folga, um agente
# com `max_tokens=256` recebe `finishReason: MAX_TOKENS` e uma frase cortada
# no meio — foi o que aconteceu no primeiro teste de verdade.
#
# Somar em vez de fixar um piso preserva a intenção de quem configurou: a
# resposta ainda pode usar os `max_tokens` pedidos, e o raciocínio sai daqui.
FOLGA_MINIMA_DE_RACIOCINIO = 1024


def folga_de_raciocinio(max_tokens: int) -> int:
    """
    Quanto reservar para o raciocínio, além da resposta pedida.

    Os 1024 fixos bastavam enquanto tudo que passava por aqui era um turno de
    WhatsApp. O parecer jurídico quebrou a conta: pedindo 4000 tokens de
    resposta, o modelo gastou 3433 só pensando e o texto foi cortado no meio da
    lista de documentos. Quanto maior a tarefa, mais o modelo pensa antes de
    escrever — a folga precisa acompanhar, e não ficar constante.

    Reservar o mesmo tanto da resposta é a regra mais simples que cobre o caso
    medido com margem, e não muda nada abaixo de 1024. Não custa: o
    `maxOutputTokens` é teto, e só se paga o que o modelo de fato gerar.
    """
    return max(FOLGA_MINIMA_DE_RACIOCINIO, max_tokens)


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
        model: Optional[str] = None,
        anexo: Optional[dict] = None,
    ) -> Tuple[str, dict]:
        """
        Gera uma resposta.

        `model` troca o modelo só nesta chamada, sem tocar no cliente: o
        parecer jurídico usa um modelo mais forte que o atendimento, e os dois
        passam por aqui.

        Raises:
            GeminiIndisponivel: sem chave, erro HTTP, ou resposta sem texto
                (o que acontece quando o filtro de segurança corta o candidato).
        """
        if not self.configured:
            raise GeminiIndisponivel("GEMINI_API_KEY não configurada")

        payload = self._montar_payload(
            system_prompt,
            user_message,
            conversation_history,
            max_tokens,
            temperature,
            anexo,
        )

        url = f"{BASE_URL}/models/{model or self.model}:generateContent"
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
        anexo: Optional[dict] = None,
    ) -> dict:
        payload = {
            "contents": self._montar_contents(
                conversation_history, user_message, anexo
            ),
        }

        if system_prompt:
            # `systemInstruction`, em camelCase, e com `parts` — não é uma
            # string solta como no Claude.
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        config = {}
        if max_tokens is not None:
            config["maxOutputTokens"] = max_tokens + folga_de_raciocinio(max_tokens)
        if temperature is not None:
            # Ao contrário dos modelos novos do Claude, o Gemini aceita
            # `temperature` — quando ele responde, o valor do agente vale.
            config["temperature"] = temperature
        if config:
            payload["generationConfig"] = config

        return payload

    @staticmethod
    def _montar_contents(
        conversation_history: Optional[List[dict]],
        user_message: str,
        anexo: Optional[dict] = None,
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

        partes: List[dict] = []
        if anexo:
            # `inlineData`, em camelCase, com o base64 cru — sem o prefixo
            # `data:`, que aqui é erro e não enfeite.
            #
            # O anexo vem antes do texto: a legenda ("olha a cláusula 8") só
            # faz sentido depois de o modelo ter visto o arquivo.
            partes.append(
                {
                    "inlineData": {
                        "mimeType": anexo["mimetype"],
                        "data": anexo["base64"],
                    }
                }
            )
        partes.append({"text": user_message})

        contents.append({"role": "user", "parts": partes})
        return contents

    @staticmethod
    def _ler_resposta(dados: dict) -> Tuple[str, dict]:
        candidatos = dados.get("candidates") or []
        if not candidatos:
            raise GeminiIndisponivel(
                f"resposta sem candidatos: {dados.get('promptFeedback', dados)}"
            )

        primeiro = candidatos[0]
        motivo = primeiro.get("finishReason")
        partes = (primeiro.get("content") or {}).get("parts") or []
        # Nem toda parte tem texto: as da série 3 vêm com `thoughtSignature`
        # ao lado, e uma parte só de assinatura não contribui nada.
        texto = "".join(parte.get("text", "") for parte in partes)

        uso = dados.get("usageMetadata") or {}
        entrada = uso.get("promptTokenCount", 0)
        resposta = uso.get("candidatesTokenCount", 0)
        raciocinio = uso.get("thoughtsTokenCount", 0)

        if not texto:
            if motivo == "MAX_TOKENS":
                raise GeminiIndisponivel(
                    f"o orçamento acabou antes da resposta: {raciocinio} tokens "
                    "foram para o raciocínio. Aumente o max_tokens do agente"
                )
            # Sem texto e sem MAX_TOKENS é o filtro de segurança cortando.
            raise GeminiIndisponivel(f"resposta sem texto (finishReason={motivo})")

        if motivo == "MAX_TOKENS":
            # Há texto, mas cortado no meio da frase. Não é erro — devolver
            # meia resposta é melhor que nenhuma —, e sem aviso ninguém liga
            # o "atendente que fala pela metade" ao limite de tokens.
            logger.warning(
                f"⚠️ Resposta do Gemini truncada por maxOutputTokens "
                f"({raciocinio} tokens de raciocínio, {resposta} de resposta)"
            )

        # O raciocínio entra no total e é cobrado, então precisa entrar na
        # conta do limitador. Some-o à saída para que entrada + saída bata com
        # o total — senão o painel mostra três números que não fecham.
        return texto, {
            "input_tokens": entrada,
            "output_tokens": resposta + raciocinio,
            "total_tokens": uso.get("totalTokenCount", entrada + resposta + raciocinio),
        }
