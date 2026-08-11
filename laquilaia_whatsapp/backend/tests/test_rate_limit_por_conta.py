"""
O limite de uso é por conta, não do processo nem da réplica.

Antes havia contadores únicos no LLMService: um usuário sozinho esgotava a
cota de todos os outros, e bastava um agente movimentado para o serviço
recusar as chamadas de qualquer outro cliente.

Depois os contadores passaram a ser por conta, mas ainda viviam na memória do
processo — com mais de uma réplica cada uma tinha o seu balde e o limite
efetivo virava `N × limite`. Agora o estado é do Redis.

Cada caso roda nos dois backends: o de memória (a reserva usada quando o
Redis cai) e o do Redis, que é o que vale em produção. Sem Redis disponível,
os casos do Redis são pulados — e a suíte diz isso em vez de fingir cobertura.
"""

import pytest

from app.services.llm_service import LLMService
from app.services.rate_limiter import (
    MemoryRateLimitBackend,
    RateLimiter,
    RedisRateLimitBackend,
)
from app.utils.exceptions import ValidationException

from tests.helpers_redis import redis_disponivel, redis_para_teste


@pytest.fixture(params=["memoria", "redis"])
async def limiter_factory(request):
    """Devolve uma fábrica de RateLimiter para o backend do parâmetro."""
    if request.param == "memoria":

        def fabricar(**limites):
            return RateLimiter(
                **limites,
                redis_backend=_BackendQuebrado(),
                memory_backend=MemoryRateLimitBackend(),
            )

        yield fabricar
        return

    if not await redis_disponivel():
        pytest.skip("Redis não disponível — caso do backend Redis pulado")

    async with redis_para_teste() as client:

        def fabricar(**limites):
            return RateLimiter(**limites, redis_backend=RedisRateLimitBackend(lambda: client))

        yield fabricar


class _BackendQuebrado:
    """
    Backend que sempre falha, para forçar a queda para a memória.

    Sem ele o caso "memória" ainda tentaria o Redis real primeiro e o teste
    não diria em qual implementação a garantia foi verificada.
    """

    async def add(self, *args):
        raise ConnectionError("sem Redis")

    async def counts(self, *args):
        raise ConnectionError("sem Redis")


class TestBucketsPorConta:
    async def test_uso_de_um_usuario_nao_conta_para_outro(self, limiter_factory):
        limiter = limiter_factory(max_calls_per_minute=60, max_tokens_per_minute=40000)

        await limiter.track("user-a", 100)
        await limiter.track("user-a", 100)

        assert (await limiter.status("user-a"))["calls_used"] == 2
        assert (await limiter.status("user-b"))["calls_used"] == 0

    async def test_limite_estourado_por_um_nao_bloqueia_o_outro(self, limiter_factory):
        limiter = limiter_factory(max_calls_per_minute=2, max_tokens_per_minute=40000)

        await limiter.track("user-a", 10)
        await limiter.track("user-a", 10)

        with pytest.raises(ValidationException):
            await limiter.check("user-a")

        # O ponto da mudança: o segundo usuário segue atendido.
        await limiter.check("user-b")

    async def test_tokens_tambem_sao_contados_por_conta(self, limiter_factory):
        limiter = limiter_factory(max_calls_per_minute=60, max_tokens_per_minute=1000)

        await limiter.track("user-a", 900)
        await limiter.track("user-a", 200)

        with pytest.raises(ValidationException):
            await limiter.check("user-a")

        assert (await limiter.status("user-b"))["tokens_used"] == 0

    async def test_status_reporta_o_restante_da_conta(self, limiter_factory):
        limiter = limiter_factory(max_calls_per_minute=10, max_tokens_per_minute=40000)

        await limiter.track("user-a", 10)

        status = await limiter.status("user-a")
        assert status["calls_remaining"] == 9
        assert status["tokens_used"] == 10

    async def test_chamadas_iguais_no_mesmo_instante_contam_separado(
        self, limiter_factory
    ):
        """
        Duas chamadas idênticas não podem colapsar numa só.

        No Redis os registros são membros de um sorted set; sem um
        desambiguador, dois usos iguais no mesmo instante seriam o mesmo
        membro e o segundo sobrescreveria o primeiro em silêncio.
        """
        limiter = limiter_factory(max_calls_per_minute=60, max_tokens_per_minute=40000)

        await limiter.track("user-a", 100)
        await limiter.track("user-a", 100)
        await limiter.track("user-a", 100)

        status = await limiter.status("user-a")
        assert status["calls_used"] == 3
        assert status["tokens_used"] == 300


class TestCompartilhadoEntreReplicas:
    """A razão de ser da mudança: duas réplicas, um balde só."""

    async def test_duas_instancias_dividem_o_mesmo_balde(self):
        if not await redis_disponivel():
            pytest.skip("Redis não disponível")

        async with redis_para_teste() as client:
            # Duas instâncias distintas do limitador, como duas réplicas do
            # backend: objetos diferentes, nenhum estado em comum na memória.
            replica_1 = RateLimiter(
                max_calls_per_minute=3,
                max_tokens_per_minute=40000,
                redis_backend=RedisRateLimitBackend(lambda: client),
            )
            replica_2 = RateLimiter(
                max_calls_per_minute=3,
                max_tokens_per_minute=40000,
                redis_backend=RedisRateLimitBackend(lambda: client),
            )

            await replica_1.track("user-a", 10)
            await replica_1.track("user-a", 10)

            # A segunda réplica enxerga o uso feito pela primeira.
            assert (await replica_2.status("user-a"))["calls_used"] == 2

            await replica_2.track("user-a", 10)

            # E o limite estoura para as duas, não para cada uma na sua vez.
            with pytest.raises(ValidationException):
                await replica_1.check("user-a")
            with pytest.raises(ValidationException):
                await replica_2.check("user-a")

    async def test_tokens_somam_entre_replicas(self):
        if not await redis_disponivel():
            pytest.skip("Redis não disponível")

        async with redis_para_teste() as client:
            replica_1 = RateLimiter(
                max_calls_per_minute=60,
                max_tokens_per_minute=1000,
                redis_backend=RedisRateLimitBackend(lambda: client),
            )
            replica_2 = RateLimiter(
                max_calls_per_minute=60,
                max_tokens_per_minute=1000,
                redis_backend=RedisRateLimitBackend(lambda: client),
            )

            await replica_1.track("user-a", 600)
            await replica_2.track("user-a", 500)

            with pytest.raises(ValidationException):
                await replica_1.check("user-a")


class TestQuedaParaMemoria:
    """Redis fora não pode derrubar o serviço nem liberar tudo sem medição."""

    async def test_sem_redis_o_limite_continua_valendo_no_processo(self):
        limiter = RateLimiter(
            max_calls_per_minute=2,
            max_tokens_per_minute=40000,
            redis_backend=_BackendQuebrado(),
        )

        await limiter.track("user-a", 10)
        await limiter.track("user-a", 10)

        with pytest.raises(ValidationException):
            await limiter.check("user-a")

    async def test_sem_redis_o_status_ainda_responde(self):
        limiter = RateLimiter(
            max_calls_per_minute=60,
            max_tokens_per_minute=40000,
            redis_backend=_BackendQuebrado(),
        )

        await limiter.track("user-a", 42)

        status = await limiter.status("user-a")
        assert status["calls_used"] == 1
        assert status["tokens_used"] == 42


class TestIntegracaoComLLMService:
    async def test_o_servico_usa_o_balde_da_conta(self):
        service = LLMService()
        service.rate_limiter = RateLimiter(
            max_calls_per_minute=60,
            max_tokens_per_minute=40000,
            redis_backend=_BackendQuebrado(),
        )

        await service._track_usage(100, "user-a")

        assert (await service.get_rate_limit_status("user-a"))["calls_used"] == 1
        assert (await service.get_rate_limit_status("user-b"))["calls_used"] == 0

    async def test_sem_usuario_usa_o_balde_compartilhado(self):
        service = LLMService()
        service.rate_limiter = RateLimiter(
            max_calls_per_minute=60,
            max_tokens_per_minute=40000,
            redis_backend=_BackendQuebrado(),
        )

        await service._track_usage(50)

        assert (await service.get_rate_limit_status())["calls_used"] == 1
        # Não vaza para a conta de ninguém.
        assert (await service.get_rate_limit_status("user-a"))["calls_used"] == 0

    async def test_limites_vem_da_configuracao(self):
        """
        Os limites eram fixos em 60/40000 no código, e as variáveis
        LLM_MAX_CALLS_PER_MINUTE / LLM_MAX_TOKENS_PER_MINUTE — documentadas no
        .env.example — não tinham efeito nenhum.
        """
        from app.config import settings

        service = LLMService()

        assert service.max_calls_per_minute == settings.llm_max_calls_per_minute
        assert service.max_tokens_per_minute == settings.llm_max_tokens_per_minute
