"""Tests for memory service with Redis caching."""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from app.services.memory_service import MemoryService, memory_service
from app.db.models import Message, Conversation
from app.db.redis_client import redis_client
from sqlalchemy.ext.asyncio import AsyncSession


class TestMemoryServiceCacheHitMiss:
    """Test cache hit and miss scenarios."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_data(self):
        """Test that cache hit returns cached data without DB query."""
        service = MemoryService(cache_ttl=3600)
        conversation_id = "conv-123"
        cache_key = service._get_cache_key(conversation_id)

        expected_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        with patch.object(service.redis, "get") as mock_get:
            mock_get.return_value = json.dumps(expected_history)

            db = AsyncMock(spec=AsyncSession)

            result = await service.get_conversation_history(
                conversation_id, db, limit=5, use_cache=True
            )

            assert result == expected_history
            mock_get.assert_called_once_with(cache_key)
            assert not db.execute.called

    @pytest.mark.asyncio
    async def test_cache_miss_queries_database(self):
        """Test that cache miss falls back to database."""
        service = MemoryService(cache_ttl=3600)
        conversation_id = "conv-123"

        messages = [
            Message(
                id="msg-1",
                conversation_id=conversation_id,
                remetente="user",
                conteudo="Hello",
                timestamp=datetime.utcnow(),
            ),
            Message(
                id="msg-2",
                conversation_id=conversation_id,
                remetente="assistant",
                conteudo="Hi!",
                timestamp=datetime.utcnow(),
            ),
        ]

        db = AsyncMock(spec=AsyncSession)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = messages
        db.execute = AsyncMock(return_value=mock_result)

        with patch.object(service.redis, "get") as mock_get:
            with patch.object(service.redis, "setex") as mock_setex:
                mock_get.return_value = None

                result = await service.get_conversation_history(
                    conversation_id, db, limit=5, use_cache=True
                )

                assert len(result) == 2
                assert result[0]["role"] == "user"
                assert result[1]["role"] == "assistant"
                mock_get.assert_called_once()
                mock_setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_disabled_always_queries_database(self):
        """Test that use_cache=False always queries database."""
        service = MemoryService(cache_ttl=3600)
        conversation_id = "conv-123"

        messages = [
            Message(
                id="msg-1",
                conversation_id=conversation_id,
                remetente="user",
                conteudo="Test",
                timestamp=datetime.utcnow(),
            ),
        ]

        db = AsyncMock(spec=AsyncSession)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = messages
        db.execute = AsyncMock(return_value=mock_result)

        with patch.object(service.redis, "get") as mock_get:
            result = await service.get_conversation_history(
                conversation_id, db, limit=5, use_cache=False
            )

            assert len(result) == 1
            mock_get.assert_not_called()


class TestMemoryServiceCacheInvalidation:
    """Test cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_cache_removes_entry(self):
        """Test that invalidate_cache removes Redis entry."""
        service = MemoryService(cache_ttl=3600)
        conversation_id = "conv-456"
        cache_key = service._get_cache_key(conversation_id)

        with patch.object(service.redis, "delete") as mock_delete:
            mock_delete.return_value = 1

            result = await service.invalidate_cache(conversation_id)

            assert result is True
            mock_delete.assert_called_once_with(cache_key)

    @pytest.mark.asyncio
    async def test_invalidate_cache_returns_false_if_not_found(self):
        """Test that invalidate_cache returns False if key doesn't exist."""
        service = MemoryService(cache_ttl=3600)
        conversation_id = "conv-missing"

        with patch.object(service.redis, "delete") as mock_delete:
            mock_delete.return_value = 0

            result = await service.invalidate_cache(conversation_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_cache_invalidation_after_new_message(self):
        """Test cache invalidation after adding new message."""
        service = MemoryService(cache_ttl=3600)
        conversation_id = "conv-789"

        # First retrieval - should cache
        messages = [
            Message(
                id="msg-1",
                conversation_id=conversation_id,
                remetente="user",
                conteudo="Hello",
                timestamp=datetime.utcnow(),
            ),
        ]

        db = AsyncMock(spec=AsyncSession)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = messages
        db.execute = AsyncMock(return_value=mock_result)

        with patch.object(service.redis, "get") as mock_get:
            with patch.object(service.redis, "setex") as mock_setex:
                with patch.object(service.redis, "delete") as mock_delete:
                    mock_get.return_value = None

                    # Get history (caches it)
                    result1 = await service.get_conversation_history(
                        conversation_id, db, use_cache=True
                    )
                    assert len(result1) == 1

                    # Invalidate cache
                    mock_delete.return_value = 1
                    invalidated = await service.invalidate_cache(conversation_id)
                    assert invalidated is True

                    # Next get should query DB again
                    result2 = await service.get_conversation_history(
                        conversation_id, db, use_cache=True
                    )
                    assert len(result2) == 1


class TestMemoryServiceManualCaching:
    """Test manual cache operations."""

    @pytest.mark.asyncio
    async def test_manual_cache_conversation(self):
        """Test manual caching of conversation history."""
        service = MemoryService(cache_ttl=3600)
        conversation_id = "conv-manual"

        history = [
            {"role": "user", "content": "Test"},
            {"role": "assistant", "content": "Response"},
        ]

        with patch.object(service.redis, "setex") as mock_setex:
            result = await service.cache_conversation(conversation_id, history)

            assert result is True
            mock_setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_manual_cache_failure_returns_false(self):
        """Test that cache failure returns False."""
        service = MemoryService(cache_ttl=3600)
        conversation_id = "conv-fail"
        history = [{"role": "user", "content": "Test"}]

        with patch.object(service.redis, "setex") as mock_setex:
            mock_setex.side_effect = Exception("Redis error")

            result = await service.cache_conversation(conversation_id, history)

            assert result is False


class TestMemoryServiceExpiredConversations:
    """Test cleanup of expired conversation caches."""

    @pytest.mark.asyncio
    async def test_clear_expired_conversations(self):
        """Test clearing cache for old conversations."""
        service = MemoryService(cache_ttl=3600)

        old_date = datetime.utcnow() - timedelta(days=35)

        old_conv = Conversation(
            id="conv-old",
            agent_id="agent-123",
            phone_number="5561999887234",
            status="ativa",
            data_criacao=old_date,
            data_ultima_msg=old_date,
        )

        recent_conv = Conversation(
            id="conv-recent",
            agent_id="agent-123",
            phone_number="5561999887234",
            status="ativa",
            data_criacao=datetime.utcnow(),
            data_ultima_msg=datetime.utcnow(),
        )

        db = AsyncMock(spec=AsyncSession)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [old_conv]
        db.execute = AsyncMock(return_value=mock_result)

        with patch.object(service.redis, "delete") as mock_delete:
            mock_delete.return_value = 1

            cleared = await service.clear_expired_conversations(db, max_age_days=30)

            assert cleared == 1
            mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_expired_with_no_old_conversations(self):
        """Test cleanup when no old conversations exist."""
        service = MemoryService(cache_ttl=3600)

        db = AsyncMock(spec=AsyncSession)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        cleared = await service.clear_expired_conversations(db, max_age_days=30)

        assert cleared == 0


class TestMemoryServiceEmptyHistory:
    """Test edge cases with empty history."""

    @pytest.mark.asyncio
    async def test_empty_conversation_history(self):
        """Test retrieval of empty conversation history."""
        service = MemoryService(cache_ttl=3600)
        conversation_id = "conv-empty"

        db = AsyncMock(spec=AsyncSession)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        with patch.object(service.redis, "get") as mock_get:
            with patch.object(service.redis, "setex") as mock_setex:
                mock_get.return_value = None

                result = await service.get_conversation_history(
                    conversation_id, db, use_cache=True
                )

                assert result == []
                mock_setex.assert_called_once()


class TestMemoryServiceMessageOrder:
    """Test that message order is preserved correctly."""

    @pytest.mark.asyncio
    async def test_messages_returned_in_chronological_order(self):
        """Test that messages are returned oldest to newest."""
        service = MemoryService(cache_ttl=3600)
        conversation_id = "conv-order"

        now = datetime.utcnow()
        messages = [
            Message(
                id="msg-3",
                conversation_id=conversation_id,
                remetente="assistant",
                conteudo="Third",
                timestamp=now + timedelta(seconds=2),
            ),
            Message(
                id="msg-1",
                conversation_id=conversation_id,
                remetente="user",
                conteudo="First",
                timestamp=now,
            ),
            Message(
                id="msg-2",
                conversation_id=conversation_id,
                remetente="assistant",
                conteudo="Second",
                timestamp=now + timedelta(seconds=1),
            ),
        ]

        db = AsyncMock(spec=AsyncSession)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = messages
        db.execute = AsyncMock(return_value=mock_result)

        with patch.object(service.redis, "get") as mock_get:
            with patch.object(service.redis, "setex") as mock_setex:
                mock_get.return_value = None

                result = await service.get_conversation_history(
                    conversation_id, db, use_cache=True
                )

                assert len(result) == 3
                assert result[0]["content"] == "First"
                assert result[1]["content"] == "Second"
                assert result[2]["content"] == "Third"


class TestMemoryServiceIntegration:
    """Integration tests for memory service."""

    @pytest.mark.asyncio
    async def test_full_cache_lifecycle(self):
        """Test complete cache lifecycle: miss → hit → invalidate → miss."""
        service = MemoryService(cache_ttl=3600)
        conversation_id = "conv-lifecycle"

        messages = [
            Message(
                id="msg-1",
                conversation_id=conversation_id,
                remetente="user",
                conteudo="Hello",
                timestamp=datetime.utcnow(),
            ),
        ]

        db = AsyncMock(spec=AsyncSession)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = messages
        db.execute = AsyncMock(return_value=mock_result)

        call_count = 0

        async def count_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_result

        db.execute = AsyncMock(side_effect=count_calls)

        with patch.object(service.redis, "get") as mock_get:
            with patch.object(service.redis, "setex") as mock_setex:
                with patch.object(service.redis, "delete") as mock_delete:
                    # First call - cache miss
                    mock_get.return_value = None
                    result1 = await service.get_conversation_history(
                        conversation_id, db, use_cache=True
                    )
                    assert len(result1) == 1
                    assert call_count == 1

                    # Second call - cache hit
                    mock_get.return_value = json.dumps(result1)
                    result2 = await service.get_conversation_history(
                        conversation_id, db, use_cache=True
                    )
                    assert result2 == result1
                    assert call_count == 1  # No new DB call

                    # Invalidate cache
                    mock_delete.return_value = 1
                    invalidated = await service.invalidate_cache(conversation_id)
                    assert invalidated is True

                    # Third call - cache miss again
                    mock_get.return_value = None
                    result3 = await service.get_conversation_history(
                        conversation_id, db, use_cache=True
                    )
                    assert call_count == 2  # New DB call
