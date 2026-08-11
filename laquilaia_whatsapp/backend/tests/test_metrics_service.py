"""
Tests for metrics service.

Os cálculos rodam contra o banco de testes de verdade. A versão anterior
mockava a AsyncSession inteira, mas o serviço encadeia várias queries com
formatos de retorno diferentes (`scalar`, `first`, `all`) e um mock único
para todas devolvia MagicMock onde o código esperava número — os testes
passavam a verificar apenas a presença de chaves no dicionário, sem
exercitar conta nenhuma. Com banco real, os números são conferidos.

Os testes de cache seguem unitários: ali o alvo é o Redis, não o SQL.
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from app.services.metrics_service import metrics_service
from app.db.database import AsyncSessionLocal
from app.db.models import (
    Agent,
    Conversation,
    Lead,
    LeadDetails,
    Message,
    User,
)


async def _seed(db, *, agent_id: str, user_id: str = "metrics-user") -> None:
    """Cria o usuário e o agente que os cálculos exigem existir."""
    db.add(
        User(
            id=user_id,
            email=f"{user_id}@example.com",
            nome="Metrics Owner",
            senha_hash="x",
            status="ativo",
        )
    )
    await db.flush()
    db.add(
        Agent(
            id=agent_id,
            user_id=user_id,
            nome="Agente de métricas",
            system_prompt="prompt",
            temperatura=0.7,
            max_tokens=1024,
            status="ativo",
        )
    )
    await db.flush()


async def _add_lead(
    db,
    *,
    agent_id: str,
    lead_id: str,
    phone: str,
    status_funil: str,
    score: int | None = None,
    problemas: str | None = None,
    when: datetime | None = None,
) -> None:
    """Cria uma conversa com um lead associado (o funil pendura no lead)."""
    when = when or datetime.utcnow()
    conversation_id = f"conv-{lead_id}"

    db.add(
        Conversation(
            id=conversation_id,
            agent_id=agent_id,
            phone_number=phone,
            status="ativa",
            data_inicio=when,
            data_ultima_msg=when,
        )
    )
    await db.flush()

    db.add(
        Lead(
            id=lead_id,
            conversation_id=conversation_id,
            phone_number=phone,
            nome=f"Lead {lead_id}",
            status_funil=status_funil,
            data_criacao=when,
            data_atualizacao=when,
        )
    )
    await db.flush()

    if score is not None or problemas is not None:
        db.add(
            LeadDetails(
                lead_id=lead_id,
                score_qualificacao=score,
                problemas_detectados=problemas,
            )
        )
        await db.flush()


class TestMetricsCalculations:
    """Cálculos exercitados contra o banco de testes."""

    agent_id = "metrics-agent"

    @pytest.mark.asyncio
    async def test_period_stats_counts_conversations_of_the_day(self):
        async with AsyncSessionLocal() as db:
            await _seed(db, agent_id=self.agent_id)
            await _add_lead(
                db,
                agent_id=self.agent_id,
                lead_id="l1",
                phone="5561900000001",
                status_funil="qualificado",
                score=80,
            )
            await _add_lead(
                db,
                agent_id=self.agent_id,
                lead_id="l2",
                phone="5561900000002",
                status_funil="novo",
                score=40,
            )
            await db.commit()

            stats = await metrics_service.calculate_period_stats(
                self.agent_id, db, "day", use_cache=False
            )

        assert stats["agent_id"] == self.agent_id
        assert stats["periodo"] == "day"
        assert stats["total_atendimentos"] == 2

    @pytest.mark.asyncio
    async def test_period_stats_rejects_range_over_90_days(self):
        async with AsyncSessionLocal() as db:
            await _seed(db, agent_id=self.agent_id)
            await db.commit()

            with pytest.raises(Exception):
                await metrics_service.calculate_period_stats(
                    self.agent_id,
                    db,
                    "custom",
                    datetime.utcnow() - timedelta(days=100),
                    datetime.utcnow(),
                    use_cache=False,
                )

    @pytest.mark.asyncio
    async def test_period_stats_fails_for_unknown_agent(self):
        async with AsyncSessionLocal() as db:
            with pytest.raises(Exception):
                await metrics_service.calculate_period_stats(
                    "agente-inexistente", db, "day", use_cache=False
                )

    @pytest.mark.asyncio
    async def test_qualification_rate_is_the_ratio_of_qualified_leads(self):
        async with AsyncSessionLocal() as db:
            await _seed(db, agent_id=self.agent_id)
            for i, status_funil in enumerate(
                ["qualificado", "qualificado", "novo", "arquivado"], start=1
            ):
                await _add_lead(
                    db,
                    agent_id=self.agent_id,
                    lead_id=f"lq{i}",
                    phone=f"556190000010{i}",
                    status_funil=status_funil,
                )
            await db.commit()

            result = await metrics_service.get_qualification_rate(
                self.agent_id, db, "day", use_cache=False
            )

        assert result["total_leads"] == 4
        assert result["leads_qualificados"] == 2
        assert result["taxa_qualificacao"] == pytest.approx(50.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_qualification_rate_is_zero_without_leads(self):
        async with AsyncSessionLocal() as db:
            await _seed(db, agent_id=self.agent_id)
            await db.commit()

            result = await metrics_service.get_qualification_rate(
                self.agent_id, db, "day", use_cache=False
            )

        # Período vazio devolve zero, não erro de divisão.
        assert result["total_leads"] == 0
        assert result["taxa_qualificacao"] == 0

    @pytest.mark.asyncio
    async def test_lead_distribution_counts_each_funnel_status(self):
        async with AsyncSessionLocal() as db:
            await _seed(db, agent_id=self.agent_id)
            for i, status_funil in enumerate(
                ["novo", "novo", "em_qualificacao", "qualificado", "agendado"], start=1
            ):
                await _add_lead(
                    db,
                    agent_id=self.agent_id,
                    lead_id=f"ld{i}",
                    phone=f"556190000020{i}",
                    status_funil=status_funil,
                )
            await db.commit()

            result = await metrics_service.get_lead_distribution(
                self.agent_id, db, use_cache=False
            )

        assert result["novo"] == 2
        assert result["em_qualificacao"] == 1
        assert result["qualificado"] == 1
        assert result["agendado"] == 1
        assert result["arquivado"] == 0
        assert result["total"] == 5

    @pytest.mark.asyncio
    async def test_lead_distribution_is_all_zeros_without_leads(self):
        async with AsyncSessionLocal() as db:
            await _seed(db, agent_id=self.agent_id)
            await db.commit()

            result = await metrics_service.get_lead_distribution(
                self.agent_id, db, use_cache=False
            )

        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_qualification_score_averages_lead_details(self):
        async with AsyncSessionLocal() as db:
            await _seed(db, agent_id=self.agent_id)
            for i, score in enumerate([60, 80, 100], start=1):
                await _add_lead(
                    db,
                    agent_id=self.agent_id,
                    lead_id=f"ls{i}",
                    phone=f"556190000030{i}",
                    status_funil="qualificado",
                    score=score,
                )
            await db.commit()

            result = await metrics_service.get_avg_qualification_score(
                self.agent_id, db, "day", use_cache=False
            )

        assert result["score_medio"] == pytest.approx(80.0, abs=0.01)
        assert result["score_min"] == 60
        assert result["score_max"] == 100

    @pytest.mark.asyncio
    async def test_problem_analysis_ranks_by_frequency(self):
        async with AsyncSessionLocal() as db:
            await _seed(db, agent_id=self.agent_id)
            problemas = ["preco alto", "preco alto", "prazo de entrega"]
            for i, problema in enumerate(problemas, start=1):
                await _add_lead(
                    db,
                    agent_id=self.agent_id,
                    lead_id=f"lp{i}",
                    phone=f"556190000040{i}",
                    status_funil="com_duvidas",
                    problemas=problema,
                )
            await db.commit()

            result = await metrics_service.get_problem_analysis(
                self.agent_id, db, "day", limit=10, use_cache=False
            )

        assert result["total_registros"] == 3
        assert result["total_unicos"] == 2
        assert result["problemas"][0]["problema"] == "preco alto"
        assert result["problemas"][0]["frequencia"] == 2

    @pytest.mark.asyncio
    async def test_problem_analysis_respects_limit(self):
        async with AsyncSessionLocal() as db:
            await _seed(db, agent_id=self.agent_id)
            for i in range(6):
                await _add_lead(
                    db,
                    agent_id=self.agent_id,
                    lead_id=f"lpl{i}",
                    phone=f"55619000005{i:02d}",
                    status_funil="com_duvidas",
                    problemas=f"problema {i}",
                )
            await db.commit()

            result = await metrics_service.get_problem_analysis(
                self.agent_id, db, "day", limit=2, use_cache=False
            )

        assert len(result["problemas"]) == 2

    @pytest.mark.asyncio
    async def test_kpis_compare_current_period_with_previous(self):
        async with AsyncSessionLocal() as db:
            await _seed(db, agent_id=self.agent_id)
            await _add_lead(
                db,
                agent_id=self.agent_id,
                lead_id="lk1",
                phone="5561900000601",
                status_funil="qualificado",
                score=90,
            )
            await db.commit()

            result = await metrics_service.get_kpis(self.agent_id, db, use_cache=False)

        for key in ("periodo_atual", "periodo_anterior", "variacao_percent", "status", "alertas"):
            assert key in result
        assert isinstance(result["alertas"], list)


class TestMetricsCache:
    """Camada de cache — aqui o alvo é o Redis, então mock é o certo."""

    agent_id = "metrics-agent"

    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        key = metrics_service._generate_cache_key(self.agent_id, "test_metric", "day")

        assert key.startswith("metrics:")
        assert self.agent_id in key
        assert "test_metric" in key
        assert "day" in key

    @pytest.mark.asyncio
    async def test_cache_hit_returns_data(self):
        with patch.object(metrics_service.redis, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = json.dumps({"test": "data"})

            assert await metrics_service._get_from_cache("test_key") == {"test": "data"}

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        with patch.object(metrics_service.redis, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            assert await metrics_service._get_from_cache("nonexistent_key") is None

    @pytest.mark.asyncio
    async def test_invalidate_agent_cache_deletes_matching_keys(self):
        keys = ["metrics:agent1:metric1:day", "metrics:agent1:metric2:day"]

        with patch.object(metrics_service.redis, "keys", new_callable=AsyncMock) as mock_keys:
            with patch.object(
                metrics_service.redis, "delete", new_callable=AsyncMock
            ) as mock_delete:
                mock_keys.return_value = keys

                await metrics_service.invalidate_agent_cache(self.agent_id)

                mock_keys.assert_called_once()
                mock_delete.assert_called_once()
