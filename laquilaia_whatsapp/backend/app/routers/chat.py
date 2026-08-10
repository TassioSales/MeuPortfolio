"""Chat and LLM interaction routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.models.llm_models import MessageRequest, MessageResponse, TokenUsage, ChatHistoryRequest
from app.db.models import Agent, Conversation, Message
from app.services.llm_service import llm_service
from app.utils.auth_middleware import get_current_user
from app.utils.exceptions import ValidationException, NotFoundException
from app.utils.logger import logger
from sqlalchemy import select
from datetime import datetime

router = APIRouter(
    prefix="/api/v1/agents",
    tags=["chat"],
)


@router.post("/{agent_id}/chat", response_model=MessageResponse)
async def chat_with_agent(
    agent_id: str,
    request: MessageRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Chat with an agent and get AI-generated response.

    This endpoint:
    1. Verifies agent ownership
    2. Retrieves or creates conversation
    3. Gets conversation history for context
    4. Calls Claude with agent's system prompt
    5. Saves conversation and returns response
    """
    try:
        # Verify agent exists and is owned by user
        result = await db.execute(
            select(Agent).where(
                (Agent.id == agent_id) & (Agent.user_id == user_id)
            )
        )
        agent = result.scalars().first()

        if not agent:
            logger.warning(f"⚠️ Agent not found: {agent_id} (user: {user_id})")
            raise NotFoundException("Agent")

        # Get or create conversation
        conversation_id = request.conversation_id
        if conversation_id:
            result = await db.execute(
                select(Conversation).where(
                    (Conversation.id == conversation_id) &
                    (Conversation.agent_id == agent_id)
                )
            )
            conversation = result.scalars().first()
            if not conversation:
                raise NotFoundException("Conversation")
        else:
            # Create new conversation (phone is optional for API testing)
            conversation = Conversation(
                agent_id=agent_id,
                phone_number="test_api",
                status="ativa",
            )
            db.add(conversation)
            await db.flush()  # Get conversation ID without committing

        # Get conversation history for context
        history = await llm_service.get_conversation_history(
            conversation.id, db, limit=5
        )

        # Generate response from Claude
        response_text, token_usage = await llm_service.generate_response(
            agent=agent,
            user_message=request.message,
            conversation_history=history,
        )

        # Save user message
        user_msg = Message(
            conversation_id=conversation.id,
            remetente="user",
            conteudo=request.message,
            timestamp=datetime.utcnow(),
        )
        db.add(user_msg)

        # Save assistant response
        assistant_msg = Message(
            conversation_id=conversation.id,
            remetente="assistant",
            conteudo=response_text,
            timestamp=datetime.utcnow(),
        )
        db.add(assistant_msg)

        # Update conversation timestamp
        conversation.data_ultima_msg = datetime.utcnow()

        await db.commit()

        logger.info(
            f"✅ Chat message processed: agent={agent_id}, "
            f"conversation={conversation.id}, tokens={token_usage['total_tokens']}"
        )

        return MessageResponse(
            response=response_text,
            tokens_used=TokenUsage(
                input_tokens=token_usage["input_tokens"],
                output_tokens=token_usage["output_tokens"],
                total_tokens=token_usage["total_tokens"],
            ),
            timestamp=datetime.utcnow(),
            model=llm_service.model,
        )

    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.detail,
        )
    except ValidationException as e:
        logger.warning(f"⚠️ Validation error: {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.detail,
        )
    except Exception as e:
        logger.error(f"❌ Error in chat: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat message",
        )


@router.post("/{agent_id}/test", response_model=MessageResponse)
async def test_agent(
    agent_id: str,
    request: MessageRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Quick test endpoint for agent without saving conversation.

    Useful for:
    - Testing agent prompts before deployment
    - Verifying system prompt behavior
    - Development and debugging
    - Does NOT save conversation history
    """
    try:
        # Verify agent exists and is owned by user
        result = await db.execute(
            select(Agent).where(
                (Agent.id == agent_id) & (Agent.user_id == user_id)
            )
        )
        agent = result.scalars().first()

        if not agent:
            logger.warning(f"⚠️ Agent not found: {agent_id} (user: {user_id})")
            raise NotFoundException("Agent")

        # Generate response without conversation history
        response_text, token_usage = await llm_service.generate_response(
            agent=agent,
            user_message=request.message,
            conversation_history=None,  # No history for test
        )

        logger.info(
            f"✅ Agent test: agent={agent_id}, tokens={token_usage['total_tokens']}"
        )

        return MessageResponse(
            response=response_text,
            tokens_used=TokenUsage(
                input_tokens=token_usage["input_tokens"],
                output_tokens=token_usage["output_tokens"],
                total_tokens=token_usage["total_tokens"],
            ),
            timestamp=datetime.utcnow(),
            model=llm_service.model,
        )

    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.detail,
        )
    except ValidationException as e:
        logger.warning(f"⚠️ Validation error: {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.detail,
        )
    except Exception as e:
        logger.error(f"❌ Error in agent test: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error testing agent",
        )


@router.get("/{agent_id}/rate-limit-status")
async def get_rate_limit_status(
    agent_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get current rate limit status for LLM API.

    Returns:
    - calls_used: Number of API calls in last minute
    - calls_limit: Maximum calls per minute
    - tokens_used: Tokens used in last minute
    - tokens_limit: Maximum tokens per minute
    - calls_remaining: Calls left in current window
    - tokens_remaining: Tokens left in current window
    """
    try:
        # Verify agent exists and is owned by user
        result = await db.execute(
            select(Agent).where(
                (Agent.id == agent_id) & (Agent.user_id == user_id)
            )
        )
        agent = result.scalars().first()

        if not agent:
            raise NotFoundException("Agent")

        return llm_service.get_rate_limit_status()

    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.detail,
        )
    except Exception as e:
        logger.error(f"❌ Error getting rate limit status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving rate limit status",
        )
