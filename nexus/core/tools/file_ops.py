from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger


WORKSPACE = Path.home() / "nexus_workspace"

# Garante que o workspace exista quando o módulo é carregado
WORKSPACE.mkdir(parents=True, exist_ok=True)

_MAX_READ_CHARS = 5000
_MAX_LIST_ITEMS = 50

# ─── Schemas ──────────────────────────────────────────────────────────────────

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": (
            "Lê o conteúdo de um arquivo no workspace do Nexus (~/ nexus_workspace/). "
            "Use para inspecionar arquivos gerados, ler dados, verificar código salvo."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Caminho relativo ao workspace (ex: 'dados.csv', 'scripts/calc.py')",
                }
            },
            "required": ["path"],
        },
    },
}

WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": (
            "Salva conteúdo em um arquivo no workspace do Nexus (~/ nexus_workspace/). "
            "Cria diretórios intermediários automaticamente. Use para persistir "
            "resultados, código gerado, relatórios, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Caminho relativo ao workspace (ex: 'resultado.txt')",
                },
                "content": {
                    "type": "string",
                    "description": "Conteúdo a ser escrito no arquivo",
                },
            },
            "required": ["path", "content"],
        },
    },
}

LIST_DIR_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_directory",
        "description": (
            "Lista o conteúdo de um diretório dentro do workspace do Nexus. "
            "Use para ver arquivos disponíveis, explorar estrutura de pastas."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Caminho relativo ao workspace (padrão: '.' para raiz)",
                    "default": ".",
                }
            },
            "required": [],
        },
    },
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _resolve(relative: str) -> Path:
    """Resolve um caminho relativo dentro do WORKSPACE (sem path traversal)."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    target = (WORKSPACE / relative).resolve()
    # Bloqueia path traversal para fora do workspace
    target.relative_to(WORKSPACE.resolve())  # levanta ValueError se sair
    return target


def _format_size(n_bytes: int) -> str:
    if n_bytes < 1024:
        return f"{n_bytes} B"
    kb = n_bytes / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    return f"{kb / 1024:.1f} MB"


def _build_tree(directory: Path, prefix: str = "", depth: int = 0, counter: list[int] | None = None) -> list[str]:
    """Constrói linhas de árvore de forma recursiva."""
    if counter is None:
        counter = [0]

    lines: list[str] = []
    try:
        entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return [f"{prefix}[sem permissão]"]

    total = len(entries)
    for idx, entry in enumerate(entries):
        if counter[0] >= _MAX_LIST_ITEMS:
            lines.append(f"{prefix}... [limite de {_MAX_LIST_ITEMS} itens atingido]")
            break
        connector = "└── " if idx == total - 1 else "├── "
        if entry.is_dir():
            lines.append(f"{prefix}{connector}📁 {entry.name}/")
            counter[0] += 1
            extension = "    " if idx == total - 1 else "│   "
            lines.extend(_build_tree(entry, prefix + extension, depth + 1, counter))
        else:
            size_str = _format_size(entry.stat().st_size)
            lines.append(f"{prefix}{connector}📄 {entry.name}  ({size_str})")
            counter[0] += 1

    return lines


# ─── Funções públicas ─────────────────────────────────────────────────────────

async def read_file(path: str) -> str:
    """Lê arquivo relativo ao WORKSPACE. Retorna conteúdo (máx 5000 chars)."""
    logger.debug(f"read_file | path={path!r}")

    def _read() -> str:
        target = _resolve(path)
        content = target.read_text(encoding="utf-8", errors="replace")
        total = len(content)
        if total > _MAX_READ_CHARS:
            truncated = content[:_MAX_READ_CHARS]
            return truncated + f"\n\n... [truncado: exibindo {_MAX_READ_CHARS} de {total} chars]"
        return content

    try:
        return await asyncio.get_event_loop().run_in_executor(None, _read)
    except ValueError:
        return "Erro: caminho fora do workspace não é permitido"
    except Exception as e:
        logger.error(f"read_file erro: {e}")
        return f"Erro: {e}"


async def write_file(path: str, content: str) -> str:
    """Salva arquivo no WORKSPACE (cria dirs intermediários)."""
    logger.debug(f"write_file | path={path!r} content_len={len(content)}")

    def _write() -> str:
        target = _resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        n_bytes = target.stat().st_size
        return f"✓ Arquivo salvo: {path} ({n_bytes} bytes)"

    try:
        return await asyncio.get_event_loop().run_in_executor(None, _write)
    except ValueError:
        return "Erro: caminho fora do workspace não é permitido"
    except Exception as e:
        logger.error(f"write_file erro: {e}")
        return f"Erro: {e}"


async def list_directory(path: str = ".") -> str:
    """Lista WORKSPACE/{path} formatado como árvore simples."""
    logger.debug(f"list_directory | path={path!r}")

    def _list() -> str:
        target = _resolve(path)
        if not target.exists():
            return f"Erro: diretório não encontrado: {path}"
        if not target.is_dir():
            return f"Erro: '{path}' não é um diretório"

        # Cabeçalho
        rel = target.relative_to(WORKSPACE.parent)
        header = f"📁 {rel}/"
        lines = _build_tree(target)

        if not lines:
            return "Diretório vazio."

        return header + "\n" + "\n".join(lines)

    try:
        return await asyncio.get_event_loop().run_in_executor(None, _list)
    except ValueError:
        return "Erro: caminho fora do workspace não é permitido"
    except Exception as e:
        logger.error(f"list_directory erro: {e}")
        return f"Erro: {e}"
