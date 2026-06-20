"""AI-powered narrative insights via Mistral AI."""
from __future__ import annotations

import os

import requests
from loguru import logger

_MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
_MODEL = "mistral-small-latest"


def _call_mistral(prompt: str, api_key: str) -> str:
    resp = requests.post(
        _MISTRAL_URL,
        json={
            "model": _MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 350,
        },
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _api_key() -> str:
    return os.getenv("MISTRAL_API_KEY", "")


def profile_insight(
    predicted_score: float,
    school: str,
    income: str,
    region: str,
    race: str,
    percentile: float,
) -> str:
    key = _api_key()
    if key:
        prompt = (
            "Você é especialista em educação brasileira. Analise este perfil ENEM e escreva "
            "3 frases: desempenho esperado, influência socioeconômica e uma dica prática. "
            f"Nota prevista: {predicted_score:.0f} pts (percentil {percentile:.0f}%). "
            f"Escola: {school}. Renda: {income}. Região: {region}. Raça: {race}. "
            "Responda em português do Brasil, sem markdown."
        )
        try:
            return _call_mistral(prompt, key)
        except Exception as e:
            logger.warning(f"Mistral error: {e}")

    level = (
        "excelente" if predicted_score >= 750
        else "muito bom" if predicted_score >= 650
        else "bom" if predicted_score >= 550
        else "abaixo da média nacional"
    )
    tip = (
        "Redação e Matemática concentram o maior impacto na média final — priorizá-las costuma "
        "elevar a nota em 30 a 50 pontos."
    )
    return (
        f"Com nota prevista de {predicted_score:.0f} pontos (nível {level}), o candidato está "
        f"no {percentile:.0f}º percentil nacional. "
        f"O perfil de escola {school.lower()} com renda '{income}' é consistente com este resultado — "
        "estudantes de escola privada e renda mais alta tendem a pontuar 80-120 pts acima da média pública. "
        + tip
    )


def overview_insight(mean_score: float, top_region: str, gap_school: float) -> str:
    key = _api_key()
    if key:
        prompt = (
            "Analista de dados educacionais brasileiro. Gere 2 frases sobre: "
            f"média geral {mean_score:.1f} pts, melhor região '{top_region}', "
            f"diferença público-privado {gap_school:.1f} pts. "
            "Factual, sem markdown, em português do Brasil."
        )
        try:
            return _call_mistral(prompt, key)
        except Exception as e:
            logger.warning(f"Mistral error: {e}")

    return (
        f"A média geral do período analisado é de **{mean_score:.1f} pontos**, com destaque para a "
        f"região **{top_region}**, que lidera o desempenho nacional. "
        f"A diferença de **{gap_school:.1f} pontos** entre escolas públicas e privadas evidencia "
        "a persistente desigualdade educacional no Brasil."
    )
