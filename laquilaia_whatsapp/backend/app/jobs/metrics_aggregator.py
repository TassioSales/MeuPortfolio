"""Job for periodic aggregation of metrics."""

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.db.database import AsyncSessionLocal
from app.db.models import (
    Conversation, Lead, LeadDetails, Message,
    ConversationMetrics, DailyStats, Agent
)
from app.utils.logger import logger


class MetricsAggregator:
    """Aggregates metrics periodically for reporting."""

    async def aggregate_hourly_metrics(self) -> None:
        """
        Calculate metrics for the last hour and update ConversationMetrics.

        Runs every hour via APScheduler.
        """
        async with AsyncSessionLocal() as db:
            try:
                logger.info("⏱️ Starting hourly metrics aggregation...")

                # Get all agents
                result = await db.execute(select(Agent.id))
                agent_ids = [row[0] for row in result.fetchall()]

                if not agent_ids:
                    logger.info("ℹ️ No agents found, skipping aggregation")
                    return

                now = datetime.utcnow()
                hour_start = now.replace(minute=0, second=0, microsecond=0)

                for agent_id in agent_ids:
                    try:
                        await self._calculate_hourly_stats(db, agent_id, hour_start, now)
                    except Exception as e:
                        logger.error(f"❌ Error aggregating metrics for {agent_id}: {e}")

                logger.info("✅ Hourly aggregation completed")

            except Exception as e:
                logger.error(f"❌ Fatal error in hourly aggregation: {e}")

    async def aggregate_daily_stats(self) -> None:
        """
        Calculate daily statistics for the previous day.

        Runs nightly at 00:00 UTC via APScheduler.
        """
        async with AsyncSessionLocal() as db:
            try:
                logger.info("📊 Starting daily stats aggregation...")

                now = datetime.utcnow()
                day_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = now.replace(hour=0, minute=0, second=0, microsecond=0)

                # Get all agents
                result = await db.execute(select(Agent.id))
                agent_ids = [row[0] for row in result.fetchall()]

                for agent_id in agent_ids:
                    try:
                        # Count messages
                        result = await db.execute(
                            select(func.count(Message.id))
                            .select_from(Message)
                            .join(Conversation)
                            .where(and_(
                                Conversation.agent_id == agent_id,
                                Message.timestamp >= day_start,
                                Message.timestamp < day_end,
                                Message.remetente == "user"
                            ))
                        )
                        msgs_received = result.scalar() or 0

                        result = await db.execute(
                            select(func.count(Message.id))
                            .select_from(Message)
                            .join(Conversation)
                            .where(and_(
                                Conversation.agent_id == agent_id,
                                Message.timestamp >= day_start,
                                Message.timestamp < day_end,
                                Message.remetente == "agent"
                            ))
                        )
                        msgs_sent = result.scalar() or 0

                        # Count qualified leads
                        result = await db.execute(
                            select(func.count(Lead.id))
                            .select_from(Lead)
                            .join(Conversation)
                            .where(and_(
                                Conversation.agent_id == agent_id,
                                Lead.status_funil.in_(["qualificado", "agendado"]),
                                Lead.data_criacao >= day_start,
                                Lead.data_criacao < day_end
                            ))
                        )
                        leads_qualified = result.scalar() or 0

                        # Count created leads
                        result = await db.execute(
                            select(func.count(Lead.id))
                            .select_from(Lead)
                            .join(Conversation)
                            .where(and_(
                                Conversation.agent_id == agent_id,
                                Lead.data_criacao >= day_start,
                                Lead.data_criacao < day_end
                            ))
                        )
                        leads_created = result.scalar() or 0

                        # Check if DailyStats exists for this day
                        result = await db.execute(
                            select(DailyStats).where(
                                and_(
                                    DailyStats.data == day_start.date(),
                                    DailyStats.agent_id == agent_id
                                )
                            )
                        )
                        daily_stat = result.scalars().first()

                        if daily_stat:
                            # Update existing
                            daily_stat.mensagens_recebidas = msgs_received
                            daily_stat.mensagens_enviadas = msgs_sent
                            daily_stat.leads_criados = leads_created
                            daily_stat.leads_qualificados = leads_qualified
                        else:
                            # Create new
                            daily_stat = DailyStats(
                                data=day_start.date(),
                                agent_id=agent_id,
                                mensagens_recebidas=msgs_received,
                                mensagens_enviadas=msgs_sent,
                                leads_criados=leads_created,
                                leads_qualificados=leads_qualified,
                            )
                            db.add(daily_stat)

                    except Exception as e:
                        logger.error(f"❌ Error calculating daily stats for {agent_id}: {e}")

                await db.commit()
                logger.info("✅ Daily aggregation completed")

            except Exception as e:
                logger.error(f"❌ Fatal error in daily aggregation: {e}")
                await db.rollback()

    async def cleanup_old_cache(self) -> None:
        """
        Clean up old cache entries from Redis.

        Runs nightly at 02:00 UTC.
        """
        try:
            from app.db.redis_client import redis_client

            logger.info("🧹 Starting cache cleanup...")

            # Pattern to match all metrics cache keys
            pattern = "metrics:*"
            keys = await redis_client.keys(pattern)

            if keys:
                deleted = await redis_client.delete(*keys)
                logger.info(f"🧹 Deleted {deleted} old cache entries")
            else:
                logger.info("ℹ️ No old cache entries found")

            logger.info("✅ Cache cleanup completed")

        except Exception as e:
            logger.error(f"❌ Error during cache cleanup: {e}")

    # ========== PRIVATE HELPERS ==========

    async def _calculate_hourly_stats(
        self,
        db: AsyncSession,
        agent_id: str,
        hour_start: datetime,
        hour_end: datetime,
    ) -> None:
        """
        Calculate metrics for an hour and update ConversationMetrics.

        Args:
            db: Database session
            agent_id: Agent ID
            hour_start: Start of hour (HH:00:00)
            hour_end: Current time
        """
        # Count conversations started in this hour
        result = await db.execute(
            select(func.count(Conversation.id))
            .where(and_(
                Conversation.agent_id == agent_id,
                Conversation.data_inicio >= hour_start,
                Conversation.data_inicio < hour_end
            ))
        )
        total_convs = result.scalar() or 0

        # Count qualified leads from conversations in this hour
        result = await db.execute(
            select(func.count(Lead.id))
            .select_from(Lead)
            .join(Conversation)
            .where(and_(
                Conversation.agent_id == agent_id,
                Lead.status_funil.in_(["qualificado", "agendado"]),
                Lead.data_criacao >= hour_start,
                Lead.data_criacao < hour_end
            ))
        )
        qualified = result.scalar() or 0

        # Calculate rate
        taxa = (qualified / total_convs * 100) if total_convs > 0 else 0

        # Avg duration
        result = await db.execute(
            select(func.avg(func.extract('epoch', Conversation.data_ultima_msg - Conversation.data_inicio)))
            .where(and_(
                Conversation.agent_id == agent_id,
                Conversation.data_inicio >= hour_start,
                Conversation.data_inicio < hour_end
            ))
        )
        avg_duration = (result.scalar() or 0) / 60  # To minutes

        # Count messages
        result = await db.execute(
            select(func.count(Message.id))
            .select_from(Message)
            .join(Conversation)
            .where(and_(
                Conversation.agent_id == agent_id,
                Message.timestamp >= hour_start,
                Message.timestamp < hour_end,
                Message.remetente == "user"
            ))
        )
        msgs_received = result.scalar() or 0

        result = await db.execute(
            select(func.count(Message.id))
            .select_from(Message)
            .join(Conversation)
            .where(and_(
                Conversation.agent_id == agent_id,
                Message.timestamp >= hour_start,
                Message.timestamp < hour_end,
                Message.remetente == "agent"
            ))
        )
        msgs_sent = result.scalar() or 0

        # Check if metrics exist for this hour
        result = await db.execute(
            select(ConversationMetrics).where(
                and_(
                    ConversationMetrics.agent_id == agent_id,
                    ConversationMetrics.data == hour_start.date()
                )
            )
        )
        metrics = result.scalars().first()

        if metrics:
            # Update
            metrics.total_atendimentos = total_convs
            metrics.taxa_qualificacao = round(taxa, 2)
            metrics.tempo_medio = round(avg_duration, 2)
            metrics.mensagens_recebidas = msgs_received
            metrics.mensagens_enviadas = msgs_sent
            metrics.leads_qualificados = qualified
        else:
            # Create new
            metrics = ConversationMetrics(
                agent_id=agent_id,
                data=hour_start.date(),
                total_atendimentos=total_convs,
                taxa_qualificacao=round(taxa, 2),
                tempo_medio=round(avg_duration, 2),
                mensagens_recebidas=msgs_received,
                mensagens_enviadas=msgs_sent,
                leads_qualificados=qualified,
            )
            db.add(metrics)

        await db.commit()
        logger.debug(f"✅ Hourly stats updated for {agent_id}: {total_convs} conversations")
