from __future__ import annotations

import asyncio
import sys
from asyncio.subprocess import PIPE

from loguru import logger


PYTHON_REPL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "python_repl",
        "description": (
            "Executa código Python e retorna o resultado. Use para: cálculos "
            "matemáticos, análise de dados, geração de gráficos, manipulação de "
            "strings, qualquer computação."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Código Python válido para executar",
                }
            },
            "required": ["code"],
        },
    },
}

# Preâmbulo injetado antes de todo código executado
_PREAMBLE = """\
import sys, os
os.chdir(os.path.expanduser("~/nexus_workspace"))
"""

_TIMEOUT_SECONDS = 15
_MAX_STDOUT = 3000
_MAX_STDERR = 1000


async def python_repl(code: str) -> str:
    """Executa código Python em subprocesso isolado. Retorna stdout/stderr."""
    logger.debug(f"python_repl | {len(code)} chars de código")

    full_code = _PREAMBLE + code

    process: asyncio.subprocess.Process | None = None
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            full_code,
            stdout=PIPE,
            stderr=PIPE,
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(),
            timeout=_TIMEOUT_SECONDS,
        )

    except asyncio.TimeoutError:
        if process is not None:
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass
        logger.warning("python_repl timeout")
        return "[Timeout] Execução excedeu 15 segundos"

    except Exception as e:
        logger.error(f"python_repl erro inesperado: {e}")
        return f"[Erro] {e}"

    if process.returncode == 0:
        stdout = stdout_bytes.decode(errors="replace")
        if len(stdout) > _MAX_STDOUT:
            stdout = stdout[:_MAX_STDOUT] + f"\n... [truncado — {len(stdout)} chars total]"
        return stdout if stdout else "(sem saída)"
    else:
        stderr = stderr_bytes.decode(errors="replace")
        if len(stderr) > _MAX_STDERR:
            stderr = stderr[:_MAX_STDERR] + "\n... [truncado]"
        return f"[Erro]\n{stderr}"
