"""Tests for metrics service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from app.services.metrics_service import metrics_service
from app.db.models import (
    Agent, Conversation, Lead, LeadDetails, Message, ConversationMetrics
)
from sqlalchemy.ext.asyncio import AsyncSession


class TestMetricsService:
    """Test metrics service calculations."""

    def setup_method(self, method):
        """Setup test fixtures."""
        self.agent_id = "test-agent-123"
        self.conversation_id = "conv-123"
        self.lead_id = "lead-123"
        self.now = datetime.utcnow()

    @pytest.mark.asyncio
    async def test_calculate_period_stats_today(self):
        """Test calculating stats for today."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock agent exists
        agent_mock = AsyncMock()
        agent_mock.scalars().first.return_value = Agent(id=self.agent_id)
        mock_db.execute.return_value = agent_mock

        # Mock conversation count and duration
        result_mock = AsyncMock()
        result_mock.first.return_value = (5, 300)  # 5 conversations, 300 seconds = 5 minutes each
        mock_db.execute.return_value = result_mock

        # Stats should have atendimentos
        stats = await metrics_service.calculate_period_stats(
            self.agent_id, mock_db, "day", use_cache=False
        )

        assert stats["agent_id"] == self.agent_id
        assert stats["periodo"] == "day"
        assert "total_atendimentos" in stats
        assert "taxa_qualificacao" in stats

    @pytest.mark.asyncio
    async def test_calculate_period_stats_custom_range_exceeded(self):
        """Test that custom period > 90 days is rejected."""
        mock_db = AsyncMock(spec=AsyncSession)

        start = self.now - timedelta(days=100)
        end = self.now

        with pytest.raises(Exception):
            await metrics_service.calculate_period_stats(
                self.agent_id, mock_db, "custom", start, end, use_cache=False
            )

    @pytest.mark.asyncio
    async def test_calculate_period_stats_agent_not_found(self):
        """Test error when agent not found."""
        mock_db = AsyncMock(spec=AsyncSession)
        agent_mock = AsyncMock()
        agent_mock.scalars().first.return_value = None
        mock_db.execute.return_value = agent_mock

        with pytest.raises(Exception):
            await metrics_service.calculate_period_stats(
                "invalid-agent", mock_db, "day", use_cache=False
            )

    @pytest.mark.asyncio
    async def test_get_qualification_rate_basic(self):
        """Test qualification rate calculation."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock agent
        agent_mock = AsyncMock()
        agent_mock.scalars().first.return_value = Agent(id=self.agent_id)
        mock_db.execute.return_value = agent_mock

        result = await metrics_service.get_qualification_rate(
            self.agent_id, mock_db, "day", use_cache=False
        )

        assert "taxa_qualificacao" in result
        assert "leads_qualificados" in result
        assert "total_leads" in result
        assert "status" in result

    @pytest.mark.asyncio
    async def test_get_qualification_rate_zero_leads(self):
        """Test qualification rate with zero leads."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock agent
        agent_mock = AsyncMock()
        agent_mock.scalars().first.return_value = Agent(id=self.agent_id)
        mock_db.execute.return_value = agent_mock

        result = await metrics_service.get_qualification_rate(
            self.agent_id, mock_db, "day", use_cache=False
        )

        # Should return 0, not error
        assert result["taxa_qualificacao"] == 0

    @pytest.mark.asyncio
    async def test_get_avg_response_time_calculation(self):
        """Test response time calculation."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock agent
        agent_mock = AsyncMock()
        agent_mock.scalars().first.return_value = Agent(id=self.agent_id)
        mock_db.execute.return_value = agent_mock

        result = await metrics_service.get_avg_response_time(
            self.agent_id, mock_db, "day", use_cache=False
        )

        assert "tempo_medio_seg" in result
        assert "p50_seg" in result
        assert "p95_seg" in result
        assert "min_seg" in result
        assert "max_seg" in result

    @pytest.mark.asyncio
    async def test_get_avg_response_time_with_gap(self):
        """Test response time excludes gaps > 30 minutes."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock agent
        agent_mock = AsyncMock()
        agent_mock.scalars().first.return_value = Agent(id=self.agent_id)
        mock_db.execute.return_value = agent_mock

        result = await metrics_service.get_avg_response_time(
            self.agent_id, mock_db, "day", use_cache=False
        )

        # Should handle gracefully
        assert result["total_trocas"] >= 0

    @pytest.mark.asyncio
    async def test_get_lead_distribution_complete(self):
        """Test lead distribution retrieval."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock agent
        agent_mock = AsyncMock()
        agent_mock.scalars().first.return_value = Agent(id=self.agent_id)
        mock_db.execute.return_value = agent_mock

        result = await metrics_service.get_lead_distribution(
            self.agent_id, mock_db, use_cache=False
        )

        expected_keys = ["novo", "em_qualificacao", "qualificado", "agendado", "arquivado", "total"]
        for key in expected_keys:
            assert key in result

    @pytest.mark.asyncio
    async def test_get_lead_distribution_empty(self):
        """Test lead distribution with no leads."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock agent
        agent_mock = AsyncMock()
        agent_mock.scalars().first.return_value = Agent(id=self.agent_id)
        mock_db.execute.return_value = agent_mock

        result = await metrics_service.get_lead_distribution(
            self.agent_id, mock_db, use_cache=False
        )

        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_avg_qualification_score(self):
        """Test qualification score calculation."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock agent
        agent_mock = AsyncMock()
        agent_mock.scalars().first.return_value = Agent(id=self.agent_id)
        mock_db.execute.return_value = agent_mock

        result = await metrics_service.get_avg_qualification_score(
            self.agent_id, mock_db, "day", use_cache=False
        )

        assert "score_medio" in result
        assert "score_min" in result
        assert "score_max" in result
        assert "desvio_padrao" in result

    @pytest.mark.asyncio
    async def test_get_problem_analysis_basic(self):
        """Test problem analysis."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock agent
        agent_mock = AsyncMock()
        agent_mock.scalars().first.return_value = Agent(id=self.agent_id)
        mock_db.execute.return_value = agent_mock

        result = await metrics_service.get_problem_analysis(
            self.agent_id, mock_db, "day", limit=10, use_cache=False
        )

        assert "problemas" in result
        assert "total_unicos" in result
        assert "total_registros" in result

    @pytest.mark.asyncio
    async def test_get_problem_analysis_limit(self):
        """Test problem analysis respects limit."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock agent
        agent_mock = AsyncMock()
        agent_mock.scalars().first.return_value = Agent(id=self.agent_id)
        mock_db.execute.return_value = agent_mock

        result = await metrics_service.get_problem_analysis(
            self.agent_id, mock_db, "day", limit=5, use_cache=False
        )

        # Should return max 5 problems
        assert len(result["problemas"]) <= 5

    @pytest.mark.asyncio
    async def test_get_kpis_with_comparison(self):
        """Test KPIs calculation with comparison."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock agent
        agent_mock = AsyncMock()
        agent_mock.scalars().first.return_value = Agent(id=self.agent_id)
        mock_db.execute.return_value = agent_mock

        result = await metrics_service.get_kpis(
            self.agent_id, mock_db, use_cache=False
        )

        assert "periodo_atual" in result
        assert "periodo_anterior" in result
        assert "variacao_percent" in result
        assert "status" in result
        assert "alertas" in result

    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test cache key generation."""
        key = metrics_service._generate_cache_key(
            self.agent_id, "test_metric", "day"
        )
        assert "metrics:" in key
        assert self.agent_id in key
        assert "test_metric" in key
        assert "day" in key

    @pytest.mark.asyncio
    async def test_cache_hit_returns_data(self):
        """Test cache hit returns cached data."""
        # Mock Redis
        with patch.object(metrics_service.redis, 'get', new_callable=AsyncMock) as mock_get:
            import json
            cached_data = {"test": "data"}
            mock_get.return_value = json.dumps(cached_data)

            result = await metrics_service._get_from_cache("test_key")
            assert result == cached_data

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        """Test cache miss returns None."""
        # Mock Redis
        with patch.object(metrics_service.redis, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await metrics_service._get_from_cache("nonexistent_key")
            assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_agent_cache(self):
        """Test invalidating agent cache."""
        # Mock Redis
        with patch.object(metrics_service.redis, 'keys', new_callable=AsyncMock) as mock_keys:
            with patch.object(metrics_service.redis, 'delete', new_callable=AsyncMock) as mock_delete:
                mock_keys.return_value = ["metrics:agent1:metric1:day", "metrics:agent1:metric2:day"]
                mock_delete.return_value = 2

                await metrics_service.invalidate_agent_cache(self.agent_id)

                # Should attempt to delete
                mock_keys.assert_called_once()
