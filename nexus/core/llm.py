"""Mistral AI client for Nexus agent."""
from __future__ import annotations

import os

import requests
from loguru import logger


class MistralClient:
    """Thin client for the Mistral AI chat completions API."""

    _API_URL = "https://api.mistral.ai/v1/chat/completions"

    def __init__(self) -> None:
        self._api_key: str | None = os.environ.get("MISTRAL_API_KEY")
        self._model: str = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")

        if not self._api_key:
            logger.warning(
                "MISTRAL_API_KEY não está configurada. "
                "Defina a variável de ambiente antes de usar o cliente."
            )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def is_configured(self) -> bool:
        """Return True if the API key is present."""
        return bool(self._api_key)

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict:
        """Send a chat completion request and return the raw response dict.

        Args:
            messages: List of message dicts in Mistral API format.
            tools: Optional list of tool definitions. When provided,
                   ``tool_choice`` is set to ``"auto"``.

        Returns:
            The parsed JSON response from the API.

        Raises:
            ValueError: If the API key is not configured.
            requests.HTTPError: If the API returns a non-2xx status.
        """
        if not self._api_key:
            raise ValueError(
                "MISTRAL_API_KEY não está configurada. "
                "Defina a variável de ambiente MISTRAL_API_KEY."
            )

        payload: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.1,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        logger.debug(
            "Enviando requisição para Mistral | model={} | mensagens={}",
            self._model,
            len(messages),
        )

        response = requests.post(
            self._API_URL,
            json=payload,
            headers=headers,
            timeout=60,
        )

        response.raise_for_status()
        result: dict = response.json()

        finish_reason = (
            result.get("choices", [{}])[0].get("finish_reason", "unknown")
        )
        logger.debug(
            "Resposta recebida | finish_reason={} | tokens={}",
            finish_reason,
            result.get("usage", {}).get("total_tokens", "?"),
        )

        return result
