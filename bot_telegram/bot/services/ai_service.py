import httpx
from loguru import logger

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL = "mistral-large-latest"
REQUEST_TIMEOUT = 30.0


async def perguntar(pergunta: str, contexto: str = "", api_key: str = "") -> str:
    """Call Mistral AI with an optional context string about user data.

    Args:
        pergunta: The user's question or prompt.
        contexto: Optional data context (expenses, notes) injected into the system message.
        api_key: Mistral API key.

    Returns:
        The AI's text response, or a friendly error message.
    """
    if not api_key:
        return "⚠️ Chave da API Mistral não configurada. Configure MISTRAL_API_KEY no arquivo .env"

    system_prompt = (
        "Você é um assistente financeiro pessoal prestativo que responde em português do Brasil. "
        "Seja direto, objetivo e use formatação clara com bullet points quando adequado. "
        "Quando tiver dados do usuário disponíveis, use-os para personalizar sua resposta."
    )

    if contexto:
        system_prompt += f"\n\nDados atuais do usuário:\n{contexto}"

    payload = {
        "model": MISTRAL_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pergunta},
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(MISTRAL_URL, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()
        resposta: str = data["choices"][0]["message"]["content"]
        logger.debug(f"Resposta Mistral recebida ({len(resposta)} chars)")
        return resposta

    except httpx.TimeoutException:
        logger.error("Timeout na chamada à API Mistral")
        return "⏱️ A IA demorou muito para responder. Tente novamente em alguns instantes."

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        logger.error(f"Erro HTTP {status} na API Mistral: {e}")
        if status == 401:
            return "🔑 Chave da API Mistral inválida. Verifique MISTRAL_API_KEY no .env"
        if status == 429:
            return "⚠️ Limite de requisições atingido. Aguarde um momento e tente novamente."
        return f"❌ Erro na API Mistral (HTTP {status}). Tente novamente mais tarde."

    except httpx.RequestError as e:
        logger.error(f"Erro de conexão com a API Mistral: {e}")
        return "🌐 Erro de conexão com a IA. Verifique sua internet e tente novamente."

    except (KeyError, IndexError) as e:
        logger.error(f"Resposta inesperada da API Mistral: {e}")
        return "❌ Resposta inesperada da IA. Tente novamente mais tarde."
