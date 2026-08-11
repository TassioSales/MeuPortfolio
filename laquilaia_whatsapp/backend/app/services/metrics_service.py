"""Metrics service for calculating and aggregating agent performance data."""

import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.db.models import (
    Conversation, Message, Lead, LeadDetails, LeadTimeline,
    ConversationMetrics, DailyStats, Agent
)
from app.db.redis_client import redis_client
from app.utils.logger import logger
from app.utils.exceptions import NotFoundException, ValidationException


class MetricsService:
    """Calculates and aggregates metrics for agent performance tracking."""

    def __init__(self, cache_ttl: int = 900):
        """
        Initialize metrics service.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 15 minutes = 900s)
        """
        self.cache_ttl = cache_ttl
        self.redis = redis_client

    async def calculate_period_stats(
        self,
        agent_id: str,
        db: AsyncSession,
        period: str = "day",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Calculate statistics for a given period.

        Args:
            agent_id: Agent ID
            db: Database session
            period: "day", "week", "month", or "custom"
            start_date: Start date for custom period
            end_date: End date for custom period
            use_cache: Whether to use Redis cache

        Returns:
            Dict with total_atendimentos, taxa_qualificacao, tempo_medio_min, etc

        Raises:
            NotFoundException: If agent not found
            ValidationException: If period parameters invalid
        """
        try:
            # Verify agent exists
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalars().first()
            if not agent:
                raise NotFoundException("Agent")

            # Calculate date range
            now = datetime.utcnow()
            if period == "day":
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=1)
            elif period == "week":
                start = now - timedelta(days=now.weekday())
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=7)
            elif period == "month":
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if now.month == 12:
                    end = start.replace(year=now.year + 1, month=1)
                else:
                    end = start.replace(month=now.month + 1)
            elif period == "custom":
                if not start_date or not end_date:
                    raise ValidationException("start_date and end_date required for custom period")
                if (end_date - start_date).days > 90:
                    raise ValidationException("Custom period limited to 90 days")
                start = start_date
                end = end_date
            else:
                raise ValidationException(f"Invalid period: {period}")

            # Check cache
            cache_key = self._generate_cache_key(agent_id, "period_stats", period, (start, end))
            if use_cache:
                cached = await self._get_from_cache(cache_key)
                if cached:
                    logger.debug(f"📦 Cache hit for period stats: {agent_id}")
                    return cached

            # Query conversations for period
            result = await db.execute(
                select(func.count(Conversation.id), func.avg(func.extract('epoch', Conversation.data_ultima_msg - Conversation.data_inicio)))
                .where(and_(
                    Conversation.agent_id == agent_id,
                    Conversation.data_inicio >= start,
                    Conversation.data_inicio < end
                ))
            )
            total_convs, avg_duration = result.first()
            total_convs = total_convs or 0
            avg_duration = (avg_duration or 0) / 60  # Convert to minutes

            # Count qualified leads
            result = await db.execute(
                select(func.count(Lead.id))
                .select_from(Lead)
                .join(Conversation)
                .where(and_(
                    Conversation.agent_id == agent_id,
                    Lead.status_funil.in_(["qualificado", "agendado"]),
                    Lead.data_criacao >= start,
                    Lead.data_criacao < end
                ))
            )
            qualified_leads = result.scalar() or 0

            # Count total leads
            result = await db.execute(
                select(func.count(Lead.id))
                .select_from(Lead)
                .join(Conversation)
                .where(and_(
                    Conversation.agent_id == agent_id,
                    Lead.data_criacao >= start,
                    Lead.data_criacao < end
                ))
            )
            total_leads = result.scalar() or 0

            # Calculate qualification rate
            taxa_qualificacao = (qualified_leads / total_leads * 100) if total_leads > 0 else 0

            stats = {
                "agent_id": agent_id,
                "periodo": period,
                "data_inicio": start.isoformat(),
                "data_fim": end.isoformat(),
                "total_atendimentos": int(total_convs),
                "taxa_qualificacao": round(taxa_qualificacao, 2),
                "tempo_medio_min": round(avg_duration, 2),
                "leads_qualificados": int(qualified_leads),
                "total_leads": int(total_leads),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Cache result
            await self._save_to_cache(cache_key, stats)
            logger.info(f"✅ Period stats calculated for {agent_id}: {total_convs} conversations")

            return stats

        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"❌ Error calculating period stats: {e}")
            raise ValidationException(f"Failed to calculate stats: {str(e)}")

    async def get_qualification_rate(
        self,
        agent_id: str,
        db: AsyncSession,
        period: str = "day",
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Get qualification rate with trend analysis.

        Args:
            agent_id: Agent ID
            db: Database session
            period: "day", "week", or "month"
            use_cache: Whether to use cache

        Returns:
            Dict with taxa_qualificacao, leads_qualificados, total_leads, trend
        """
        try:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            if not result.scalars().first():
                raise NotFoundException("Agent")

            cache_key = self._generate_cache_key(agent_id, "qualification_rate", period)
            if use_cache:
                cached = await self._get_from_cache(cache_key)
                if cached:
                    return cached

            # Get current period stats
            now = datetime.utcnow()
            if period == "day":
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=1)
                prev_start = start - timedelta(days=1)
                prev_end = start
            elif period == "week":
                start = now - timedelta(days=now.weekday())
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=7)
                prev_start = start - timedelta(days=7)
                prev_end = start
            else:  # month
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if now.month == 12:
                    end = start.replace(year=now.year + 1, month=1)
                    prev_start = (start.replace(year=now.year - 1) if now.month == 1
                                  else start.replace(month=now.month - 1))
                    prev_end = start
                else:
                    end = start.replace(month=now.month + 1)
                    prev_start = start.replace(month=now.month - 1) if now.month > 1 else start.replace(year=now.year - 1, month=12)
                    prev_end = start

            # Current period
            result = await db.execute(
                select(func.count(Lead.id))
                .select_from(Lead)
                .join(Conversation)
                .where(and_(
                    Conversation.agent_id == agent_id,
                    Lead.status_funil.in_(["qualificado", "agendado"]),
                    Lead.data_criacao >= start,
                    Lead.data_criacao < end
                ))
            )
            qualified_curr = result.scalar() or 0

            result = await db.execute(
                select(func.count(Lead.id))
                .select_from(Lead)
                .join(Conversation)
                .where(and_(
                    Conversation.agent_id == agent_id,
                    Lead.data_criacao >= start,
                    Lead.data_criacao < end
                ))
            )
            total_curr = result.scalar() or 0

            taxa_curr = (qualified_curr / total_curr * 100) if total_curr > 0 else 0

            # Previous period for trend
            result = await db.execute(
                select(func.count(Lead.id))
                .select_from(Lead)
                .join(Conversation)
                .where(and_(
                    Conversation.agent_id == agent_id,
                    Lead.status_funil.in_(["qualificado", "agendado"]),
                    Lead.data_criacao >= prev_start,
                    Lead.data_criacao < prev_end
                ))
            )
            qualified_prev = result.scalar() or 0

            result = await db.execute(
                select(func.count(Lead.id))
                .select_from(Lead)
                .join(Conversation)
                .where(and_(
                    Conversation.agent_id == agent_id,
                    Lead.data_criacao >= prev_start,
                    Lead.data_criacao < prev_end
                ))
            )
            total_prev = result.scalar() or 0

            taxa_prev = (qualified_prev / total_prev * 100) if total_prev > 0 else 0

            # Calculate trend
            trend = taxa_curr - taxa_prev if taxa_prev > 0 else 0

            data = {
                "taxa_qualificacao": round(taxa_curr, 2),
                "leads_qualificados": int(qualified_curr),
                "total_leads": int(total_curr),
                "periodo": period,
                "trend": round(trend, 2),
                "status": "rising" if trend > 1 else ("falling" if trend < -1 else "stable"),
                "timestamp": datetime.utcnow().isoformat(),
            }

            await self._save_to_cache(cache_key, data)
            return data

        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"❌ Error calculating qualification rate: {e}")
            raise ValidationException(f"Failed to calculate rate: {str(e)}")

    async def get_avg_response_time(
        self,
        agent_id: str,
        db: AsyncSession,
        period: str = "day",
        use_cache: bool = True,
    ) -> Dict[str, float]:
        """
        Calculate average response time between user and agent messages.

        Args:
            agent_id: Agent ID
            db: Database session
            period: "day", "week", or "month"
            use_cache: Whether to use cache

        Returns:
            Dict with tempo_medio_seg, p50, p95, min, max, total_trocas
        """
        try:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            if not result.scalars().first():
                raise NotFoundException("Agent")

            cache_key = self._generate_cache_key(agent_id, "response_time", period)
            if use_cache:
                cached = await self._get_from_cache(cache_key)
                if cached:
                    return cached

            # Calculate date range
            now = datetime.utcnow()
            if period == "day":
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "week":
                start = now - timedelta(days=now.weekday())
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # month
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Get all messages for conversations in period, ordered by time
            result = await db.execute(
                select(Message)
                .select_from(Message)
                .join(Conversation)
                .where(and_(
                    Conversation.agent_id == agent_id,
                    Message.timestamp >= start
                ))
                .order_by(Message.conversation_id, Message.timestamp)
            )
            messages = result.scalars().all()

            # Calculate response times between consecutive user and agent messages
            response_times = []
            for i in range(len(messages) - 1):
                curr = messages[i]
                next_msg = messages[i + 1]

                # If current is user and next is agent, calculate response time
                if curr.remetente == "user" and next_msg.remetente == "agent":
                    delta_sec = (next_msg.timestamp - curr.timestamp).total_seconds()
                    # Skip if gap > 30 minutes (conversation paused)
                    if 0 < delta_sec < 1800:
                        response_times.append(delta_sec)

            if not response_times:
                response_times = [0]

            response_times.sort()
            avg_time = sum(response_times) / len(response_times)
            p50 = response_times[len(response_times) // 2] if response_times else 0
            p95_idx = int(len(response_times) * 0.95)
            p95 = response_times[p95_idx] if p95_idx < len(response_times) else response_times[-1]

            data = {
                "tempo_medio_seg": round(avg_time, 2),
                "p50_seg": round(p50, 2),
                "p95_seg": round(p95, 2),
                "min_seg": round(min(response_times), 2) if response_times else 0,
                "max_seg": round(max(response_times), 2) if response_times else 0,
                "total_trocas": len(response_times),
                "timestamp": datetime.utcnow().isoformat(),
            }

            await self._save_to_cache(cache_key, data)
            logger.info(f"✅ Response time calculated: {data['tempo_medio_seg']}s avg")
            return data

        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"❌ Error calculating response time: {e}")
            raise ValidationException(f"Failed to calculate response time: {str(e)}")

    async def get_lead_distribution(
        self,
        agent_id: str,
        db: AsyncSession,
        use_cache: bool = True,
    ) -> Dict[str, int]:
        """
        Get current distribution of leads by status funnel.

        Args:
            agent_id: Agent ID
            db: Database session
            use_cache: Whether to use cache

        Returns:
            Dict with novo, em_qualificacao, qualificado, agendado, arquivado counts
        """
        try:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            if not result.scalars().first():
                raise NotFoundException("Agent")

            cache_key = self._generate_cache_key(agent_id, "lead_distribution", "current")
            if use_cache:
                cached = await self._get_from_cache(cache_key)
                if cached:
                    return cached

            # Count by status
            statuses = ["novo", "em_qualificacao", "qualificado", "agendado", "arquivado"]
            distribution = {}
            total = 0

            for status in statuses:
                result = await db.execute(
                    select(func.count(Lead.id))
                    .select_from(Lead)
                    .join(Conversation)
                    .where(and_(
                        Conversation.agent_id == agent_id,
                        Lead.status_funil == status
                    ))
                )
                count = result.scalar() or 0
                distribution[status] = int(count)
                total += count

            distribution["total"] = total

            await self._save_to_cache(cache_key, distribution)
            logger.info(f"✅ Lead distribution retrieved: {total} total leads")
            return distribution

        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"❌ Error getting lead distribution: {e}")
            raise ValidationException(f"Failed to get distribution: {str(e)}")

    async def get_avg_qualification_score(
        self,
        agent_id: str,
        db: AsyncSession,
        period: str = "day",
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Get average qualification score of leads.

        Args:
            agent_id: Agent ID
            db: Database session
            period: "day", "week", or "month"
            use_cache: Whether to use cache

        Returns:
            Dict with score_medio, min, max, desvio_padrao, total_leads
        """
        try:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            if not result.scalars().first():
                raise NotFoundException("Agent")

            cache_key = self._generate_cache_key(agent_id, "qualification_score", period)
            if use_cache:
                cached = await self._get_from_cache(cache_key)
                if cached:
                    return cached

            # Calculate date range
            now = datetime.utcnow()
            if period == "day":
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "week":
                start = now - timedelta(days=now.weekday())
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # month
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Get all scores
            result = await db.execute(
                select(LeadDetails.score_qualificacao)
                .select_from(LeadDetails)
                .join(Lead)
                .join(Conversation)
                .where(and_(
                    Conversation.agent_id == agent_id,
                    Lead.data_criacao >= start,
                    LeadDetails.score_qualificacao.isnot(None)
                ))
            )
            scores = [s[0] for s in result.fetchall()]

            if not scores:
                scores = [0]

            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)
            variance = sum((x - avg_score) ** 2 for x in scores) / len(scores)
            std_dev = variance ** 0.5

            data = {
                "score_medio": round(avg_score, 2),
                "score_min": int(min_score),
                "score_max": int(max_score),
                "desvio_padrao": round(std_dev, 2),
                "total_leads": len(scores),
                "timestamp": datetime.utcnow().isoformat(),
            }

            await self._save_to_cache(cache_key, data)
            return data

        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"❌ Error calculating qualification score: {e}")
            raise ValidationException(f"Failed to calculate score: {str(e)}")

    async def get_problem_analysis(
        self,
        agent_id: str,
        db: AsyncSession,
        period: str = "day",
        limit: int = 10,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze problems detected in leads.

        Args:
            agent_id: Agent ID
            db: Database session
            period: "day", "week", or "month"
            limit: Top N problems to return
            use_cache: Whether to use cache

        Returns:
            Dict with problemas list (problema, frequencia) and total counts
        """
        try:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            if not result.scalars().first():
                raise NotFoundException("Agent")

            # `limit=` nomeado: na posição seguinte fica `custom_range`, e o
            # int cairia no `start, end = custom_range` lá dentro.
            cache_key = self._generate_cache_key(
                agent_id, "problem_analysis", period, limit=limit
            )
            if use_cache:
                cached = await self._get_from_cache(cache_key)
                if cached:
                    return cached

            # Calculate date range
            now = datetime.utcnow()
            if period == "day":
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "week":
                start = now - timedelta(days=now.weekday())
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # month
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Get all problems
            result = await db.execute(
                select(LeadDetails.problemas_detectados)
                .select_from(LeadDetails)
                .join(Lead)
                .join(Conversation)
                .where(and_(
                    Conversation.agent_id == agent_id,
                    Lead.data_criacao >= start,
                    LeadDetails.problemas_detectados.isnot(None)
                ))
            )
            problems_text = [p[0] for p in result.fetchall()]

            # Parse and count problems
            problem_count = {}
            for text in problems_text:
                if text:
                    # Split by comma or semicolon
                    items = [x.strip() for x in text.replace(";", ",").split(",")]
                    for item in items:
                        if item:
                            problem_count[item] = problem_count.get(item, 0) + 1

            # Sort by frequency
            sorted_problems = sorted(problem_count.items(), key=lambda x: x[1], reverse=True)
            top_problems = [
                {"problema": p[0], "frequencia": p[1]}
                for p in sorted_problems[:limit]
            ]

            data = {
                "problemas": top_problems,
                "total_unicos": len(problem_count),
                "total_registros": len(problems_text),
                "timestamp": datetime.utcnow().isoformat(),
            }

            await self._save_to_cache(cache_key, data)
            return data

        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"❌ Error analyzing problems: {e}")
            raise ValidationException(f"Failed to analyze problems: {str(e)}")

    async def get_kpis(
        self,
        agent_id: str,
        db: AsyncSession,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Get consolidated KPIs with comparison to previous period.

        Args:
            agent_id: Agent ID
            db: Database session
            use_cache: Whether to use cache

        Returns:
            Dict with periodo_atual, periodo_anterior, variacao_percent, status
        """
        try:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            if not result.scalars().first():
                raise NotFoundException("Agent")

            cache_key = self._generate_cache_key(agent_id, "kpis", "today")
            if use_cache:
                cached = await self._get_from_cache(cache_key)
                if cached:
                    return cached

            # Get today's and yesterday's stats
            today_stats = await self.calculate_period_stats(agent_id, db, "day", use_cache=False)

            yesterday_start = (datetime.utcnow() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_end = yesterday_start + timedelta(days=1)
            yesterday_stats = await self.calculate_period_stats(
                agent_id, db, "custom", yesterday_start, yesterday_end, use_cache=False
            )

            # Build KPI dict
            kpis = {
                "periodo_atual": {
                    "atendimentos": today_stats["total_atendimentos"],
                    "taxa_qualificacao": today_stats["taxa_qualificacao"],
                    "tempo_medio_seg": today_stats["tempo_medio_min"] * 60,
                    "score_medio": 0,  # Will calculate below
                    "leads_qualificados": today_stats["leads_qualificados"],
                },
                "periodo_anterior": {
                    "atendimentos": yesterday_stats["total_atendimentos"],
                    "taxa_qualificacao": yesterday_stats["taxa_qualificacao"],
                    "tempo_medio_seg": yesterday_stats["tempo_medio_min"] * 60,
                    "score_medio": 0,
                    "leads_qualificados": yesterday_stats["leads_qualificados"],
                },
                "variacao_percent": {},
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Get scores for today
            today_score = await self.get_avg_qualification_score(agent_id, db, "day", use_cache=False)
            kpis["periodo_atual"]["score_medio"] = today_score["score_medio"]

            # Calculate variations
            for key in ["atendimentos", "taxa_qualificacao", "score_medio", "leads_qualificados"]:
                curr = kpis["periodo_atual"][key]
                prev = kpis["periodo_anterior"][key]
                variation = ((curr - prev) / prev * 100) if prev > 0 else 0
                kpis["variacao_percent"][key] = round(variation, 2)

            # Determine status
            if kpis["variacao_percent"]["taxa_qualificacao"] > 5:
                kpis["status"] = "excellent"
            elif kpis["variacao_percent"]["taxa_qualificacao"] < -5:
                kpis["status"] = "concerning"
            else:
                kpis["status"] = "on_track"

            # Add alerts
            kpis["alertas"] = []
            if kpis["variacao_percent"]["taxa_qualificacao"] < -10:
                kpis["alertas"].append("Taxa de qualificação caindo rapidamente")
            if kpis["periodo_atual"]["atendimentos"] == 0:
                kpis["alertas"].append("Nenhum atendimento hoje")

            await self._save_to_cache(cache_key, kpis)
            logger.info(f"✅ KPIs calculated for {agent_id}")
            return kpis

        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"❌ Error calculating KPIs: {e}")
            raise ValidationException(f"Failed to calculate KPIs: {str(e)}")

    # ========== PRIVATE HELPER METHODS ==========

    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve from Redis cache."""
        try:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.warning(f"⚠️ Cache retrieval failed: {e}")
            return None

    async def _save_to_cache(self, key: str, data: Dict[str, Any], ttl: int = None) -> None:
        """Save to Redis cache."""
        try:
            ttl = ttl or self.cache_ttl
            await self.redis.setex(key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"⚠️ Cache save failed: {e}")

    def _generate_cache_key(
        self,
        agent_id: str,
        metric_type: str,
        period: str,
        custom_range: Optional[Tuple] = None,
        limit: Optional[int] = None,
    ) -> str:
        """Generate cache key."""
        key = f"metrics:{agent_id}:{metric_type}:{period}"
        if custom_range:
            start, end = custom_range
            key += f":{start.isoformat()}:{end.isoformat()}"
        if limit:
            key += f":{limit}"
        return key

    async def invalidate_agent_cache(self, agent_id: str) -> None:
        """Invalidate all cache entries for an agent."""
        try:
            pattern = f"metrics:{agent_id}:*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"🧹 Invalidated {len(keys)} cache entries for {agent_id}")
        except Exception as e:
            logger.warning(f"⚠️ Cache invalidation failed: {e}")


# Singleton instance
metrics_service = MetricsService()
