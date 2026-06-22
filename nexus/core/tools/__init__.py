from __future__ import annotations

from collections.abc import Callable

from loguru import logger

from .web_search import web_search, WEB_SEARCH_SCHEMA
from .python_repl import python_repl, PYTHON_REPL_SCHEMA
from .file_ops import read_file, write_file, list_directory, READ_FILE_SCHEMA, WRITE_FILE_SCHEMA, LIST_DIR_SCHEMA
from .web_fetch import fetch_url, FETCH_URL_SCHEMA


# Lista de schemas JSON enviada ao Mistral para declarar as ferramentas disponíveis
TOOLS_SCHEMA: list[dict] = [
    WEB_SEARCH_SCHEMA,
    PYTHON_REPL_SCHEMA,
    READ_FILE_SCHEMA,
    WRITE_FILE_SCHEMA,
    LIST_DIR_SCHEMA,
    FETCH_URL_SCHEMA,
]

# Mapa nome → função async
TOOLS_MAP: dict[str, Callable] = {
    "web_search": web_search,
    "python_repl": python_repl,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "fetch_url": fetch_url,
}


async def execute_tool(name: str, args: dict) -> str:
    """Executa uma ferramenta pelo nome. Retorna string com resultado."""
    if name not in TOOLS_MAP:
        available = ", ".join(TOOLS_MAP.keys())
        logger.warning(f"execute_tool: ferramenta desconhecida '{name}' (disponíveis: {available})")
        return f"Erro: ferramenta '{name}' não encontrada. Disponíveis: {available}"

    logger.info(f"execute_tool | tool={name} args={list(args.keys())}")
    try:
        result: str = await TOOLS_MAP[name](**args)
        logger.debug(f"execute_tool | {name} retornou {len(result)} chars")
        return result
    except TypeError as e:
        logger.error(f"execute_tool | argumentos inválidos para '{name}': {e}")
        return f"Erro: argumentos inválidos para '{name}': {e}"
    except Exception as e:
        logger.error(f"execute_tool | erro em '{name}': {e}")
        return f"Erro ao executar '{name}': {e}"


__all__ = [
    "TOOLS_SCHEMA",
    "TOOLS_MAP",
    "execute_tool",
    # ferramentas individuais (re-exportadas para conveniência)
    "web_search",
    "python_repl",
    "read_file",
    "write_file",
    "list_directory",
    "fetch_url",
]
