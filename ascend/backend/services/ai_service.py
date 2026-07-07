import asyncio
import json
from functools import lru_cache
from typing import AsyncGenerator

import httpx
from loguru import logger

from core.config import settings

# gemini-2.5-flash primeiro — é o que tem quota disponível no free tier
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

# Circuit breaker: set to True on 401/403 so we stop hitting Mistral every request
_mistral_auth_failed = False


@lru_cache(maxsize=1)
def _build_gemini():
    if not settings.GEMINI_API_KEY:
        return None
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai


def _is_auth_error(msg: str) -> bool:
    return "401" in msg or "403" in msg or "Unauthorized" in msg.lower() or "Forbidden" in msg.lower()


class AIService:
    @property
    def genai(self):
        return _build_gemini()

    # ------------------------------------------------------------------
    # Streaming público
    # ------------------------------------------------------------------
    async def stream_chat(
        self, messages: list[dict], user_context: dict
    ) -> AsyncGenerator[str, None]:
        global _mistral_auth_failed
        system_prompt = self._build_coach_prompt(user_context)
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        if settings.MISTRAL_API_KEY and not _mistral_auth_failed:
            try:
                async for token in self._mistral_stream_http(full_messages):
                    yield token
                return
            except Exception as e:
                err = str(e)
                if _is_auth_error(err):
                    _mistral_auth_failed = True
                    logger.error("Mistral API key inválida (401) — usando Gemini para todas as requisições.")
                else:
                    logger.warning(f"Mistral falhou: {e}, tentando Gemini...")

        if self.genai:
            async for token in self._gemini_stream_with_fallback(full_messages):
                yield token
            return

        yield "Configure MISTRAL_API_KEY ou GEMINI_API_KEY no .env para ativar o coach."

    # ------------------------------------------------------------------
    # Mistral — httpx direto (contorna bug do SDK com stream+erros)
    # ------------------------------------------------------------------
    async def _mistral_stream_http(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        body = {
            "model": "mistral-large-latest",
            "messages": messages,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=60, write=10, pool=5)) as client:
            async with client.stream("POST", MISTRAL_URL, headers=headers, json=body) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise RuntimeError(
                        f"Mistral HTTP {response.status_code}: {error_body.decode()[:200]}"
                    )
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue

    # ------------------------------------------------------------------
    # Gemini com fallback entre modelos
    # ------------------------------------------------------------------
    async def _gemini_stream_with_fallback(
        self, messages: list[dict]
    ) -> AsyncGenerator[str, None]:
        prompt = self._messages_to_prompt(messages)
        last_error = None

        for model_name in GEMINI_MODELS:
            try:
                model = self.genai.GenerativeModel(model_name)
                response = await model.generate_content_async(prompt, stream=True)
                async for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                error_str = str(e)
                last_error = e
                if "429" in error_str or "quota" in error_str.lower():
                    logger.warning(f"Gemini {model_name} quota atingida, tentando próximo...")
                    await asyncio.sleep(2)
                    continue
                elif "404" in error_str or "not found" in error_str.lower():
                    logger.warning(f"Gemini {model_name} indisponível, tentando próximo...")
                    continue
                else:
                    logger.error(f"Gemini {model_name} erro inesperado: {e}")
                    break

        logger.error(f"Todos os modelos Gemini falharam: {last_error}")
        yield "Serviço de IA temporariamente indisponível. Tente novamente em instantes."

    # ------------------------------------------------------------------
    # Geração de texto (não-streaming) — para roadmap etc.
    # ------------------------------------------------------------------
    async def generate_text(self, prompt: str) -> str:
        global _mistral_auth_failed
        if settings.MISTRAL_API_KEY and not _mistral_auth_failed:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        MISTRAL_URL,
                        headers={
                            "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "mistral-large-latest",
                            "messages": [{"role": "user", "content": prompt}],
                            "stream": False,
                        },
                    )
                    if resp.status_code == 200:
                        return resp.json()["choices"][0]["message"]["content"] or ""
                    if resp.status_code in (401, 403):
                        _mistral_auth_failed = True
                        logger.error("Mistral API key inválida (401) — usando Gemini.")
                    else:
                        logger.warning(f"Mistral generate_text HTTP {resp.status_code}")
            except Exception as e:
                logger.warning(f"Mistral generate_text falhou: {e}")

        if self.genai:
            for model_name in GEMINI_MODELS:
                try:
                    model = self.genai.GenerativeModel(model_name)
                    resp = await model.generate_content_async(prompt)
                    return resp.text
                except Exception as e:
                    err = str(e)
                    if "429" in err or "quota" in err.lower():
                        await asyncio.sleep(3)
                        continue
                    elif "404" in err or "not found" in err.lower():
                        continue
                    logger.error(f"Gemini {model_name} generate_text falhou: {e}")
                    break

        return ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _messages_to_prompt(self, messages: list[dict]) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        turns = "\n".join(
            f"{'Usuário' if m['role'] == 'user' else 'Assistente'}: {m['content']}"
            for m in messages if m["role"] != "system"
        )
        return f"{system}\n\n{turns}" if system else turns

    def _build_coach_prompt(self, ctx: dict) -> str:
        return (
            f"Você é o Trilha, um coach de carreira AI especializado em desenvolvimento técnico.\n"
            f"Usuário: {ctx['name']} | Cargo atual: {ctx['current_role']} → Meta: {ctx['target_role']}\n"
            f"Progresso: {ctx['progress_pct']:.0f}% do roadmap concluído.\n"
            f"Próximo milestone: {ctx['next_milestone']}.\n"
            f"Skills conhecidas: {', '.join(ctx['known_skills']) or 'não informadas'}.\n"
            f"Responda em português brasileiro. Seja direto e motivador."
        )


ai_service = AIService()
