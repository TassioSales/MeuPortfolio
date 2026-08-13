"""Memory service for optimized conversation history retrieval with Redis caching."""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.models import Message, Conversation
from app.db.redis_client import redis_client
from app.utils.logger import logger
from app.utils.exceptions import ValidationException


class MemoryService:
    """Manages conversation history with Redis caching for optimal performance."""

    def __init__(self, cache_ttl: int = 3600):
        """
        Initialize memory service.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 1 hour)
        """
        self.cache_ttl = cache_ttl
        self.redis = redis_client

    def _get_cache_key(self, conversation_id: str) -> str:
        """Generate cache key for conversation history."""
        return f"conv_history:{conversation_id}"

    async def get_conversation_history(
        self,
        conversation_id: str,
        db: AsyncSession,
        limit: int = 5,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history with Redis caching.

        First tries cache, then falls back to database if cache miss.
        Cache is invalidated after TTL or manual invalidation.

        Args:
            conversation_id: Conversation ID to fetch history for
            db: Database session
            limit: Max number of messages to retrieve
            use_cache: Whether to use Redis cache (default True)

        Returns:
            List of message dicts in format:
            [{"role": "user"|"assistant", "content": "message text"}, ...]

        Raises:
            ValidationException: If conversation not found
        """
        try:
            cache_key = self._get_cache_key(conversation_id)

            if use_cache:
                cached = await self._get_from_cache(cache_key)
                if cached is not None:
                    logger.debug(
                        f"📦 Cache hit for conversation {conversation_id} "
                        f"(size: {len(cached)} messages)"
                    )
                    return cached

            logger.debug(f"📝 Fetching history from DB for {conversation_id}")
            history = await self._fetch_from_db(conversation_id, db, limit)

            if use_cache:
                await self._save_to_cache(cache_key, history)

            return history

        except Exception as e:
            logger.error(f"❌ Error retrieving conversation history: {e}")
            raise ValidationException(f"Failed to retrieve history: {str(e)}")

    async def cache_conversation(
        self,
        conversation_id: str,
        history: List[Dict[str, Any]],
    ) -> bool:
        """
        Manually cache conversation history.

        Useful after processing a message to ensure cache is fresh.

        Args:
            conversation_id: Conversation ID
            history: List of message dicts

        Returns:
            True if cached successfully, False otherwise
        """
        try:
            cache_key = self._get_cache_key(conversation_id)
            # `_save_to_cache` trata a exceção internamente e devolve False —
            # ignorar esse retorno faria reportar sucesso numa gravação falha.
            saved = await self._save_to_cache(cache_key, history)
            if saved:
                logger.debug(f"✅ Cached {len(history)} messages for {conversation_id}")
            return saved
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache conversation: {e}")
            return False

    async def invalidate_cache(self, conversation_id: str) -> bool:
        """
        Clear cache for a specific conversation.

        Call this after adding new messages to ensure fresh cache on next retrieval.

        Args:
            conversation_id: Conversation ID to invalidate

        Returns:
            True if invalidated, False if key didn't exist
        """
        try:
            cache_key = self._get_cache_key(conversation_id)
            result = await self.redis.delete(cache_key)
            if result:
                logger.debug(f"🗑️ Invalidated cache for {conversation_id}")
            return bool(result)
        except Exception as e:
            logger.warning(f"⚠️ Failed to invalidate cache: {e}")
            return False

    async def clear_expired_conversations(
        self,
        db: AsyncSession,
        max_age_days: int = 30,
    ) -> int:
        """
        Clear cache for conversations older than max_age_days.

        Run periodically to maintain cache size.

        Args:
            db: Database session
            max_age_days: Age threshold in days

        Returns:
            Number of cache entries cleared
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

            result = await db.execute(
                select(Conversation).where(
                    Conversation.data_ultima_msg < cutoff_date
                )
            )
            old_conversations = result.scalars().all()

            cleared = 0
            for conv in old_conversations:
                if await self.invalidate_cache(conv.id):
                    cleared += 1

            if cleared > 0:
                logger.info(f"🧹 Cleared {cleared} expired conversation caches")

            return cleared
        except Exception as e:
            logger.error(f"❌ Error clearing expired caches: {e}")
            return 0

    async def _get_from_cache(
        self,
        cache_key: str,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve from Redis cache.

        Args:
            cache_key: Redis key

        Returns:
            Cached history or None if not found/expired
        """
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data is None:
                return None

            return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"⚠️ Cache retrieval error: {e}")
            return None

    async def _save_to_cache(
        self,
        cache_key: str,
        history: List[Dict[str, Any]],
    ) -> bool:
        """
        Save to Redis cache with TTL.

        Args:
            cache_key: Redis key
            history: Data to cache

        Returns:
            True if successful
        """
        try:
            json_data = json.dumps(history)
            await self.redis.setex(cache_key, self.cache_ttl, json_data)
            return True
        except Exception as e:
            logger.warning(f"⚠️ Cache save error: {e}")
            return False

    async def _fetch_from_db(
        self,
        conversation_id: str,
        db: AsyncSession,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Fetch conversation history from database.

        Args:
            conversation_id: Conversation ID
            db: Database session
            limit: Max messages to retrieve

        Returns:
            List of message dicts
        """
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.timestamp))
            .limit(limit)
        )
        messages = result.scalars().all()

        if not messages:
            logger.debug(f"📭 No messages found for conversation {conversation_id}")
            return []

        # Cliente é `user`; **todo o resto** é o escritório falando.
        #
        # A comparação era ao contrário (`"assistant" if remetente ==
        # "assistant" else "user"`), e com ela a mensagem que o operador
        # escreve à mão entraria no histórico como se fosse o cliente. O modelo
        # leria a própria resposta do escritório como pergunta e responderia a
        # ela — o atendimento conversando sozinho.
        history = [
            {
                "role": "user" if msg.remetente == "user" else "assistant",
                "content": msg.conteudo,
            }
            for msg in reversed(messages)
        ]

        return history


memory_service = MemoryService()
