"""LLM service for Claude integration."""

from typing import List, Optional, Iterator, Tuple
from datetime import datetime, timedelta
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError
from app.config import settings
from app.utils.logger import logger
from app.utils.exceptions import ValidationException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Agent, Message, Conversation
import asyncio


class LLMService:
    """Service for managing Claude LLM interactions."""

    def __init__(self):
        """Initialize LLM service with Anthropic client."""
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.max_calls_per_minute = 60
        self.max_tokens_per_minute = 40000
        self.call_timestamps: List[datetime] = []
        self.token_timestamps: List[Tuple[datetime, int]] = []

    async def generate_response(
        self,
        agent: Agent,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
    ) -> Tuple[str, dict]:
        """
        Generate response using Claude with context.

        Args:
            agent: Agent model instance
            user_message: Current user message
            conversation_history: Previous messages for context

        Returns:
            Tuple of (response_text, token_usage_dict)

        Raises:
            ValidationException: Rate limit or validation errors
        """
        try:
            # Check rate limits
            self._check_rate_limits()

            # Build messages array
            messages = self._build_messages(conversation_history, user_message)

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=agent.max_tokens or settings.max_tokens,
                temperature=agent.temperatura or settings.temperature,
                system=agent.system_prompt,
                messages=messages,
            )

            # Extract response and token usage
            response_text = response.content[0].text
            token_usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }

            # Track usage
            self._track_usage(token_usage["total_tokens"])

            logger.info(
                f"✅ Claude response generated for agent {agent.id} "
                f"(tokens: {token_usage['total_tokens']})"
            )

            return response_text, token_usage

        except RateLimitError as e:
            logger.warning(f"⚠️ Rate limit exceeded: {e}")
            raise ValidationException("Rate limit exceeded. Please try again in a moment.")
        except APIConnectionError as e:
            logger.error(f"❌ API connection error: {e}")
            raise ValidationException("Connection error. Please try again.")
        except APIError as e:
            logger.error(f"❌ API error: {e}")
            raise ValidationException(f"API error: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            raise

    def stream_response(
        self,
        agent: Agent,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
    ) -> Iterator[str]:
        """
        Stream response from Claude (generator).

        Args:
            agent: Agent model instance
            user_message: Current user message
            conversation_history: Previous messages for context

        Yields:
            Text chunks from Claude response
        """
        try:
            # Check rate limits
            self._check_rate_limits()

            # Build messages array
            messages = self._build_messages(conversation_history, user_message)

            # Stream from Claude API
            with self.client.messages.stream(
                model=self.model,
                max_tokens=agent.max_tokens or settings.max_tokens,
                temperature=agent.temperatura or settings.temperature,
                system=agent.system_prompt,
                messages=messages,
            ) as stream:
                total_tokens = 0
                for text in stream.text_stream:
                    yield text

                # Track usage from final message
                if hasattr(stream, "get_final_message"):
                    final = stream.get_final_message()
                    total_tokens = (
                        final.usage.input_tokens + final.usage.output_tokens
                    )
                    self._track_usage(total_tokens)
                    logger.info(
                        f"✅ Claude stream completed for agent {agent.id} "
                        f"(tokens: {total_tokens})"
                    )

        except RateLimitError as e:
            logger.warning(f"⚠️ Rate limit exceeded: {e}")
            raise ValidationException("Rate limit exceeded.")
        except Exception as e:
            logger.error(f"❌ Error streaming response: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using Claude's tokenizer.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        try:
            # Rough approximation: ~4 chars per token
            # For accurate counting, we'd need beta_messages_2024_12_19 with token counting
            # But for MVP, this approximation works
            token_count = len(text) // 4
            return max(1, token_count)
        except Exception as e:
            logger.error(f"❌ Error counting tokens: {e}")
            return len(text) // 4

    async def get_conversation_history(
        self,
        conversation_id: str,
        db: AsyncSession,
        limit: int = 10,
    ) -> List[dict]:
        """
        Retrieve conversation history from database.

        Args:
            conversation_id: Conversation ID
            db: Database session
            limit: Maximum number of messages to retrieve

        Returns:
            List of conversation messages
        """
        try:
            result = await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.timestamp.desc())
                .limit(limit)
            )
            messages = result.scalars().all()

            # Reverse to get chronological order
            messages.reverse()

            return [
                {"role": msg.remetente, "content": msg.conteudo}
                for msg in messages
            ]
        except Exception as e:
            logger.error(f"❌ Error retrieving conversation history: {e}")
            return []

    def _build_messages(
        self,
        conversation_history: Optional[List[dict]],
        user_message: str,
    ) -> List[dict]:
        """
        Build messages array for Claude API.

        Args:
            conversation_history: Previous messages
            user_message: Current user message

        Returns:
            Formatted messages for Claude
        """
        messages = []

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    def _check_rate_limits(self) -> None:
        """
        Check if rate limits are exceeded.

        Raises:
            ValidationException: If rate limit exceeded
        """
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)

        # Check calls per minute
        recent_calls = [ts for ts in self.call_timestamps if ts > one_minute_ago]
        if len(recent_calls) >= self.max_calls_per_minute:
            raise ValidationException(
                f"Rate limit exceeded: {self.max_calls_per_minute} calls per minute"
            )

        # Check tokens per minute
        recent_tokens = sum(
            tokens for ts, tokens in self.token_timestamps if ts > one_minute_ago
        )
        if recent_tokens >= self.max_tokens_per_minute:
            raise ValidationException(
                f"Rate limit exceeded: {self.max_tokens_per_minute} tokens per minute"
            )

    def _track_usage(self, total_tokens: int) -> None:
        """
        Track API usage for rate limiting.

        Args:
            total_tokens: Total tokens used in this request
        """
        now = datetime.utcnow()
        self.call_timestamps.append(now)
        self.token_timestamps.append((now, total_tokens))

        # Clean up old entries (older than 2 minutes)
        two_minutes_ago = now - timedelta(minutes=2)
        self.call_timestamps = [ts for ts in self.call_timestamps if ts > two_minutes_ago]
        self.token_timestamps = [
            (ts, tokens) for ts, tokens in self.token_timestamps if ts > two_minutes_ago
        ]

        logger.debug(
            f"📊 Usage tracked: {len(self.call_timestamps)} calls, "
            f"{sum(t[1] for t in self.token_timestamps)} tokens in last minute"
        )

    def get_rate_limit_status(self) -> dict:
        """
        Get current rate limit status.

        Returns:
            Dict with usage statistics
        """
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)

        recent_calls = len([ts for ts in self.call_timestamps if ts > one_minute_ago])
        recent_tokens = sum(
            tokens for ts, tokens in self.token_timestamps if ts > one_minute_ago
        )

        return {
            "calls_used": recent_calls,
            "calls_limit": self.max_calls_per_minute,
            "tokens_used": recent_tokens,
            "tokens_limit": self.max_tokens_per_minute,
            "calls_remaining": max(0, self.max_calls_per_minute - recent_calls),
            "tokens_remaining": max(0, self.max_tokens_per_minute - recent_tokens),
        }


# Global instance
llm_service = LLMService()
