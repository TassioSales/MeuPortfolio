"""
Limite de uso do Claude por conta, compartilhado entre réplicas.

A janela é deslizante de 60 segundos, contada em duas dimensões: chamadas e
tokens. Cada conta tem o seu balde — o uso de um cliente não consome a cota
de outro.

O estado vive no **Redis**, e não no processo: com mais de uma réplica do
backend, contadores em memória dão a cada uma o seu próprio balde e o limite
efetivo vira `N × limite`. Se o Redis não estiver disponível, o limitador cai
para a memória do processo, que é justamente esse comportamento degradado —
preferível tanto a recusar todas as chamadas quanto a deixá-las passar sem
medição nenhuma.

**Precisão.** `check` (antes da chamada) e `track` (depois, quando o total de
tokens finalmente é conhecido) são operações separadas, então duas requisições
simultâneas podem passar pela verificação antes de qualquer uma registrar o
seu uso, e a janela estoura um pouco. Não dá para reservar antecipadamente o
que ainda não se sabe quanto vai custar; o objetivo aqui é conter o uso, não
cravar o teto no token exato.
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple
from uuid import uuid4

from app.utils.exceptions import ValidationException
from app.utils.logger import logger

# Janela do limite.
WINDOW_SECONDS = 60

# Por quanto tempo as entradas ficam guardadas. Maior que a janela para o
# corte por score nunca depender do TTL ter rodado antes.
RETENTION_SECONDS = 120


class MemoryRateLimitBackend:
    """Contadores no processo. Usado como reserva quando o Redis falha."""

    def __init__(self) -> None:
        # (timestamp, tokens) por balde.
        self._entries: Dict[str, List[Tuple[float, int]]] = defaultdict(list)

    async def add(self, bucket: str, tokens: int) -> None:
        now = time.time()
        self._entries[bucket].append((now, tokens))
        cutoff = now - RETENTION_SECONDS
        self._entries[bucket] = [e for e in self._entries[bucket] if e[0] > cutoff]

    async def counts(self, bucket: str) -> Tuple[int, int]:
        cutoff = time.time() - WINDOW_SECONDS
        recentes = [e for e in self._entries[bucket] if e[0] > cutoff]
        return len(recentes), sum(tokens for _, tokens in recentes)


class RedisRateLimitBackend:
    """
    Contadores no Redis, em dois sorted sets por balde.

    O score é o instante da chamada, o que torna o corte da janela um
    `ZREMRANGEBYSCORE` — sem varrer o conjunto inteiro. O total de tokens vai
    no próprio membro (`"<tokens>:<uuid>"`), já que sorted set ordena por
    score mas não soma valores; o uuid só garante que duas chamadas iguais no
    mesmo instante não colapsem em um membro só.
    """

    def __init__(self, client_provider) -> None:
        # Recebe uma função, e não o cliente: no boot o `redis_client.redis`
        # ainda é None, e guardar o valor aqui congelaria esse None.
        self._client_provider = client_provider

    def _keys(self, bucket: str) -> Tuple[str, str]:
        return f"ratelimit:calls:{bucket}", f"ratelimit:tokens:{bucket}"

    async def add(self, bucket: str, tokens: int) -> None:
        client = self._client_provider()
        if client is None:
            raise ConnectionError("Redis indisponível")

        calls_key, tokens_key = self._keys(bucket)
        now = time.time()
        marca = uuid4().hex
        cutoff = now - RETENTION_SECONDS

        pipe = client.pipeline(transaction=True)
        pipe.zadd(calls_key, {marca: now})
        pipe.zadd(tokens_key, {f"{tokens}:{marca}": now})
        pipe.zremrangebyscore(calls_key, 0, cutoff)
        pipe.zremrangebyscore(tokens_key, 0, cutoff)
        # O TTL evita que a conta de um cliente que sumiu fique ocupando
        # memória para sempre.
        pipe.expire(calls_key, RETENTION_SECONDS)
        pipe.expire(tokens_key, RETENTION_SECONDS)
        await pipe.execute()

    async def counts(self, bucket: str) -> Tuple[int, int]:
        client = self._client_provider()
        if client is None:
            raise ConnectionError("Redis indisponível")

        calls_key, tokens_key = self._keys(bucket)
        cutoff = time.time() - WINDOW_SECONDS

        pipe = client.pipeline(transaction=True)
        pipe.zcount(calls_key, cutoff, "+inf")
        pipe.zrangebyscore(tokens_key, cutoff, "+inf")
        chamadas, membros = await pipe.execute()

        return int(chamadas or 0), sum(_tokens_do_membro(m) for m in membros or [])


def _tokens_do_membro(membro) -> int:
    """
    Extrai o total de tokens de um membro `"<tokens>:<uuid>"`.

    O cliente devolve bytes quando não está em `decode_responses`, e os outros
    usuários do `redis_client` dependem do modo atual — por isso a conversão
    fica aqui, e não numa mudança global de configuração.
    """
    if isinstance(membro, bytes):
        membro = membro.decode()
    try:
        return int(str(membro).split(":", 1)[0])
    except (ValueError, IndexError):
        # Membro fora do formato não deve derrubar a contagem inteira.
        logger.warning(f"⚠️ Membro de rate limit ignorado: {membro!r}")
        return 0


class RateLimiter:
    """Janela deslizante por conta, no Redis com reserva em memória."""

    def __init__(
        self,
        max_calls_per_minute: int,
        max_tokens_per_minute: int,
        redis_backend=None,
        memory_backend=None,
    ) -> None:
        self.max_calls_per_minute = max_calls_per_minute
        self.max_tokens_per_minute = max_tokens_per_minute
        self._memory = memory_backend or MemoryRateLimitBackend()
        self._redis = redis_backend
        if self._redis is None:
            from app.db.redis_client import redis_client

            self._redis = RedisRateLimitBackend(lambda: redis_client.redis)

    async def _executar(self, operacao: str, *args):
        """
        Roda a operação no Redis e, se ele falhar, na memória.

        A queda é por chamada, não definitiva: o cliente do redis-py reconecta
        sozinho, então uma instabilidade momentânea não condena o processo a
        contar em memória até reiniciar.
        """
        try:
            return await getattr(self._redis, operacao)(*args)
        except Exception as e:
            logger.warning(
                f"⚠️ Rate limit sem Redis, contando só neste processo ({e}). "
                "Com mais de uma réplica o limite efetivo fica maior."
            )
            return await getattr(self._memory, operacao)(*args)

    async def check(self, bucket: str) -> None:
        """Recusa a chamada se a conta já estourou a janela."""
        chamadas, tokens = await self._executar("counts", bucket)

        if chamadas >= self.max_calls_per_minute:
            raise ValidationException(
                f"Rate limit exceeded: {self.max_calls_per_minute} calls per minute"
            )

        if tokens >= self.max_tokens_per_minute:
            raise ValidationException(
                f"Rate limit exceeded: {self.max_tokens_per_minute} tokens per minute"
            )

    async def track(self, bucket: str, tokens: int) -> None:
        """Registra uma chamada concluída e o que ela custou."""
        await self._executar("add", bucket, tokens)

    async def status(self, bucket: str) -> dict:
        chamadas, tokens = await self._executar("counts", bucket)
        return {
            "calls_used": chamadas,
            "calls_limit": self.max_calls_per_minute,
            "tokens_used": tokens,
            "tokens_limit": self.max_tokens_per_minute,
            "calls_remaining": max(0, self.max_calls_per_minute - chamadas),
            "tokens_remaining": max(0, self.max_tokens_per_minute - tokens),
        }
