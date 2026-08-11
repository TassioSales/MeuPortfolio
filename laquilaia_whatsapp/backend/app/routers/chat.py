"""Chat and LLM interaction routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.models.llm_models import (
    MessageRequest,
    MessageResponse,
    TokenUsage,
    ChatHistoryMessage,
    ChatHistoryResponse,
)
from app.db.models import Agent, Conversation, Message
from app.services.llm_service import llm_service
from app.utils.auth_middleware import get_current_user
from app.utils.exceptions import ValidationException, NotFoundException
from app.utils.logger import logger
from sqlalchemy import select
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/v1/agents",
    tags=["chat"],
)

# Telefone usado pelas conversas criadas pelo playground, para distingui-las
# das conversas reais vindas do WhatsApp.
TEST_PHONE_NUMBER = "test_api"


async def _get_agent_or_404(agent_id: str, user_id: str, db: AsyncSession) -> Agent:
    """Fetch an agent owned by the user, or raise NotFound."""
    result = await db.execute(
        select(Agent).where((Agent.id == agent_id) & (Agent.user_id == user_id))
    )
    agent = result.scalars().first()

    if not agent:
        logger.warning(f"⚠️ Agent not found: {agent_id} (user: {user_id})")
        raise NotFoundException("Agent")

    return agent


async def _find_test_conversation(agent_id: str, db: AsyncSession) -> Conversation | None:
    """Return the playground conversation of an agent, if it already exists."""
    result = await db.execute(
        select(Conversation).where(
            (Conversation.agent_id == agent_id)
            & (Conversation.phone_number == TEST_PHONE_NUMBER)
        )
    )
    return result.scalars().first()


async def _get_or_create_test_conversation(
    agent_id: str, db: AsyncSession
) -> Conversation:
    """Reuse the agent's playground conversation, creating it on first use."""
    conversation = await _find_test_conversation(agent_id, db)

    if conversation is None:
        conversation = Conversation(
            agent_id=agent_id,
            phone_number=TEST_PHONE_NUMBER,
            status="ativa",
        )
        db.add(conversation)
        await db.flush()  # Get conversation ID without committing

    return conversation


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
            # A conversa de teste é reaproveitada, não recriada: existe uma
            # constraint única (agent_id, phone_number) e o telefone aqui é
            # fixo, então um segundo INSERT com o mesmo agente estouraria.
            conversation = await _get_or_create_test_conversation(agent_id, db)

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
            conversation_id=conversation.id,
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
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in chat: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat message",
        )


@router.get("/{agent_id}/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    agent_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Return the playground conversation history, oldest message first."""
    try:
        await _get_agent_or_404(agent_id, user_id, db)

        conversation = await _find_test_conversation(agent_id, db)
        if conversation is None:
            # Agente que ainda não foi testado: histórico vazio, não é erro.
            return ChatHistoryResponse(conversation_id=None, messages=[])

        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.timestamp)
        )

        return ChatHistoryResponse(
            conversation_id=conversation.id,
            messages=[
                ChatHistoryMessage(
                    id=message.id,
                    remetente=message.remetente,
                    conteudo=message.conteudo,
                    timestamp=message.timestamp,
                )
                for message in result.scalars().all()
            ],
        )

    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting chat history",
        )


@router.delete("/{agent_id}/chat/history", status_code=status.HTTP_200_OK)
async def reset_chat_history(
    agent_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Clear the playground conversation.

    Apaga as mensagens e a própria conversa: como o telefone de teste é fixo,
    manter a conversa vazia serviria só para ocupar a constraint única.
    """
    try:
        await _get_agent_or_404(agent_id, user_id, db)

        conversation = await _find_test_conversation(agent_id, db)
        if conversation is None:
            return {"detail": "No test conversation to reset", "deleted": 0}

        result = await db.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        messages = result.scalars().all()
        for message in messages:
            await db.delete(message)

        await db.delete(conversation)
        await db.commit()

        logger.info(f"🧹 Playground conversation reset: agent={agent_id}")
        return {"detail": "Test conversation reset", "deleted": len(messages)}

    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error resetting chat history: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting chat history",
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
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
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

        # Com o user_id, e não sem: sem ele a resposta vinha do balde
        # compartilhado e mostrava sempre zero, qualquer que fosse o uso da
        # conta — o limite é por conta desde que deixou de ser do processo.
        return await llm_service.get_rate_limit_status(user_id)

    except NotFoundException as e:
        logger.warning(f"⚠️ {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.detail,
        )
    # Erros HTTP deliberados (404, 400, 403...) precisam subir intactos:
    # o catch-all abaixo os transformaria em 500.
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting rate limit status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving rate limit status",
        )


# ========== PAUSA HUMANA (Fase 16) ==========
#
# Router próprio: o `router` deste módulo tem prefixo /api/v1/agents, o que
# faria a URL virar /agents/conversations/... — a conversa não é subrecurso
# do agente nesta operação.

conversations_router = APIRouter(
    prefix="/api/v1/conversations",
    tags=["conversations"],
)

class ConversationStatusResponse(BaseModel):
    """Estado de automação de uma conversa."""
    conversation_id: str
    status: str
    ia_ativa: bool


async def _get_owned_conversation(
    conversation_id: str, user_id: str, db: AsyncSession
) -> Conversation:
    """
    Fetch a conversation, ensuring it belongs to an agent of this user.

    O join com Agent é o que impede um usuário pausar a conversa de outro:
    sem ele, bastaria adivinhar o id.
    """
    result = await db.execute(
        select(Conversation)
        .join(Agent, Conversation.agent_id == Agent.id)
        .where((Conversation.id == conversation_id) & (Agent.user_id == user_id))
    )
    conversation = result.scalars().first()

    if not conversation:
        raise NotFoundException("Conversation")

    return conversation


async def _set_conversation_status(
    conversation_id: str, user_id: str, novo_status: str, db: AsyncSession
) -> ConversationStatusResponse:
    conversation = await _get_owned_conversation(conversation_id, user_id, db)
    conversation.status = novo_status
    await db.commit()

    logger.info(f"🔄 Conversa {conversation_id} agora está '{novo_status}'")
    return ConversationStatusResponse(
        conversation_id=conversation.id,
        status=novo_status,
        ia_ativa=novo_status != "pausada",
    )


@conversations_router.post(
    "/{conversation_id}/pause",
    response_model=ConversationStatusResponse,
)
async def pause_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Hand the conversation over to a human.

    As mensagens do cliente continuam sendo registradas; a IA é que para de
    responder, para operador e agente não falarem juntos com o cliente.
    """
    try:
        return await _set_conversation_status(conversation_id, user_id, "pausada", db)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao pausar conversa: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error pausing conversation",
        )


@conversations_router.post(
    "/{conversation_id}/resume",
    response_model=ConversationStatusResponse,
)
async def resume_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Give the conversation back to the AI."""
    try:
        return await _set_conversation_status(conversation_id, user_id, "ativa", db)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao retomar conversa: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resuming conversation",
        )


@conversations_router.get(
    "/{conversation_id}/status",
    response_model=ConversationStatusResponse,
)
async def get_conversation_status(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Whether the AI is answering this conversation."""
    try:
        conversation = await _get_owned_conversation(conversation_id, user_id, db)
        return ConversationStatusResponse(
            conversation_id=conversation.id,
            status=conversation.status,
            ia_ativa=conversation.status != "pausada",
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao consultar conversa: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting conversation status",
        )
