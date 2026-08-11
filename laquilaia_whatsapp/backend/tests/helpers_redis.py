"""
Acesso ao Redis nos testes.

Os testes de limite de uso precisam do Redis de verdade: um mock provaria
apenas que o código chama os comandos que o próprio teste espera, e não que a
janela deslizante em sorted set conta certo. Quando o Redis não está no ar, os
casos que dependem dele são pulados explicitamente.
"""

from contextlib import asynccontextmanager

import redis.asyncio as redis

from app.config import settings

# Banco separado do de desenvolvimento: os testes apagam tudo o que encontram.
TEST_DB = 15


def _url() -> str:
    base = settings.redis_url.rstrip("/")
    # Descarta o número de banco que já venha na URL, para não montar
    # `redis://host:6379/0/15`.
    partes = base.split("/")
    if len(partes) > 3 and partes[-1].isdigit():
        base = "/".join(partes[:-1])
    return f"{base}/{TEST_DB}"


async def redis_disponivel() -> bool:
    try:
        client = redis.from_url(_url())
        await client.ping()
        await client.close()
        return True
    except Exception:
        return False


@asynccontextmanager
async def redis_para_teste():
    """Cliente num banco limpo, esvaziado na entrada e na saída."""
    client = redis.from_url(_url())
    try:
        await client.flushdb()
        yield client
    finally:
        try:
            await client.flushdb()
        finally:
            # `close()`, não `aclose()`: o segundo só existe a partir do
            # redis-py 5.0.1 e aqui a versão presa é a 5.0.0. Com `aclose()`
            # o AttributeError era engolido e os testes de Redis pulavam em
            # silêncio, como se o serviço estivesse fora.
            await client.close()
