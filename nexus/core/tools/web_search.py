from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger
from duckduckgo_search import DDGS


WEB_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Busca informações atuais na web via DuckDuckGo. Use para: notícias, "
            "dados em tempo real, preços, eventos recentes, documentação, qualquer "
            "info que precise de atualização."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Termos de busca (em português ou inglês)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Número de resultados (1-10, padrão: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}


def _sync_search(query: str, max_results: int) -> list[dict[str, Any]]:
    """Execução síncrona da busca DuckDuckGo."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return results


async def web_search(query: str, max_results: int = 5) -> str:
    """Busca na web via DuckDuckGo. Retorna resultados formatados em texto."""
    logger.debug(f"web_search | query={query!r} max_results={max_results}")
    try:
        loop = asyncio.get_event_loop()
        results: list[dict[str, Any]] = await loop.run_in_executor(
            None, _sync_search, query, max_results
        )
    except Exception as e:
        logger.error(f"web_search erro: {e}")
        return f"Erro na busca: {e}"

    if not results:
        return f"Nenhum resultado encontrado para: {query}"

    lines: list[str] = []
    for i, item in enumerate(results, start=1):
        title = item.get("title", "Sem título")
        url = item.get("href", "")
        body = item.get("body", "").strip()
        lines.append(f"{i}. [{title}]({url})")
        if body:
            lines.append(f"   {body}")
        lines.append("")

    return "\n".join(lines).rstrip()
