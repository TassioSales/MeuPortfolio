from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from loguru import logger


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        f"Erro não tratado: {request.method} {request.url.path} "
        f"— {type(exc).__name__}: {exc}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor."},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning(
        f"HTTP {exc.status_code}: {request.method} {request.url.path} — {exc.detail}"
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
