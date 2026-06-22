from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from loguru import logger


FETCH_URL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "fetch_url",
        "description": (
            "Busca o conteúdo de uma URL e extrai o texto limpo da página. "
            "Use para ler artigos, documentação, páginas de produto, conteúdo "
            "específico de um link encontrado em uma busca."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL completa a ser buscada (ex: https://exemplo.com/artigo)",
                }
            },
            "required": ["url"],
        },
    },
}

_MAX_TEXT_CHARS = 4000
_TIMEOUT_SECONDS = 20
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
# Tags removidas por não contribuírem com conteúdo útil
_NOISE_TAGS = [
    "script", "style", "nav", "footer", "header",
    "aside", "form", "noscript", "iframe", "ads",
    "advertisement", "banner", "cookie", "popup",
]


async def fetch_url(url: str) -> str:
    """Busca conteúdo de uma URL e extrai texto limpo."""
    logger.debug(f"fetch_url | url={url!r}")

    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
    except Exception as e:
        logger.error(f"fetch_url erro ao buscar {url!r}: {e}")
        return f"Erro ao buscar URL: {e}"

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # Remove tags de ruído
    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    # Extrai texto das tags mais relevantes, em ordem de prioridade
    main_content = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(id="main")
        or soup.find(class_="content")
        or soup.body
        or soup
    )

    raw_text = main_content.get_text(separator="\n", strip=True)

    # Limpa linhas em branco excessivas
    lines = [line.strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line]
    clean_text = "\n".join(lines)

    if len(clean_text) > _MAX_TEXT_CHARS:
        clean_text = clean_text[:_MAX_TEXT_CHARS] + f"\n\n... [truncado — {len(clean_text)} chars total]"

    return f"[Fonte: {url}]\n\n{clean_text}"
